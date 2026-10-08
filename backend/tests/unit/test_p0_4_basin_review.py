"""P0-4 official basin list: syntax, staging and evidence-gated tri-state decisions."""

from datetime import datetime, timezone
from hashlib import sha256
from decimal import Decimal
import json

import pytest
from sqlalchemy import create_engine, select
from backend.tests.legal_approval_testkit import sign_subject
from sqlalchemy.orm import Session

from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.models import (
    ReviewedBasinSnapshotModel, SourceModel, SourceVersionModel,
)
from tarim_destek_rag.database.repository import BasinRepository
from tarim_destek_rag.models.farmer_parcel import FarmerProfile, Parcel
from tarim_destek_rag.normalization.basin_2026 import (
    BASIN_SOURCE_URL, BASIN_SOURCE_ID, PINNED_BASIN_PDF_SHA256,
    stage_basin_districts, validate_basin_catalog,
)
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.rules.rules_impl import PlannedProductionRule


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def register_synthetic_snapshot(session, *, approve=False, crops=None, starred=True, monkeypatch=None):
    source = SourceModel(
        source_id=BASIN_SOURCE_ID, url=BASIN_SOURCE_URL,
        title="synthetic complete legal source for unit tests only",
        authority="MINISTRY_OF_AGRICULTURE", content_type="PDF", active=True,
    )
    session.add(source)
    session.flush()
    version = SourceVersionModel(
        source_id=source.source_id,
        content_hash=PINNED_BASIN_PDF_SHA256, version=1,
        detected_at="2026-10-08T10:00:00Z", effective_from="2026-01-01",
        effective_to="2027-12-31", superseded=False,
    )
    session.add(version)
    session.flush()
    snapshot = ReviewedBasinSnapshotModel(
        province="KONYA", district="KARATAY", production_year=2026,
        crop_codes_json=json.dumps(crops or ["BUĞDAY", "MISIR_DANE"]),
        drip_required_for_grain_maize=starred,
        document_page=53, source_version_id=version.id,
        review_status="VERIFIED" if approve else "DRAFT",
        coverage_complete=approve,
        reviewed_by="SYNTHETIC_TEST" if approve else None,
        reviewed_at=datetime.now(timezone.utc) if approve else None,
        review_reference="NOT_AN_ACTUAL_SIGNOFF" if approve else None,
    )
    session.add(snapshot)
    session.commit()
    if approve:
        if monkeypatch is None:
            raise ValueError("Signed approval fixture requires monkeypatch")
        sign_subject(session, snapshot, monkeypatch)
    return snapshot


def make_parcel(crop="MISIR_DANE", drip=None):
    return Parcel(crop=crop, production_year=2026, area_da=Decimal("12.4"),
                  drip_irrigation=drip)


def test_legacy_or_draft_missing_is_unknown_not_unsuitable(session):
    repo = BasinRepository(session)
    assert repo.evaluate_official_crop("KONYA", "KARATAY", "BUĞDAY", 2026).outcome == "UNKNOWN"
    register_synthetic_snapshot(session, approve=False)
    assert repo.evaluate_official_crop("KONYA", "KARATAY", "BUĞDAY", 2026).outcome == "UNKNOWN"


def test_approved_complete_district_can_prove_both_membership_and_nonmembership(session, monkeypatch):
    register_synthetic_snapshot(session, approve=True, monkeypatch=monkeypatch)
    repo = BasinRepository(session)
    wheat = repo.evaluate_official_crop("KONYA", "KARATAY", "BUĞDAY", 2026)
    assert wheat.outcome == "LISTED"
    assert wheat.source_version_id is not None and wheat.document_page == 53
    assert wheat.drip_irrigation_required is False
    corn = repo.evaluate_official_crop("KONYA", "KARATAY", "MISIR_DANE", 2026)
    assert corn.outcome == "LISTED"
    assert corn.drip_irrigation_required is True
    assert repo.evaluate_official_crop("KONYA", "KARATAY", "PATATES", 2026).outcome == "NOT_LISTED"
    assert repo.evaluate_official_crop("KONYA", "KARATAY", "PAMUK", 2026).outcome == "UNKNOWN"
    assert repo.evaluate_official_crop("KONYA", "SELÇUKLU", "BUĞDAY", 2026).outcome == "UNKNOWN"
    assert repo.evaluate_official_crop("KONYA", "KARATAY", "BUĞDAY", 2025).outcome == "UNKNOWN"


@pytest.mark.parametrize("drip,expected,missing", [
    (None, EligibilityStatusEnum.REVIEW, "verified_water_scope"),
    (False, EligibilityStatusEnum.REVIEW, "verified_water_scope"),
    (True, EligibilityStatusEnum.REVIEW, "verified_water_scope"),
])
def test_starred_grain_maize_condition_cannot_auto_grant_payment(
    session, drip, expected, missing, monkeypatch
):
    register_synthetic_snapshot(session, approve=True, monkeypatch=monkeypatch)
    farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    result = PlannedProductionRule().evaluate(farmer, make_parcel(drip=drip), session)
    assert result.status == expected
    if missing:
        assert missing in result.missing_fields
    # 2025/42 repealed the 2026 drip exception; no drip value can
    # establish maize entitlement without signed 2026 water designation.
    assert not result.failed_checks
    assert "drip_irrigation" not in result.missing_fields
    assert "verified_support_rate" in result.missing_fields


