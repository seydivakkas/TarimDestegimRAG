from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tarim_destek_rag.calculator.calculator import (
    DISCLAIMER_TEXT,
    SupportCalculator,
)
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.models.farmer_parcel import FarmerProfile, IrrigationStatusEnum, Parcel
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.normalization.seed_data import seed_2026_support_data
from tarim_destek_rag.rules.orchestrator import DecisionOrchestrator
from tarim_destek_rag.rules.rules_impl import (
    BasicSupportRule,
    CertifiedSeedRule,
    PlannedProductionRule,
    WaterRestrictionRule,
)


def get_test_db_session():
    """Test için in-memory DB oturumu hazırlar."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    session = Session(engine)
    seed_2026_support_data(session)
    return session


def test_basic_support_eligible():
    """ÇKS'li, 2026 Buğday üreticisi Temel Desteğe uygundur."""
    session = get_test_db_session()
    farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    parcel = Parcel(crop="BUĞDAY", area_da=Decimal("25.0"), production_year=2026)

    rule = BasicSupportRule()
    res = rule.evaluate(farmer, parcel, session)
    assert res.status == EligibilityStatusEnum.ELIGIBLE
    assert len(res.failed_checks) == 0
    assert "BUĞDAY" in res.passed_checks[3]


def test_basic_support_missing_cks():
    """ÇKS durumu bilinmiyorsa REVIEW dönmeli ve eksik alan bildirilmelidir."""
    session = get_test_db_session()
    farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=None)
    parcel = Parcel(crop="BUĞDAY", area_da=Decimal("10.0"), production_year=2026)

    rule = BasicSupportRule()
    res = rule.evaluate(farmer, parcel, session)
    assert res.status == EligibilityStatusEnum.REVIEW
    assert "cks_status" in res.missing_fields


def test_planned_production_rules():
    """Konya Karatay'da Buğday desteklenirken Pamuk desteklenmez."""
    session = get_test_db_session()
    farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    parcel_wheat = Parcel(crop="BUĞDAY", area_da=Decimal("15.0"), production_year=2026)
    parcel_cotton = Parcel(crop="PAMUK", area_da=Decimal("15.0"), production_year=2026)

    rule = PlannedProductionRule()
    res_wheat = rule.evaluate(farmer, parcel_wheat, session)
    res_cotton = rule.evaluate(farmer, parcel_cotton, session)

    assert res_wheat.status == EligibilityStatusEnum.ELIGIBLE
    assert res_cotton.status == EligibilityStatusEnum.NOT_ELIGIBLE


def test_certified_seed_missing_evidence():
    """Sertifika beyanı yapılmamışsa REVIEW dönmeli."""
    session = get_test_db_session()
    farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    parcel = Parcel(
        crop="BUĞDAY",
        area_da=Decimal("10.0"),
        production_year=2026,
        seed_certificate_available=None,
    )

    rule = CertifiedSeedRule()
    res = rule.evaluate(farmer, parcel, session)
    assert res.status == EligibilityStatusEnum.REVIEW
    assert "seed_certificate_available" in res.missing_fields


def test_water_restriction_rule():
    """Konya Karatay su kısıtı bölgesindedir ve mercimek uygundur."""
    session = get_test_db_session()
    farmer_konya = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    parcel_lentil = Parcel(crop="MERCİMEK", area_da=Decimal("20.0"), production_year=2026, irrigation=IrrigationStatusEnum.IRRIGATED)

    farmer_bursa = FarmerProfile(province="BURSA", district="NİLÜFER", cks_status=True)

    rule = WaterRestrictionRule()
    res_konya = rule.evaluate(farmer_konya, parcel_lentil, session)
    res_bursa = rule.evaluate(farmer_bursa, parcel_lentil, session)

    assert res_konya.status == EligibilityStatusEnum.ELIGIBLE
    assert res_bursa.status == EligibilityStatusEnum.NOT_ELIGIBLE


def test_calculator_precision():
    """Master plan örneği: 12.4 da * 465 TL/da = 5766.00 TL tam Decimal hesabı."""
    session = get_test_db_session()
    farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    parcel = Parcel(crop="BUĞDAY", area_da=Decimal("12.4"), production_year=2026)

    rule = BasicSupportRule()
    rule_res = rule.evaluate(farmer, parcel, session)

    calc_res = SupportCalculator.calculate(rule_res, parcel.area_da, Decimal("465.00"))

    assert calc_res.status == EligibilityStatusEnum.ELIGIBLE
    assert calc_res.estimated_amount == Decimal("5766.00")
    assert calc_res.formula == "12.4 da * 465.00 TL/da = 5766.00 TL"
    assert calc_res.disclaimer == DISCLAIMER_TEXT


def test_orchestrator_evaluate_all():
    """Orchestrator tüm 5 kuralı tek seferde deterministik işletmelidir."""
    session = get_test_db_session()
    farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    parcel = Parcel(
        crop="BUĞDAY",
        area_da=Decimal("20.0"),
        production_year=2026,
        seed_certificate_available=True,
    )

    orchestrator = DecisionOrchestrator()
    results = orchestrator.evaluate_all(farmer, parcel, session)
    assert len(results) == 5
    # Temel ve Planlı üretim ve tohum uygun olmalı
    res_map = {r.support_id: r.status for r in results}
    assert res_map["BASIC_SUPPORT_2026"] == EligibilityStatusEnum.ELIGIBLE
    assert res_map["PLANNED_PRODUCTION_2026"] == EligibilityStatusEnum.ELIGIBLE
    assert res_map["CERTIFIED_SEED_2026"] == EligibilityStatusEnum.ELIGIBLE
