"""P0-8B: future-year PDF page proof + SQL provenance + DSL/rate safety.

All example pages and future-year prices are synthetic code fixtures.
No test claims to contain future or approved Turkish legal entitlements.
"""
from __future__ import annotations

import hashlib

import pymupdf
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from tarim_destek_rag.auto_updater.grounding_repository import (
    load_grounded_sentence,
    resolve_archived_pdf,
    stage_evidence,
)
from tarim_destek_rag.auto_updater.pdf_grounding import PDFGroundingEngine
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.models import (
    SentenceBoundingBoxModel,
    SourceDocumentModel,
    SourceModel,
)
from tarim_destek_rag.rules.dynamic_engine import DynamicRateCatalog
from tarim_destek_rag.updates.pdf_evidence import UnverifiableEvidence

QUOTE = "Synthetic 2030 example: qualified parcels satisfy this demonstration condition."
SOURCE = "https://www.resmigazete.gov.tr/eskiler/2030/01/example-regulation.pdf"
SOURCE_ID = "SYNTHETIC-RG-2030"


@pytest.fixture
def source_pdf(tmp_path):
    pdf = pymupdf.open()
    pdf.new_page(width=595, height=842)
    page = pdf.new_page(width=595, height=842)
    page.insert_text((50, 160), QUOTE, fontsize=10)
    original = pdf.tobytes()
    pdf.close()
    sha = hashlib.sha256(original).hexdigest()
    originals = tmp_path / "originals"
    originals.mkdir()
    (originals / (sha + ".pdf")).write_bytes(original)
    return tmp_path, original, sha


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add(SourceModel(
            source_id=SOURCE_ID, url=SOURCE, title="Synthetic legal test PDF",
            authority="OFFICIAL_GAZETTE", content_type="PDF", active=True,
        ))
        db.commit()
        yield db
    engine.dispose()


def stage(session, source_pdf, year=2030):
    folder, raw, sha = source_pdf
    return stage_evidence(
        session, archive_root=folder, source_id=SOURCE_ID,
        production_year=year, sha256=sha,
        original_url=SOURCE, page_number=2,
        exact_quote=QUOTE, article="Madde TEST", paragraph="1",
    )


def candidate(sentence, sha, year=2030):
    return {
        "schema_version": 1, "program_key": "BASIC_SUPPORT",
        "crop_code": "BUGDAY", "production_year": year,
        "province": "*", "district": "*",
        "base_coefficient": "100.00",
        "category_multiplier": "1.2500",
        "official_unit_amount": "125.00",
        "unit": "TRY/da", "effective_from": f"{year}-01-01",
        "effective_to": None, "source_document_sha256": sha,
        "source_sentence_id": sentence.id, "review_status": "DRAFT",
        "conditions": {"all_of": [
            {"field": "cks_registered", "op": "eq", "value": True},
            {"field": "crop_code", "op": "in", "value": ["BUGDAY"]},
        ]},
    }


def test_layout_bound_pdf_page_with_png_and_webp(source_pdf):
    folder, raw, sha = source_pdf
    ev = PDFGroundingEngine.ground(
        raw, document_sha256=sha, page_number=2,
        exact_quote=QUOTE, article="Madde TEST",
    )
    assert ev.page_number == 2
    assert len(ev.boxes) >= 1
    assert ev.to_dict()["article"] == "Madde TEST"
    for fmt in ("png", "webp"):
        image, mime = PDFGroundingEngine.render_highlighted_page(
            raw, ev, dpi=144, image_format=fmt,
        )
        assert len(image) > 1000
        assert mime == f"image/{fmt}"
        if fmt == "png":
            assert image[:8] == b"\x89PNG\r\n\x1a\n"
    assert resolve_archived_pdf(folder, sha) == raw


def test_pdf_absent_line_wrong_page_and_changed_bytes_fail_closed(source_pdf):
    _, raw, sha = source_pdf
    for bad_page, text in [(1, QUOTE), (2, "This sentence is fabricated and absent.")]:
        with pytest.raises(UnverifiableEvidence):
            PDFGroundingEngine.ground(
                raw, document_sha256=sha,
                page_number=bad_page, exact_quote=text,
            )
    with pytest.raises(UnverifiableEvidence):
        PDFGroundingEngine.ground(
            raw + b"alteration", document_sha256=sha,
            page_number=2, exact_quote=QUOTE,
        )


