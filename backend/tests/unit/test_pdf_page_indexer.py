"""P0-39: real page screenshots, no synthetic PDF or guessed legal citations."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pymupdf
import pytest

from tarim_destek_rag.citations import pdf_page_indexer as module
from tarim_destek_rag.citations.pdf_page_indexer import (
    OfficialPdfIndexer,
    get_page_dropdown_choices,
    normalize_tr,
    render_evidence_by_key,
    render_page_evidence_card,
)


@pytest.fixture
def original_fixture(tmp_path: Path) -> OfficialPdfIndexer:
    """A labelled synthetic *test* PDF, never shipped as an official source."""
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((60, 80), "MADDE 1 Uretim Yili Kayit Sistemi 2026")
    doc.new_page()
    contents = doc.tobytes()
    doc.close()
    digest = hashlib.sha256(contents).hexdigest()
    archive = tmp_path / "archive"
    originals = archive / "originals"
    originals.mkdir(parents=True)
    (originals / f"{digest}.pdf").write_bytes(contents)
    manifest = tmp_path / "source-manifest.json"
    manifest.write_text(json.dumps({"sources": [{
        "id": "SYNTHETIC_TEST_ONLY",
        "format": "pdf",
        "url": "https://www.resmigazete.gov.tr/fixture/synthetic-test-only.pdf",
        "original_sha256": digest,
        "original_bytes": len(contents),
    }]}), encoding="utf-8")
    indexer = OfficialPdfIndexer(archive_root=archive, manifest_path=manifest)
    indexer.index_pdf(
        contents, doc_id="SYNTHETIC_TEST_ONLY",
        doc_title="Sentetik yalnız birim testi",
        gazette_issue="TEST", gazette_date="TEST",
        official_url="https://www.resmigazete.gov.tr/fixture/synthetic-test-only.pdf",
    )
    return indexer


def test_turkish_search_normalization() -> None:
    assert normalize_tr("ÇKS Üretim Şartı") == "cks uretim sarti"


def test_untrusted_legacy_cache_is_not_loaded(tmp_path: Path) -> None:
    cache = tmp_path / "gazette_page_index.json"
    cache.write_text(json.dumps({"RG_DECISION_8859": [
        {"doc_id": "RG_DECISION_8859", "raw_text": "FAKE RESMİ MADDE"}
    ]}), encoding="utf-8")
    indexer = OfficialPdfIndexer(
        index_path=cache,
        archive_root=tmp_path / "no-archive",
        manifest_path=tmp_path / "not-present",
    )
    indexer.seed_default_gazette_documents()
    assert indexer.get_all_pages() == []


def test_verified_original_shows_real_page_png_and_provenance(
    original_fixture: OfficialPdfIndexer,
) -> None:
    p1 = original_fixture.get_page("SYNTHETIC_TEST_ONLY", 1)
    assert p1 is not None
    assert p1.page_number == 1 and p1.total_pages == 2
    png, highlighted, sha = original_fixture.screenshot(p1, query="MADDE 1")
    assert png.startswith(b"\x89PNG\r\n\x1a\n")
    assert highlighted > 0
    assert sha == p1.source_sha256
    rendered = render_page_evidence_card(p1, indexer=original_fixture)
    assert "data:image/png;base64," in rendered
    assert sha in rendered
    assert "#page=1" in rendered
    assert "Özgün PDF sayfa ekran görüntüsü" in rendered


def test_original_second_page_does_not_fabricate_ocr_or_tables(
    original_fixture: OfficialPdfIndexer,
) -> None:
    p2 = original_fixture.get_page("SYNTHETIC_TEST_ONLY", 2)
    assert p2 and p2.raw_text == "" and p2.tables == []
    html = render_page_evidence_card(p2, indexer=original_fixture)
    assert "OCR/pasaj eşleşmesi henüz onaylanmadı" in html
    assert "Orijinal Resmî Gazete Sayfası Görsel Delili" not in html
    assert not p2.graphics.has_official_seal


def test_unsigned_bytes_cannot_be_indexed(original_fixture: OfficialPdfIndexer) -> None:
    p1 = original_fixture.get_page("SYNTHETIC_TEST_ONLY", 1)
    assert p1
    with pytest.raises(ValueError, match="synthetic"):
        original_fixture.index_pdf(
            b"%PDF-fake", doc_id=p1.doc_id,
            doc_title="fake", gazette_issue="X", gazette_date="X",
            official_url=p1.official_url.split("#")[0],
        )


def test_original_tampering_or_source_removal_fails_closed(
    original_fixture: OfficialPdfIndexer,
) -> None:
    p1 = original_fixture.get_page("SYNTHETIC_TEST_ONLY", 1)
    assert p1
    source = original_fixture.archive_root / "originals" / f"{p1.source_sha256}.pdf"
    source.write_bytes(b"altered")
    assert "HOLD" in render_page_evidence_card(p1, indexer=original_fixture)
    with pytest.raises(ValueError, match="digest"):
        original_fixture.screenshot(p1)


def test_wrong_page_or_provenance_cannot_be_rendered(
    original_fixture: OfficialPdfIndexer,
) -> None:
    p1 = original_fixture.get_page("SYNTHETIC_TEST_ONLY", 1)
    assert p1
    assert original_fixture.get_page("SYNTHETIC_TEST_ONLY", 1000) is None
    p1.official_url = "https://www.resmigazete.gov.tr/fake.pdf#page=1"
    assert render_page_evidence_card(p1, indexer=original_fixture).count("HOLD") == 1


def test_search_returns_only_real_text_matches(
    original_fixture: OfficialPdfIndexer,
) -> None:
    matches = original_fixture.search_pages("MADDE 1")
    assert len(matches) == 1
    assert matches[0].page_number == 1
    assert original_fixture.search_pages("uysalmayan birim tutar 999") == []
    assert original_fixture.search_pages("belge") == []
    assert original_fixture.get_article_page("MADDE 6") is None


def test_missing_archived_source_has_no_dropdown_and_no_fallback(
    tmp_path: Path,
) -> None:
    with patch.object(module, "_GLOBAL_INDEXER", OfficialPdfIndexer(
        archive_root=tmp_path / "missing",
        manifest_path=tmp_path / "not-here.json",
    )):
        assert get_page_dropdown_choices() == []
        assert "HOLD" in render_evidence_by_key("RG_DECISION_8859:1")
        assert "HOLD" in render_evidence_by_key("MADDE 1")
        assert "HOLD" in render_evidence_by_key("RG_DECISION_8859:1", "367")


def test_archive_raster_is_not_automatically_ocr_verified(
    original_fixture: OfficialPdfIndexer,
) -> None:
    page = original_fixture.get_page("SYNTHETIC_TEST_ONLY", 2)
    assert page
    with patch.object(module.shutil, "which", return_value=None):
        result, status = original_fixture.ocr_page(page)
    assert result == ""
    assert status == "OCR_NOT_INSTALLED"


def test_originals_manifest_html_is_not_fake_pdf(tmp_path: Path) -> None:
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sources": [{
        "id": "RG_COMMUNIQUE_2024_39", "format": "html",
        "url": "https://resmigazete.gov.tr/example.htm",
        "original_sha256": "a" * 64,
    }]}), encoding="utf-8")
    engine = OfficialPdfIndexer(archive_root=tmp_path, manifest_path=manifest)
    engine.load_verified_originals()
    assert engine.get_all_pages() == []
    with pytest.raises(ValueError, match="Missing or ambiguous"):
        engine._source("RG_COMMUNIQUE_2024_39")
