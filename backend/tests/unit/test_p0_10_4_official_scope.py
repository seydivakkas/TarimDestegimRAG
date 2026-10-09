"""P0-10.4 original-PDF visual table + indexed legal-temporal graph contracts.

All tests are deterministic; legal-year completeness remains strictly HOLD.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.p0_10_4_temporal_audit import (
    CoverageContractError,
    audit_year,
    build_report,
    validate_ek20,
    validate_inventory,
)

CONFIG = Path("configs")


@pytest.fixture
def inventory() -> dict:
    return json.loads(
        (CONFIG / "p0_10_4_legal_inventory.json").read_text(encoding="utf-8")
    )


@pytest.fixture
def annex() -> dict:
    return json.loads(
        (CONFIG / "p0_10_4_ek20_visual_transcription.json").read_text(
            encoding="utf-8"
        )
    )


@pytest.fixture
def originals() -> dict:
    return json.loads(
        (CONFIG / "p0_10_3_original_source_manifest.json").read_text(
            encoding="utf-8"
        )
    )


def test_actual_EK20_pdf_one_page_12_rows_frozen_sha(
    annex: dict, originals: dict,
) -> None:
    validate_ek20(annex, originals)
    assert annex["source_sha256"] == (
        "6984c901775212e0500148cbbb2d87ea34ad3783e10d6c798fa9ca320bf06a79"
    )
    assert annex["source_pdf_page_count"] == 1
    assert len(annex["rows"]) == 12
    assert annex["automatic_rate_activation"] is False
    assert annex["independent_legal_reviewer_approved"] is False


@pytest.mark.parametrize("year", [2025, 2026, 2027])
def test_ek20_is_2026_only_not_assumed_applicable_to_other_years(
    annex: dict, year: int,
) -> None:
    assert (year == annex["production_year"]) is (year == 2026)


def test_ek20_package_amounts_derived_from_visually_inspected_cells(
    annex: dict, originals: dict,
) -> None:
    validate_ek20(annex, originals)
    data = {x["row_id"]: x for x in annex["rows"]}
    assert data["greenhouse_mixed"]["biological_tl_da"] == 3800
    assert data["greenhouse_mixed"]["feromone_trap_tl_da"] == 850
    assert annex["package_support"]["greenhouse_kobuks_tl_da"] == 4650
    assert data["citrus"]["biological_tl_da"] == 700
    assert data["citrus"]["feromone_trap_tl_da"] == 850
    assert annex["package_support"]["open_field_tl_da"] == 1550
    assert data["open_tomato"]["feromone_only_tl_da"] == 250
    assert data["olive"]["biotechnical_tl_da"] == 310
    assert data["peach"]["feromone_only_tl_da"] == 310
    assert data["nectarine"]["feromone_only_tl_da"] == 310


def test_visual_dash_is_not_a_zero_amount(
    annex: dict, originals: dict,
) -> None:
    assert next(r for r in annex["rows"] if r["row_id"] == "apple")[
        "biological_tl_da"
    ] is None
    corrupted = copy.deepcopy(annex)
    next(r for r in corrupted["rows"] if r["row_id"] == "apple")[
        "biological_tl_da"
    ] = -1
    with pytest.raises(CoverageContractError):
        validate_ek20(corrupted, originals)


def test_ek20_detects_a_forged_original_pdf_hash(
    annex: dict, originals: dict,
) -> None:
    changed = copy.deepcopy(annex)
    changed["source_sha256"] = "f" * 64
    with pytest.raises(CoverageContractError, match="pinned original PDF"):
        validate_ek20(changed, originals)


def test_ek20_rows_cannot_be_silently_omitted(
    annex: dict, originals: dict,
) -> None:
    changed = copy.deepcopy(annex)
    changed["rows"].pop()
    with pytest.raises(CoverageContractError, match="Incomplete/duplicate"):
        validate_ek20(changed, originals)


def test_full_inventory_includes_missing_2025_and_2026_changes(
    inventory: dict,
) -> None:
    validate_inventory(inventory)
    by_number = {row["number"]: row for row in inventory["documents"]}
    assert by_number["2025/13"]["retroactive_valid_from"] == "2025-01-01"
    assert by_number["10394"]["effective_date"] == "2026-01-01"
    assert by_number["2025/42"]["preserves_prior_year"] == [2025]
    assert by_number["11781"]["effective_date"] == "2027-01-01"
    assert by_number["11781"]["retroactive_validity_from"]["MADDE 4"] == (
        "2025-01-01"
    )
    assert by_number["11781"]["retroactive_validity_from"]["MADDE 1(a)"] == (
        "2026-01-01"
    )
    assert by_number["2024/39"]["article_exceptions"]["MADDE 10"] == (
        "2025-05-01"
    )


def test_repeals_include_all_three_explicit_base_2024_39_targets(
    inventory: dict,
) -> None:
    by_id = {d["id"]: d for d in inventory["documents"]}
    for name in ["repealed_2022_32", "repealed_2022_34", "repealed_2023_48"]:
        assert by_id[name]["repealed_by"] == "communique_2024_39"
        assert by_id[name]["original_sha256"] is None
    assert by_id["repealed_2022_32"]["repeal_article"] == "MADDE 21(1)"


def test_partial_inventory_must_fail_closed_when_2025_13_is_removed(
    inventory: dict,
) -> None:
    changed = copy.deepcopy(inventory)
    changed["documents"] = [
        d for d in changed["documents"] if d["id"] != "communique_2025_13"
    ]
    with pytest.raises(CoverageContractError, match="Missing identified"):
        validate_inventory(changed)


def test_partial_inventory_must_fail_closed_when_11781_is_removed(
    inventory: dict,
) -> None:
    changed = copy.deepcopy(inventory)
    changed["documents"] = [
        d for d in changed["documents"] if d["id"] != "decision_11781"
    ]
    with pytest.raises(CoverageContractError, match="Missing identified"):
        validate_inventory(changed)


def test_broken_amendment_graph_is_rejected(inventory: dict) -> None:
    changed = copy.deepcopy(inventory)
    target = next(
        d for d in changed["documents"] if d["id"] == "decision_10394"
    )
    target["amends"] = "unknown_8859"
    with pytest.raises(CoverageContractError, match="Broken amends"):
        validate_inventory(changed)


def test_false_completeness_claim_is_rejected(inventory: dict) -> None:
    changed = copy.deepcopy(inventory)
    changed["exhaustive_archive_index_scan_completed"] = True
    with pytest.raises(CoverageContractError, match="full Gazette/Ministry"):
        validate_inventory(changed)


@pytest.mark.parametrize("year", [2025, 2026, 2027])
def test_all_years_hold_for_unproven_official_index_and_amendment_recall(
    inventory: dict, year: int,
) -> None:
    result = audit_year(inventory, year)
    assert result["status"] == "HOLD"
    assert result["source_inventory_is_complete"] is False
    assert result["automatic_rate_activation"] is False
    assert result["missing_gates"]
    assert len(result["unpinned_or_unarchived_source_ids"]) >= 3


def test_2025_requires_two_transition_checks_and_one_retroactivity_check(
    inventory: dict,
) -> None:
    flags = audit_year(inventory, 2025)["legal_time_review_flags"]
    assert any("2025/13" in flag for flag in flags)
    assert any("10394" in flag for flag in flags)
    assert any("11781" in flag for flag in flags)


def test_2026_checks_11781_retroactive_effect(inventory: dict) -> None:
    flags = audit_year(inventory, 2026)["legal_time_review_flags"]
    assert any("11781" in flag for flag in flags)
    assert any("10394" in flag for flag in flags)


def test_2027_future_update_coverage_cannot_be_preadjudicated(
    inventory: dict,
) -> None:
    flags = audit_year(inventory, 2027)["legal_time_review_flags"]
    assert any("FUTURE_UPDATES" in flag for flag in flags)


def test_end_to_end_source_and_legal_gate_remains_unapproved(
    inventory: dict, annex: dict, originals: dict,
) -> None:
    report = build_report(inventory, annex, originals)
    assert report["ek20_original_pdf_visual_table_status"] == (
        "TRANSCRIBED_NEEDS_INDEPENDENT_REVIEW"
    )
    assert report["complete_official_coverage_proven"] is False
    assert report["legal_approval"] is False
    assert report["payable_activation"] is False
    assert {x["year"] for x in report["production_year_assessments"]} == {
        2025, 2026, 2027
    }
