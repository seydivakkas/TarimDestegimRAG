"""P0-10.7: original amended clauses, year specificity and all-facts HOLD."""
from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import pytest
from tarim_destek_rag.citations.claim_coverage import audit_evaluation_claims
from tarim_destek_rag.citations.claim_source_matrix import (
    audit_claim_matrix,
    validate_source_span,
)

CONFIG = Path("configs")


def _matrix() -> dict:
    return json.loads((CONFIG / "p0_10_7_claim_source_matrix.json").read_text(encoding="utf-8"))


def _manifest() -> dict:
    return json.loads((CONFIG / "p0_10_3_original_source_manifest.json").read_text(encoding="utf-8"))


def _evaluation(year: int = 2026, text: str = "Çiftçi Kayıt Sistemi (ÇKS) kaydı aktif.") -> dict:
    return {
        "parcel": {"production_year": year},
        "rules": [{
            "rule_id": "RULE_BASIC_SUPPORT_2026",
            "support_id": "BASIC_SUPPORT_2026",
            "passed_checks": [text],
            "failed_checks": [],
            "missing_fields": ["verified_support_rate"],
        }],
        "explanations": [],
    }


def test_claims_with_no_verified_source_never_become_payable(tmp_path: Path) -> None:
    matrix, sources = _matrix(), _manifest()
    report = audit_evaluation_claims(
        _evaluation(), claim_matrix=matrix,
        source_manifest=sources, archive_root=tmp_path,
    )
    claim = report["claims"][0]
    assert claim["claim_id"] and len(claim["claim_id"]) == 24
    assert claim["candidate_span_id"] == "BASE_2024_39_ART4_P1"
    assert claim["source_location_status"] == "CLAIM_TO_SOURCE_SPAN_NOT_VERIFIED"
    assert report["claim_level_verified_count"] == 0
    assert report["claim_source_matrix"]["ek20_payment_approved"] is False
    assert report["acceptance"] == "HOLD"
    assert all(c["highlighted_pdf_url"] is None for c in report["claims"])


@pytest.mark.parametrize("year,text", [
    (2025, "Çiftçi Kayıt Sistemi (ÇKS) kaydı aktif."),
    (2027, "Çiftçi Kayıt Sistemi (ÇKS) kaydı aktif."),
    (2026, "ÇKS kaydı aktif."),
])
def test_wrong_year_or_different_wording_has_no_source_mapping(
    tmp_path: Path, year: int, text: str,
) -> None:
    report = audit_claim_matrix(_evaluation(year, text), _matrix(), _manifest(), tmp_path)
    assert report["claims"][0]["candidate_span_id"] is None
    assert report["claims"][0]["acceptance"] == "HOLD"


def test_untrusted_rule_identity_cannot_inherit_another_binding(tmp_path: Path) -> None:
    data = _evaluation()
    data["rules"][0]["rule_id"] = "RULE_CERTIFIED_SEED_2026"
    report = audit_claim_matrix(data, _matrix(), _manifest(), tmp_path)
    assert report["claims"][0]["candidate_span_id"] is None


def test_2025_42_ek20_only_2026_and_not_approved(tmp_path: Path) -> None:
    for year in (2025, 2026, 2027):
        report = audit_claim_matrix(_evaluation(year), _matrix(), _manifest(), tmp_path)
        assert report["ek20_status"] == "HOLD"
        assert report["ek20_payment_approved"] is False
        assert report["claim_verified_count"] == 0


def test_forged_source_hash_or_target_article_is_hold(tmp_path: Path) -> None:
    orig = b"<html><body><b>MADDE 2-</b><span>Exact amended provision for testing.</span></body></html>"
    sha = hashlib.sha256(orig).hexdigest()
    store = tmp_path / "originals"
    store.mkdir()
    (store / (sha + ".html")).write_bytes(orig)
    source = {
        "id": "RG_AMENDMENT_2025_42",
        "original_sha256": sha,
        "url": "https://resmigazete.gov.tr/eskiler/2025/12/20251230-9.htm",
        "format": "html",
    }
    entry = {
        "span_id": "TEST_ART2",
        "source_id": source["id"],
        "source_sha256": sha,
        "source_url": source["url"],
        "article": "MADDE 2",
        "target_provision": "2024/39 MADDE 4(3)",
        "exact_quote": "Exact amended provision for testing.",
    }
    assert validate_source_span(entry, {"sources": [source]}, tmp_path)[
        "source_location_status"
    ] == "ORIGINAL_HTML_SPAN_LOCATED"
    changed = copy.deepcopy(entry)
    changed["article"] = "MADDE 15"
    assert validate_source_span(changed, {"sources": [source]}, tmp_path)[
        "source_location_status"
    ] == "HOLD"
    changed = copy.deepcopy(entry)
    changed["source_sha256"] = "a" * 64
    assert validate_source_span(changed, {"sources": [source]}, tmp_path)[
        "source_location_status"
    ] == "HOLD"
    (store / (sha + ".html")).write_bytes(b"tampered")
    assert validate_source_span(entry, {"sources": [source]}, tmp_path)[
        "source_location_status"
    ] == "HOLD"



