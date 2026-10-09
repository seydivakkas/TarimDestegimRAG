"""P0-10.3 official original-byte evidence: deterministic fail-closed regression tests."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path
from urllib.parse import urlparse

import pytest
from pypdf import PdfWriter

from scripts.p0_10_3_source_integrity import (
    SourceIntegrityError,
    _atomic_bytes,
    assess_year_coverage,
    collect,
    validate_url,
)

MANIFEST_PATH = Path("configs/p0_10_3_original_source_manifest.json")


@pytest.fixture
def manifest() -> dict:
    # Tests use deterministic synthetic bytes, never confuse synthetic SHA
    # with exact pinned real official-origin HTTP/PDF response digests.
    doc = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    for row in doc["sources"]:
        row["original_sha256"] = None
        row["original_bytes"] = None
    return doc


def _pdf() -> bytes:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=500)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def _responses(manifest: dict) -> dict[str, tuple[bytes, str]]:
    annex_pdf = _pdf()
    result = {}
    for row in manifest["sources"]:
        if row["format"] == "pdf":
            # Blank mock PDFs have no text. Real EK-20 marker validation is
            # separately exercised as a negative case.
            row.pop("expected_pdf_text_marker", None)
            result[row["url"]] = (annex_pdf, "application/pdf")
        else:
            annex_url = next(
                item["url"] for item in manifest["sources"]
                if item.get("parent_id") == row["id"]
            )
            content = (
                "<html><body><p>Gazette official test source</p>"
                f'<a href="{annex_url}">Official annex</a></body></html>'
            ).encode()
            result[row["url"]] = (content, "text/html")
    return result


def _fake_fetch(responses):
    def fetch(url):
        if url not in responses:
            raise SourceIntegrityError("Unavailable original")
        return responses[url]
    return fetch


def test_official_original_source_manifest_pins_real_byte_sha_without_covering_year() -> None:
    raw = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    assert len(raw["sources"]) == 5
    assert raw["complete_official_coverage_proven"] is False
    assert raw["target_production_years"] == [2025, 2026, 2027]
    assert raw["origin_byte_manifest_status"].startswith("PINNED_5_OF_5")
    assert all(
        len(row["original_sha256"]) == 64 and row["original_bytes"] > 1000
        for row in raw["sources"]
    )
    assert all(
        row["provenance_evidence_run_ids"] == [37906860240, 37906865615]
        for row in raw["sources"]
    )
    assert {r["role"] for r in raw["sources"]} == {
        "BASE_DECISION", "BASE_COMMUNIQUE", "BASE_COMMUNIQUE_ANNEX",
        "AMENDMENT", "AMENDMENT_ANNEX",
    }


def test_direct_source_links_to_original_pdf_annexes_are_pinned_in_manifest(
    manifest: dict,
) -> None:
    urls = {row["id"]: row["url"] for row in manifest["sources"]}
    assert urls["RG_AMENDMENT_2025_42_ANNEX"].endswith("20251230-9-1.pdf")
    assert urls["RG_COMMUNIQUE_2024_39_ANNEX"].endswith("20241231M5-8-1.pdf")


def test_collect_recorded_byte_hashes_match_original_source_bytes(
    manifest: dict, tmp_path: Path,
) -> None:
    responses = _responses(manifest)
    result = collect(manifest, tmp_path, mode="collect", fetch=_fake_fetch(responses))
    assert result["source_status"] == "PASS"
    assert result["year_scope_completeness"] == "NOT_PROVEN"
    assert result["legal_activation"] is False
    assert len(result["documents"]) == 5
    for doc in result["documents"]:
        body = responses[doc["url"]][0]
        assert doc["sha256"] == hashlib.sha256(body).hexdigest()
        assert doc["original_response"] is True
        assert doc["pinned"] is False
        suffix = ".pdf" if urlparse(doc["url"]).path.endswith(".pdf") else ".html"
        assert (tmp_path / "originals" / (doc["sha256"] + suffix)).read_bytes() == body
    assert (tmp_path / "report.json").exists()


def test_verify_refuses_to_approve_a_missing_digest(
    manifest: dict, tmp_path: Path,
) -> None:
    result = collect(
        manifest, tmp_path, mode="verify",
        fetch=_fake_fetch(_responses(manifest)),
    )
    assert result["source_status"] == "HOLD"
    assert len(result["errors"]) == 5
    assert all("Unpinned" in x["error"] for x in result["errors"])


def test_verify_accepts_only_correct_pinned_byte_digests(
    manifest: dict, tmp_path: Path,
) -> None:
    responses = _responses(manifest)
    for row in manifest["sources"]:
        row["original_sha256"] = hashlib.sha256(responses[row["url"]][0]).hexdigest()
        if row["id"] == "RG_AMENDMENT_2025_42_ANNEX":
            row.pop("expected_pdf_text_marker", None)
    result = collect(manifest, tmp_path, mode="verify", fetch=_fake_fetch(responses))
    assert result["source_status"] == "PASS"
    assert all(r["pinned"] for r in result["documents"])
    assert result["year_scope_completeness"] == "NOT_PROVEN"
    # Repeat with identical source bytes to check immutable replay and report overwrite.
    again = collect(manifest, tmp_path, mode="verify", fetch=_fake_fetch(responses))
    assert again["source_status"] == "PASS"


def test_verify_refuses_altered_original_document(
    manifest: dict, tmp_path: Path,
) -> None:
    responses = _responses(manifest)
    for row in manifest["sources"]:
        row["original_sha256"] = hashlib.sha256(responses[row["url"]][0]).hexdigest()
        row.pop("expected_pdf_text_marker", None)
    first_key = manifest["sources"][0]["url"]
    old = responses[first_key]
    responses[first_key] = (old[0] + b"tampered", old[1])
    report = collect(manifest, tmp_path, mode="verify", fetch=_fake_fetch(responses))
    assert report["source_status"] == "HOLD"
    assert any("differs from pinned manifest" in x["error"] for x in report["errors"])


def test_missing_annex_href_is_not_documented_as_verified(
    manifest: dict, tmp_path: Path,
) -> None:
    responses = _responses(manifest)
    parent = next(x for x in manifest["sources"] if x["id"] == "RG_AMENDMENT_2025_42")
    responses[parent["url"]] = (b"<html><body>No annex link</body></html>", "text/html")
    report = collect(manifest, tmp_path, mode="collect", fetch=_fake_fetch(responses))
    assert report["source_status"] == "HOLD"
    assert any(x["stage"] == "PARENT_ANNEX_LINK" for x in report["errors"])


def test_missing_official_annex_bytes_fail_closed(
    manifest: dict, tmp_path: Path,
) -> None:
    responses = _responses(manifest)
    annex = next(x for x in manifest["sources"] if x["id"] == "RG_AMENDMENT_2025_42_ANNEX")
    del responses[annex["url"]]
    report = collect(manifest, tmp_path, mode="collect", fetch=_fake_fetch(responses))
    assert report["source_status"] == "HOLD"
    assert any(x["id"] == annex["id"] for x in report["errors"])


def test_pdf_magic_and_trailer_cannot_be_html_disguised_as_pdf(
    manifest: dict, tmp_path: Path,
) -> None:
    responses = _responses(manifest)
    url = manifest["sources"][0]["url"]
    responses[url] = (b"<html>not pdf</html>", "application/pdf")
    result = collect(manifest, tmp_path, mode="collect", fetch=_fake_fetch(responses))
    assert result["source_status"] == "HOLD"
    assert any("PDF magic/trailer" in x["error"] for x in result["errors"])


@pytest.mark.parametrize("url", [
    "http://resmigazete.gov.tr/eskiler/2024/12/x.pdf",
    "https://evil.example/eskiler/x.pdf",
    "https://resmigazete.gov.tr.evil.example/x.pdf",
    "https://evil.example@resmigazete.gov.tr/x.pdf",
    "https://resmigazete.gov.tr:8443/x.pdf",
    "https://resmigazete.gov.tr/x.pdf#fragment",
])
def test_unapproved_official_url_must_fail_closed(url: str) -> None:
    with pytest.raises(SourceIntegrityError):
        validate_url(url)


def test_immutable_original_bytes_cannot_be_replaced(tmp_path: Path) -> None:
    path = tmp_path / "originals" / "pinned.html"
    _atomic_bytes(path, b"original")
    _atomic_bytes(path, b"original")
    with pytest.raises(SourceIntegrityError):
        _atomic_bytes(path, b"silently-replaced")
    assert path.read_bytes() == b"original"


@pytest.mark.parametrize("year", [2025, 2026, 2027])
def test_production_year_coverage_cannot_be_claimed_from_only_five_sources(
    manifest: dict, year: int,
) -> None:
    report = {
        "source_status": "PASS", "errors": [],
        "documents": [
            {"id": row["id"], "pinned": True}
            for row in manifest["sources"]
        ],
    }
    result = assess_year_coverage(manifest, report, year)
    assert result["status"] == "HOLD"
    assert "OFFICIAL_INDEX_AND_AMENDMENT_RECALL_NOT_PROVEN" in result["reasons"]
    assert result["legal_activation"] is False
    if year == 2025:
        assert "PRIOR_YEAR_TRANSITION_MUST_BE_REVIEWED" in result["reasons"]


def test_2026_missing_amendment_annex_forces_incomplete_scope(
    manifest: dict,
) -> None:
    report = {
        "source_status": "HOLD", "errors": [],
        "documents": [
            {"id": row["id"], "pinned": True}
            for row in manifest["sources"]
            if row["id"] != "RG_AMENDMENT_2025_42_ANNEX"
        ],
    }
    result = assess_year_coverage(manifest, report, 2026)
    assert result["status"] == "HOLD"
    assert result["missing_source_ids"] == ["RG_AMENDMENT_2025_42_ANNEX"]



def test_pinned_original_byte_pass_does_not_validate_unreadable_annex_table(
    manifest: dict, tmp_path: Path,
) -> None:
    responses = _responses(manifest)
    for row in manifest["sources"]:
        row["original_sha256"] = hashlib.sha256(responses[row["url"]][0]).hexdigest()
    annex = next(
        row for row in manifest["sources"]
        if row["id"] == "RG_AMENDMENT_2025_42_ANNEX"
    )
    annex["expected_pdf_text_marker"] = "EK-20"
    report = collect(
        manifest, tmp_path, mode="verify", fetch=_fake_fetch(responses)
    )
    assert report["original_byte_integrity_status"] == "PASS"
    assert report["source_status"] == "HOLD"
    assert report["annex_table_semantics_status"] == "HOLD"
    assert any(e["stage"] == "ANNEX_SEMANTIC_CONTENT" for e in report["errors"])
