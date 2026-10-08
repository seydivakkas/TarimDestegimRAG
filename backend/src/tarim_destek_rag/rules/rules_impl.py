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
        amount_record = support_repo.get_amount(self.support_id, parcel.crop)
        if amount_record:
            passed.append(f"{parcel.crop} ürünü için temel destek tanımı mevcut.")
        else:
            failed.append(f"{parcel.crop} ürünü için 2026 temel destek birim fiyatı bulunamadı.")

        # BÜGEM 2026 cetveli dipnotu: resmen su kısıtı bulunan havzalarda
        # dane mısır ve patates ekilişlerine temel destek ödenmez.
        if parcel.crop in {"MISIR", "PATATES"}:
            restricted = WaterRestrictionRepository(session).get_restriction(
                farmer.province, farmer.district, parcel.production_year
            )
            if restricted:
                failed.append(
                    f"{farmer.province}/{farmer.district} su kısıtı havzasında "
                    f"{parcel.crop} için temel destek ödenmez."
                )

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
            source_ids=[self.default_source_id],
            trace=trace,
            metadata={"unit_amount": float(amount_record.unit_amount) if amount_record else None},
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
        is_supported = basin_repo.is_crop_supported_in_basin(
            farmer.province, farmer.district, parcel.crop, parcel.production_year
        )

        loc = f"{farmer.province}/{farmer.district}"
        if is_supported:
            passed.append(
                f"{parcel.crop} ürünü, {loc} havzasında desteklenen öncelikli ürünlerdendir."
            )
        else:
            failed.append(
                f"{parcel.crop} ürünü, {loc} havzasında planlı üretim kapsamında yer almamaktadır."
            )

        # 3. Birim Tutar Kontrolü
        support_repo = SupportRepository(session)
        amount_record = support_repo.get_amount(self.support_id, parcel.crop)
        if amount_record:
            passed.append(f"{parcel.crop} için planlı üretim birim desteği tanımlı.")
        else:
            failed.append(f"{parcel.crop} için planlı üretim destek tutarı bulunamadı.")

        if missing:
            status = EligibilityStatusEnum.REVIEW
        elif failed:
            status = EligibilityStatusEnum.NOT_ELIGIBLE
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
            source_ids=[self.default_source_id],
            trace=trace,
            metadata={"unit_amount": float(amount_record.unit_amount) if amount_record else None},
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
        amount_record = support_repo.get_amount(self.support_id, parcel.crop)
        if not amount_record:
            failed.append(f"{parcel.crop} için sertifikalı tohum desteği bulunmuyor.")
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

        if missing:
            status = EligibilityStatusEnum.REVIEW
        elif failed:
            status = EligibilityStatusEnum.NOT_ELIGIBLE
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
            source_ids=[self.default_source_id],
            trace=trace,
            metadata={"unit_amount": float(amount_record.unit_amount) if amount_record else None},
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
        amount_record = support_repo.get_amount(self.support_id, parcel.crop)
        if not amount_record:
            failed.append(f"{parcel.crop} için sertifikalı fidan desteği bulunmuyor.")
        else:
            passed.append(f"{parcel.crop} için fidan desteği programı mevcut.")

        if parcel.sapling_certificate_available is None:
            missing.append("sapling_certificate_available")
        elif parcel.sapling_certificate_available is True:
            passed.append("Sertifikalı fidan sertifikası mevcut.")
        else:
            failed.append("Sertifikalı fidan kullanılmamış.")

        if missing:
            status = EligibilityStatusEnum.REVIEW
        elif failed:
            status = EligibilityStatusEnum.NOT_ELIGIBLE
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
            source_ids=[self.default_source_id],
            trace=trace,
            metadata={"unit_amount": float(amount_record.unit_amount) if amount_record else None},
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
            failed.append(
                f"{loc} bölgesi yeraltı su kısıtı ilan edilmiş havzalar arasında yer almamaktadır."
            )
        else:
            passed.append(f"{loc} yeraltı su kısıtı bölgesindedir.")

        # BÜGEM 2026 cetveline göre su kısıtı ek desteği yalnızca sulu tarım
        # arazilerinde uygulanır; bilgi yoksa uygunluk kesinleştirilmez.
        if parcel.irrigation == IrrigationStatusEnum.UNKNOWN:
            missing.append("irrigation")
            trace.append("Sulama durumu beyan edilmedi; inceleme gerekli.")
        elif parcel.irrigation == IrrigationStatusEnum.IRRIGATED:
            passed.append("Parsel sulu tarım arazisidir.")
        else:
            failed.append("Su kısıtı ilave desteği için sulu tarım arazisi şartı sağlanmadı.")

        # Su kısıtında desteklenen münavebe ürünü mü?
        support_repo = SupportRepository(session)
        amount_record = support_repo.get_amount(self.support_id, parcel.crop)
        if amount_record:
            passed.append(
                f"{parcel.crop} ürünü su kısıtı bölgesinde münavebe ürünü olarak desteklenir."
            )
        else:
            failed.append(
                f"{parcel.crop} ürünü su kısıtı bölgesinde ilave destekleme kapsamında değildir."
            )

        if missing:
            status = EligibilityStatusEnum.REVIEW
        elif failed:
            status = EligibilityStatusEnum.NOT_ELIGIBLE
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
            source_ids=[self.default_source_id],
            trace=trace,
            metadata={"unit_amount": float(amount_record.unit_amount) if amount_record else None},
        )
