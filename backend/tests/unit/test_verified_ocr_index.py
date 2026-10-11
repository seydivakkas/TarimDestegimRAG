"""Every OCR candidate must link to an original-byte-verified PDF page."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path
from unittest.mock import patch

import pymupdf
import pytest
from tarim_destek_rag.citations.pdf_page_indexer import OfficialPdfIndexer
from tarim_destek_rag.citations.verified_ocr_index import (
    index_official_document,
    search_ocr_candidates,
    write_index_atomic,
)


@pytest.fixture
def source(tmp_path: Path) -> OfficialPdfIndexer:
    doc = pymupdf.open()
    page = doc.new_page()
    page.insert_text((55, 75), "MADDE 1 ORIGINAL NATIVE TEXT")
    doc.new_page()
    data = doc.tobytes()
    doc.close()
    digest = hashlib.sha256(data).hexdigest()
    archive = tmp_path / "archive"
    source_dir = archive / "originals"
    source_dir.mkdir(parents=True)
    (source_dir / f"{digest}.pdf").write_bytes(data)
    file = tmp_path / "manifest.json"
    file.write_text(json.dumps({"sources": [{
        "id": "SYNTHETIC_TEST_ONLY", "format": "pdf",
        "url": "https://www.resmigazete.gov.tr/tests/synthetic-only.pdf",
        "original_sha256": digest, "original_bytes": len(data),
    }]}), encoding="utf-8")
    idx = OfficialPdfIndexer(manifest_path=file, archive_root=archive)
    idx.load_verified_originals()
    assert len(idx.get_all_pages()) == 2
    return idx


def test_all_pages_indexed_with_original_sha_and_ocr_hold(
    source: OfficialPdfIndexer,
) -> None:
    with patch.object(source, "ocr_page", return_value=("", "OCR_NOT_INSTALLED")):
        report = index_official_document(source, "SYNTHETIC_TEST_ONLY")
    assert report["indexed_page_count"] == 2
    assert report["ocr_unavailable_page_numbers"] == [2]
    assert report["technical_status"] == "INCOMPLETE_OCR_HOLD"
    assert report["pages"][0]["method"] == "PDF_NATIVE_TEXT_UNREVIEWED"
    assert report["pages"][1]["method"] == "OCR_NOT_INSTALLED"
    assert all(not r["legal_approved"] for r in report["pages"])
    assert report["payable_activation"] is False


def test_only_ocr_candidates_link_to_actual_page_image(
    tmp_path: Path, source: OfficialPdfIndexer,
) -> None:
    with patch.object(source, "ocr_page", return_value=(
        "SUNI OCR ADAY SAYFA ICERIGI", "OCR_UNREVIEWED",
    )):
        report = index_official_document(source, "SYNTHETIC_TEST_ONLY")
    assert report["technical_status"] == "SEARCHABLE_REVIEW_REQUIRED"
    output = tmp_path / ("verified_ocr_" + report["original_sha256"] + ".json")
    write_index_atomic(report, output)
    matches = search_ocr_candidates(
        source, "SUNI OCR ADAY", index_dir=tmp_path,
    )
    assert len(matches) == 1
    assert matches[0]["page_number"] == 2
    assert matches[0]["status"] == "OCR_CANDIDATE_UNREVIEWED"
    assert matches[0]["claim_verified"] is False
    assert search_ocr_candidates(source, "not anywhere", index_dir=tmp_path) == []


def test_modified_ocr_cache_and_original_never_give_verified_match(
    tmp_path: Path, source: OfficialPdfIndexer,
) -> None:
    with patch.object(source, "ocr_page", return_value=("candidate", "OCR_UNREVIEWED")):
        report = index_official_document(source, "SYNTHETIC_TEST_ONLY")
    output = tmp_path / ("verified_ocr_" + report["original_sha256"] + ".json")
    wrong = json.loads(json.dumps(report))
    wrong["original_page_count"] += 1
    write_index_atomic(wrong, output)
    assert search_ocr_candidates(source, "candidate", index_dir=tmp_path) == []

    write_index_atomic(report, output)
    real = source.archive_root / "originals" / (report["original_sha256"] + ".pdf")
    real.write_bytes(b"tampered")
    assert search_ocr_candidates(source, "candidate", index_dir=tmp_path) == []
    with pytest.raises(ValueError, match="mismatch"):
        index_official_document(source, "SYNTHETIC_TEST_ONLY")
