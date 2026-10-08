"""Sprint 0 / PR-001 Veri Doğruluğu, Kural Önceliği ve Güvenilirlik Testleri.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tarim_destek_rag.citations.verifier import CitationVerifier
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.explainer.template_explainer import CitationDetail
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
from tarim_destek_rag.rules.rules_impl import (
    BasicSupportRule,
    CertifiedSaplingRule,
    PlannedProductionRule,
    WaterRestrictionRule,
)


@pytest.fixture
def memory_db_session():
    """İzole bellek içi test veritabanı oturumu."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    session = Session(engine)
    seed_2026_support_data(session)
    try:
        yield session
    finally:
        session.close()


def test_frontend_irrigation_enum_roundtrip():
    """1. test_frontend_irrigation_enum_roundtrip:
    Kullanıcının Sulu/Kuru/Bilinmiyor seçimi API irrigation alanından aynen geçer.
    """
    from frontend_pc.app import evaluate_farmer_parcel

    mock_client = MagicMock()
    mock_client.evaluate_full.return_value = {
        "rules": [],
        "calculations": [],
        "explanations": [],
        "total_estimated_amount": 0.0,
    }

    # Sulu seçimi
    evaluate_farmer_parcel(
        province="KONYA",
        district="KARATAY",
        cks_status="Evet (Aktif)",
        age_group="Standart",
        gender="Erkek",
        crop="BUĞDAY",
        area_da=10.0,
        irrigation_type="Sulu Tarım",
        seed_cert="Evet",
        sapling_cert="Hayır",
        closed_orchard="Hayır",
        client=mock_client,
    )
    sent_parcel = mock_client.evaluate_full.call_args[0][1]
    assert sent_parcel["irrigation"] == "IRRIGATED"

    # Kuru seçimi
    evaluate_farmer_parcel(
        province="KONYA",
        district="KARATAY",
        cks_status="Evet (Aktif)",
        age_group="Standart",
        gender="Erkek",
        crop="BUĞDAY",
        area_da=10.0,
        irrigation_type="Kuru Tarım",
        seed_cert="Evet",
        sapling_cert="Hayır",
        closed_orchard="Hayır",
        client=mock_client,
    )
    sent_parcel = mock_client.evaluate_full.call_args[0][1]
    assert sent_parcel["irrigation"] == "DRY"

    # Bilinmiyor seçimi
    evaluate_farmer_parcel(
        province="KONYA",
        district="KARATAY",
        cks_status="Evet (Aktif)",
        age_group="Standart",
        gender="Erkek",
        crop="BUĞDAY",
        area_da=10.0,
        irrigation_type="❓ Bilmiyorum",
        seed_cert="Evet",
        sapling_cert="Hayır",
        closed_orchard="Hayır",
        client=mock_client,
    )
    sent_parcel = mock_client.evaluate_full.call_args[0][1]
    assert sent_parcel["irrigation"] == "UNKNOWN"


def test_water_restriction_requires_irrigated(memory_db_session):
    """2. test_water_restriction_requires_irrigated:
    Kuru tarım parselinde su kısıtı desteği uygunluk kararı verilmez; bilinmiyor REVIEW olur.
    """
    rule = WaterRestrictionRule()
    farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)

    # 1. Kuru parsel -> NOT_ELIGIBLE
    p_dry = Parcel(
        crop="MERCİMEK",
        area_da=Decimal("20.0"),
        production_year=2026,
        irrigation=IrrigationStatusEnum.DRY,
    )
    res_dry = rule.evaluate(farmer, p_dry, memory_db_session)
    assert res_dry.status == EligibilityStatusEnum.NOT_ELIGIBLE
    assert any("sulu tarım" in f.lower() for f in res_dry.failed_checks)

    # 2. Bilinmiyor -> REVIEW
    p_unk = Parcel(
        crop="MERCİMEK",
        area_da=Decimal("20.0"),
        production_year=2026,
        irrigation=IrrigationStatusEnum.UNKNOWN,
    )
    res_unk = rule.evaluate(farmer, p_unk, memory_db_session)
    assert res_unk.status == EligibilityStatusEnum.REVIEW
    assert "irrigation" in res_unk.missing_fields

    # 3. Sulu parsel -> Şartlar sağlandı ancak resmi onay kapısı fail-closed (REVIEW)
    p_irr = Parcel(
        crop="MERCİMEK",
        area_da=Decimal("20.0"),
        production_year=2026,
        irrigation=IrrigationStatusEnum.IRRIGATED,
    )
    res_irr = rule.evaluate(farmer, p_irr, memory_db_session)
    assert res_irr.status == EligibilityStatusEnum.REVIEW
    assert len(res_irr.failed_checks) == 0
    assert any("sulu arazi şartı sağlandı" in p.lower() for p in res_irr.passed_checks)
    assert "verified_water_provenance" in res_irr.missing_fields


