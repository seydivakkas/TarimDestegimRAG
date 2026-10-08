"""P0-8 future-year scan and exact PDF evidence guardrails.

Only local synthetic portal responses/PDF bytes are used. Never present a
synthetic amount or made-up legal sentence as real Turkish legislation.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pymupdf
import pytest

from tarim_destek_rag.updates.discovery import (
    OfficialPortal, UnsafeOfficialSource, _official_url,
    read_portals, scan_official_sources,
)
from tarim_destek_rag.updates.pdf_evidence import (
    UnverifiableEvidence, highlighted_pdf_copy, locate_pdf_quote, evidence_deeplink,
)


@pytest.fixture
def fake_portal():
    portal = OfficialPortal(
        source_id="EXAMPLE_MINISTRY_TEST",
        index_url="https://www.tarimorman.gov.tr/test/index",
        allowed_hosts=("www.tarimorman.gov.tr",),
    )
    source = "https://www.tarimorman.gov.tr/test/2030-support.pdf"
    state = {"pdf": b"%PDF-FAKE-TEST-DOC-2030-v1"}
    def fetch(url, hosts):
        _official_url(url, hosts)
        if url == portal.index_url:
            return (
                ('<a href="/test/2030-support.pdf">2030 destek tebliği</a>'
                 '<a href="http://evil.invalid/legislation.pdf">sahte destek</a>'
                 '<a href="/test/2030-support.pdf">duplicate</a>').encode("utf-8"),
                "text/html",
            )
        if url == source:
            return state["pdf"], "application/pdf"
        raise ValueError("Unlisted host/url")
    return portal, source, state, fetch


def test_2030_discovery_is_idempotent_and_never_publishes(tmp_path, fake_portal):
    portal, url, state, fetch = fake_portal
    first = scan_official_sources(
        production_year=2030, portals=[portal], output=tmp_path, fetch=fetch,
    )
    assert first["new_or_changed"] == 1
    assert first["documents"][0]["status"] == "NEW_DOCUMENT"
    assert first["publication_activated"] is False
    assert first["complete_official_coverage_proven"] is False
    assert first["documents"][0]["legal_effective_from"] is None
    original_sha = first["documents"][0]["sha256"]
    original = tmp_path / "originals" / (original_sha + ".pdf")
    assert original.read_bytes() == state["pdf"]
    second = scan_official_sources(
        production_year=2030, portals=[portal], output=tmp_path, fetch=fetch,
    )
    assert second["documents"][0]["status"] == "UNCHANGED"
    assert second["new_or_changed"] == 0
    state["pdf"] = b"%PDF-FAKE-TEST-DOC-2030-v2"
    third = scan_official_sources(
        production_year=2030, portals=[portal], output=tmp_path, fetch=fetch,
    )
    assert third["documents"][0]["status"] == "CHANGED_DOCUMENT"
    assert third["documents"][0]["previous_sha256"] == original_sha
    assert original.read_bytes() == b"%PDF-FAKE-TEST-DOC-2030-v1"
    assert len(list((tmp_path / "originals").glob("*.pdf"))) == 2


@pytest.mark.parametrize("url", [
    "http://www.tarimorman.gov.tr/supports",
    "https://evil.tarimorman.gov.tr.evil.invalid/document.pdf",
    "https://example.invalid/doc",
    "https://user:pass@www.tarimorman.gov.tr/document",
    "https://www.tarimorman.gov.tr:8080/unsafe",
])
def test_official_source_url_validation_blocks_outsiders(url):
    with pytest.raises(UnsafeOfficialSource):
        _official_url(url, ("www.tarimorman.gov.tr",))


def test_portal_outage_is_not_misreported_as_no_changes(tmp_path, fake_portal):
    portal, _, _, _ = fake_portal
    def outage(_url, _allowed):
        raise TimeoutError("Official publisher unavailable")
    report = scan_official_sources(
        production_year=2030, portals=[portal], output=tmp_path, fetch=outage,
    )
    assert report["errors"]
    assert report["publication_activated"] is False
    assert report["status"] == "REVIEW_REQUIRED"


def test_same_sha_file_tamper_refuses_reuse(tmp_path, fake_portal):
    portal, _, _, fetch = fake_portal
    scan = scan_official_sources(
        production_year=2029, portals=[portal], output=tmp_path, fetch=fetch,
    )
    sha = scan["documents"][0]["sha256"]
    (tmp_path / "originals" / (sha + ".pdf")).write_bytes(b"tampered")
    duplicate = scan_official_sources(
        production_year=2029, portals=[portal], output=tmp_path, fetch=fetch,
    )
    assert duplicate["errors"]
    assert duplicate["status"] == "REVIEW_REQUIRED"


def test_malformed_registry_cannot_add_nonofficial_host(tmp_path):
    registry = tmp_path / "portals.json"
    registry.write_text(json.dumps({"portals":[{
        "source_id":"FAKE", "index_url":"https://evil-tarimorman.gov.tr/redirect",
        "allowed_hosts":["evil-tarimorman.gov.tr"],
    }]}), encoding="utf-8")
    with pytest.raises(UnsafeOfficialSource):
        read_portals(registry)


@pytest.fixture
def test_pdf():
    # Intentionally invented textual content. No official legal claim.
    doc = pymupdf.open()
    page = doc.new_page(width=600, height=500)
    sentence = "Synthetic sample clause: example support requires active registration."
    page.insert_text((40, 90), sentence, fontsize=12)
    raw = doc.tobytes()
    doc.close()
    return raw, sentence


def test_pdf_exact_quote_highlights_right_page_and_keeps_original(test_pdf):
    pdf_bytes, sentence = test_pdf
    sha = hashlib.sha256(pdf_bytes).hexdigest()
    proof = locate_pdf_quote(
        pdf_bytes, expected_sha256=sha,
        page_1_indexed=1, exact_quote=sentence,
    )
    assert proof.match_count == 1
    assert proof.page_1_indexed == 1
    assert proof.exact_quote == sentence
    assert proof.normalized_quads
    link = evidence_deeplink(proof)
    assert link.startswith(f"/evidence/highlight/{sha}?page=1&quote=")
    assert "%20" in link
    highlighted = highlighted_pdf_copy(pdf_bytes, proof)
    assert hashlib.sha256(pdf_bytes).hexdigest() == sha
    with pymupdf.open(stream=highlighted, filetype="pdf") as marked:
        assert marked.page_count == 1
        assert len(list(marked[0].annots())) == 1


def test_pdf_rejects_wrong_sha_wrong_page_and_fabricated_quote(test_pdf):
    pdf_bytes, sentence = test_pdf
    sha = hashlib.sha256(pdf_bytes).hexdigest()
    with pytest.raises(UnverifiableEvidence, match="SHA-256"):
        locate_pdf_quote(pdf_bytes, expected_sha256="0"*64,
                         page_1_indexed=1, exact_quote=sentence)
    with pytest.raises(UnverifiableEvidence, match="page"):
        locate_pdf_quote(pdf_bytes, expected_sha256=sha,
                         page_1_indexed=5, exact_quote=sentence)
    with pytest.raises(UnverifiableEvidence, match="not found"):
        locate_pdf_quote(pdf_bytes, expected_sha256=sha,
                         page_1_indexed=1,
                         exact_quote="This sentence does not occur in the source PDF.")


def test_pdf_ambiguous_sentence_cannot_create_unique_citation():
    doc = pymupdf.open()
    page = doc.new_page()
    sentence = "Synthetic identical legal passage appears twice."
    page.insert_text((40, 80), sentence)
    page.insert_text((40, 110), sentence)
    contents = doc.tobytes()
    doc.close()
    with pytest.raises(UnverifiableEvidence, match="multiple"):
        locate_pdf_quote(
            contents, expected_sha256=hashlib.sha256(contents).hexdigest(),
            page_1_indexed=1, exact_quote=sentence,
        )


def test_legacy_2026_preview_does_not_fabricate_quote_as_law():
    from tarim_destek_rag.citations.document_links import render_document_viewer_html
    output = render_document_viewer_html("MADDE 1")
    assert "Mevzuat cümlesi doğrulanmadı" in output
    assert "Önceki örnek önizlemeler" in output
    assert "Çiftçi Kayıt Sistemi (ÇKS) kaydı aktif olan" not in output
