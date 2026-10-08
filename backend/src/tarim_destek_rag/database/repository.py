import json
import re
from dataclasses import dataclass
from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from tarim_destek_rag.normalization.basin_2026 import (
    BASIN_SOURCE_ID, BASIN_SOURCE_URL, PINNED_BASIN_PDF_SHA256,
)

from tarim_destek_rag.database.legal_approvals import two_person_approved

from tarim_destek_rag.database.models import (
    ApplicationWindowModel,
    BasinCropRuleModel,
    ReviewedBasinSnapshotModel,
    ReviewedWaterRestrictionScopeModel,
    SourceModel,
    SourceVersionModel,
    SupportAmountModel,
    SupportProgramModel,
    WaterRestrictionModel,
    VerifiedSupportRateModel,
)


class SourceRepository:
    """Kaynak ve versiyon veri erişim katmanı."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert_source(
        self,
        source_id: str,
        url: str,
        authority: str,
        title: str,
        content_type: str = "HTML",
        active: bool = True,
        priority: int = 0,
    ) -> SourceModel:
        """Kaynağı ekler veya günceller."""
        stmt = select(SourceModel).where(SourceModel.source_id == source_id)
        source = self.session.scalars(stmt).first()
        if not source:
            source = SourceModel(
                source_id=source_id,
                url=url,
                authority=authority,
                title=title,
                content_type=content_type,
                active=active,
                priority=priority,
            )
            self.session.add(source)
        else:
            source.url = url
            source.title = title
            source.active = active
            source.priority = priority
        self.session.flush()
        return source

    def add_version(
        self,
        source_id: str,
        content_hash: str,
        detected_at: str,
        version: int = 1,
        superseded: bool = False,
    ) -> SourceVersionModel:
        """Yeni bir versiyon kaydı ekler."""
        ver = SourceVersionModel(
            source_id=source_id,
            content_hash=content_hash,
            detected_at=detected_at,
            version=version,
            superseded=superseded,
        )
        self.session.add(ver)
        self.session.flush()
        return ver

    def get_source(self, source_id: str) -> SourceModel | None:
        return self.session.get(SourceModel, source_id)


class SupportRepository:
    """Destekleme programları ve tutarları veri erişim katmanı."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def get_program(self, program_id: str) -> SupportProgramModel | None:
        return self.session.get(SupportProgramModel, program_id)

    def list_programs(self, year: int = 2026) -> list[SupportProgramModel]:
        stmt = select(SupportProgramModel).where(
            SupportProgramModel.year == year, SupportProgramModel.active.is_(True)
        )
        return list(self.session.scalars(stmt).all())

    def get_legacy_amount(self, program_id: str, crop_name: str) -> SupportAmountModel | None:
        """Unverified historic/seed values. Never use for entitlement calculations."""
        stmt = select(SupportAmountModel).where(
            SupportAmountModel.program_id == program_id,
            SupportAmountModel.crop_name == crop_name,
        )
        return self.session.scalars(stmt).first()

    def get_amount(
        self,
        program_id: str,
        crop_name: str,
        *,
        production_year: int,
        province: str,
        district: str,
        as_of: date | None = None,
    ) -> VerifiedSupportRateModel | None:
        """Fail closed unless exactly one approved, effective, evidenced component matches.

        No legacy rate fallback. National rates may apply to a local query, but
        overlapping approved national/local versions produce an ambiguous result.
        """
        evaluation_date = as_of if as_of is not None else date.today()
        stmt = (
            select(VerifiedSupportRateModel)
            .join(
                SourceVersionModel,
                VerifiedSupportRateModel.source_version_id == SourceVersionModel.id,
            )
            .join(SourceModel, SourceVersionModel.source_id == SourceModel.source_id)
            .join(
                SupportProgramModel,
                VerifiedSupportRateModel.program_id == SupportProgramModel.id,
            )
            .where(
                VerifiedSupportRateModel.program_id == program_id,
                VerifiedSupportRateModel.crop_name == crop_name,
                VerifiedSupportRateModel.production_year == production_year,
                VerifiedSupportRateModel.review_status == "VERIFIED",
                VerifiedSupportRateModel.unit == "TRY/da",
                VerifiedSupportRateModel.unit_amount > 0,
                VerifiedSupportRateModel.effective_from <= evaluation_date,
                or_(
                    VerifiedSupportRateModel.effective_to.is_(None),
                    VerifiedSupportRateModel.effective_to >= evaluation_date,
                ),
                SourceModel.active.is_(True),
                SupportProgramModel.active.is_(True),
                SupportProgramModel.year == production_year,
                SourceVersionModel.superseded.is_(False),
                or_(
                    and_(
                        VerifiedSupportRateModel.province == "*",
                        VerifiedSupportRateModel.district == "*",
                    ),
                    and_(
                        VerifiedSupportRateModel.province == province.strip().upper(),
                        VerifiedSupportRateModel.district == district.strip().upper(),
                    ),
                ),
            )
        )
        candidates = list(self.session.scalars(stmt).all())
        usable: list[VerifiedSupportRateModel] = []
        for rate in candidates:
            version = rate.source_version
            if (
                not rate.approved_by
                or not rate.approved_at
                or not rate.review_reference
                or not rate.legal_clause.strip()
                or version is None
                or not re.fullmatch(r"[0-9a-fA-F]{64}", version.content_hash or "")
                or not version.detected_at
                or not version.effective_from
                or version.effective_from > evaluation_date.isoformat()
                or (version.effective_to and version.effective_to < evaluation_date.isoformat())
                or (rate.effective_to is not None and rate.effective_to < rate.effective_from)
            ):
                continue
            if not two_person_approved(self.session, rate):
                continue
            usable.append(rate)
        return usable[0] if len(usable) == 1 else None

    def list_amount_history(
        self,
        program_id: str,
        crop_name: str,
    ) -> list[SupportAmountModel]:
        """Bir program ve ürün için tüm mevzuat sürümleri ve tutar geçmişini listeler."""
        stmt = (
            select(SupportAmountModel)
            .where(
                SupportAmountModel.program_id == program_id,
                SupportAmountModel.crop_name == crop_name,
            )
            .order_by(SupportAmountModel.production_year.desc(), SupportAmountModel.id.desc())
        )
        return list(self.session.scalars(stmt).all())

    def get_window(self, program_id: str, year: int = 2026) -> ApplicationWindowModel | None:
        """Başvuru takvimini sorgular."""
        stmt = select(ApplicationWindowModel).where(
            ApplicationWindowModel.program_id == program_id,
            ApplicationWindowModel.year == year,
        )
        return self.session.scalars(stmt).first()



