"""No displayed legal quote unless identical source PDF bytes, text and page match."""
from __future__ import annotations

import hashlib
import json

import pytest
from tarim_destek_rag.citations.document_links import format_highlighted_citation_card
from tarim_destek_rag.citations.exact_index import index_quote, lookup_exact_pdf_citation
from tarim_destek_rag.explainer.template_explainer import SUPPORT_CITATION_DEFAULTS


def test_unverified_explanation_never_appears_as_original_pdf_quote() -> None:
    cit = SUPPORT_CITATION_DEFAULTS["BASIC_SUPPORT_2026"].model_dump()
    result = format_highlighted_citation_card(cit, status="ELIGIBLE")
    assert "resmî alıntı değildir" in result
    assert "PDF’de işaretli cümleyi aç" not in result
    assert "📜 <i>" not in result
    assert "367 TL/da" in result


def test_arbitrary_fake_highlight_url_does_not_make_unverified_text_proof() -> None:
    data = {
        "title": "Tebliğ",
        "section": "MADDE 1",
        "url": "https://resmigazete.gov.tr/eskiler/2024/12/20241231M5-8.htm",
        "snippet": "<script>alert('fake legal citation')</script>",
        "highlighted_pdf_url": "/evidence/highlight/not-real",
    }
    html = format_highlighted_citation_card(data)
    assert "<script>" not in html
    assert "&lt;script&gt;" in html
    assert "PDF’de işaretli cümleyi aç" not in html
    assert "resmî alıntı değildir" in html


def test_citations_without_local_original_archive_cannot_be_verified(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    monkeypatch.setenv("TARIM_RAG_UPDATE_ARCHIVE", str(tmp_path / "missing"))
    monkeypatch.setenv("TARIM_RAG_ORIGINAL_SOURCE_MANIFEST", str(tmp_path / "missing.json"))
    assert lookup_exact_pdf_citation("BASIC_SUPPORT_2026") is None


def test_original_pdf_quote_index_link_and_tamper_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    fitz = pytest.importorskip("pymupdf")
    source_url = "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf"
    quote = "MADDE 1 - Bu metin gercek PDF sayfasinda birebir eslesen ornek cumledir."
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((60, 70), quote, fontsize=10)
    raw = doc.tobytes()
    doc.close()
    digest = hashlib.sha256(raw).hexdigest()
    root = tmp_path / "archive"
    orig = root / "originals"
    orig.mkdir(parents=True)
    target = orig / (digest + ".pdf")
    target.write_bytes(raw)
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sources": [
        {"id": "RG_DECISION_8859", "format": "pdf", "url": source_url,
         "original_sha256": digest}
    ]}), encoding="utf-8")
    monkeypatch.setenv("TARIM_RAG_UPDATE_ARCHIVE", str(root))
    monkeypatch.setenv("TARIM_RAG_ORIGINAL_SOURCE_MANIFEST", str(manifest))
    row = {
        "support_id": "BASIC_SUPPORT_2026",
        "source_id": "RG_DECISION_8859",
        "source_sha256": digest,
        "source_url": source_url,
        "page_number": 1,
        "exact_quote": quote,
        "section": "MADDE 1",
        "title": "8859 sayılı Karar",
        "year": 2026,
    }
    out = index_quote(row, root=root, manifest=manifest)
    assert out["verification_status"] == "EXACT_PDF_MATCH_PENDING_LEGAL_REVIEW"
    assert out["source_sha256"] == digest
    matched = lookup_exact_pdf_citation("BASIC_SUPPORT_2026")
    assert matched is not None
    assert matched["exact_quote"] == quote
    assert "page=1" in matched["highlighted_pdf_url"]
    html = format_highlighted_citation_card({
        "title": matched["title"], "section": matched["section"],
        "snippet": matched["exact_quote"],
        "url": matched["source_url"] + "#page=1",
        "verification_status": matched["verification_status"],
        "highlighted_pdf_url": matched["highlighted_pdf_url"],
        "page_number": matched["page_number"],
        "document_sha256": matched["source_sha256"],
    })
    assert "PDF’de işaretli cümleyi aç" in html
    assert "birebir bulunan pasaj" in html
    # Source is silently changed while index remains identical -> no evidence.
    target.write_bytes(raw + b"tampered")
    assert lookup_exact_pdf_citation("BASIC_SUPPORT_2026") is None


def test_nonexistent_quote_cannot_be_indexed(
    monkeypatch: pytest.MonkeyPatch, tmp_path,
) -> None:
    fitz = pytest.importorskip("pymupdf")
    url = "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf"
    pdf = fitz.open()
    pdf.new_page().insert_text((40, 40), "Source contains unrelated words.")
    data = pdf.tobytes()
    pdf.close()
    digest = hashlib.sha256(data).hexdigest()
    root = tmp_path / "originals-root"
    originals = root / "originals"
    originals.mkdir(parents=True)
    (originals / (digest + ".pdf")).write_bytes(data)
    mf = tmp_path / "manifest.json"
    mf.write_text(json.dumps({"sources": [{
        "id": "RG_DECISION_8859", "format": "pdf",
        "url": url, "original_sha256": digest,
    }]}), encoding="utf-8")
    fake = {
        "support_id": "BASIC_SUPPORT_2026",
        "source_id": "RG_DECISION_8859",
        "source_url": url,
        "source_sha256": digest,
        "page_number": 1,
        "exact_quote": "Çiftçiye destek ödenir ve tüm şartlar sağlanmış sayılır.",
        "section": "MADDE 1",
    }
    with pytest.raises(ValueError, match="cannot be independently verified"):
        index_quote(fake, root=root, manifest=mf)
    assert not (root / "verified_citations.json").exists()
