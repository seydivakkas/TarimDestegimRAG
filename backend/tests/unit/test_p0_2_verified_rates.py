"""P0-2: no unreviewed rate reaches an individual support calculation.

Approval/hash/source fixtures are synthetic test data, NOT official legal rates.
"""

from datetime import date, datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from tarim_destek_rag.calculator.calculator import SupportCalculator
from backend.tests.legal_approval_testkit import sign_subject
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
                url="https://www.resmigazete.gov.tr/eskiler/2026/09/20260908-7.pdf",
                authority="OFFICIAL_GAZETTE",
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


def test_verified_component_is_calculated_with_exact_decimal(session, monkeypatch):
    sign_subject(session, add_rate(session), monkeypatch)
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


def test_wrong_year_district_and_time_range_rejected(session, monkeypatch):
    rate = add_rate(session, province="KONYA", district="KARATAY",
                    effective_from=date(2026, 10, 1), effective_to=date(2026, 10, 31))
    sign_subject(session, rate, monkeypatch)
    assert lookup(session) is not None
    assert lookup(session, year=2025) is None
    assert lookup(session, province="SAMSUN", district="ÇARŞAMBA") is None
    assert lookup(session, as_of=date(2026, 9, 30)) is None
    assert lookup(session, as_of=date(2026, 11, 1)) is None


def test_superseded_source_version_rejected(session, monkeypatch):
    sign_subject(session, add_rate(session, superseded=True), monkeypatch)
    assert lookup(session) is None


def test_source_not_yet_effective_rejected(session, monkeypatch):
    sign_subject(session, add_rate(session, source_version_start="2027-01-01"), monkeypatch)
    assert lookup(session) is None


def test_deactivated_source_rejected(session, monkeypatch):
    sign_subject(session, add_rate(session), monkeypatch)
    session.get(SourceModel, "SYNTHETIC-LEGAL-DOCUMENT").active = False
    session.commit()
    assert lookup(session) is None


def test_overlapping_approved_sources_are_ambiguous(session):
    add_rate(session)
    add_rate(session)
    assert lookup(session) is None


def test_blank_evidence_hash_rejected(session, monkeypatch):
    rate = add_rate(session)
    sign_subject(session, rate, monkeypatch)
    rate.source_version.content_hash = "not-sha256"
    session.commit()
    assert lookup(session) is None


def test_sqlite_additive_migration_keeps_old_rows_and_marks_them_draft():
    """Existing deployed SQLite databases may predate 2026 provenance fields."""
    from tarim_destek_rag.database.connection import init_db

    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as connection:
        connection.exec_driver_sql("""
            CREATE TABLE support_amounts (
                id INTEGER PRIMARY KEY,
                program_id VARCHAR(64) NOT NULL,
                crop_name VARCHAR(64) NOT NULL,
                category VARCHAR(64),
                unit_amount NUMERIC(10,2) NOT NULL,
                unit VARCHAR(16),
                source_id VARCHAR(64) NOT NULL
            )
        """)
        connection.exec_driver_sql("""
            INSERT INTO support_amounts
            (id, program_id, crop_name, unit_amount, unit, source_id)
            VALUES (1, 'BASIC_SUPPORT_2026', 'BUĞDAY', 465, 'TRY/da', 'LEGACY')
        """)

    # Migration is idempotent, and neither existing amount nor source is touched.
    init_db(engine)
    init_db(engine)
    with engine.connect() as connection:
        info = connection.exec_driver_sql(
            "PRAGMA table_info('support_amounts')"
        ).all()
        columns = {row[1] for row in info}
        assert {"production_year", "verification_status", "effective_from"} <= columns
        row = connection.exec_driver_sql(
            "SELECT unit_amount, source_id, verification_status FROM support_amounts WHERE id=1"
        ).one()
        assert Decimal(str(row[0])) == Decimal("465")
        assert row[1] == "LEGACY"
        assert row[2] == "DRAFT"


def test_bootstrap_does_not_auto_approve_or_overwrite_prior_legacy_amounts():
    from tarim_destek_rag.normalization.seed_data import seed_2026_support_data

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        seed_2026_support_data(session, include_faqs=False)
        repo = SupportRepository(session)
        legacy = repo.get_legacy_amount("BASIC_SUPPORT_2026", "BUĞDAY")
        assert legacy is not None
        assert legacy.verification_status == "DRAFT"
        legacy.unit_amount = Decimal("123.45")
        session.commit()

        seed_2026_support_data(session, include_faqs=False)
        session.expire_all()
        assert repo.get_legacy_amount("BASIC_SUPPORT_2026", "BUĞDAY").unit_amount == Decimal("123.45")
        assert lookup(session) is None
