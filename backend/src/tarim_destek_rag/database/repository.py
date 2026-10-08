from sqlalchemy import select
from sqlalchemy.orm import Session

from tarim_destek_rag.database.models import (
    ApplicationWindowModel,
    BasinCropRuleModel,
    SourceModel,
    SourceVersionModel,
    SupportAmountModel,
    SupportProgramModel,
    WaterRestrictionModel,
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

    def get_amount(self, program_id: str, crop_name: str) -> SupportAmountModel | None:
        """Belirtilen program ve ürün için birim destek tutarını sorgular."""
        stmt = select(SupportAmountModel).where(
            SupportAmountModel.program_id == program_id,
            SupportAmountModel.crop_name == crop_name,
        )
        return self.session.scalars(stmt).first()

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
