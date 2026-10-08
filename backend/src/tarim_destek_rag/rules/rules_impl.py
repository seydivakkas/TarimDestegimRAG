from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from tarim_destek_rag.database.models import ReviewedWaterRestrictionScopeModel
from tarim_destek_rag.database.repository import (
    BasinRepository,
    SupportRepository,
    WaterRestrictionRepository,
    WaterScopeAssessment,
)
from tarim_destek_rag.models.farmer_parcel import FarmerProfile, IrrigationStatusEnum, Parcel
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.rules.base import BaseRule, RuleResult


def _enforce_2026_water_crop_exclusion(
    farmer: FarmerProfile, parcel: Parcel, session: Session,
    failed: list[str], missing: list[str], trace: list[str],
) -> None:
    """2025/42 m.12 / 2024/39 m.17/2(j), 2026 effective water exclusions.

    Art.5-7 support exclusion applies to GRAIN MAIZE and POTATO in declared
    water-restricted districts. Historic drip practice does not override it.
    """
    if parcel.production_year != 2026:
        return
    if parcel.crop == "MISIR":
        missing.append("crop_subtype")
        trace.append("2026 mısır türü (dane/silaj) belirtilmemiş.")
        return
    if parcel.crop not in ("MISIR_DANE", "PATATES"):
        return
    water_repo = WaterRestrictionRepository(session)
    has_scope = session.scalars(
        select(ReviewedWaterRestrictionScopeModel.id).limit(1)
    ).first() is not None
    if has_scope:
        water = water_repo.assess_2026(
            farmer.province, farmer.district, 2026
        )
    else:
        res = water_repo.evaluate_official_water_restriction(
            farmer.province, farmer.district, 2026
        )
        water = WaterScopeAssessment(outcome=res.outcome, reason=res.reason)

    if water.outcome == "UNKNOWN":
        missing.append("verified_water_scope")
        trace.append("2026 su kısıtı konumu doğrulanmadı: " + water.reason)
    elif water.outcome == "RESTRICTED":
        failed.append(
            "2025/42 m.12 uyarınca 2026 su kısıtı ilan edilmiş havzada "
            "dane mısır/patates ekilişine m.5-7 destek ödemesi yapılamaz."
        )
    else:
        trace.append("2026 su kısıtı dışında; diğer uygunluk koşulları ayrıca denetlenir.")


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

        _enforce_2026_water_crop_exclusion(farmer, parcel, session, failed, missing, trace)

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

        _enforce_2026_water_crop_exclusion(farmer, parcel, session, failed, missing, trace)

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
        assessment = basin_repo.evaluate_official_crop(
            farmer.province, farmer.district, parcel.crop, parcel.production_year
        )
        if assessment.outcome == "UNKNOWN":
            missing.append("verified_basin_provenance")
            trace.append(f"{loc} için bağımsız onaylı tam ilçe listesi yok: {assessment.reason}")
        elif assessment.outcome == "NOT_LISTED":
            failed.append(
                f"{parcel.crop}, {loc} için tamamı incelenmiş resmî ürün deseninde yok."
            )
            trace.append(assessment.reason)
        else:
            passed.append(
                f"{parcel.crop}, {loc} için onaylı 2026 ürün deseninde listeleniyor."
            )
            if assessment.drip_irrigation_required:
                if parcel.drip_irrigation is None:
                    missing.append("drip_irrigation")
                    trace.append(
                        "Dane mısır için yıldızlı ilçede damla sulama şartı; bilgi eksik."
                    )
                elif parcel.drip_irrigation is False:
                    failed.append("Dane mısır için zorunlu damla sulama uygulanmıyor.")
                else:
                    passed.append("Dane mısır damla sulama şartı beyanen sağlandı.")

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

        _enforce_2026_water_crop_exclusion(farmer, parcel, session, failed, missing, trace)

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

        _enforce_2026_water_crop_exclusion(farmer, parcel, session, failed, missing, trace)

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

        _enforce_2026_water_crop_exclusion(farmer, parcel, session, failed, missing, trace)

        if farmer.cks_status is None:
            missing.append("cks_status")
        elif not farmer.cks_status:
            failed.append("ÇKS kaydı zorunludur.")
        else:
            passed.append("ÇKS kaydı aktif.")

        water_repo = WaterRestrictionRepository(session)
        has_scope = session.scalars(
            select(ReviewedWaterRestrictionScopeModel.id).limit(1)
        ).first() is not None
        loc = f"{farmer.province}/{farmer.district}"
        if has_scope:
            assessment = water_repo.assess_2026(
                farmer.province, farmer.district, parcel.production_year
            )
            if assessment.outcome == "UNKNOWN":
                missing.append("verified_water_provenance")
                trace.append(f"{loc} 2026 su kısıtı belgesi henüz onaylı değil: {assessment.reason}")
            elif assessment.outcome == "NOT_RESTRICTED":
                failed.append(
                    f"{loc} resmî karara göre yeraltı su kısıtı bölgesinde yer almamaktadır."
                )
                trace.append(assessment.reason)
            else:
                passed.append(
                    f"{loc} onaylı resmî mevzuata göre yeraltı su kısıtı bölgesindedir."
                )
                trace.append(assessment.reason)
        else:
            assessment = water_repo.evaluate_official_water_restriction(
                farmer.province, farmer.district, parcel.production_year
            )
            if assessment.outcome == "NOT_RESTRICTED":
                failed.append(
                    f"{loc} resmî karara göre yeraltı su kısıtı bölgesinde yer almamaktadır."
                )
                trace.append(assessment.reason)
            elif assessment.outcome == "RESTRICTED":
                passed.append(
                    f"{loc} onaylı resmî mevzuata göre yeraltı su kısıtı bölgesindedir."
                )
                trace.append(assessment.reason)
            else:
                missing.append("verified_water_provenance")
                trace.append(f"{loc} su kısıtı resmî dayanağı: {assessment.reason}")

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