def test_genuine_transcribed_ek20_cells_are_all_hold_and_dashes_none(
    tmp_path: Path,
) -> None:
    matrix, sources = _matrix(), _manifest()
    annex = matrix["ek20"]
    sha = annex["source_sha256"]
    originals = tmp_path / "originals"
    originals.mkdir()
    # A forged file can never unlock cell reporting by filename alone.
    (originals / (sha + ".pdf")).write_bytes(b"fake official PDF")
    result = audit_claim_matrix(_evaluation(), matrix, sources, tmp_path)
    assert result["ek20_status"] == "HOLD"
    assert result["ek20_cells"] == []
    assert result["ek20_payment_approved"] is False


def test_ek20_transcript_requires_all_rows_and_nonnegative_cell_values(
    tmp_path: Path,
) -> None:
    # Independent review remains outstanding even when the source is pinned.
    matrix = _matrix()
    assert len(matrix["ek20_visual_transcription"]["rows"]) == 12
    first = matrix["ek20_visual_transcription"]["rows"][0]
    assert first["biological_tl_da"] == 3800
    assert first["biotechnical_tl_da"] is None
    assert matrix["ek20_visual_transcription"]["automatic_rate_activation"] is False
    assert audit_claim_matrix(_evaluation(2025), matrix, _manifest(), tmp_path)[
        "ek20_cells"
    ] == []



def test_original_amendment_highlight_returns_source_bound_sandboxed_copy() -> None:
    from fastapi.testclient import TestClient
    from tarim_destek_rag.api.main import app

    matrix = _matrix()
    sha = matrix["spans"][1]["source_sha256"]
    root = Path("data/legal_update_archive") / "originals"
    if not (root / (sha + ".html")).is_file():
        pytest.skip("Real original amendment not installed in offline CI")
    client = TestClient(app)
    span_id = matrix["spans"][1]["span_id"]
    response = client.get(
        f"/evidence/highlight/amendment/{sha}",
        params={"span_id": span_id},
    )
    assert response.status_code == 200, response.text[:400]
    assert response.content.count(b'id="tarim-evidence-highlight"') == 1
    assert response.headers["x-original-source-sha256"] == sha
    assert "sandbox" in response.headers["content-security-policy"]
    assert (root / (sha + ".html")).read_bytes().find(b"<mark") == -1

    not_this_article = client.get(
        f"/evidence/highlight/amendment/{sha}",
        params={"span_id": "BASE_2024_39_ART4_P1"},
    )
    assert not_this_article.status_code == 409
    wrong_sha = client.get(
        "/evidence/highlight/amendment/" + "a" * 64,
        params={"span_id": span_id},
    )
    assert wrong_sha.status_code == 409


def test_original_2025_42_amendment_clauses_are_exact_when_available() -> None:
    matrix, sources = _matrix(), _manifest()
    root = Path("data/legal_update_archive")
    sha = matrix["spans"][1]["source_sha256"]
    if not (root / "originals" / (sha + ".html")).is_file():
        pytest.skip("Pinned 2025/42 original HTML not installed in offline job")
    for entry in matrix["spans"]:
        result = validate_source_span(entry, sources, root)
        assert result["source_location_status"] == "ORIGINAL_HTML_SPAN_LOCATED", result
        assert result["legal_status"] == "HOLD"
    report = audit_claim_matrix(_evaluation(), matrix, sources, root)
    assert report["normative_source_located_count"] == 1
    assert report["claim_verified_count"] == 0
    assert report["acceptance"] == "HOLD"
    assert report["claims"][0]["highlighted_pdf_url"] is None
    assert len(report["source_spans"]) == 5
    assert any(s["target_provision"] == "GEÇİCİ MADDE 2(1)"
               and s["source_location_status"] == "ORIGINAL_HTML_SPAN_LOCATED"
               for s in report["source_spans"])
    assert report["ek20_status"] in ("VISUAL_TABLE_PENDING_INDEPENDENT_CELL_REVIEW", "HOLD")
    assert report["ek20_payment_approved"] is False
