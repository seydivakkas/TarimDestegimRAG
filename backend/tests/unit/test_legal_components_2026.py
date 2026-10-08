"""2026 legal component golden cases; stale 310 TL source must not be used."""

import json
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from tarim_destek_rag.calculator.calculator import SupportCalculator
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.models import (
    SourceVersionModel,
    SupportProgramModel,
    VerifiedSupportRateModel,
)
from tarim_destek_rag.database.repository import SupportRepository
from tarim_destek_rag.models.farmer_parcel import FarmerProfile, Parcel
from tarim_destek_rag.normalization.legal_components_2026 import (
    CATALOG,
    PROGRAMS,
    UNVERIFIED_CONTENT_HASH,
    load_component_catalog,
    stage_component_rates,
)
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.rules.orchestrator import DecisionOrchestrator


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add_all([
            SupportProgramModel(id=p, name=p, year=2026, active=True)
            for p in sorted(PROGRAMS)
        ])
        s.commit()
        yield s
    engine.dispose()


def mapping():
    data = load_component_catalog()
    return {(x["program_id"], x["crop_name"]): Decimal(x["unit_amount"])
            for x in data["components"]}


@pytest.mark.parametrize("program,crop,expected", [
    ("BASIC_SUPPORT_2026", "BUĞDAY", "477.10"),
    ("PLANNED_PRODUCTION_2026", "BUĞDAY", "477.10"),
    ("BASIC_SUPPORT_2026", "MISIR_DANE", "477.10"),
    ("PLANNED_PRODUCTION_2026", "MISIR_DANE", "477.10"),
    ("BASIC_SUPPORT_2026", "AYÇİÇEĞİ_YAĞLIK", "550.50"),
    ("PLANNED_PRODUCTION_2026", "AYÇİÇEĞİ_YAĞLIK", "550.50"),
    ("BASIC_SUPPORT_2026", "PAMUK_KÜTLÜ", "825.75"),
    ("PLANNED_PRODUCTION_2026", "PAMUK_KÜTLÜ", "825.75"),
    ("BASIC_SUPPORT_2026", "MERCİMEK", "367.00"),
    ("PLANNED_PRODUCTION_2026", "MERCİMEK", "367.00"),
    ("CERTIFIED_SEED_2026", "BUĞDAY", "205.52"),
    ("CERTIFIED_SEED_2026", "PATATES", "807.40"),
    ("CERTIFIED_SAPLING_2026", "FINDIK", "1835.00"),
    ("WATER_RESTRICTION_2026", "MERCİMEK", "293.60"),
    ("WATER_RESTRICTION_2026", "BUĞDAY", "513.80"),
    ("WATER_RESTRICTION_2026", "AYÇİÇEĞİ_YAĞLIK", "440.40"),
])
def test_2026_documented_coefficient_cases(program, crop, expected):
    assert mapping()[(program, crop)] == Decimal(expected)


def test_scope_and_2027_exclusions():
    doc = load_component_catalog()
    assert doc["production_year"] == 2026
    assert doc["base_coefficient"] == "367.00"
    assert doc["source_version"]["content_hash"] is None
    assert doc["validation_gate"]["primary_pdf_byte_hash_verified"] is True
    observed = {
        x["id"]: x["sha256_of_fetched_pdf_bytes"] for x in doc["citations"]
        if "sha256_of_fetched_pdf_bytes" in x
    }
    assert len(observed) == 3
    assert doc["source_version"]["primary_pdf_sha256_observed"] == observed["RG-2026-11781"]
    assert doc["validation_gate"]["approval"] is False
    assert all(x["review_status"] == "DRAFT" for x in doc["components"])
    assert len(doc["components"]) == 56
    assert len(doc["citations"]) >= 4
    assert any("2027" in x for x in doc["not_applicable_to_2026"])


def test_no_2027_chickpea_extra_or_seed_coefficient_leak():
    rates = mapping()
    assert rates[("PLANNED_PRODUCTION_2026", "NOHUT")] == Decimal("367.00")
    assert rates[("CERTIFIED_SEED_2026", "BUĞDAY")] == Decimal("205.52")
    assert rates[("BASIC_SUPPORT_2026", "FINDIK")] == Decimal("550.50")


