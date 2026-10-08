"""Unit and cryptographic tests for P0-5b 2026 water restriction reconciliation (Issue #17)."""

from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.models import (
    ReviewedWaterRestrictionDistrictModel,
    SourceModel,
    SourceVersionModel,
    SupportProgramModel,
    VerifiedSupportRateModel,
)
from tarim_destek_rag.database.repository import (
    WaterRestrictionRepository,
)
from tarim_destek_rag.models.farmer_parcel import (
    FarmerProfile,
    IrrigationStatusEnum,
    Parcel,
)
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.normalization.water_restriction_2026 import (
    PINNED_TEBLIG_2024_39_SHA256,
    WATER_SOURCE_ID,
    WATER_SOURCE_URL,
    load_water_restriction_catalog,
    stage_water_restriction_districts,
    validate_water_restriction_catalog,
)
from tarim_destek_rag.rules.rules_impl import WaterRestrictionRule

from backend.tests.legal_approval_testkit import sign_subject


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        # Temel kaynak ve versiyonu ekle
        source = SourceModel(
            source_id=WATER_SOURCE_ID,
            url=WATER_SOURCE_URL,
            title="Tebliğ 2024/39",
            authority="OFFICIAL_GAZETTE",
            content_type="PDF",
            active=True,
            priority=1,
        )
        s.add(source)
        s.flush()
        version = SourceVersionModel(
            source_id=source.source_id,
            content_hash=PINNED_TEBLIG_2024_39_SHA256,
            version=1,
            detected_at="2026-10-08T10:00:00Z",
            effective_from="2026-01-01",
            effective_to="2026-12-31",
            superseded=False,
        )
        s.add(version)
        s.flush()
        yield s
    engine.dispose()


def test_catalog_validation_and_staging(session):
    """Katalog yapısı, sağlama ve DRAFT staging kontrolü."""
    catalog = load_water_restriction_catalog()
    districts = validate_water_restriction_catalog(catalog)
    assert len(districts) >= 52

    staged = stage_water_restriction_districts(session)
    assert staged == len(districts)

    # Staged kayıtların hepsi DRAFT olmalı, onaylı olmamalıdır
    repo = WaterRestrictionRepository(session)
    res = repo.evaluate_official_water_restriction("KONYA", "KARATAY", 2026)
    assert res.outcome == "UNKNOWN"
    assert "onaylı tekil resmî su kısıtı kaydı bulunamadı" in res.reason.lower()


def test_unseeded_district_returns_unknown(session):
    """Kütükte hiç yer almayan bir ilçe fail-closed UNKNOWN döner."""
    repo = WaterRestrictionRepository(session)
    res = repo.evaluate_official_water_restriction("HAKKARİ", "YÜKSEKOVA", 2026)
    assert res.outcome == "UNKNOWN"


def test_conflict_districts_stay_unknown_even_if_reviewed(session, monkeypatch):
    """Kırıkhan, Yalıhüyük ve Nusaybin çelişkili ilçeleri UNDER_REVIEW kalır ve UNKNOWN üretir."""
    version = session.query(SourceVersionModel).first()
    model = ReviewedWaterRestrictionDistrictModel(
        province="HATAY",
        district="KIRIKHAN",
        production_year=2026,
        restriction_status="UNDER_REVIEW",
        effective_from="2026-01-01",
        effective_to="2026-12-31",
        source_version_id=version.id,
        document_page=8,
        legal_clause="Madde 6/3(a,b,c)",
        conflict_notes="52_DISTRICT_FAQ_OMISSION_VS_2024_39",
        review_status="VERIFIED",
        reviewed_by="LEGAL_EXPERT",
        reviewed_at=datetime.now(UTC),
        review_reference="CONFLICT_AUDIT",
    )
    session.add(model)
    session.commit()
    sign_subject(session, model, monkeypatch)

    repo = WaterRestrictionRepository(session)
    res = repo.evaluate_official_water_restriction("HATAY", "KIRIKHAN", 2026)
    assert res.outcome == "UNKNOWN"
    assert "52_DISTRICT_FAQ_OMISSION" in res.reason


def test_signed_restricted_and_not_restricted_evaluation(session, monkeypatch):
    """Çift onaylı RESTRICTED ve NOT_RESTRICTED kayıtlarının doğru tri-state sonuçları."""
    version = session.query(SourceVersionModel).first()

    # 1. KONYA / KARATAY -> RESTRICTED
    karatay = ReviewedWaterRestrictionDistrictModel(
        province="KONYA",
        district="KARATAY",
        production_year=2026,
        restriction_status="RESTRICTED",
        effective_from="2026-01-01",
        effective_to="2026-12-31",
        source_version_id=version.id,
        document_page=6,
        legal_clause="Madde 6/3(a)",
        review_status="VERIFIED",
        reviewed_by="EXPERT_1",
        reviewed_at=datetime.now(UTC),
        review_reference="REF_1",
    )
    session.add(karatay)

    # 2. KONYA / SELÇUKLU -> NOT_RESTRICTED
    selcuklu = ReviewedWaterRestrictionDistrictModel(
        province="KONYA",
        district="SELÇUKLU",
        production_year=2026,
        restriction_status="NOT_RESTRICTED",
        effective_from="2026-01-01",
        effective_to="2026-12-31",
        source_version_id=version.id,
        document_page=6,
        legal_clause="Madde 6/3(a)",
        review_status="VERIFIED",
        reviewed_by="EXPERT_1",
        reviewed_at=datetime.now(UTC),
        review_reference="REF_2",
    )
    session.add(selcuklu)
    session.commit()

    signers = sign_subject(session, karatay, monkeypatch)
    sign_subject(session, selcuklu, monkeypatch, signers=signers)

    repo = WaterRestrictionRepository(session)
    assert repo.evaluate_official_water_restriction("KONYA", "KARATAY", 2026).outcome == "RESTRICTED"
    assert repo.evaluate_official_water_restriction("KONYA", "SELÇUKLU", 2026).outcome == "NOT_RESTRICTED"


