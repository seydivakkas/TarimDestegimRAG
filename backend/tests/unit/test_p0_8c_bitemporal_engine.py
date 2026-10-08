"""Unit tests for P0-8C Bitemporal Declarative Rule Engine.

Validates:
1. Invariant program keys without year suffixes (BASIC_SUPPORT, etc.).
2. Temporal isolation: Year 2029 rules are untouched by 2030 rules.
3. Zero silent fallback: Year 2030 evaluation never falls back to 2026 seed.
4. Validity window (effective_from .. effective_to).
5. Fail-closed policy for DRAFT rules (payable_amount is None).
6. Exact Decimal arithmetic validation.
"""

from datetime import date, datetime, timezone
from decimal import Decimal
import pytest

from tarim_destek_rag.rules.bitemporal_engine import (
    BitemporalRule,
    BitemporalRuleCatalog,
    INVARIANT_PROGRAM_KEYS,
)


@pytest.fixture
def sample_2029_candidate():
    return {
        "schema_version": 1,
        "rule_id": "RULE_2029_BASIC_BUGDAY",
        "program_key": "BASIC_SUPPORT",
        "crop_code": "BUĞDAY",
        "production_year": 2029,
        "province": "*",
        "district": "*",
        "base_coefficient": "480.00",
        "category_multiplier": "1.0000",
        "official_unit_amount": "480.00",
        "unit": "TRY/da",
        "effective_from": "2029-01-01",
        "effective_to": "2029-12-31",
        "published_at": "2028-12-25T10:00:00Z",
        "discovered_at": "2028-12-26T08:00:00Z",
        "source_document_sha256": "a" * 64,
        "source_sentence_id": 101,
        "conditions": {
            "all_of": [
                {"field": "cks_registered", "op": "eq", "value": True},
                {"field": "crop_code", "op": "eq", "value": "BUĞDAY"},
            ]
        },
        "review_status": "DRAFT",
    }


@pytest.fixture
def sample_2030_candidate():
    return {
        "schema_version": 1,
        "rule_id": "RULE_2030_BASIC_BUGDAY",
        "program_key": "BASIC_SUPPORT",
        "crop_code": "BUĞDAY",
        "production_year": 2030,
        "province": "*",
        "district": "*",
        "base_coefficient": "540.00",
        "category_multiplier": "1.0000",
        "official_unit_amount": "540.00",
        "unit": "TRY/da",
        "effective_from": "2030-01-01",
        "effective_to": "2030-12-31",
        "published_at": "2029-12-25T10:00:00Z",
        "discovered_at": "2029-12-26T08:00:00Z",
        "source_document_sha256": "b" * 64,
        "source_sentence_id": 102,
        "conditions": {
            "all_of": [
                {"field": "cks_registered", "op": "eq", "value": True},
                {"field": "crop_code", "op": "eq", "value": "BUĞDAY"},
            ]
        },
        "review_status": "DRAFT",
    }


def test_invariant_program_keys_set():
    assert "BASIC_SUPPORT" in INVARIANT_PROGRAM_KEYS
    assert "PLANNED_PRODUCTION" in INVARIANT_PROGRAM_KEYS
    assert "WATER_RESTRICTION" in INVARIANT_PROGRAM_KEYS
    assert "CERTIFIED_SEED" in INVARIANT_PROGRAM_KEYS
    assert "CERTIFIED_SAPLING" in INVARIANT_PROGRAM_KEYS
    # Must NOT have year suffix in the key
    assert not any("2026" in k or "2030" in k for k in INVARIANT_PROGRAM_KEYS)


def test_bitemporal_candidate_validation_and_arithmetic(sample_2029_candidate):
    rule = BitemporalRuleCatalog.validate_candidate(sample_2029_candidate)
    assert rule.program_key == "BASIC_SUPPORT"
    assert rule.production_year == 2029
    assert rule.official_unit_amount == Decimal("480.00")

    # Tampered arithmetic must fail
    tampered = dict(sample_2029_candidate, official_unit_amount="500.00")
    with pytest.raises(ValueError, match="Aritmetik tutar uyumsuzluğu"):
        BitemporalRuleCatalog.validate_candidate(tampered)