def test_missing_basin_data_not_equivalent_to_ineligible(memory_db_session, monkeypatch):
    """3. test_missing_basin_data_not_equivalent_to_ineligible:
    Henüz kaynaklanmamış ilçe, açık destek dışı ilçe gibi muamele görmez; REVIEW döner.
    """
    rule = PlannedProductionRule()

    # Bilinmeyen ilçe: HAKKARİ / YÜKSEKOVA (seed kütüğünde yok)
    farmer_unknown = FarmerProfile(province="HAKKARİ", district="YÜKSEKOVA", cks_status=True)
    parcel = Parcel(crop="BUĞDAY", area_da=Decimal("10.0"), production_year=2026)

    res_unknown = rule.evaluate(farmer_unknown, parcel, memory_db_session)
    assert res_unknown.status == EligibilityStatusEnum.REVIEW
    assert "verified_basin_provenance" in res_unknown.missing_fields

    # Bilinen ve onaylı ilçe ama desteklenmeyen ürün:
    from backend.tests.unit.test_p0_4_basin_review import register_synthetic_snapshot

    register_synthetic_snapshot(
        memory_db_session,
        approve=True,
        crops=["BUĞDAY", "ARPA"],
        starred=False,
        monkeypatch=monkeypatch,
    )

    farmer_known = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    parcel_patates = Parcel(crop="PATATES", area_da=Decimal("10.0"), production_year=2026)

    res_known = rule.evaluate(farmer_known, parcel_patates, memory_db_session)
    assert res_known.status == EligibilityStatusEnum.NOT_ELIGIBLE
    assert any("resmî ürün deseninde yok" in f for f in res_known.failed_checks)


def test_certified_sapling_requires_closed_orchard_and_min_area(memory_db_session):
    """4. test_certified_sapling_requires_closed_orchard_and_min_area:
    Kapama bahçe değilse veya alan < 5 da ise NOT_ELIGIBLE, belirtilmemişse REVIEW.
    """
    rule = CertifiedSaplingRule()
    farmer = FarmerProfile(province="SAMSUN", district="ÇARŞAMBA", cks_status=True)

    # 1. Alan < 5 da -> NOT_ELIGIBLE
    p_small = Parcel(
        crop="FINDIK",
        area_da=Decimal("4.5"),
        production_year=2026,
        sapling_certificate_available=True,
        is_closed_orchard=True,
    )
    res_small = rule.evaluate(farmer, p_small, memory_db_session)
    assert res_small.status == EligibilityStatusEnum.NOT_ELIGIBLE
    assert any("5 dekar" in f for f in res_small.failed_checks)

    # 2. Kapama bahçe değil (False) -> NOT_ELIGIBLE
    p_not_orchard = Parcel(
        crop="FINDIK",
        area_da=Decimal("10.0"),
        production_year=2026,
        sapling_certificate_available=True,
        is_closed_orchard=False,
    )
    res_not_orchard = rule.evaluate(farmer, p_not_orchard, memory_db_session)
    assert res_not_orchard.status == EligibilityStatusEnum.NOT_ELIGIBLE
    assert any("kapama meyve bahçesi" in f.lower() for f in res_not_orchard.failed_checks)

    # 3. Kapama bahçe beyan edilmemiş (None) -> REVIEW
    p_none_orchard = Parcel(
        crop="FINDIK",
        area_da=Decimal("10.0"),
        production_year=2026,
        sapling_certificate_available=True,
        is_closed_orchard=None,
    )
    res_none_orchard = rule.evaluate(farmer, p_none_orchard, memory_db_session)
    assert res_none_orchard.status == EligibilityStatusEnum.REVIEW
    assert "is_closed_orchard" in res_none_orchard.missing_fields

    # 4. Tüm fiziki şartlar sağlandı -> onaylı imza/fiyat olmadan fail-closed REVIEW
    p_ok = Parcel(
        crop="FINDIK",
        area_da=Decimal("10.0"),
        production_year=2026,
        sapling_certificate_available=True,
        is_closed_orchard=True,
    )
    res_ok = rule.evaluate(farmer, p_ok, memory_db_session)
    assert res_ok.status == EligibilityStatusEnum.REVIEW
    assert len(res_ok.failed_checks) == 0
    assert any("kapama meyve bahçesi şartı sağlandı" in p.lower() for p in res_ok.passed_checks)
    assert any("asgari alan şartı" in p.lower() for p in res_ok.passed_checks)
    assert "verified_support_rate" in res_ok.missing_fields


