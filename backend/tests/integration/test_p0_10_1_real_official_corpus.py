"""P0-10.1: pinned genuine-source replay, with six independent real-source parser regression contracts.

The captures are third-party HTML representations of official Resmi Gazete pages,
NOT byte-identical original legal documents. Their SHA-256 checks verify capture
immutability only; none of these tests authorizes legal/rate publication.
Former XFAIL contracts are now required to PASS on real captured source text.
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


def test_real_2024_39_classifies_by_own_heading_not_cited_presidential_decision() -> None:
    text = _real_source_text("communique_2024_39")
    assert LegislationAnalyzer.classify_type(text) == LegislationType.BAKANLIK_TEBLIGI


def test_real_2025_42_own_number_is_not_base_2024_39() -> None:
    text = _real_source_text("amendment_2025_42")
    identity = LegislationAnalyzer.extract_identity(text)
    assert identity.number == "2025/42"


def test_real_2025_42_amends_actual_2024_39_fifth_duplicate_issue() -> None:
    text = _real_source_text("amendment_2025_42")
    amendment = LegislationAnalyzer.extract_amendment_target(text)
    assert amendment is not None
    assert amendment.base_legislation_no == "2024/39"
    assert amendment.base_rg_date == "2024-12-31"
    assert amendment.base_rg_number == "32769"


def test_real_2025_42_effective_date_is_not_gazette_publication_date() -> None:
    text = _real_source_text("amendment_2025_42")
    effective = LegislationAnalyzer.extract_effective_dates(text, default_rg_date="2025-12-30")
    assert effective.effective_date == "2026-01-01"


def test_real_2024_39_article_22_is_not_publication_day() -> None:
    text = _real_source_text("communique_2024_39")
    effective = LegislationAnalyzer.extract_effective_dates(text, default_rg_date="2024-12-31")
    assert effective.effective_date == "2025-01-01"
    assert effective.is_publication_date is False
    assert effective.article_effective_dates["MADDE 10"] == "2025-05-01"


def test_real_2025_42_annex_is_not_substituted_with_entire_page_hash() -> None:
    text = _real_source_text("amendment_2025_42")
    annexes = LegislationAnalyzer.extract_annex_tables([text])
    assert any(a.annex_code == "EK-20" for a in annexes)
    page_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()
    assert all(a.content_sha256 is None for a in annexes if a.annex_code == "EK-20")
    assert page_hash not in {a.content_sha256 for a in annexes}


def test_real_2025_42_issuing_gazette_metadata_is_not_amended_gazette() -> None:
    text = _real_source_text("amendment_2025_42")
    identity = LegislationAnalyzer.extract_identity(text)
    assert identity.rg_date == "2025-12-30"
    assert identity.rg_number == "33123"


def test_real_2024_39_original_gazette_metadata_is_from_own_heading() -> None:
    text = _real_source_text("communique_2024_39")
    identity = LegislationAnalyzer.extract_identity(text)
    assert identity.rg_date == "2024-12-31"
    assert identity.rg_number == "32769"


def test_unknown_effective_date_is_not_fabricated_from_gazette() -> None:
    document = "RESMÎ GAZETE 1/2/2026\nTEBLİĞ NO: 2026/1\nMADDE 1- Usul."
    dates = LegislationAnalyzer.extract_effective_dates(
        document, default_rg_date="2026-02-01"
    )
    assert dates.effective_date is None
    assert dates.is_publication_date is False
    assert dates.article_effective_dates == {}


def test_publication_day_clause_is_supported_when_explicit() -> None:
    document = (
        "TEBLİĞ NO: 2026/2\n"
        "MADDE 1- Kapsam.\n"
        "MADDE 2- Bu Tebliğ yayımı tarihinde yürürlüğe girer."
    )
    dates = LegislationAnalyzer.extract_effective_dates(
        document, default_rg_date="2026-02-01"
    )
    assert dates.effective_date == "2026-02-01"
    assert dates.is_publication_date is True
