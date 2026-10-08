"""P0-2: no unreviewed rate reaches an individual support calculation.

Approval/hash/source fixtures are synthetic test data, NOT official legal rates.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tarim_destek_rag.calculator.calculator import SupportCalculator
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.models import (
    SourceModel,
    SourceVersionModel,
    SupportAmountModel,
    SupportProgramModel,
    VerifiedSupportRateModel,
)
from tarim_destek_rag.database.repository import SupportRepository
from tarim_destek_rag.models.farmer_parcel import FarmerProfile, Parcel
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.rules.rules_impl import BasicSupportRule


AS_OF = date(2026, 10, 8)


@pytest.fixture()
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add_all([
            SupportProgramModel(id="BASIC_SUPPORT_2026", name="Temel Destek", year=2026),
            SourceModel(
                source_id="SYNTHETIC-LEGAL-DOCUMENT",
                title="TEST ONLY - synthetic source",
                url="https://example.invalid/document",
                authority="TEST_ONLY",
                content_type="PDF",
                active=True,
            ),
        ])
        s.flush()
        s.add(SupportAmountModel(
            program_id="BASIC_SUPPORT_2026",
            crop_name="BUĞDAY",
            unit_amount=Decimal("465.00"),
            unit="TRY/da",
            source_id="SYNTHETIC-LEGAL-DOCUMENT",
        ))
        s.commit()
        yield s
    engine.dispose()


def add_rate(
    session,
    *,
    state="VERIFIED",
    approved=True,
    effective_from=date(2026, 1, 1),
    effective_to=None,
    province="*",
    district="*",
    superseded=False,
    source_version_start="2026-01-01",
):
    version = SourceVersionModel(
        source_id="SYNTHETIC-LEGAL-DOCUMENT",
        version=session.query(SourceVersionModel).count() + 1,
        content_hash="a" * 64,
        detected_at="2026-09-08T09:00:00Z",
        effective_from=source_version_start,
        superseded=superseded,
    )
    session.add(version)
    session.flush()
    rate = VerifiedSupportRateModel(
        program_id="BASIC_SUPPORT_2026",
        crop_name="BUĞDAY",
        production_year=2026,
        province=province,
        district=district,
        unit_amount=Decimal("477.10"),
        unit="TRY/da",
        effective_from=effective_from,
        effective_to=effective_to,
        source_version_id=version.id,
        legal_clause="Synthetic test clause - do not publish",
        review_status=state,
        approved_by="test_reviewer" if approved else None,
        approved_at=datetime(2026, 10, 8, tzinfo=timezone.utc) if approved else None,
        review_reference="TEST-APPROVAL-001" if approved else None,
    )
    session.add(rate)
    session.commit()
    return rate


def lookup(session, **kwargs):
    return SupportRepository(session).get_amount(
        "BASIC_SUPPORT_2026", "BUĞDAY",
        production_year=kwargs.pop("year", 2026),
        province=kwargs.pop("province", "KONYA"),
        district=kwargs.pop("district", "KARATAY"),
        as_of=kwargs.pop("as_of", AS_OF),
    )


def test_legacy_seed_is_preserved_but_never_used(session):
    repo = SupportRepository(session)
    assert repo.get_legacy_amount("BASIC_SUPPORT_2026", "BUĞDAY").unit_amount == Decimal("465.00")
    assert lookup(session) is None
    farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    parcel = Parcel(crop="BUĞDAY", area_da=Decimal("12.4"), production_year=2026)
    decision = BasicSupportRule().evaluate(farmer, parcel, session)
    assert decision.status == EligibilityStatusEnum.REVIEW
    assert "verified_support_rate" in decision.missing_fields
    calc = SupportCalculator.calculate(decision, parcel.area_da, None)
    assert calc.estimated_amount is None
    assert calc.status == EligibilityStatusEnum.REVIEW


@pytest.mark.parametrize("state,approved", [
    ("DRAFT", True), ("REVOKED", True), ("VERIFIED", False),
])
def test_unapproved_or_revoked_versions_fail_closed(session, state, approved):
    add_rate(session, state=state, approved=approved)
    assert lookup(session) is None


def test_verified_component_is_calculated_with_exact_decimal(session):
    add_rate(session)
    rate = lookup(session)
    assert rate is not None
    assert rate.unit_amount == Decimal("477.10")
    farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    parcel = Parcel(crop="BUĞDAY", area_da=Decimal("12.4"), production_year=2026)
    decision = BasicSupportRule().evaluate(farmer, parcel, session)
    assert decision.status == EligibilityStatusEnum.ELIGIBLE
    assert decision.source_ids == ["SYNTHETIC-LEGAL-DOCUMENT"]
    calc = SupportCalculator.calculate(decision, parcel.area_da, rate.unit_amount)
    assert calc.estimated_amount == Decimal("5916.04")


def test_wrong_year_district_and_time_range_rejected(session):
    add_rate(session, province="KONYA", district="KARATAY",
             effective_from=date(2026, 10, 1), effective_to=date(2026, 10, 31))
    assert lookup(session) is not None
    assert lookup(session, year=2025) is None
    assert lookup(session, province="SAMSUN", district="ÇARŞAMBA") is None
    assert lookup(session, as_of=date(2026, 9, 30)) is None
    assert lookup(session, as_of=date(2026, 11, 1)) is None


def test_superseded_source_version_rejected(session):
    add_rate(session, superseded=True)
    assert lookup(session) is None


def test_source_not_yet_effective_rejected(session):
    add_rate(session, source_version_start="2027-01-01")
    assert lookup(session) is None


def test_deactivated_source_rejected(session):
    add_rate(session)
    session.get(SourceModel, "SYNTHETIC-LEGAL-DOCUMENT").active = False
    session.commit()
    assert lookup(session) is None


def test_overlapping_approved_sources_are_ambiguous(session):
    add_rate(session)
    add_rate(session)
    assert lookup(session) is None


def test_blank_evidence_hash_rejected(session):
    rate = add_rate(session)
    rate.source_version.content_hash = "not-sha256"
    session.commit()
    assert lookup(session) is None