@dataclass(frozen=True)
class BasinCropAssessment:
    """Evidence-backed outcome for the *planning* crop list only."""

    outcome: str  # LISTED, NOT_LISTED, UNKNOWN
    reason: str
    source_version_id: int | None = None
    document_page: int | None = None
    drip_irrigation_required: bool = False


class BasinRepository:
    """Tarım havzaları ve ürün uygunluğu veri erişim katmanı."""

    def __init__(self, session: Session) -> None:
        self.session = session


    def evaluate_official_crop(
        self,
        province: str,
        district: str,
        crop_code: str,
        year: int,
    ) -> BasinCropAssessment:
        """Fail closed on missing, stale, duplicate or incomplete district lists.

        Old BasinCropRuleModel seed rows have NO authority here.
        A complete reviewed district list allows a negative membership result.
        These outcomes concern the planning *list*, not final farmer eligibility.
        """
        stmt = (
            select(ReviewedBasinSnapshotModel)
            .join(
                SourceVersionModel,
                ReviewedBasinSnapshotModel.source_version_id == SourceVersionModel.id,
            )
            .join(SourceModel, SourceVersionModel.source_id == SourceModel.source_id)
            .where(
                ReviewedBasinSnapshotModel.province == province.strip().upper(),
                ReviewedBasinSnapshotModel.district == district.strip().upper(),
                ReviewedBasinSnapshotModel.production_year == year,
                ReviewedBasinSnapshotModel.review_status == "VERIFIED",
                ReviewedBasinSnapshotModel.coverage_complete.is_(True),
                SourceModel.active.is_(True),
                SourceVersionModel.superseded.is_(False),
            )
        )
        snapshots = list(self.session.scalars(stmt).all())
        if len(snapshots) != 1:
            return BasinCropAssessment(
                "UNKNOWN", "Resmî tam ilçe ürün listesi henüz doğrulanmadı veya çakışıyor."
            )
        snapshot = snapshots[0]
        version = snapshot.source_version
        if (
            not snapshot.reviewed_by
            or not snapshot.reviewed_at
            or not snapshot.review_reference
            or snapshot.document_page < 1
            or not version
            or version.source_id != BASIN_SOURCE_ID
            or version.content_hash != PINNED_BASIN_PDF_SHA256
            or version.source is None
            or version.source.url != BASIN_SOURCE_URL
            or not version.effective_from
            or version.effective_from > f"{year}-12-31"
            or (version.effective_to and version.effective_to < f"{year}-01-01")
        ):
            return BasinCropAssessment("UNKNOWN", "Belge sürümü veya bağımsız onay eksik.")
        if not two_person_approved(self.session, snapshot):
            return BasinCropAssessment(
                "UNKNOWN", "İlçe ürün listesi iki bağımsız kriptografik onaydan geçmedi."
            )
        try:
            crops = json.loads(snapshot.crop_codes_json)
        except (TypeError, ValueError):
            crops = None
        if (
            not isinstance(crops, list)
            or not crops
            or any(not isinstance(x, str) or not x for x in crops)
            or len(set(crops)) != len(crops)
        ):
            return BasinCropAssessment("UNKNOWN", "Ürün listesi bütünlük kontrolü başarısız.")
        crop = crop_code.strip().upper()
        # Generic crop labels must not become false negatives for subtype lists.
        # E.g. MISIR != MISIR_DANE and PAMUK != PAMUK_KÜTLÜ.
        known_exact_codes = {
            "ARPA", "ASPİR", "AYÇİÇEĞİ_YAĞLIK", "BUĞDAY", "FASULYE_KURU",
            "KANOLA", "MERCİMEK", "MISIR_DANE", "NOHUT", "PAMUK_KÜTLÜ",
            "PATATES", "SOĞAN_KURU", "SOYA", "YEM_BITKILERI_GROUP",
        }
        if crop not in known_exact_codes:
            return BasinCropAssessment(
                "UNKNOWN", "Ürün alt türü resmî listeyle kesin eşleştirilemiyor."
            )
        if crop not in crops:
            return BasinCropAssessment(
                "NOT_LISTED", "Onaylı eksiksiz ilçe ürün deseninde bu ürün bulunmuyor.",
                snapshot.source_version_id, snapshot.document_page,
            )
        drip = snapshot.drip_required_for_grain_maize and crop == "MISIR_DANE"
        return BasinCropAssessment(
            "LISTED", "Onaylı 2026 ilçe ürün deseninde ürün mevcut.",
            snapshot.source_version_id, snapshot.document_page, drip,
        )

    def has_basin_records(
        self, province: str, district: str, year: int = 2026
    ) -> bool:
        """İl ve ilçe için sisteme işlenmiş havza kuralı kaydı bulunup bulunmadığını kontrol eder."""
        stmt = select(BasinCropRuleModel).where(
            BasinCropRuleModel.province == province.upper(),
            BasinCropRuleModel.district == district.upper(),
            BasinCropRuleModel.year == year,
        )
        return self.session.scalars(stmt).first() is not None

    def is_crop_supported_in_basin(
        self, province: str, district: str, crop_name: str, year: int = 2026
    ) -> bool:
        """İl, ilçe ve ürün bazında havza planlı üretim desteğini doğrular."""
        stmt = select(BasinCropRuleModel).where(
            BasinCropRuleModel.province == province.upper(),
            BasinCropRuleModel.district == district.upper(),
            BasinCropRuleModel.crop_name == crop_name.upper(),
            BasinCropRuleModel.year == year,
            BasinCropRuleModel.is_supported.is_(True),
        )
        rule = self.session.scalars(stmt).first()
        return rule is not None


