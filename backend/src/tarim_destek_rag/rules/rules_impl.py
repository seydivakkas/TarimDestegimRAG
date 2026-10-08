from decimal import Decimal

from sqlalchemy.orm import Session

from tarim_destek_rag.database.repository import (
    BasinRepository,
    SupportRepository,
    WaterRestrictionRepository,
)
from tarim_destek_rag.models.farmer_parcel import FarmerProfile, IrrigationStatusEnum, Parcel
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.rules.base import BaseRule, RuleResult


class BasicSupportRule(BaseRule):
    """Temel Destek Değerlendirme Kuralı (2026)."""

    rule_id = "RULE_BASIC_SUPPORT_2026"
    support_id = "BASIC_SUPPORT_2026"
    support_name = "Temel Destek"

    def evaluate(self, farmer: FarmerProfile, parcel: Parcel, session: Session) -> RuleResult:
        passed = []
        failed = []
        missing = []
        trace = []

        trace.append("Temel destek değerlendirmesi başlatıldı.")

        # 1. Üretim Yılı Kontrolü
        if parcel.production_year == 2026:
            passed.append("Üretim yılı 2026.")
        else:
            failed.append(f"Üretim yılı 2026 değil ({parcel.production_year}).")

        # 2. ÇKS Durumu Kontrolü
        if farmer.cks_status is None:
            missing.append("cks_status")
            trace.append("ÇKS kayıt bilgisi eksik (REVIEW).")
        elif farmer.cks_status is True:
            passed.append("Çiftçi Kayıt Sistemi (ÇKS) kaydı aktif.")
        else:
            failed.append("Çiftçi Kayıt Sistemi (ÇKS) kaydı bulunmuyor.")

        # 3. Parsel Alanı
        if parcel.area_da > 0:
            passed.append(f"Parsel alanı geçerli ({parcel.area_da} da).")
        else:
            failed.append("Parsel alanı sıfır veya negatif.")

        # 4. Ürün Birim Fiyatı Kontrolü
        support_repo = SupportRepository(session)
        amount_record = support_repo.get_amount(
            self.support_id, parcel.crop,
            production_year=parcel.production_year,
            province=farmer.province, district=farmer.district,
        )
        if amount_record:
            passed.append(f"{parcel.crop} ürünü için temel destek tanımı mevcut.")
        else:
            missing.append("verified_support_rate")
            trace.append("Kaynağı ve onayı doğrulanmış birim fiyat bulunamadı.")

        if failed:
            status = EligibilityStatusEnum.NOT_ELIGIBLE
        elif missing:
            status = EligibilityStatusEnum.REVIEW
        else:
            status = EligibilityStatusEnum.ELIGIBLE

        return RuleResult(
            rule_id=self.rule_id,
            support_id=self.support_id,
            support_name=self.support_name,
            status=status,
            passed_checks=passed,
            failed_checks=failed,
            missing_fields=missing,
            source_ids=([amount_record.source_version.source_id] if amount_record else []),
            trace=trace,
            metadata={
                "unit_amount": str(amount_record.unit_amount) if amount_record else None,
                "verified_rate_version_id": amount_record.id if amount_record else None,
                "verification_required": amount_record is None,
            },
        )


class PlannedProductionRule(BaseRule):
    """Planlı Üretim Desteği Değerlendirme Kuralı (2026)."""

    rule_id = "RULE_PLANNED_PRODUCTION_2026"
    support_id = "PLANNED_PRODUCTION_2026"
    support_name = "Planlı Üretim Desteği"

    def evaluate(self, farmer: FarmerProfile, parcel: Parcel, session: Session) -> RuleResult:
        passed = []
        failed = []
        missing = []
        trace = []

        trace.append("Planlı üretim havza uygunluğu değerlendiriliyor.")

        # 1. ÇKS zorunludur
        if farmer.cks_status is None:
            missing.append("cks_status")
        elif not farmer.cks_status:
            failed.append("ÇKS kaydı olmadığı için planlı üretim desteği verilemez.")
        else:
            passed.append("ÇKS kaydı aktif.")

        # 2. Havza ürün uygunluğu
        basin_repo = BasinRepository(session)
        loc = f"{farmer.province}/{farmer.district}"
        has_basin_data = basin_repo.has_basin_records(
            farmer.province, farmer.district, parcel.production_year
        )
        if not has_basin_data:
            missing.append("basin_data")
            trace.append(
                f"{loc} için 2026 yılı havza planlı üretim mevzuat verisi henüz kütüğe işlenmemiştir (DOĞRULAMA GEREKLİ)."
            )
        else:
            is_supported = basin_repo.is_crop_supported_in_basin(
                farmer.province, farmer.district, parcel.crop, parcel.production_year
            )
            if is_supported:
                passed.append(
                    f"{parcel.crop} ürünü, {loc} havzasında desteklenen öncelikli ürünlerdendir."
                )
            else:
                missing.append("verified_basin_crop")
                trace.append("Ürün-havza kaydı yokluğu doğrulanmış ret anlamına gelmez.")

        # Mevcut ilçe havza seed kayıtları resmî kapsam sertifikası değildir.
        missing.append("verified_basin_provenance")

        # 3. Birim Tutar Kontrolü
        support_repo = SupportRepository(session)
        amount_record = support_repo.get_amount(
            self.support_id, parcel.crop,
            production_year=parcel.production_year,
            province=farmer.province, district=farmer.district,
        )
        if amount_record:
            passed.append(f"{parcel.crop} için planlı üretim birim desteği tanımlı.")
        else:
            missing.append("verified_support_rate")
            trace.append("Planlı üretim için mevzuat sürümü onaylı birim fiyat bulunamadı.")

        if failed:
            status = EligibilityStatusEnum.NOT_ELIGIBLE
        elif missing:
            status = EligibilityStatusEnum.REVIEW
        else:
            status = EligibilityStatusEnum.ELIGIBLE

        return RuleResult(
            rule_id=self.rule_id,
            support_id=self.support_id,
            support_name=self.support_name,
            status=status,
            passed_checks=passed,
            failed_checks=failed,
            missing_fields=missing,
            source_ids=([amount_record.source_version.source_id] if amount_record else []),
            trace=trace,
            metadata={
                "unit_amount": str(amount_record.unit_amount) if amount_record else None,
                "verified_rate_version_id": amount_record.id if amount_record else None,
                "verification_required": amount_record is None,
            },
        )


