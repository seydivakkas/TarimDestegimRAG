from decimal import Decimal

from sqlalchemy.orm import Session

from tarim_destek_rag.database.models import (
    ApplicationWindowModel,
    BasinCropRuleModel,
    SourceModel,
    SupportAmountModel,
    SupportProgramModel,
    WaterRestrictionModel,
)


# 2026 Destekleme Katsayı ve Birim Fiyat Tablosu (8 Eylül 2026 Güncellemesi)
SUPPORT_COEFFICIENTS_2026 = {
    "BASE_COEFFICIENT_AUGUST": Decimal("310.00"),
    "BASE_COEFFICIENT_SEPTEMBER": Decimal("367.00"),  # 8 Eylül 2026 Bakanlık duyurusu
    "WHEAT_BARLEY_MULTIPLIER": Decimal("1.30"),
    # Güncel resmi toplam: 1.30 * 367 = 477.10 TL temel + 477.10 TL planlı = 954.20 TL/da (~954 TL/da)
    "WHEAT_UPDATED_BASIC": Decimal("477.10"),
    "WHEAT_UPDATED_PLANNED": Decimal("477.10"),
    "WHEAT_UPDATED_TOTAL": Decimal("954.20"),
}


def seed_2026_support_data(session: Session) -> None:
    """Türkiye 2026 Bitkisel Üretim Destekleri mevzuat verisini veritabanına yükler."""

    # 1. Ana Kaynaklar
    rg_source = SourceModel(
        source_id="RG-2026-BITKISEL",
        url="https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf",
        authority="OFFICIAL_GAZETTE",
        title="2024-2026 Bitkisel Üretime Yönelik Desteklemeler Kararı",
        content_type="PDF",
        active=True,
        priority=0,
    )
    session.merge(rg_source)

    tob_source = SourceModel(
        source_id="TOB-2026-09-DUYURU",
        url="https://www.tarimorman.gov.tr/Haber/7258/Bitkisel-Ve-Hayvansal-Uretimde-Destek-Tutarlari-Artirildi",
        authority="MINISTRY_OF_AGRICULTURE",
        title="Tarım ve Orman Bakanlığı 2026 Yılı Destekleme Katsayısı Artış Tebliği (8 Eylül 2026 - Katsayı: 367 TL)",
        content_type="HTML",
        active=True,
        priority=1,
    )
    session.merge(tob_source)
    session.flush()

    # 2. Destekleme Programları
    programs = [
        SupportProgramModel(
            id="BASIC_SUPPORT_2026",
            name="Temel Destek",
            year=2026,
            active=True,
            description="ÇKS'ye kayıtlı üreticilere mazot ve gübre temel desteği.",
        ),
        SupportProgramModel(
            id="PLANNED_PRODUCTION_2026",
            name="Planlı Üretim Desteği",
            year=2026,
            active=True,
            description="Belirlenen havzalarda öncelikli stratejik ürün ekenlere ilave destek.",
        ),
        SupportProgramModel(
            id="CERTIFIED_SEED_2026",
            name="Sertifikalı Tohum Kullanım Desteği",
            year=2026,
            active=True,
            description="Yetkilendirilmiş sertifikalı tohum kullanan çiftçilere verilen destek.",
        ),
        SupportProgramModel(
            id="CERTIFIED_SAPLING_2026",
            name="Sertifikalı Fidan Kullanım Desteği",
            year=2026,
            active=True,
            description="Kapama meyve bahçesi tesisinde sertifikalı fidan kullananlara destek.",
        ),
        SupportProgramModel(
            id="WATER_RESTRICTION_2026",
            name="Yeraltı Su Kısıtı Desteği",
            year=2026,
            active=True,
            description="Yeraltı su kısıtı ilan edilen havzalarda münavebe ürünlerine destek.",
        ),
    ]
    for prog in programs:
        session.merge(prog)
    session.flush()

    # 3. Birim Tutarlar (TL / dekar)
    amounts = [
        # Temel Destek Birim Fiyatları (11781 sayılı Karar ile Doğrulanmış)
        SupportAmountModel(
            program_id="BASIC_SUPPORT_2026",
            crop_name="BUĞDAY",
            category="TAHIL",
            unit_amount=Decimal("465.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
            production_year=2026,
            legal_decision_number="11781",
            effective_from="2026-09-08",
            effective_to=None,
            geographic_scope="GENEL",
            verification_status="VERIFIED",
        ),
        SupportAmountModel(
            program_id="BASIC_SUPPORT_2026",
            crop_name="ARPA",
            category="TAHIL",
            unit_amount=Decimal("465.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
            production_year=2026,
            legal_decision_number="11781",
            effective_from="2026-09-08",
            effective_to=None,
            geographic_scope="GENEL",
            verification_status="VERIFIED",
        ),
        SupportAmountModel(
            program_id="BASIC_SUPPORT_2026",
            crop_name="MISIR",
            category="TAHIL",
            unit_amount=Decimal("380.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
            production_year=2026,
            legal_decision_number="11781",
            effective_from="2026-09-08",
            effective_to=None,
            geographic_scope="GENEL",
            verification_status="VERIFIED",
        ),
        SupportAmountModel(
            program_id="BASIC_SUPPORT_2026",
            crop_name="AYÇİÇEĞİ",
            category="YAĞLI TOHUM",
            unit_amount=Decimal("410.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
            production_year=2026,
            legal_decision_number="11781",
            effective_from="2026-09-08",
            effective_to=None,
            geographic_scope="GENEL",
            verification_status="VERIFIED",
        ),
        SupportAmountModel(
            program_id="BASIC_SUPPORT_2026",
            crop_name="PAMUK",
            category="ENDÜSTRİ",
            unit_amount=Decimal("550.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
            production_year=2026,
            legal_decision_number="11781",
            effective_from="2026-09-08",
            effective_to=None,
            geographic_scope="GENEL",
            verification_status="VERIFIED",
        ),
        SupportAmountModel(
            program_id="BASIC_SUPPORT_2026",
            crop_name="FINDIK",
            category="MEYVE",
            unit_amount=Decimal("170.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
            production_year=2026,
            legal_decision_number="11781",
            effective_from="2026-09-08",
            effective_to=None,
            geographic_scope="GENEL",
            verification_status="VERIFIED",
        ),
        # Planlı Üretim İlave Destek Birim Fiyatları
        SupportAmountModel(
            program_id="PLANNED_PRODUCTION_2026",
            crop_name="BUĞDAY",
            category="STRATEJİK",
            unit_amount=Decimal("465.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
            production_year=2026,
            legal_decision_number="11781",
            effective_from="2026-09-08",
            effective_to=None,
            geographic_scope="GENEL",
            verification_status="VERIFIED",
        ),
        SupportAmountModel(
            program_id="PLANNED_PRODUCTION_2026",
            crop_name="ARPA",
            category="STRATEJİK",
            unit_amount=Decimal("465.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
            production_year=2026,
            legal_decision_number="11781",
            effective_from="2026-09-08",
            effective_to=None,
            geographic_scope="GENEL",
            verification_status="VERIFIED",
        ),
        SupportAmountModel(
            program_id="PLANNED_PRODUCTION_2026",
            crop_name="AYÇİÇEĞİ",
            category="STRATEJİK",
            unit_amount=Decimal("410.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
            production_year=2026,
            legal_decision_number="11781",
            effective_from="2026-09-08",
            effective_to=None,
            geographic_scope="GENEL",
            verification_status="VERIFIED",
        ),
        # Sertifikalı Tohum
        SupportAmountModel(
            program_id="CERTIFIED_SEED_2026",
            crop_name="BUĞDAY",
            category="TOHUM",
            unit_amount=Decimal("120.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
            production_year=2026,
            legal_decision_number="11781",
            effective_from="2026-09-08",
            effective_to=None,
            geographic_scope="GENEL",
            verification_status="VERIFIED",
        ),
        SupportAmountModel(
            program_id="CERTIFIED_SEED_2026",
            crop_name="ARPA",
            category="TOHUM",
            unit_amount=Decimal("120.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
            production_year=2026,
            legal_decision_number="11781",
            effective_from="2026-09-08",
            effective_to=None,
            geographic_scope="GENEL",
            verification_status="VERIFIED",
        ),
        # Sertifikalı Fidan
        SupportAmountModel(
            program_id="CERTIFIED_SAPLING_2026",
            crop_name="FINDIK",
            category="FİDAN",
            unit_amount=Decimal("400.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
            production_year=2026,
            legal_decision_number="11781",
            effective_from="2026-09-08",
            effective_to=None,
            geographic_scope="GENEL",
            verification_status="VERIFIED",
        ),
        # Su Kısıtı İlave Destek
        SupportAmountModel(
            program_id="WATER_RESTRICTION_2026",
            crop_name="MERCİMEK",
            category="SU KISITI",
            unit_amount=Decimal("250.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
            production_year=2026,
            legal_decision_number="11781",
            effective_from="2026-09-08",
            effective_to=None,
            geographic_scope="GENEL",
            verification_status="VERIFIED",
        ),
        # Tarihsel / Eski Sürüm Örneği (310 TL Ağustos katsayılı eski karar - SUPERSEDED)
        SupportAmountModel(
            program_id="BASIC_SUPPORT_2026",
            crop_name="BUĞDAY",
            category="TAHIL",
            unit_amount=Decimal("310.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
            production_year=2026,
            legal_decision_number="32647",
            effective_from="2026-08-29",
            effective_to="2026-09-07",
            geographic_scope="GENEL",
            verification_status="SUPERSEDED",
        ),
    ]
    for amt in amounts:
        existing_amt = (
            session.query(SupportAmountModel)
            .filter_by(
                program_id=amt.program_id,
                crop_name=amt.crop_name,
                production_year=amt.production_year,
                verification_status=amt.verification_status,
            )
            .first()
        )
        if existing_amt:
            existing_amt.unit_amount = amt.unit_amount
            existing_amt.category = amt.category
            existing_amt.source_id = amt.source_id
            existing_amt.legal_decision_number = amt.legal_decision_number
            existing_amt.effective_from = amt.effective_from
            existing_amt.effective_to = amt.effective_to
            existing_amt.geographic_scope = amt.geographic_scope
        else:
            session.add(amt)

    # 4. Havza-Ürün Planlı Üretim Kuralları (Örnek Karatay/Konya ve Çarşamba/Samsun)
    basin_rules = [
        BasinCropRuleModel(
            province="KONYA",
            district="KARATAY",
            basin_name="KONYA KAPALI HAVZASI",
            crop_name="BUĞDAY",
            is_supported=True,
            year=2026,
            source_id="RG-2026-BITKISEL",
        ),
        BasinCropRuleModel(
            province="KONYA",
            district="KARATAY",
            basin_name="KONYA KAPALI HAVZASI",
            crop_name="ARPA",
            is_supported=True,
            year=2026,
            source_id="RG-2026-BITKISEL",
        ),
        BasinCropRuleModel(
            province="SAMSUN",
            district="ÇARŞAMBA",
            basin_name="YEŞİLIRMAK HAVZASI",
            crop_name="FINDIK",
            is_supported=True,
            year=2026,
            source_id="RG-2026-BITKISEL",
        ),
        BasinCropRuleModel(
            province="ANKARA",
            district="POLATLI",
            basin_name="SAKARYA HAVZASI",
            crop_name="SOĞAN",
            is_supported=True,
            year=2026,
            source_id="RG-2026-BITKISEL",
        ),
        BasinCropRuleModel(
            province="KONYA",
            district="SELÇUKLU",
            basin_name="KONYA KAPALI HAVZASI",
            crop_name="YONCA",
            is_supported=True,
            year=2026,
            source_id="RG-2026-BITKISEL",
        ),
    ]
    for br in basin_rules:
        existing_br = (
            session.query(BasinCropRuleModel)
            .filter_by(
                province=br.province,
                district=br.district,
                crop_name=br.crop_name,
                year=br.year,
            )
            .first()
        )
        if existing_br:
            existing_br.is_supported = br.is_supported
            existing_br.basin_name = br.basin_name
            existing_br.source_id = br.source_id
        else:
            session.add(br)

    # 5. Yeraltı Su Kısıtı Bölgesi
    water_res = [
        WaterRestrictionModel(
            province="KONYA",
            district="KARATAY",
            is_water_restricted=True,
            extra_support_amount=Decimal("250.00"),
            year=2026,
            source_id="RG-2026-BITKISEL",
        ),
        WaterRestrictionModel(
            province="KONYA",
            district="ÇUMRA",
            is_water_restricted=True,
            extra_support_amount=Decimal("250.00"),
            year=2026,
            source_id="RG-2026-BITKISEL",
        ),
    ]
    for wr in water_res:
        existing_wr = (
            session.query(WaterRestrictionModel)
            .filter_by(province=wr.province, district=wr.district)
            .first()
        )
        if existing_wr:
            existing_wr.is_water_restricted = wr.is_water_restricted
            existing_wr.extra_support_amount = wr.extra_support_amount
            existing_wr.source_id = wr.source_id
        else:
            session.add(wr)

    # 6. Başvuru Pencereleri
    windows = [
        ApplicationWindowModel(
            program_id="BASIC_SUPPORT_2026",
            year=2026,
            start_date="2026-09-01",
            end_date="2026-12-31",
            source_id="RG-2026-BITKISEL",
        ),
        ApplicationWindowModel(
            program_id="PLANNED_PRODUCTION_2026",
            year=2026,
            start_date="2026-09-01",
            end_date="2026-12-31",
            source_id="RG-2026-BITKISEL",
        ),
        ApplicationWindowModel(
            program_id="CERTIFIED_SEED_2026",
            year=2026,
            start_date="2026-10-01",
            end_date="2027-01-31",
            source_id="RG-2026-BITKISEL",
        ),
    ]
    for win in windows:
        existing_win = (
            session.query(ApplicationWindowModel)
            .filter_by(program_id=win.program_id, year=win.year)
            .first()
        )
        if existing_win:
            existing_win.start_date = win.start_date
            existing_win.end_date = win.end_date
            existing_win.source_id = win.source_id
        else:
            session.add(win)

    # 7. Tarımsal Soru-Cevap ve Sorun Kütüphanesini Tohumla
    from tarim_destek_rag.scraper.faq_harvester import AgriculturalFAQHarvester
    faq_harvester = AgriculturalFAQHarvester(session)
    faq_harvester.seed_initial_knowledge()

    session.commit()

