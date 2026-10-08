"""Unit tests for P0-8D Atomic Snapshot Publisher and conflict detection.

Validates:
1. Conflict detection: overlapping validity periods with conflicting rates fails validation (PUBLISH BLOCKED).
2. Multi-year mixture rejection: snapshot must contain exactly one target production year.
3. Content-addressed deterministic snapshot hash calculation.
4. Clean validation when all rules are mutually consistent.
"""

from decimal import Decimal
import pytest

from tarim_destek_rag.auto_updater.atomic_publisher import (
    AtomicSnapshotPublisher,
    PublishConflictError,
)


@pytest.fixture
def valid_snapshot_rules():
    return [
        {
            "schema_version": 1,
            "rule_id": "R_2030_BASIC_WHEAT",
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
            "source_document_sha256": "c" * 64,
            "source_sentence_id": 201,
            "conditions": {
                "all_of": [
                    {"field": "cks_registered", "op": "eq", "value": True},
                    {"field": "crop_code", "op": "eq", "value": "BUĞDAY"},
                ]
            },
            "review_status": "DRAFT",
        },
        {
            "schema_version": 1,
            "rule_id": "R_2030_BASIC_BARLEY",
            "program_key": "BASIC_SUPPORT",
            "crop_code": "ARPA",
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
            "source_document_sha256": "c" * 64,
            "source_sentence_id": 202,
            "conditions": {
                "all_of": [
                    {"field": "cks_registered", "op": "eq", "value": True},
                    {"field": "crop_code", "op": "eq", "value": "ARPA"},
                ]
            },
            "review_status": "DRAFT",
        },
    ]


def test_valid_snapshot_passes_validation(valid_snapshot_rules):
    result = AtomicSnapshotPublisher.validate_snapshot(valid_snapshot_rules)
    assert result.is_valid is True
    assert result.target_production_year == 2030
    assert result.rule_count == 2
    assert len(result.snapshot_sha256) == 64
    assert result.errors == ()


def test_mixed_years_rejected(valid_snapshot_rules):
    # Alter second rule to 2029
    mixed = [
        valid_snapshot_rules[0],
        dict(valid_snapshot_rules[1], production_year=2029, rule_id="R_2029_BARLEY"),
    ]
    result = AtomicSnapshotPublisher.validate_snapshot(mixed)
    assert result.is_valid is False
    assert any("tek bir üretim yılına" in err for err in result.errors)


def test_conflicting_rates_blocks_publish(valid_snapshot_rules):
    # Introduce second rule for same crop (BUĞDAY) in same year with overlapping window and different rate
    conflicting_rule = dict(
        valid_snapshot_rules[0],
        rule_id="R_2030_CONFLICT_WHEAT",
        base_coefficient="500.00",
        official_unit_amount="500.00",
    )
    conflicting_bundle = [valid_snapshot_rules[0], conflicting_rule]
    result = AtomicSnapshotPublisher.validate_snapshot(conflicting_bundle)
    assert result.is_valid is False
    assert any("Çakışma tespit edildi" in err for err in result.errors)
    assert any("YAYIN ENGELLENDİ" in err for err in result.errors)


def test_deterministic_digest_calculation(valid_snapshot_rules):
    digest1 = AtomicSnapshotPublisher.compute_snapshot_digest(valid_snapshot_rules)
    digest2 = AtomicSnapshotPublisher.compute_snapshot_digest(valid_snapshot_rules)
    assert digest1 == digest2
    assert len(digest1) == 64