class CertifiedSeedRule(BaseRule):
    """Sertifikalı Tohum Kullanım Desteği Kuralı."""

    rule_id = "RULE_CERTIFIED_SEED_2026"
    support_id = "CERTIFIED_SEED_2026"
    support_name = "Sertifikalı Tohum Kullanım Desteği"

    def evaluate(self, farmer: FarmerProfile, parcel: Parcel, session: Session) -> RuleResult:
        passed = []
        failed = []
        missing = []
        trace = []

        if farmer.cks_status is None:
            missing.append("cks_status")
        elif not farmer.cks_status:
            failed.append("ÇKS kaydı zorunludur.")
        else:
            passed.append("ÇKS kaydı aktif.")

        support_repo = SupportRepository(session)
        amount_record = support_repo.get_amount(
            self.support_id, parcel.crop,
            production_year=parcel.production_year,
            province=farmer.province, district=farmer.district,
        )
        if not amount_record:
            missing.append("verified_support_rate")
            trace.append("Sertifikalı tohum için onaylı tutar bulunamadı.")
        else:
            passed.append(f"{parcel.crop} için tohum desteği programı mevcut.")

        # Sertifika beyanı kontrolü
        if parcel.seed_certificate_available is None:
            missing.append("seed_certificate_available")
            trace.append("Sertifikalı tohum faturası/belgesi beyan edilmemiş (REVIEW).")
        elif parcel.seed_certificate_available is True:
            passed.append("Sertifikalı tohum belgesi/faturası mevcut.")
        else:
            failed.append("Sertifikalı tohum kullanılmamış.")

        if failed:
            status = EligibilityStatusEnum.NOT_ELIGIBLE
        elif missing:
            status = EligibilityStatusEnum.REVIEW
        else:
            status = EligibilityStatusEnum.ELIGIBLE

        return RuleResult(
            rule_id=self.rule_id,
            support_id=self.support_id,
            support_name=self.support_name,
            status=status,
            passed_checks=passed,
            failed_checks=failed,
            missing_fields=missing,
            source_ids=([amount_record.source_version.source_id] if amount_record else []),
            trace=trace,
            metadata={
                "unit_amount": str(amount_record.unit_amount) if amount_record else None,
                "verified_rate_version_id": amount_record.id if amount_record else None,
                "verification_required": amount_record is None,
            },
        )


