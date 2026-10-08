"""Official 2026 published combined totals are reference data, not entitlements."""

import json
from decimal import Decimal

import pytest

from tarim_destek_rag.normalization.official_rates import (
    DEFAULT_CATALOG,
    find_legacy_rate_discrepancies,
    load_official_reference,
    reference_rates_by_crop,
)


def test_official_source_metadata_and_coefficient():
    catalog = load_official_reference()
    assert catalog["production_year"] == 2026
    assert catalog["base_support_coefficient"]["amount"] == "367.00"
    assert catalog["source"]["published_on"] == "2026-09-08"
    assert catalog["legal_reference"]["decision_number"] == "11781"
    assert catalog["source"]["content_sha256"] is None
    assert catalog["legal_use_constraints"]["calculate_individual_entitlement_allowed"] is False


def test_published_totals_are_combined_and_not_component_rates():
    rates = reference_rates_by_crop()
    assert rates["BUĞDAY"].amount_per_da == Decimal("954.00")
    assert rates["ARPA"].amount_per_da == Decimal("954.00")
    assert rates["MISIR_DANE"].amount_per_da == Decimal("954.00")
    assert rates["AYÇİÇEĞİ_YAĞLIK"].amount_per_da == Decimal("1101.00")
    assert rates["PAMUK"].amount_per_da == Decimal("1652.00")
    assert rates["PATATES"].amount_per_da == Decimal("734.00")
    assert rates["MERCİMEK"].amount_per_da == Decimal("734.00")
    assert len(rates) == 13
    assert all(not r.individual_entitlement_approved for r in rates.values())


def test_legacy_seed_wheat_total_disagrees_with_ministry():
    discrepancies = find_legacy_rate_discrepancies(
        {
            ("BASIC_SUPPORT_2026", "BUĞDAY"): Decimal("465.00"),
            ("PLANNED_PRODUCTION_2026", "BUĞDAY"): Decimal("465.00"),
        }
    )
    assert len(discrepancies) == 1
    discrepancy = discrepancies[0]
    assert discrepancy.crop_code == "BUĞDAY"
    assert discrepancy.legacy_sum == Decimal("930.00")
    assert discrepancy.delta == Decimal("24.00")


def test_missing_component_does_not_mean_zero_amount():
    assert find_legacy_rate_discrepancies(
        {("BASIC_SUPPORT_2026", "BUĞDAY"): Decimal("465.00")}
    ) == []


@pytest.mark.parametrize(
    "field,value",
    [
        ("calculate_individual_entitlement_allowed", True),
        ("split_into_program_rates_allowed", True),
    ],
)
def test_tampered_usage_policy_rejected(tmp_path, field, value):
    data = json.loads(DEFAULT_CATALOG.read_text(encoding="utf-8"))
    data["legal_use_constraints"][field] = value
    testfile = tmp_path / "tampered.json"
    testfile.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_official_reference(testfile)


def test_duplicate_crop_reference_rejected(tmp_path):
    data = json.loads(DEFAULT_CATALOG.read_text(encoding="utf-8"))
    data["combined_support_references"].append(
        {
            "crop_codes": ["BUĞDAY"],
            "amount_per_da": "1.00",
            "context": "duplicate",
        }
    )
    testfile = tmp_path / "duplicate.json"
    testfile.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(ValueError):
        load_official_reference(testfile)
