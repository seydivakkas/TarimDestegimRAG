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



def test_real_evaluation_exposes_all_three_source_marks_when_installed() -> None:
    """A farmer click opens the real 8859 PDF, 2024/39 HTML, and basin PDF."""
    from tarim_destek_rag.citations.basin_visual import PINNED_BASIN_PDF_SHA256

    originals = [
        _archive() / "originals" / (SOURCE_SHA + ".html"),
        _archive() / "originals" / (PINNED_BASIN_PDF_SHA256 + ".pdf"),
        _archive() / "originals" / (
            "89df0b6222edb4eddf3d5f588a4007061458adec8d518e3fbdb86b46ae5ba85f.pdf"
        ),
    ]
    if any(not p.is_file() for p in originals):
        pytest.skip("All three official original sources must be installed for E2E test")
    from fastapi.testclient import TestClient
    from tarim_destek_rag.api.main import app

    from frontend_pc.formatters import render_reasons_markdown

    with TestClient(app) as client:
        r = client.post("/evaluate", json={
            "farmer": {
                "farmer_id": "F-01", "province": "KONYA", "district": "KARATAY",
                "cks_status": True,
            },
            "parcel": {
                "parcel_id": "P-01", "farmer_id": "F-01", "crop": "BUĞDAY",
                "area_da": 25, "production_year": 2026,
                "seed_certificate_available": True,
            },
        })
        assert r.status_code == 200
        response = r.json()
        evidence = response["basin_evidence"]
        assert evidence and evidence["page_number"] == 53
        assert evidence["province"] == "KONYA" and evidence["district"] == "KARATAY"
        assert evidence["crop_code"] == "BUĞDAY"
        basic = next(
            x for x in response["explanations"] if x["support_id"] == "BASIC_SUPPORT_2026"
        )
        visual = next(
            c for c in basic["citations"]
            if c["verification_status"] == "VISUAL_SOURCE_LOCATED_PENDING_SECOND_REVIEW"
        )
        html = next(
            c for c in basic["citations"]
            if c["verification_status"] == "ORIGINAL_HTML_TEXT_LOCATED_PENDING_LEGAL_REVIEW"
        )
        reasons = render_reasons_markdown(response)
        assert "HTML’de işaretli fıkrayı aç" in reasons
        assert "PDF’de işaretli cümleyi aç" in reasons
        assert "İlçeyi mavi, ürünü sarı" in reasons
        for url in (
            visual["highlighted_pdf_url"], html["highlighted_pdf_url"],
            evidence["highlighted_pdf_url"],
        ):
            result = client.get(url)
            assert result.status_code == 200
            assert result.headers["X-Original-Source-SHA256"] in {
                SOURCE_SHA, PINNED_BASIN_PDF_SHA256,
                "89df0b6222edb4eddf3d5f588a4007061458adec8d518e3fbdb86b46ae5ba85f",
            }
            assert len(result.content) > 10_000

def test_html_installer_retries_transient_timeouts_with_exact_sha(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    from contextlib import contextmanager

    import httpx
    from tarim_destek_rag.citations import original_html

    fixture = b"<html><body>Offline retry fixture</body></html>"
    sha = hashlib.sha256(fixture).hexdigest()
    monkeypatch.setattr(original_html, "SOURCE_SHA", sha)
    archive = tmp_path / "archive"
    manifest = tmp_path / "manifest.json"
    manifest.write_text(json.dumps({"sources": [{
        "id": original_html.SOURCE_ID,
        "url": original_html.SOURCE_URL,
        "format": "html",
        "original_sha256": sha,
    }]}), encoding="utf-8")
    monkeypatch.setenv("TARIM_RAG_UPDATE_ARCHIVE", str(archive))
    monkeypatch.setenv("TARIM_RAG_ORIGINAL_SOURCE_MANIFEST", str(manifest))
    monkeypatch.setattr(original_html.time, "sleep", lambda _: None)
    attempts: list[int] = []

    class FakeResponse:
        status_code = 200
        url = original_html.SOURCE_URL
        headers = {"Content-Encoding": "identity", "Content-Type": "text/html"}

        def iter_raw(self):
            yield fixture

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return False

        @contextmanager
        def stream(self, *args, **kwargs):
            attempts.append(1)
            if len(attempts) < 3:
                raise httpx.ReadTimeout("Temporary upstream timeout")
            yield FakeResponse()

    monkeypatch.setattr(httpx, "Client", FakeClient)
    result = original_html.install_html_original()
    assert len(attempts) == 3
    assert result["sha256"] == sha
    assert (archive / "originals" / (sha + ".html")).read_bytes() == fixture


def test_html_download_exhaustion_preserves_fail_closed_archive(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
) -> None:
    """Two unreachable official endpoints never create or approve a source."""
    import httpx
    from tarim_destek_rag.citations import original_html

    requested: list[str] = []

    class TimedOutClient:
        def __init__(self, **kwargs: object) -> None:
            assert kwargs["follow_redirects"] is False
            assert kwargs["trust_env"] is False

        def __enter__(self) -> "TimedOutClient":
            return self

        def __exit__(self, *_args: object) -> None:
            pass

        def stream(self, method: str, url: str, **_kwargs: object) -> None:
            assert method == "GET"
            requested.append(url)
            raise httpx.ReadTimeout("official host unavailable")

    monkeypatch.setenv("TARIM_RAG_UPDATE_ARCHIVE", str(tmp_path))
    monkeypatch.setattr(httpx, "Client", TimedOutClient)
    monkeypatch.setattr(original_html.time, "sleep", lambda _: None)
    with pytest.raises(RuntimeError, match="HOLD"):
        original_html.install_html_original()
    assert requested == [
        original_html.SOURCE_URL,
        original_html.SOURCE_URL,
        original_html.SOURCE_URL.replace(
            "://resmigazete.gov.tr/", "://www.resmigazete.gov.tr/", 1
        ),
        original_html.SOURCE_URL.replace(
            "://resmigazete.gov.tr/", "://www.resmigazete.gov.tr/", 1
        ),
    ]
    assert not (tmp_path / "originals").exists()
