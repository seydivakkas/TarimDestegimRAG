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


def seed_2026_support_data(session: Session) -> None:
    """Yalnızca geçmiş/demo verisini bir kez ekler; güvenilir fiyat yetkisi vermez."""

    # 1. Ana Kaynak
    rg_source = SourceModel(
        source_id="RG-2026-BITKISEL",
        url="https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf",
        authority="OFFICIAL_GAZETTE",
        title="2024-2026 Bitkisel Üretime Yönelik Desteklemeler Kararı",
        content_type="PDF",
        active=True,
        priority=0,
    )
    # Do not rewrite an existing source URL/status used for historical provenance.
    if session.get(SourceModel, rg_source.source_id) is None:
        session.add(rg_source)
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
        # Temel Destek Birim Fiyatları
        SupportAmountModel(
            program_id="BASIC_SUPPORT_2026",
            crop_name="BUĞDAY",
            category="TAHIL",
            unit_amount=Decimal("465.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
        ),
        SupportAmountModel(
            program_id="BASIC_SUPPORT_2026",
            crop_name="ARPA",
            category="TAHIL",
            unit_amount=Decimal("465.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
        ),
        SupportAmountModel(
            program_id="BASIC_SUPPORT_2026",
            crop_name="MISIR",
            category="TAHIL",
            unit_amount=Decimal("380.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
        ),
        SupportAmountModel(
            program_id="BASIC_SUPPORT_2026",
            crop_name="AYÇİÇEĞİ",
            category="YAĞLI TOHUM",
            unit_amount=Decimal("410.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
        ),
        SupportAmountModel(
            program_id="BASIC_SUPPORT_2026",
            crop_name="PAMUK",
            category="ENDÜSTRİ",
            unit_amount=Decimal("550.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
        ),
        SupportAmountModel(
            program_id="BASIC_SUPPORT_2026",
            crop_name="FINDIK",
            category="MEYVE",
            unit_amount=Decimal("170.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
        ),
        # Planlı Üretim İlave Destek Birim Fiyatları
        SupportAmountModel(
            program_id="PLANNED_PRODUCTION_2026",
            crop_name="BUĞDAY",
            category="STRATEJİK",
            unit_amount=Decimal("465.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
        ),
        SupportAmountModel(
            program_id="PLANNED_PRODUCTION_2026",
            crop_name="ARPA",
            category="STRATEJİK",
            unit_amount=Decimal("465.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
        ),
        SupportAmountModel(
            program_id="PLANNED_PRODUCTION_2026",
            crop_name="AYÇİÇEĞİ",
            category="STRATEJİK",
            unit_amount=Decimal("410.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
        ),
        # Sertifikalı Tohum
        SupportAmountModel(
            program_id="CERTIFIED_SEED_2026",
            crop_name="BUĞDAY",
            category="TOHUM",
            unit_amount=Decimal("120.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
        ),
        SupportAmountModel(
            program_id="CERTIFIED_SEED_2026",
            crop_name="ARPA",
            category="TOHUM",
            unit_amount=Decimal("120.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
        ),
        # Sertifikalı Fidan
        SupportAmountModel(
            program_id="CERTIFIED_SAPLING_2026",
            crop_name="FINDIK",
            category="FİDAN",
            unit_amount=Decimal("400.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
        ),
        # Su Kısıtı İlave Destek
        SupportAmountModel(
            program_id="WATER_RESTRICTION_2026",
            crop_name="MERCİMEK",
            category="SU KISITI",
            unit_amount=Decimal("250.00"),
            unit="TRY/da",
            source_id="RG-2026-BITKISEL",
        ),
    ]
    for amt in amounts:
        existing_amt = (
            session.query(SupportAmountModel)
            .filter_by(program_id=amt.program_id, crop_name=amt.crop_name)
            .first()
        )
        # Preserve existing historic rows verbatim. Startup must never overwrite
        # a previously saved rate with a stale demonstration seed value.
        # Only verified_support_rates are used for live decisions/calculations.
        if existing_amt is None:
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

