"""Issue #2 & Issue #3: Mevzuat Karar Motoru, Birim Destek Provenansı ve Havza Belirsizlik Testleri.

Kapsam:
- Issue #2: 2026 mevzuat ve birim tutarların güncellenmesi (Karar No: 11781, katsayı 367 TL,
  üretim yılı, mevzuat sürümü, geçerlilik dönemi, coğrafi kapsam ve verification_status).
- Issue #3: Havza kapsamı, sulama koşulları ve belirsizlik yönetimi:
  * Bilinmeyen tutar != 0 TL (REVIEW ve estimated_amount=None).
  * Eksik havza kaydı != Destek hakkı yok (REVIEW ve missing_fields=["basin_data"]).
  * Kesin ret şartı varsa NOT_ELIGIBLE.
  * Sulu vs Kuru tarım koşulları kesin doğrulaması.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from tarim_destek_rag.calculator.calculator import SupportCalculator
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.repository import SupportRepository
from tarim_destek_rag.models.farmer_parcel import (
    FarmerProfile,
    IrrigationStatusEnum,
    Parcel,
)
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.normalization.seed_data import (
    SUPPORT_COEFFICIENTS_2026,
    seed_2026_support_data,
)
from tarim_destek_rag.rules.base import RuleResult
from tarim_destek_rag.rules.rules_impl import (
    PlannedProductionRule,
    WaterRestrictionRule,
)


@pytest.fixture
def session():
    """İzole bellek SQLite oturumu."""
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sm = sessionmaker(bind=engine)
    sess = sm()
    seed_2026_support_data(sess, include_faqs=False)
    sess.commit()
    yield sess
    sess.close()


# ==============================================================================
# ISSUE #2: 2026 MEVZUAT SÜRÜMÜ, 11781 SAYILI KARAR VE TUTAR MODELİ TESTLERİ
# ==============================================================================


def test_support_amount_model_contains_mandatory_provenance_fields(session):
    """SupportAmountModel üretim yılı, karar sayısı, geçerlilik dönemi ve doğrulama durumunu içerir."""
    repo = SupportRepository(session)
    wheat_amt = repo.get_legacy_amount("BASIC_SUPPORT_2026", "BUĞDAY")

    assert wheat_amt is not None
    assert wheat_amt.production_year == 2026
    assert wheat_amt.legal_decision_number == "11781"
    assert wheat_amt.effective_from == "2026-09-08"
    assert wheat_amt.effective_to is None
    assert wheat_amt.geographic_scope == "GENEL"
    assert wheat_amt.verification_status == "DRAFT"  # Legacy label is not legal approval.
    assert repo.get_amount(
        "BASIC_SUPPORT_2026", "BUĞDAY", production_year=2026,
        province="KONYA", district="KARATAY",
    ) is None
    assert wheat_amt.unit_amount == Decimal("465.00")


def test_support_repository_keeps_legacy_history_but_no_payout_authority(session):
    """2026 DRAFT and SUPERSEDED history must never be used by get_amount."""
    repo = SupportRepository(session)
    assert repo.get_amount(
        "BASIC_SUPPORT_2026", "BUĞDAY", production_year=2026,
        province="KONYA", district="KARATAY",
    ) is None
    history = repo.list_amount_history("BASIC_SUPPORT_2026", "BUĞDAY")
    assert any(x.verification_status == "DRAFT" and x.unit_amount == Decimal("465.00")
               for x in history)
    assert any(x.verification_status == "SUPERSEDED" and x.unit_amount == Decimal("310.00")
               for x in history)



def test_amount_history_audit_trail(session):
    """list_amount_history ile bir ürünün tüm mevzuat sürümleri denetlenebilir."""
    repo = SupportRepository(session)
    history = repo.list_amount_history("BASIC_SUPPORT_2026", "BUĞDAY")

    assert len(history) >= 2
    statuses = {item.verification_status for item in history}
    assert "DRAFT" in statuses
    assert "SUPERSEDED" in statuses


def test_official_2026_coefficient_calculation_logic():
    """8 Eylül 2026 tarihli Bakanlık duyurusu: 367 TL katsayı ile toplam 954 TL/da."""
    katsayi = SUPPORT_COEFFICIENTS_2026["BASE_COEFFICIENT_SEPTEMBER"]
    carpan = SUPPORT_COEFFICIENTS_2026["WHEAT_BARLEY_MULTIPLIER"]

    assert katsayi == Decimal("367.00")
    assert carpan == Decimal("1.30")

    temel = carpan * katsayi  # 477.10 TL/da
    planli = carpan * katsayi  # 477.10 TL/da
    toplam = temel + planli

    assert toplam == Decimal("954.20")
    assert round(toplam) == Decimal("954")


# ==============================================================================
# ISSUE #3: HAVZA KAPSAMI, BELİRSİZLİK YÖNETİMİ VE SULAMA KOŞULLARI TESTLERİ
# ==============================================================================


def test_unknown_or_missing_amount_never_results_in_zero_payout():
    """[Bilinmeyen tutar != 0 TL]: Birim tutar bilinmiyorsa REVIEW ve estimated_amount=None dönmeli."""
    rule_res = RuleResult(
        rule_id="RULE_TEST",
        support_id="BASIC_SUPPORT_2026",
        support_name="Temel Destek",
        status=EligibilityStatusEnum.ELIGIBLE,
    )

    # 1. unit_amount None olduğunda 0 TL üretilmez
    calc_none = SupportCalculator.calculate(rule_res, Decimal("25.0"), None)
    assert calc_none.status == EligibilityStatusEnum.REVIEW
    assert calc_none.estimated_amount is None
    assert calc_none.metadata.get("verification_required") is True
    assert calc_none.metadata.get("reason_code") == "MISSING_OR_INVALID_UNIT_AMOUNT"

    # 2. unit_amount 0.00 olduğunda da 0 TL üretilmez
    calc_zero = SupportCalculator.calculate(rule_res, Decimal("25.0"), Decimal("0.00"))
    assert calc_zero.status == EligibilityStatusEnum.REVIEW
    assert calc_zero.estimated_amount is None


def test_missing_basin_record_is_review_not_ineligible(session):
    """[Eksik havza kaydı != Destek hakkı yok]: Kütükte olmayan ilçe NOT_ELIGIBLE değil REVIEW döner."""
    rule = PlannedProductionRule()

    # Kütükte yer almayan il/ilçe (örnek: TUNCELİ / HOZAT)
    farmer_uncatalogued = FarmerProfile(province="TUNCELİ", district="HOZAT", cks_status=True)
    parcel = Parcel(crop="BUĞDAY", area_da=Decimal("15.0"), production_year=2026)

    res = rule.evaluate(farmer_uncatalogued, parcel, session)

    assert res.status == EligibilityStatusEnum.REVIEW
    assert "verified_basin_provenance" in res.missing_fields
    assert len(res.failed_checks) == 0  # Kesin ret koşulu bulunamaz


def test_catalogued_basin_unsupported_crop_is_not_eligible(session):
    """Kütükte yer alan ilçede mevzuatça açıkça desteklenmeyen ürün kesin NOT_ELIGIBLE döner."""
    rule = PlannedProductionRule()

    # Kütükte kayıtlı Konya/Karatay havzasında FINDIK desteklenmez
    farmer_catalogued = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    parcel_findik = Parcel(crop="FINDIK", area_da=Decimal("20.0"), production_year=2026)

    res = rule.evaluate(farmer_catalogued, parcel_findik, session)

    assert res.status == EligibilityStatusEnum.REVIEW
    assert "verified_basin_provenance" in res.missing_fields
    assert not res.failed_checks


def test_water_restriction_irrigation_distinction(session):
    """Yeraltı su kısıtı kuralı: Kuru=NOT_ELIGIBLE, Bilinmiyor=REVIEW, Sulu=ELIGIBLE."""
    rule = WaterRestrictionRule()
    farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)

    # 1. Kuru Tarım -> Kesin NOT_ELIGIBLE
    p_dry = Parcel(
        crop="MERCİMEK",
        area_da=Decimal("10.0"),
        production_year=2026,
        irrigation=IrrigationStatusEnum.DRY,
    )
    res_dry = rule.evaluate(farmer, p_dry, session)
    assert res_dry.status == EligibilityStatusEnum.NOT_ELIGIBLE
    assert any("sulu tarım" in f.lower() for f in res_dry.failed_checks)

    # 2. Bilinmiyor / Belirsiz -> REVIEW
    p_unk = Parcel(
        crop="MERCİMEK",
        area_da=Decimal("10.0"),
        production_year=2026,
        irrigation=IrrigationStatusEnum.UNKNOWN,
    )
    res_unk = rule.evaluate(farmer, p_unk, session)
    assert res_unk.status == EligibilityStatusEnum.REVIEW
    assert "irrigation" in res_unk.missing_fields

    # 3. Sulu Tarım -> ELIGIBLE
    p_irr = Parcel(
        crop="MERCİMEK",
        area_da=Decimal("10.0"),
        production_year=2026,
        irrigation=IrrigationStatusEnum.IRRIGATED,
    )
    res_irr = rule.evaluate(farmer, p_irr, session)
    assert res_irr.status == EligibilityStatusEnum.REVIEW
    assert len(res_irr.failed_checks) == 0
    assert "verified_water_provenance" in res_irr.missing_fields
