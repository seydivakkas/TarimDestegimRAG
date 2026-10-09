"""The selected district and crop must be found in the SAME original PDF table row."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from tarim_destek_rag.citations.basin_visual import (
    PINNED_BASIN_PDF_SHA256,
    highlight_basin_crop_copy,
    locate_basin_crop,
    lookup_basin_crop_evidence,
)

from frontend_pc.formatters import render_reasons_markdown


def test_basin_manifest_is_not_approved_entitlement() -> None:
    catalog = json.loads(
        Path("configs/2026_2027_basin_crop_draft.json").read_text(encoding="utf-8")
    )
    assert catalog["original_pdf_sha256"] == PINNED_BASIN_PDF_SHA256
    assert catalog["district_count"] == 945
    assert catalog["production_years"] == [2026, 2027]
    assert catalog["approval"] == "DRAFT_REQUIRES_HUMAN_ROW_AND_FOOTNOTE_REVIEW"


def test_no_original_source_means_no_pdf_evidence(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    monkeypatch.setenv("TARIM_RAG_UPDATE_ARCHIVE", str(tmp_path / "absent"))
    assert lookup_basin_crop_evidence("KONYA", "KARATAY", "BUĞDAY", 2026) is None
    assert lookup_basin_crop_evidence("KONYA", "KARATAY", "MISIR", 2026) is None
    assert lookup_basin_crop_evidence("KONYA", "KARATAY", "BUĞDAY", 2025) is None
    assert lookup_basin_crop_evidence("UNKNOWN", "KARATAY", "BUĞDAY", 2026) is None
    assert lookup_basin_crop_evidence("TRABZON", "AKÇAABAT", "FINDIK", 2026) is None


def test_untrusted_response_can_never_be_payment_eligibility() -> None:
    fake = {
        "rules": [],
        "basin_evidence": {
            "verification_status": "ORIGINAL_PDF_ROW_AND_CROP_LOCATED_DRAFT_REVIEW",
            "province": "KONYA", "district": "KARATAY", "crop_label": "Buğday",
            "page_number": 53,
            "source_url": "https://www.tarimorman.gov.tr/original.pdf",
            "highlighted_pdf_url": (
                "/evidence/highlight/basin/" + PINNED_BASIN_PDF_SHA256
                + "?province=KONYA&district=KARATAY&crop=BU%C4%9EDAY&production_year=2026#page=53"
            ),
        },
    }
    html = render_reasons_markdown(fake)
    assert "KONYA / KARATAY" in html
    assert "Buğday" in html
    assert "PDF sayfa 53" in html
    assert "mavi, ürünü sarı" in html
    assert "destek uygunluğu/ödeme kanıtı değildir" in html
    fake["basin_evidence"] = None
    assert "birebir işaretleme şu anda doğrulanamadı" in render_reasons_markdown(fake)


@pytest.mark.parametrize("city,district,crop,page_no", [
    ("KONYA", "KARATAY", "BUĞDAY", 53),
    ("ADANA", "CEYHAN", "ARPA", 1),
    ("SAMSUN", "ATAKUM", "BUĞDAY", 67),
    ("TRABZON", "AKÇAABAT", "PATATES", 75),
])
def test_official_pdf_multiple_district_rows_when_installed(
    city: str, district: str, crop: str, page_no: int,
) -> None:
    root = Path("data/legal_update_archive")
    source = root / "originals" / (PINNED_BASIN_PDF_SHA256 + ".pdf")
    if not source.exists():
        pytest.skip("Exact original PDF not installed; dedicated CI installs it first")
    assert hashlib.sha256(source.read_bytes()).hexdigest() == PINNED_BASIN_PDF_SHA256
    proof, original = locate_basin_crop(city, district, crop, 2026)
    assert proof["page_number"] == page_no
    assert proof["verification_status"] == "ORIGINAL_PDF_ROW_AND_CROP_LOCATED_DRAFT_REVIEW"
    assert proof["eligible"] is None and proof["approved_rate"] is None
    marked = highlight_basin_crop_copy(
        city, district, crop, 2026, expected_sha256=PINNED_BASIN_PDF_SHA256,
    )
    import pymupdf

    with pymupdf.open(stream=marked, filetype="pdf") as pdf:
        assert pdf.page_count == 81
        annotations = list(pdf[page_no - 1].annots())
        assert len(annotations) == 2
        assert all(a.type[1] == "Square" for a in annotations)
    assert hashlib.sha256(original).hexdigest() == PINNED_BASIN_PDF_SHA256
    assert source.read_bytes() == original


def test_different_legal_year_and_generic_subtype_never_infer_crop() -> None:
    assert lookup_basin_crop_evidence("KONYA", "KARATAY", "BUĞDAY", 2025) is None
    assert lookup_basin_crop_evidence("KONYA", "KARATAY", "MISIR", 2027) is None
    assert lookup_basin_crop_evidence("TRABZON", "AKÇAABAT", "FINDIK", 2026) is None