def test_rule_failure_priority_over_missing(memory_db_session):
    """5. test_rule_failure_priority_over_missing:
    Ölümcül ret şartı varken eksik alan olması durumunda sonuç REVIEW ile gizlenemez; NOT_ELIGIBLE olur.
    """
    rule = BasicSupportRule()
    # ÇKS yok (False - kesin ret) fakat başka bir eksik alan var
    farmer_no_cks = FarmerProfile(province="KONYA", district="KARATAY", cks_status=False)
    parcel_wrong_year = Parcel(crop="BUĞDAY", area_da=Decimal("10.0"), production_year=2025)

    res = rule.evaluate(farmer_no_cks, parcel_wrong_year, memory_db_session)
    assert res.status == EligibilityStatusEnum.NOT_ELIGIBLE


def test_citation_missing_or_wrong_quote_fails():
    """6. test_citation_missing_or_wrong_quote_fails:
    Boş atıf veya <10 karakter snippet veya boş madde VERIFIED olmaz.
    """
    from tarim_destek_rag.models.source import AuthorityEnum, SourceDefinition
    from tarim_destek_rag.scraper.registry import SourceRegistry

    reg = SourceRegistry()
    reg.register(
        SourceDefinition(
            id="RG-2026-BITKISEL",
            url="https://resmigazete.gov.tr",
            authority=AuthorityEnum.OFFICIAL_GAZETTE,
            title="Resmî Gazete",
            active=True,
        )
    )
    verifier = CitationVerifier(registry=reg)

    # 1. Boş snippet
    cit_empty_snippet = CitationDetail(
        source_id="RG-2026-BITKISEL",
        title="2026 Kararı",
        section="Madde 1",
        year=2026,
        snippet="",
    )
    v1 = verifier.verify(cit_empty_snippet)
    assert not v1.is_valid
    assert v1.status == "EMPTY_OR_SHORT_SNIPPET"

    # 2. Çok kısa snippet (<10 char)
    cit_short_snippet = CitationDetail(
        source_id="RG-2026-BITKISEL",
        title="2026 Kararı",
        section="Madde 1",
        year=2026,
        snippet="Kısa",
    )
    v2 = verifier.verify(cit_short_snippet)
    assert not v2.is_valid
    assert v2.status == "EMPTY_OR_SHORT_SNIPPET"

    # 3. Boş madde / section
    cit_empty_sec = CitationDetail(
        source_id="RG-2026-BITKISEL",
        title="2026 Kararı",
        section="",
        year=2026,
        snippet="Resmî gazete maddesi geçerli uzunlukta metin.",
    )
    v3 = verifier.verify(cit_empty_sec)
    assert not v3.is_valid
    assert v3.status == "MISSING_SECTION"

    # 4. Geçerli atıf
    cit_valid = CitationDetail(
        source_id="RG-2026-BITKISEL",
        title="2026 Kararı",
        section="Madde 1",
        year=2026,
        snippet="Resmî gazete maddesi geçerli uzunlukta tam mevzuat alıntısı.",
    )
    v4 = verifier.verify(cit_valid)
    assert v4.is_valid
    assert v4.status == "VERIFIED"