class CertifiedSaplingRule(BaseRule):
    """Sertifikalı Fidan Kullanım Desteği Kuralı."""

    rule_id = "RULE_CERTIFIED_SAPLING_2026"
    support_id = "CERTIFIED_SAPLING_2026"
    support_name = "Sertifikalı Fidan Kullanım Desteği"

    def evaluate(self, farmer: FarmerProfile, parcel: Parcel, session: Session) -> RuleResult:
        passed = []
        failed = []
        missing = []
        trace = []

        if farmer.cks_status is None:
            missing.append("cks_status")
        elif not farmer.cks_status:
            failed.append("ÇKS kaydı zorunludur.")
        else:
            passed.append("ÇKS kaydı aktif.")

        support_repo = SupportRepository(session)
        amount_record = support_repo.get_amount(
            self.support_id, parcel.crop,
            production_year=parcel.production_year,
            province=farmer.province, district=farmer.district,
        )
        if not amount_record:
            missing.append("verified_support_rate")
            trace.append("Sertifikalı fidan için onaylı tutar bulunamadı.")
        else:
            passed.append(f"{parcel.crop} için fidan desteği programı mevcut.")

        if parcel.sapling_certificate_available is None:
            missing.append("sapling_certificate_available")
        elif parcel.sapling_certificate_available is True:
            passed.append("Sertifikalı fidan sertifikası mevcut.")
        else:
            failed.append("Sertifikalı fidan kullanılmamış.")

        # Kapama meyve bahçesi şartı
        if parcel.is_closed_orchard is False:
            failed.append("Sertifikalı fidan desteği sadece kapama meyve bahçesi tesisinde verilir.")
        elif parcel.is_closed_orchard is True:
            passed.append("Kapama meyve bahçesi şartı sağlandı.")
        elif parcel.is_closed_orchard is None:
            missing.append("is_closed_orchard")
            trace.append("Kapama meyve bahçesi durumu beyan edilmemiş (REVIEW).")

        # Asgari alan kontrolü (en az 5 dekar)
        if parcel.area_da < Decimal("5.0"):
            failed.append(
                f"Sertifikalı fidan desteği için asgari kapama bahçe alanı 5 dekardır (Parsel alanı: {parcel.area_da} da)."
            )
        else:
            passed.append(f"Asgari alan şartı (en az 5 da) sağlandı ({parcel.area_da} da).")

        if failed:
            status = EligibilityStatusEnum.NOT_ELIGIBLE
        elif missing:
            status = EligibilityStatusEnum.REVIEW
        else:
            status = EligibilityStatusEnum.ELIGIBLE

        return RuleResult(
            rule_id=self.rule_id,
            support_id=self.support_id,
            support_name=self.support_name,
            status=status,
            passed_checks=passed,
            failed_checks=failed,
            missing_fields=missing,
            source_ids=([amount_record.source_version.source_id] if amount_record else []),
            trace=trace,
            metadata={
                "unit_amount": str(amount_record.unit_amount) if amount_record else None,
                "verified_rate_version_id": amount_record.id if amount_record else None,
                "verification_required": amount_record is None,
            },
        )


class WaterRestrictionRule(BaseRule):
    """Yeraltı Su Kısıtı Desteği Kuralı."""

    rule_id = "RULE_WATER_RESTRICTION_2026"
    support_id = "WATER_RESTRICTION_2026"
    support_name = "Yeraltı Su Kısıtı Desteği"

    def evaluate(self, farmer: FarmerProfile, parcel: Parcel, session: Session) -> RuleResult:
        passed = []
        failed = []
        missing = []
        trace = []

        if farmer.cks_status is None:
            missing.append("cks_status")
        elif not farmer.cks_status:
            failed.append("ÇKS kaydı zorunludur.")
        else:
            passed.append("ÇKS kaydı aktif.")

        water_repo = WaterRestrictionRepository(session)
        restriction = water_repo.get_restriction(
            farmer.province, farmer.district, parcel.production_year
        )

        loc = f"{farmer.province}/{farmer.district}"
        if not restriction:
            missing.append("verified_water_restriction")
            trace.append("Su kısıtı kaydı yokluğu resmî ret anlamına gelmez.")
        else:
            passed.append(f"{loc} yeraltı su kısıtı bölgesindedir.")

        # Örnek coğrafi seed verisi resmî kararı ispatlamaz.
        missing.append("verified_water_provenance")

        # Su kısıtında desteklenen münavebe ürünü mü?
        support_repo = SupportRepository(session)
        amount_record = support_repo.get_amount(
            self.support_id, parcel.crop,
            production_year=parcel.production_year,
            province=farmer.province, district=farmer.district,
        )
        if amount_record:
            passed.append(
                f"{parcel.crop} ürünü su kısıtı bölgesinde münavebe ürünü olarak desteklenir."
            )
        else:
            missing.append("verified_support_rate")
            trace.append("Su kısıtı için onaylı bileşen tutarı bulunamadı.")

        # 4. Sulama Durumu Kontrolü (Sulu tarım arazisi şartı)
        if parcel.irrigation == IrrigationStatusEnum.UNKNOWN:
            missing.append("irrigation")
            trace.append("Sulama durumu bilinmiyor (REVIEW).")
        elif parcel.irrigation == IrrigationStatusEnum.DRY:
            failed.append(
                "Yeraltı su kısıtı desteği sadece sulu tarım arazilerinde su tasarrufu sağlayan münavebe ürünlerine verilir (Kuru tarım arazileri bu ilave desteğe uygun değildir)."
            )
        elif parcel.irrigation == IrrigationStatusEnum.IRRIGATED:
            passed.append("Parsel sulu tarım arazisi statüsündedir (Sulu arazi şartı sağlandı).")

        if failed:
            status = EligibilityStatusEnum.NOT_ELIGIBLE
        elif missing:
            status = EligibilityStatusEnum.REVIEW
        else:
            status = EligibilityStatusEnum.ELIGIBLE

        return RuleResult(
            rule_id=self.rule_id,
            support_id=self.support_id,
            support_name=self.support_name,
            status=status,
            passed_checks=passed,
            failed_checks=failed,
            missing_fields=missing,
            source_ids=([amount_record.source_version.source_id] if amount_record else []),
            trace=trace,
            metadata={
                "unit_amount": str(amount_record.unit_amount) if amount_record else None,
                "verified_rate_version_id": amount_record.id if amount_record else None,
                "verification_required": amount_record is None,
            },
        )