def test_source_superseded_or_invalid_snapshot_fails_closed(session, monkeypatch):
    snapshot = register_synthetic_snapshot(session, approve=True, monkeypatch=monkeypatch)
    version = snapshot.source_version
    version.superseded = True
    session.commit()
    assert BasinRepository(session).evaluate_official_crop(
        "KONYA", "KARATAY", "BUĞDAY", 2026
    ).outcome == "UNKNOWN"
    version.superseded = False
    version.content_hash = "unverified"
    session.commit()
    assert BasinRepository(session).evaluate_official_crop(
        "KONYA", "KARATAY", "BUĞDAY", 2026
    ).outcome == "UNKNOWN"


def test_official_parser_extracts_starred_district_and_subtypes():
    from scripts.extract_2026_basin_pdf import parse_table_rows

    tables = [[
        ["HAVZA ADI", "PLANLAMAYA KONU HAVZA ÜRÜN DESENİ"],
        ["Konya/Karatay *", "Arpa, Buğday, Mısır (Dane), Yem Bitkileri"],
        ["Adana/Aladağ", "Arpa, Ayçiçeği (Yağlık), Buğday, Nohut"],
    ]]
    rows, issues = parse_table_rows(tables, 53)
    assert issues == []
    assert len(rows) == 2
    assert rows[0]["starred_drip_maize_condition"] is True
    assert "MISIR_DANE" in rows[0]["crop_codes"]
    assert "YEM_BITKILERI_GROUP" in rows[0]["crop_codes"]
    assert rows[1]["starred_drip_maize_condition"] is False


def test_unknown_crop_label_quarantined_by_pdf_parser():
    from scripts.extract_2026_basin_pdf import parse_table_rows

    rows, errors = parse_table_rows([[["Konya/Karatay", "Unrecognized Exotic Crop"]]], 53)
    assert not rows
    assert len(errors) == 1


def _synthetic_complete_catalog(pdf_bytes):
    rows = [
        {
            "province": f"TESTPROVINCE{n}", "district": f"DISTRICT{j}",
            "crop_codes": ["ARPA", "BUĞDAY"],
            "starred_drip_maize_condition": False,
            "review_status": "DRAFT",
            "complete_row_verified_by_human": False,
            "source_page": n + 1,
        }
        for n in range(80) for j in range(11)
    ]
    return {
        "schema_version": 1,
        "production_years": [2026, 2027],
        "source_url": BASIN_SOURCE_URL,
        "original_pdf_sha256": sha256(pdf_bytes).hexdigest(),
        "approval": "DRAFT_REQUIRES_HUMAN_ROW_AND_FOOTNOTE_REVIEW",
        "page_count": 81, "district_count": len(rows), "province_count": 80,
        "districts": rows,
    }


def test_import_requires_official_pdf_bytes_and_preserves_draft(session, tmp_path, monkeypatch):
    # Explicit synthetic PDF-like bytes; source content is NEVER legally approved.
    pdf = b"%PDF-SYNTHETIC_TEST_ONLY"
    monkeypatch.setattr(
        "tarim_destek_rag.normalization.basin_2026.PINNED_BASIN_PDF_SHA256",
        sha256(pdf).hexdigest(),
    )
    catalog = _synthetic_complete_catalog(pdf)
    datafile = tmp_path / "staged.json"
    pdffile = tmp_path / "source.pdf"
    datafile.write_text(json.dumps(catalog), encoding="utf-8")
    assert validate_basin_catalog(catalog)
    assert stage_basin_districts(session, datafile) == 880
    assert session.scalars(select(ReviewedBasinSnapshotModel)).all() == []
    with pytest.raises(ValueError, match="mandatory"):
        stage_basin_districts(session, datafile, apply=True)
    pdffile.write_bytes(b"%PDF-INVALID")
    with pytest.raises(ValueError, match="do not match"):
        stage_basin_districts(session, datafile, apply=True, pdf_path=pdffile)
    pdffile.write_bytes(pdf)
    assert stage_basin_districts(session, datafile, apply=True, pdf_path=pdffile) == 1760
    session.commit()
    assert stage_basin_districts(session, datafile, apply=True, pdf_path=pdffile) == 0
    all_rows = session.scalars(select(ReviewedBasinSnapshotModel)).all()
    assert len(all_rows) == 1760
    assert all(r.review_status == "DRAFT" and not r.coverage_complete for r in all_rows)
    assert BasinRepository(session).evaluate_official_crop(
        "TESTPROVINCE0", "DISTRICT0", "BUĞDAY", 2026
    ).outcome == "UNKNOWN"


def test_partial_national_extraction_is_rejected():
    catalog = _synthetic_complete_catalog(b"%PDF-SYNTHETIC")
    catalog["original_pdf_sha256"] = PINNED_BASIN_PDF_SHA256
    catalog["districts"] = catalog["districts"][:10]
    catalog["district_count"] = 10
    catalog["province_count"] = 1
    with pytest.raises(ValueError, match="Partial"):
        validate_basin_catalog(catalog)


@pytest.mark.parametrize("raw,code", [
    ("Mısır (Dane)", "MISIR_DANE"),
    ("Dane Mısır", "MISIR_DANE"),
    ("Pamuk (Kütlü)", "PAMUK_KÜTLÜ"),
    ("Ayçiçeği (Yağlık)", "AYÇİÇEĞİ_YAĞLIK"),
    ("Kolza (Kanola)", "KANOLA"),
    ("Kuru Fasulye", "FASULYE_KURU"),
    ("Soğan (Kuru)", "SOĞAN_KURU"),
    ("Mısır", "MISIR"),
    ("Pamuk", "PAMUK"),
])
def test_official_subtype_aliases_never_guess_generic_crop(raw, code):
    from tarim_destek_rag.normalization.normalizer import normalize_crop_name

    assert normalize_crop_name(raw) == code
