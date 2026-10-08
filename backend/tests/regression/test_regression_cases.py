"""Regresyon Test Paketi (Master Plan TD-P20 / Section 37).

Mevzuat değişiklikleri, sınır koşulları, kesinleşmiş tutarlar,
kaynak sürümleme ve determinizm garantilerini test eder.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from decimal import Decimal

from tarim_destek_rag.calculator.calculator import SupportCalculator
from tarim_destek_rag.citations.verifier import CitationVerifier
from tarim_destek_rag.database.connection import SessionLocal, init_db
from tarim_destek_rag.normalization.seed_data import seed_2026_support_data
from tarim_destek_rag.database.repository import SupportRepository
from tarim_destek_rag.explainer.template_explainer import CitationDetail
from tarim_destek_rag.models.farmer_parcel import FarmerProfile, Parcel
from tarim_destek_rag.models.source import AuthorityEnum, SourceDefinition
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.rules.orchestrator import DecisionOrchestrator
from tarim_destek_rag.scraper.registry import SourceRegistry


def test_regression_known_eligibility_and_amounts():
    """Bilinen tarihsel kararlar ve tutarların değişmezliği regresyon testi."""
    init_db()
    session = SessionLocal()
    try:
        seed_2026_support_data(session, include_faqs=False)
        orchestrator = DecisionOrchestrator()
        support_repo = SupportRepository(session)

        # 1. Konya/Karatay Buğday (Temel Destek + Planlı Üretim)
        farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
        parcel = Parcel(crop="BUĞDAY", area_da=Decimal("12.4"), production_year=2026)

        results = orchestrator.evaluate_all(farmer, parcel, session)
        basic_res = next(r for r in results if r.support_id == "BASIC_SUPPORT_2026")
        planned_res = next(r for r in results if r.support_id == "PLANNED_PRODUCTION_2026")

        assert basic_res.status == EligibilityStatusEnum.REVIEW
        assert planned_res.status == EligibilityStatusEnum.REVIEW

        # Legacy seed is inspectable but cannot yield a verified payout.
        amt_rec = support_repo.get_legacy_amount("BASIC_SUPPORT_2026", "BUĞDAY")
        assert amt_rec.unit_amount == Decimal("465.00")
        assert support_repo.get_amount(
            "BASIC_SUPPORT_2026", "BUĞDAY",
            production_year=2026, province="KONYA", district="KARATAY",
        ) is None
        calc = SupportCalculator.calculate(basic_res, parcel.area_da, None)
        assert calc.estimated_amount is None

        # 2. Samsun/Çarşamba Fındık (10.0 da * 170.00 = 1700.00 TL)
        f_samsun = FarmerProfile(province="SAMSUN", district="ÇARŞAMBA", cks_status=True)
        p_findik = Parcel(crop="FINDIK", area_da=Decimal("10.0"), production_year=2026)
        res_samsun = orchestrator.evaluate_all(f_samsun, p_findik, session)
        basic_findik = next(r for r in res_samsun if r.support_id == "BASIC_SUPPORT_2026")
        amt_findik = support_repo.get_legacy_amount("BASIC_SUPPORT_2026", "FINDIK")
        assert amt_findik.unit_amount == Decimal("170.00")
        calc_findik = SupportCalculator.calculate(basic_findik, p_findik.area_da, None)
        assert calc_findik.estimated_amount is None
    finally:
        session.close()


def test_regression_supersession_and_outdated_source():
    """Mülga/eski mevzuat tespiti ve reddedilmesi regresyon testi."""
    reg = SourceRegistry()
    reg.register(
        SourceDefinition(
            id="RG-2026-BITKISEL",
            url="https://resmigazete.gov.tr/2026",
            authority=AuthorityEnum.OFFICIAL_GAZETTE,
            title="2026 Kararı",
            active=True,
        )
    )
    reg.register(
        SourceDefinition(
            id="RG-2023-BITKISEL",
            url="https://resmigazete.gov.tr/2023",
            authority=AuthorityEnum.OFFICIAL_GAZETTE,
            title="Eski 2023 Kararı (Mülga)",
            active=False,
        )
    )

    verifier = CitationVerifier(registry=reg)

    # Güncel kaynak geçerli
    valid_cit = CitationDetail(
        source_id="RG-2026-BITKISEL",
        title="2026 Kararı",
        section="Madde 1",
        year=2026,
        snippet="Mevzuat metni",
    )
    assert verifier.verify(valid_cit).is_valid is True

    # Eski / Pasif kaynak otomatik olarak reddedilmeli
    invalid_cit = CitationDetail(
        source_id="RG-2023-BITKISEL",
        title="Eski 2023 Kararı (Mülga)",
        section="Madde 1",
        year=2023,
        snippet="Eski mevzuat",
    )
    res_inv = verifier.verify(invalid_cit)
    assert res_inv.is_valid is False
    assert res_inv.status in ["INACTIVE_SOURCE", "OUTDATED_YEAR"]


def test_regression_zero_llm_determinism():
    """Sıfır LLM ilkesi: Aynı girdilerle 50 kez ardışık çalıştırıldığında sıfır varyans testi."""
    init_db()
    session = SessionLocal()
    try:
        seed_2026_support_data(session, include_faqs=False)
        orchestrator = DecisionOrchestrator()
        farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
        parcel = Parcel(
            crop="BUĞDAY",
            area_da=Decimal("25.5"),
            production_year=2026,
            seed_certificate_available=True,
        )

        first_eval = orchestrator.evaluate_all(farmer, parcel, session)
        first_statuses = [r.status for r in first_eval]
        first_checks = [r.passed_checks for r in first_eval]

        for _ in range(50):
            current_eval = orchestrator.evaluate_all(farmer, parcel, session)
            current_statuses = [r.status for r in current_eval]
            current_checks = [r.passed_checks for r in current_eval]

            assert current_statuses == first_statuses
            assert current_checks == first_checks
    finally:
        session.close()