def test_default_dry_run_has_no_database_side_effect(session):
    assert stage_component_rates(session) == 56
    assert session.scalars(select(VerifiedSupportRateModel)).all() == []
    assert session.scalars(select(SourceVersionModel)).all() == []


def test_explicit_stage_is_idempotent_preserves_unverified_hash_and_blocks_calculation(session):
    assert stage_component_rates(session, apply=True) == 56
    session.commit()
    assert stage_component_rates(session, apply=True) == 0
    session.commit()
    versions = session.scalars(select(SourceVersionModel)).all()
    assert len(versions) == 1
    assert versions[0].content_hash == UNVERIFIED_CONTENT_HASH
    assert versions[0].version == 0
    assert len(session.scalars(select(VerifiedSupportRateModel)).all()) == 56
    assert all(r.review_status == "DRAFT" and r.approved_by is None
               for r in session.scalars(select(VerifiedSupportRateModel)).all())

    repo = SupportRepository(session)
    assert repo.get_amount(
        "BASIC_SUPPORT_2026", "BUĞDAY",
        production_year=2026, province="KONYA", district="KARATAY",
        as_of=date(2026, 10, 8),
    ) is None
    farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    parcel = Parcel(crop="BUĞDAY", area_da=Decimal("12.4"), production_year=2026)
    decisions = DecisionOrchestrator().evaluate_all(farmer, parcel, session)
    basic = next(x for x in decisions if x.support_id == "BASIC_SUPPORT_2026")
    assert basic.status == EligibilityStatusEnum.REVIEW
    calc = SupportCalculator.calculate(basic, parcel.area_da, None)
    assert calc.status == EligibilityStatusEnum.REVIEW
    assert calc.estimated_amount is None


def test_hash_unknown_still_blocks_even_if_approval_metadata_injected(session):
    stage_component_rates(session, apply=True)
    staged = session.scalars(
        select(VerifiedSupportRateModel).where(
            VerifiedSupportRateModel.program_id == "BASIC_SUPPORT_2026",
            VerifiedSupportRateModel.crop_name == "BUĞDAY",
        )
    ).one()
    staged.review_status = "VERIFIED"
    staged.approved_by = "UNTRUSTED_TEST"
    staged.approved_at = datetime.now(UTC)
    staged.review_reference = "FORGED"
    session.commit()
    assert SupportRepository(session).get_amount(
        "BASIC_SUPPORT_2026", "BUĞDAY",
        production_year=2026, province="KONYA", district="KARATAY",
    ) is None


def test_no_implicit_mutation_of_staged_rate(session):
    stage_component_rates(session, apply=True)
    rate = session.scalars(
        select(VerifiedSupportRateModel).where(
            VerifiedSupportRateModel.program_id == "BASIC_SUPPORT_2026",
            VerifiedSupportRateModel.crop_name == "BUĞDAY",
        )
    ).one()
    rate.unit_amount = Decimal("9999.99")
    session.commit()
    with pytest.raises(ValueError, match="Staged record drift"):
        stage_component_rates(session, apply=True)


def test_wrong_year_future_price_and_tampered_catalog_rejected(tmp_path):
    original = json.loads(CATALOG.read_text(encoding="utf-8"))
    for mutate in (
        lambda d: d["components"][0].update(unit_amount="310.00"),
        lambda d: d["components"][0].update(review_status="VERIFIED"),
        lambda d: d["components"][0].update(production_year=2027),
        lambda d: d["validation_gate"].update(approval=True),
        lambda d: d["source_version"].update(content_hash="0"*64),
        lambda d: d["source_version"].update(primary_pdf_sha256_observed="f"*64),
        lambda d: d["validation_gate"].update(primary_pdf_byte_hash_verified=False),
        lambda d: d["components"].append(dict(d["components"][0])),
    ):
        datum = json.loads(json.dumps(original))
        mutate(datum)
        location = tmp_path / "tamper.json"
        location.write_text(json.dumps(datum, ensure_ascii=False), encoding="utf-8")
        with pytest.raises(ValueError):
            load_component_catalog(location)
