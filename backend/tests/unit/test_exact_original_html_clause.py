"""Original 2024/39 official Gazette HTML: same exact legal paragraph or no link."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from tarim_destek_rag.citations.document_links import format_highlighted_citation_card
from tarim_destek_rag.citations.original_html import (
    SOURCE_SHA,
    highlighted_html_copy,
    lookup_html_clause,
)


def _archive() -> Path:
    return Path("data/legal_update_archive")


def test_original_html_is_exactly_pinned_and_not_approved() -> None:
    config = json.loads(
        Path("configs/p0_10_6_2024_39_html_clauses.json").read_text(encoding="utf-8")
    )
    assert config["schema_version"] == 1
    assert len(config["clauses"]) == 1
    row = config["clauses"][0]
    assert row["source_sha256"] == SOURCE_SHA
    assert row["article"] == "MADDE 4" and row["paragraph"] == "1"
    assert row["legal_review_completed"] is False
    assert row["year"] == 2026


def test_exact_original_html_renders_marked_source_without_changing_original(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    source = _archive() / "originals" / (SOURCE_SHA + ".html")
    if not source.is_file():
        pytest.skip("Original official Gazette bytes must be installed for live evidence test")
    monkeypatch.setenv("TARIM_RAG_UPDATE_ARCHIVE", str(_archive()))
    original = source.read_bytes()
    assert hashlib.sha256(original).hexdigest() == SOURCE_SHA
    proof = lookup_html_clause("BASIC_SUPPORT_2026")
    assert proof and proof["source_sha256"] == SOURCE_SHA
    assert proof["section"] == "MADDE 4 (1)"
    assert proof["verification_status"] == "ORIGINAL_HTML_TEXT_LOCATED_PENDING_LEGAL_REVIEW"
    copy = highlighted_html_copy("BASIC_SUPPORT_2026", expected_sha256=SOURCE_SHA)
    assert copy.count(b'id="tarim-evidence-highlight"') == 1
    assert "Desteklemelerden yararlanmak için".encode() in copy
    assert source.read_bytes() == original
    html = format_highlighted_citation_card({
        "title": proof["title"], "section": proof["section"], "year": proof["year"],
        "url": proof["source_url"], "snippet": proof["exact_quote"],
        "highlighted_pdf_url": proof["highlighted_html_url"],
        "verification_status": proof["verification_status"],
        "document_sha256": proof["source_sha256"],
    })
    assert "HTML’de işaretli fıkrayı aç" in html
    assert "Resmî kaynağı aç" in html


def test_html_mismatch_unknown_program_and_wrong_section_fail_closed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    source = _archive() / "originals" / (SOURCE_SHA + ".html")
    if not source.is_file():
        pytest.skip("Original source must be installed before fail-closed verification")
    original = source.read_bytes()
    archive = tmp_path / "originals"
    archive.mkdir()
    (archive / (SOURCE_SHA + ".html")).write_bytes(original)
    monkeypatch.setenv("TARIM_RAG_UPDATE_ARCHIVE", str(tmp_path))
    assert lookup_html_clause("NONEXISTENT_SUPPORT") is None
    config = json.loads(
        Path("configs/p0_10_6_2024_39_html_clauses.json").read_text(encoding="utf-8")
    )
    config["clauses"][0]["article"] = "MADDE 5"
    custom = tmp_path / "fake_clause_index.json"
    custom.write_text(json.dumps(config), encoding="utf-8")
    monkeypatch.setenv("TARIM_RAG_HTML_CLAUSE_INDEX", str(custom))
    assert lookup_html_clause("BASIC_SUPPORT_2026") is None
    config["clauses"][0]["article"] = "MADDE 4"
    config["clauses"][0]["exact_quote"] = "Hayali destek hükümleri gerçek resmî metinde yoktur."
    custom.write_text(json.dumps(config), encoding="utf-8")
    assert lookup_html_clause("BASIC_SUPPORT_2026") is None
    (archive / (SOURCE_SHA + ".html")).write_bytes(original + b"tampered")
    assert lookup_html_clause("BASIC_SUPPORT_2026") is None


def test_original_html_api_is_sandboxed_when_available() -> None:
    source = _archive() / "originals" / (SOURCE_SHA + ".html")
    if not source.is_file():
        pytest.skip("Official original not present in general backend regression")
    from fastapi.testclient import TestClient
    from tarim_destek_rag.api.main import app

    with TestClient(app) as client:
        response = client.get(
            "/evidence/highlight/html/" + SOURCE_SHA,
            params={"support_id": "BASIC_SUPPORT_2026"},
        )
        assert response.status_code == 200
        assert 'id="tarim-evidence-highlight"' in response.text
        assert response.headers["X-Original-Source-SHA256"] == SOURCE_SHA
        assert "sandbox" in response.headers["Content-Security-Policy"]
        assert "allow-scripts" not in response.headers["Content-Security-Policy"]
        invalid = client.get(
            "/evidence/highlight/html/" + "0" * 64,
            params={"support_id": "BASIC_SUPPORT_2026"},
        )
        assert invalid.status_code == 409