def test_discovery_before_publication_fails(sample_2029_candidate):
    invalid = dict(
        sample_2029_candidate,
        published_at="2028-12-28T00:00:00Z",
        discovered_at="2028-12-20T00:00:00Z",
    )
    with pytest.raises(ValueError, match="Discovery time cannot precede"):
        BitemporalRuleCatalog.validate_candidate(invalid)


def test_strict_temporal_isolation(sample_2029_candidate, sample_2030_candidate):
    catalog = BitemporalRuleCatalog.from_candidates([
        sample_2029_candidate,
        sample_2030_candidate,
    ])

    facts = {"cks_registered": True, "crop_code": "BUĞDAY"}

    # 1. Query for 2029 within 2029 validity window
    res_2029 = catalog.evaluate(
        program_key="BASIC_SUPPORT",
        crop_code="BUĞDAY",
        production_year=2029,
        as_of_date=date(2029, 6, 15),
        facts=facts,
    )
    assert res_2029.production_year == 2029
    assert res_2029.proposed_unit_amount == Decimal("480.00")
    assert res_2029.status == "REVIEW"  # DRAFT rule cannot pay out
    assert res_2029.payable_amount is None

    # 2. Query for 2030 within 2030 validity window
    res_2030 = catalog.evaluate(
        program_key="BASIC_SUPPORT",
        crop_code="BUĞDAY",
        production_year=2030,
        as_of_date=date(2030, 5, 20),
        facts=facts,
    )
    assert res_2030.production_year == 2030
    assert res_2030.proposed_unit_amount == Decimal("540.00")

    # 3. Query for 2031 where NO rule exists -> Must return UNKNOWN, never fallback to 2026/2029/2030
    res_2031 = catalog.evaluate(
        program_key="BASIC_SUPPORT",
        crop_code="BUĞDAY",
        production_year=2031,
        as_of_date=date(2031, 3, 1),
        facts=facts,
    )
    assert res_2031.status == "UNKNOWN"
    assert res_2031.payable_amount is None
    assert res_2031.proposed_unit_amount is None
    assert "Eski yıllara geri dönülemez" in res_2031.reason


def test_effective_date_boundary_isolation(sample_2029_candidate):
    catalog = BitemporalRuleCatalog.from_candidates([sample_2029_candidate])
    facts = {"cks_registered": True, "crop_code": "BUĞDAY"}

    # Querying 2029 production year but as_of_date is before effective_from
    res_before = catalog.evaluate(
        program_key="BASIC_SUPPORT",
        crop_code="BUĞDAY",
        production_year=2029,
        as_of_date=date(2028, 12, 31),
        facts=facts,
    )
    assert res_before.status == "UNKNOWN"

    # Querying 2029 production year after effective_to
    res_after = catalog.evaluate(
        program_key="BASIC_SUPPORT",
        crop_code="BUĞDAY",
        production_year=2029,
        as_of_date=date(2030, 1, 1),
        facts=facts,
    )
    assert res_after.status == "UNKNOWN"


def test_verified_rule_grants_payment(sample_2029_candidate):
    verified_candidate = dict(sample_2029_candidate, review_status="VERIFIED")
    catalog = BitemporalRuleCatalog.from_candidates([verified_candidate])
    facts = {"cks_registered": True, "crop_code": "BUĞDAY"}

    result = catalog.evaluate(
        program_key="BASIC_SUPPORT",
        crop_code="BUĞDAY",
        production_year=2029,
        as_of_date=date(2029, 6, 1),
        facts=facts,
    )
    assert result.status == "ELIGIBLE"
    assert result.payable_amount == Decimal("480.00")