@dataclass(frozen=True)
class WaterScopeAssessment:
    outcome: str  # RESTRICTED, NOT_RESTRICTED, UNKNOWN
    reason: str
    source_version_id: int | None = None


class WaterRestrictionRepository:
    """Yeraltı su kısıtı veri erişim katmanı."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def assess_2026(self, province: str, district: str, year: int) -> WaterScopeAssessment:
        """Only complete dual-signed 2024/39 + 2025/42 national scope may decide.

        In particular, old demo water_restrictions rows and the 945 crop-plan
        district star flags have NO authority over water support eligibility.
        """
        if year != 2026:
            return WaterScopeAssessment("UNKNOWN", "2026 dışındaki üretim yılı incelenmedi.")
        from tarim_destek_rag.normalization.water_2026 import (
            PRIMARY_ID, AMENDMENT_ID, PINNED_DISTRICTS,
        )

        candidates = list(self.session.scalars(select(
            ReviewedWaterRestrictionScopeModel
        ).where(
            ReviewedWaterRestrictionScopeModel.production_year == year,
            ReviewedWaterRestrictionScopeModel.review_status == "VERIFIED",
            ReviewedWaterRestrictionScopeModel.coverage_complete.is_(True),
        )).all())
        if len(candidates) != 1:
            return WaterScopeAssessment(
                "UNKNOWN", "Tam, benzersiz ve onaylı 2026 su kısıtı kapsamı bulunamadı."
            )
        scope = candidates[0]
        base = scope.source_version
        amend = scope.amendment_source_version
        if (
            not scope.reviewed_by or not scope.reviewed_at or not scope.review_reference
            or base is None or amend is None
            or base.source_id != PRIMARY_ID or amend.source_id != AMENDMENT_ID
            or not base.effective_from or not amend.effective_from
            or base.effective_from > "2026-12-31"
            or amend.effective_from > "2026-01-01"
            or (base.effective_to and base.effective_to < "2026-01-01")
            or (amend.effective_to and amend.effective_to < "2026-12-31")
            or not two_person_approved(self.session, scope)
        ):
            return WaterScopeAssessment(
                "UNKNOWN", "Kaynak sürümleri veya çift imzalı 2026 onayı eksik."
            )
        try:
            keys = json.loads(scope.district_keys_json)
        except (TypeError, ValueError):
            keys = None
        if not isinstance(keys, list) or set(keys) != PINNED_DISTRICTS or len(keys) != 52:
            return WaterScopeAssessment("UNKNOWN", "Ulusal 52 ilçe hukukî kümesi uyuşmuyor.")
        def tr_upper(value: str) -> str:
            return value.strip().replace("i", "İ").replace("ı", "I").upper()
        key = f"{tr_upper(province)}/{tr_upper(district)}"
        if key in keys:
            return WaterScopeAssessment(
                "RESTRICTED", "2024/39 m.6/3(a) 2026 onaylı su kısıtı ilçesi.",
                scope.source_version_id,
            )
        return WaterScopeAssessment(
            "NOT_RESTRICTED", "Onaylı 2026 tam su kısıtı ilçe listesinde yer almıyor.",
            scope.source_version_id,
        )

    def get_restriction(
        self, province: str, district: str, year: int = 2026
    ) -> WaterRestrictionModel | None:
        """Konumun su kısıtı bölgesinde olup olmadığını sorgular."""
        stmt = select(WaterRestrictionModel).where(
            WaterRestrictionModel.province == province.upper(),
            WaterRestrictionModel.district == district.upper(),
            WaterRestrictionModel.year == year,
            WaterRestrictionModel.is_water_restricted.is_(True),
        )
        return self.session.scalars(stmt).first()
