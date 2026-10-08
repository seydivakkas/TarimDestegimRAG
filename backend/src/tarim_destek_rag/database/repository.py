import re
from datetime import date

from sqlalchemy import and_, or_, select
from sqlalchemy.orm import Session

from tarim_destek_rag.database.models import (
    ApplicationWindowModel,
    BasinCropRuleModel,
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
            usable.append(rate)
        return usable[0] if len(usable) == 1 else None

    def get_window(self, program_id: str, year: int = 2026) -> ApplicationWindowModel | None:
        """Başvuru takvimini sorgular."""
        stmt = select(ApplicationWindowModel).where(
            ApplicationWindowModel.program_id == program_id,
            ApplicationWindowModel.year == year,
        )
        return self.session.scalars(stmt).first()


class BasinRepository:
    """Tarım havzaları ve ürün uygunluğu veri erişim katmanı."""

    def __init__(self, session: Session) -> None:
        self.session = session

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


class WaterRestrictionRepository:
    """Yeraltı su kısıtı veri erişim katmanı."""

    def __init__(self, session: Session) -> None:
        self.session = session

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