def test_calculation_official_wheat_2026_updated_coefficient():
    """7. test_calculation_official_wheat_2026_updated_coefficient:
    8 Eylül 2026 Bakanlık katsayı güncellemesi (367 TL) ile Buğday temel ve planlı üretim tutarı hesaplanır.
    """
    katsayi = SUPPORT_COEFFICIENTS_2026["BASE_COEFFICIENT_SEPTEMBER"]
    carpan = SUPPORT_COEFFICIENTS_2026["WHEAT_BARLEY_MULTIPLIER"]
    assert katsayi == Decimal("367.00")
    assert carpan == Decimal("1.30")

    temel_destek = carpan * katsayi  # 477.10 TL/da
    planli_destek = carpan * katsayi  # 477.10 TL/da
    toplam_destek = temel_destek + planli_destek  # 954.20 TL/da

    assert temel_destek == Decimal("477.10")
    assert planli_destek == Decimal("477.10")
    assert toplam_destek == Decimal("954.20")
    assert round(toplam_destek) == Decimal("954")  # Bakanlığın duyurduğu ~954 TL/da


def test_report_is_not_misrepresented_as_government_document():
    """8. test_report_is_not_misrepresented_as_government_document:
    Sistem raporu doğrudan kamu kurumu belgesi gibi başlık taşımaz, bağımsız simülasyon uyarısı içerir.
    """
    from frontend_pc.app import generate_evaluation_report

    mock_client = MagicMock()
    mock_client.evaluate_full.return_value = {
        "rules": [],
        "calculations": [],
        "explanations": [],
        "total_estimated_amount": 1000.0,
    }

    res_update = generate_evaluation_report(
        province="KONYA",
        district="KARATAY",
        cks_status="Evet (Aktif)",
        age_group="Standart",
        gender="Erkek",
        crop="BUĞDAY",
        area_da=10.0,
        irrigation_type="Kuru Tarım",
        seed_cert="Evet",
        sapling_cert="Hayır",
        closed_orchard="Hayır",
        client=mock_client,
    )

    report_path = res_update["value"]
    with open(report_path, encoding="utf-8") as f:
        content = f.read()

    # Resmî kurum başlığı taşımamalı
    first_line = content.splitlines()[0]
    assert first_line != "# T.C. TARIM VE ORMAN BAKANLIĞI"
    assert "Bağımsız Bilgilendirme ve Tahmini Ön Değerlendirme Raporu" in content
    assert "resmî belgesi, ödeme taahhüdü veya idari onay kararı DEĞİLDİR" in content


def test_unknown_application_window_not_open():
    """9. test_unknown_application_window_not_open:
    Tarih girilmemişse veya henüz başvuru başlamamışsa durum BAŞVURUYA AÇIK olarak gösterilmez.
    """
    from frontend_pc.app import calculate_window_status

    # Tarih yoksa
    s, e, status = calculate_window_status(None, None, True)
    assert "DOĞRULANMADI" in status
    assert "BAŞVURUYA AÇIK" not in status

    # Gelecek tarih (Örn: 2099)
    s, e, status_future = calculate_window_status("2099-01-01", "2099-12-31", True)
    assert "BAŞVURUYA YAKLAŞIYOR" in status_future

    # Geçmiş tarih (Örn: 2020)
    s, e, status_past = calculate_window_status("2020-01-01", "2020-12-31", True)
    assert "BAŞVURU SÜRESİ DOLDU" in status_past