def test_original_sentence_sql_archive_pinned_and_idempotent(session, source_pdf):
    row = stage(session, source_pdf)
    assert stage(session, source_pdf).id == row.id
    assert session.scalar(select(SourceDocumentModel)).production_year == 2030
    assert session.scalar(select(SentenceBoundingBoxModel)).exact_text == QUOTE
    quote, document, grounded, original = load_grounded_sentence(
        session, archive_root=source_pdf[0], evidence_id=row.id, year=2030,
    )
    assert document.original_url == SOURCE
    assert grounded.page_number == 2
    assert original == source_pdf[1]
    with pytest.raises(LookupError):
        load_grounded_sentence(
            session, archive_root=source_pdf[0], evidence_id=row.id, year=2029,
        )


def test_same_official_pdf_can_apply_to_two_production_years(session, source_pdf):
    first = stage(session, source_pdf, year=2029)
    second = stage(session, source_pdf, year=2030)
    assert first.id != second.id
    assert session.scalars(select(SourceDocumentModel)).all().__len__() == 2


def test_corrupted_archived_original_invalidates_saved_page(session, source_pdf):
    row = stage(session, source_pdf)
    archive = source_pdf[0] / "originals" / (source_pdf[2] + ".pdf")
    archive.write_bytes(b"%PDF-FORGED")
    with pytest.raises(ValueError, match="altered"):
        load_grounded_sentence(
            session, archive_root=source_pdf[0], evidence_id=row.id, year=2030,
        )


def test_draft_dynamic_coefficient_writes_no_payment(session, source_pdf):
    sentence = stage(session, source_pdf)
    d = candidate(sentence, source_pdf[2])
    row = DynamicRateCatalog.stage(session, d)
    assert row.production_year == 2030
    assert row.review_status == "DRAFT"
    assert row.proposed_unit_amount == 125
    assert DynamicRateCatalog.stage(session, d).id == row.id
    preview = DynamicRateCatalog.preview(
        d, year=2030, facts={"cks_registered": True, "crop_code": "BUGDAY"}
    )
    assert preview.status == "REVIEW"
    assert preview.payable_amount is None
    assert preview.proposed_unit_amount == 125
    assert DynamicRateCatalog.preview(
        d, year=2029, facts={"cks_registered": True, "crop_code": "BUGDAY"}
    ).proposed_unit_amount is None


def test_unproven_rule_or_crop_fails_closed(session, source_pdf):
    sentence = stage(session, source_pdf)
    d = candidate(sentence, source_pdf[2])
    incomplete = DynamicRateCatalog.preview(
        d, year=2030, facts={"crop_code": "BUGDAY"}
    )
    assert incomplete.status == "REVIEW"
    assert incomplete.payable_amount is None
    crop_wrong = DynamicRateCatalog.preview(
        d, year=2030, facts={"cks_registered": True, "crop_code": "MISIR"}
    )
    assert crop_wrong.status == "REVIEW"
    assert crop_wrong.proposed_unit_amount is None


@pytest.mark.parametrize("change", [
    lambda x: x.update(review_status="VERIFIED"),
    lambda x: x.update(base_coefficient="110.00"),
    lambda x: x.update(official_unit_amount="0.00"),
    lambda x: x.update(official_unit_amount="125.99"),
    lambda x: x.update(effective_from="2026-01-01"),
    lambda x: x.update(source_document_sha256="0"*64),
    lambda x: x.update(conditions={"all_of": [{"field": "eval", "op": "eq", "value": True}]}),
    lambda x: x.update(conditions={"any_of": [{"field": "crop_code", "op": "eq", "value": "BUGDAY"}]}),
])
def test_untrusted_dynamic_json_cannot_invent_support_amount_or_rule(
    session, source_pdf, change
):
    sentence = stage(session, source_pdf)
    data = candidate(sentence, source_pdf[2])
    change(data)
    if data["source_document_sha256"] == "0"*64:
        with pytest.raises(ValueError, match="PDF clause"):
            DynamicRateCatalog.stage(session, data)
    else:
        with pytest.raises(ValueError):
            DynamicRateCatalog.validate(data)


def test_stored_candidate_cannot_be_silently_repriced(session, source_pdf):
    sentence = stage(session, source_pdf)
    data = candidate(sentence, source_pdf[2])
    DynamicRateCatalog.stage(session, data)
    altered = dict(data, base_coefficient="50.00",
                   category_multiplier="2.5000")
    with pytest.raises(ValueError, match="Conflicting"):
        DynamicRateCatalog.stage(session, altered)