def test_water_restriction_rule_full_matrix(session, monkeypatch):
    """WaterRestrictionRule kural motoru tüm karar matrisi doğrulaması."""
    version = session.query(SourceVersionModel).first()

    # Karatay'ı onayla
    karatay = ReviewedWaterRestrictionDistrictModel(
        province="KONYA",
        district="KARATAY",
        production_year=2026,
        restriction_status="RESTRICTED",
        effective_from="2026-01-01",
        effective_to="2026-12-31",
        source_version_id=version.id,
        document_page=6,
        legal_clause="Madde 6/3(a)",
        review_status="VERIFIED",
        reviewed_by="EXPERT",
        reviewed_at=datetime.now(UTC),
        review_reference="REF",
    )
    # Selçuklu'yu onayla (Kısıtsız)
    selcuklu = ReviewedWaterRestrictionDistrictModel(
        province="KONYA",
        district="SELÇUKLU",
        production_year=2026,
        restriction_status="NOT_RESTRICTED",
        effective_from="2026-01-01",
        effective_to="2026-12-31",
        source_version_id=version.id,
        document_page=6,
        legal_clause="Madde 6/3(a)",
        review_status="VERIFIED",
        reviewed_by="EXPERT",
        reviewed_at=datetime.now(UTC),
        review_reference="REF",
    )
    # Program ve onaylı tutar ekle
    prog = SupportProgramModel(id="WATER_RESTRICTION_2026", name="Su Kısıtı", year=2026, active=True)
    rate = VerifiedSupportRateModel(
        program_id="WATER_RESTRICTION_2026",
        crop_name="MERCİMEK",
        production_year=2026,
        province="*",
        district="*",
        unit_amount=Decimal("250.00"),
        unit="TRY/da",
        effective_from=datetime(2026, 1, 1).date(),
        effective_to=datetime(2026, 12, 31).date(),
        legal_clause="Madde 6/3(b)",
        source_version_id=version.id,
        review_status="VERIFIED",
        approved_by="EXPERT",
        approved_at=datetime.now(UTC),
        review_reference="RATE_REF",
    )
    session.add_all([karatay, selcuklu, prog, rate])
    session.commit()

    signers = sign_subject(session, karatay, monkeypatch)
    sign_subject(session, selcuklu, monkeypatch, signers=signers)
    sign_subject(session, rate, monkeypatch, signers=signers)

    rule = WaterRestrictionRule()

    # 1. ÇKS yok -> NOT_ELIGIBLE
    f_no_cks = FarmerProfile(province="KONYA", district="KARATAY", cks_status=False)
    p = Parcel(crop="MERCİMEK", area_da=Decimal("20.0"), production_year=2026, irrigation=IrrigationStatusEnum.IRRIGATED)
    assert rule.evaluate(f_no_cks, p, session).status == EligibilityStatusEnum.NOT_ELIGIBLE

    # 2. Kuru arazi -> Kesin NOT_ELIGIBLE (Madde 6/3-b)
    f_ok = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    p_dry = Parcel(crop="MERCİMEK", area_da=Decimal("20.0"), production_year=2026, irrigation=IrrigationStatusEnum.DRY)
    res_dry = rule.evaluate(f_ok, p_dry, session)
    assert res_dry.status == EligibilityStatusEnum.NOT_ELIGIBLE
    assert any("sulu tarım" in f.lower() for f in res_dry.failed_checks)

    # 3. Bilinmeyen sulama -> REVIEW
    p_unk = Parcel(crop="MERCİMEK", area_da=Decimal("20.0"), production_year=2026, irrigation=IrrigationStatusEnum.UNKNOWN)
    res_unk = rule.evaluate(f_ok, p_unk, session)
    assert res_unk.status == EligibilityStatusEnum.REVIEW
    assert "irrigation" in res_unk.missing_fields

    # 4. Kısıtsız ilçe (Selçuklu) -> NOT_ELIGIBLE
    f_selcuklu = FarmerProfile(province="KONYA", district="SELÇUKLU", cks_status=True)
    res_selc = rule.evaluate(f_selcuklu, p, session)
    assert res_selc.status == EligibilityStatusEnum.NOT_ELIGIBLE
    assert any("bölgesinde yer almamaktadır" in f.lower() for f in res_selc.failed_checks)

    # 5. Tüm şartlar sağlandı (Karatay + Sulu + Mercimek + Çift İmza) -> ELIGIBLE
    res_ok = rule.evaluate(f_ok, p, session)
    assert res_ok.status == EligibilityStatusEnum.ELIGIBLE
    assert res_ok.metadata["unit_amount"] == "250.00"
