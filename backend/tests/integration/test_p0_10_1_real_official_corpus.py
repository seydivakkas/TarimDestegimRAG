"""P0-10.1: pinned genuine-source replay, with explicit known regression RED cases.

The captures are third-party HTML representations of official Resmi Gazete pages,
NOT byte-identical original legal documents. Their SHA-256 checks verify capture
immutability only; none of these tests authorizes legal/rate publication.
Known failed contracts use strict xfail so any unexpected XPASS forces a review.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from tarim_destek_rag.updates.legislation_analyzer import LegislationAnalyzer
from tarim_destek_rag.updates.legislation_models import LegislationType

CORPUS_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "p0_10_official"
MANIFEST = json.loads((CORPUS_ROOT / "manifest.json").read_text(encoding="utf-8"))
DOCUMENTS = {row["key"]: row for row in MANIFEST["documents"]}


def _capture_bytes(key: str) -> bytes:
    rec = DOCUMENTS[key]
    return (CORPUS_ROOT / Path(rec["path"]).name).read_bytes()


def _real_source_text(key: str) -> str:
    return "\n".join(LegislationAnalyzer.extract_pages(_capture_bytes(key), "text/html"))


@pytest.mark.parametrize("key", sorted(DOCUMENTS))
def test_captured_real_official_source_bytes_are_pinned(key: str) -> None:
    item = DOCUMENTS[key]
    blob = _capture_bytes(key)
    assert len(blob) == item["capture_bytes"]
    assert hashlib.sha256(blob).hexdigest() == item["capture_sha256"]
    assert item["capture_http_status"] == 200
    assert item["source_url"].startswith("https://")
    assert item["original_source_sha256"] is None
    assert item["stage"] == "DRAFT_AWAITING_BYTE_EXACT_SOURCE"


def test_real_corpus_cannot_claim_full_legal_coverage_or_payout() -> None:
    assert MANIFEST["coverage_status"].startswith("INCOMPLETE")
    assert MANIFEST["complete_official_coverage_proven"] is False
    assert MANIFEST["legal_activation"] is False
    assert len(DOCUMENTS) == 3


def test_real_decision_8859_is_detected_as_presidential_decision() -> None:
    text = _real_source_text("decision_8859")
    identity = LegislationAnalyzer.extract_identity(text)
    assert identity.legislation_type == LegislationType.CUMHURBASKANI_KARARI
    assert identity.number == "8859"


def test_real_2025_42_is_recognized_as_amendment_type() -> None:
    text = _real_source_text("amendment_2025_42")
    assert LegislationAnalyzer.classify_type(text) == LegislationType.DEGISIKLIK_TEBLIGI


@pytest.mark.xfail(strict=True, reason="P010-A01: citation of Decision 8859 in real 2024/39 must not turn a communique into a decision")
def test_real_2024_39_classifies_by_own_heading_not_cited_presidential_decision() -> None:
    text = _real_source_text("communique_2024_39")
    assert LegislationAnalyzer.classify_type(text) == LegislationType.BAKANLIK_TEBLIGI


@pytest.mark.xfail(strict=True, reason="P010-A02: own amendment number 2025/42 comes after cited base number 2024/39")
def test_real_2025_42_own_number_is_not_base_2024_39() -> None:
    text = _real_source_text("amendment_2025_42")
    identity = LegislationAnalyzer.extract_identity(text)
    assert identity.number == "2025/42"


@pytest.mark.xfail(strict=True, reason="P010-A03: 32769 beşinci mükerrer base reference needs a dedicated reference grammar")
def test_real_2025_42_amends_actual_2024_39_fifth_duplicate_issue() -> None:
    text = _real_source_text("amendment_2025_42")
    amendment = LegislationAnalyzer.extract_amendment_target(text)
    assert amendment is not None
    assert amendment.base_legislation_no == "2024/39"
    assert amendment.base_rg_date == "2024-12-31"
    assert amendment.base_rg_number == "32769"


@pytest.mark.xfail(strict=True, reason="P010-A05: official 2025/42 entered force 1 Jan 2026, not publication day")
def test_real_2025_42_effective_date_is_not_gazette_publication_date() -> None:
    text = _real_source_text("amendment_2025_42")
    effective = LegislationAnalyzer.extract_effective_dates(text, default_rg_date="2025-12-30")
    assert effective.effective_date == "2026-01-01"


@pytest.mark.xfail(strict=True, reason="P010-A05: 2024/39 Article 22 has separate 1 Jan/1 May 2025 effective dates")
def test_real_2024_39_article_22_is_not_publication_day() -> None:
    text = _real_source_text("communique_2024_39")
    effective = LegislationAnalyzer.extract_effective_dates(text, default_rg_date="2024-12-31")
    assert effective.effective_date == "2025-01-01"
    assert effective.is_publication_date is False


@pytest.mark.xfail(strict=True, reason="P010-A07: a reference to EK-20 is not a hashed independently acquired annex")
def test_real_2025_42_annex_is_not_substituted_with_entire_page_hash() -> None:
    text = _real_source_text("amendment_2025_42")
    annexes = LegislationAnalyzer.extract_annex_tables([text])
    assert any(a.annex_code == "EK-20" for a in annexes)
    page_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert all(a.content_sha256 != page_hash for a in annexes if a.annex_code == "EK-20")
