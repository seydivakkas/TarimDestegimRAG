"""Shared proof URL contract: PC explanation and downloadable report must agree."""
from __future__ import annotations

from urllib.parse import quote

import pytest
from tarim_destek_rag.citations.evidence_contract import verified_highlight_path

from frontend_pc.formatters import generate_report_markdown, render_reasons_markdown


def _response(citations: list[dict], basin: dict | None = None) -> dict:
    return {
        "total_estimated_amount": None,
        "rules": [{
            "support_id": "BASIC_SUPPORT_2026", "support_name": "Temel Destek",
            "status": "REVIEW", "passed_checks": ["ÇKS aktif"],
            "failed_checks": ["Tohum sertifikası eksik"],
            "missing_fields": ["origin_verified"],
        }],
        "calculations": [],
        "explanations": [{
            "support_id": "BASIC_SUPPORT_2026",
            "summary_tr": "Ön değerlendirme",
            "detailed_reason_tr": "Ek belge kontrolü gerekir",
            "citations": citations,
        }],
        "basin_evidence": basin,
    }


def _report(resp: dict) -> str:
    return generate_report_markdown(
        resp,
        {"province": "KONYA", "district": "KARATAY", "cks_status": True},
        {"crop": "BUĞDAY", "area_da": 25, "production_year": 2026},
    )


def _pdf() -> dict:
    sha = "a" * 64
    snippet = "Özgün metindeki birebir fıkra örneği."
    return {
        "title": "Resmî PDF", "section": "MADDE 2(1)",
        "snippet": snippet,
        "verification_status": "EXACT_PDF_MATCH_PENDING_LEGAL_REVIEW",
        "document_sha256": sha, "page_number": 2,
        "highlighted_pdf_url": (
            f"/evidence/highlight/{sha}?page=2&quote={quote(snippet, safe='')}"
        ),
    }


def test_report_and_pc_show_same_exact_pdf_evidence_link(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_PUBLIC_BASE_URL", "http://127.0.0.1:8000")
    proof = _pdf()
    resp = _response([proof])
    link = proof["highlighted_pdf_url"]
    report, pc = _report(resp), render_reasons_markdown(resp)
    assert verified_highlight_path(proof, "BASIC_SUPPORT_2026") == link
    assert "PDF’de işaretli cümleyi aç" in pc
    assert "işaretli özgün belgeyi aç" in report
    # HTML attributes escape '&' in both surfaces.
    assert link.replace("&", "&amp;") in report
    assert link.replace("&", "&amp;") in pc
    assert "Özgün metinde birebir konumlanan pasaj" in report
    assert "Kaynak eşleşmesi aşağıda" in report


def test_report_unverified_explanations_have_no_guessed_madde_or_page() -> None:
    guessed = {
        "title": "Konu", "section": "MADDE 1", "snippet": "Doğrulanmamış açıklama",
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=1",
    }
    report = _report(_response([guessed]))
    assert "Birebir madde/fıkra" not in report  # status is a descriptive explanation
    assert "resmî cümle ve madde/fıkra doğrulanmadı" in report
    assert "#page=1" not in report
    assert "↗](" not in report
    assert "sarı işaretli" not in report
    assert "2026 Resmî Gazete |" not in report
    assert "ÇKS aktif" in report and "Tohum sertifikası eksik" in report


@pytest.mark.parametrize("mutation", [
    {"page_number": 3},
    {"document_sha256": "b" * 64},
    {"highlighted_pdf_url": "/evidence/highlight/" + "a" * 64 + "?page=2&quote=wrong"},
    {"verification_status": "UNVERIFIED_EXPLANATION"},
])
def test_forged_pdf_evidence_is_never_linked_in_report(mutation: dict) -> None:
    evidence = {**_pdf(), **mutation}
    assert verified_highlight_path(evidence, "BASIC_SUPPORT_2026") is None
    report = _report(_response([evidence]))
    assert "işaretli özgün belgeyi aç" not in report
    assert "Kanıt bağlantısı yok" in report


def test_html_clause_and_basin_use_same_source_bound_contract() -> None:
    html_sha = "b" * 64
    clause = {
        "snippet": "Birebir HTML hükmü",
        "verification_status": "ORIGINAL_HTML_TEXT_LOCATED_PENDING_LEGAL_REVIEW",
        "document_sha256": html_sha,
        "highlighted_pdf_url": (
            f"/evidence/highlight/html/{html_sha}?support_id=BASIC_SUPPORT_2026"
            "#tarim-evidence-highlight"
        ),
    }
    assert verified_highlight_path(clause, "BASIC_SUPPORT_2026") is not None
    assert verified_highlight_path(clause, "WATER_RESTRICTION_2026") is None
    assert "işaretli özgün belgeyi aç" in _report(_response([clause]))

    sha = "c" * 64
    basin = {
        "verification_status": "ORIGINAL_PDF_ROW_AND_CROP_LOCATED_DRAFT_REVIEW",
        "source_sha256": sha,
        "province": "KONYA", "district": "KARATAY", "crop_code": "BUĞDAY",
        "crop_label": "Buğday", "production_year": 2026, "page_number": 53,
        "eligible": None, "approved_rate": None,
        "highlighted_pdf_url": (
            f"/evidence/highlight/basin/{sha}?province=KONYA&district=KARATAY"
            "&crop=BU%C4%9EDAY&production_year=2026#page=53"
        ),
    }
    assert verified_highlight_path(basin) == basin["highlighted_pdf_url"]
    report = _report(_response([], basin))
    assert "İlçe ve ürünün aynı PDF satırındaki işaretlerini aç" in report
    assert "kesin uygunluk veya ödeme hakkı anlamına gelmez" in report
    for invalid in (
        {**basin, "crop_code": "ARPA"},
        {**basin, "production_year": 2025},
        {**basin, "page_number": 51},
        {**basin, "eligible": True},
        {**basin, "source_sha256": "d" * 64},
    ):
        assert verified_highlight_path(invalid) is None
        assert "İlçe/ürün için özgün PDF satırı doğrulanmadı" in _report(_response([], invalid))


def test_no_match_never_becomes_legal_entitlement() -> None:
    empty = _report(_response([]))
    assert "Birebir madde/fıkra henüz doğrulanmadı" in empty
    assert "ilçe/ürün" in empty.lower()
    assert "işaretli belge" not in empty
