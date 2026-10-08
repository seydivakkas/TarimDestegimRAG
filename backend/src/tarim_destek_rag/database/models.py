from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from tarim_destek_rag.database.connection import Base


class SourceModel(Base):
    """Resmî kaynak tablosu."""

    __tablename__ = "sources"

    source_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    url: Mapped[str] = mapped_column(String(512), nullable=False)
    authority: Mapped[str] = mapped_column(String(64), nullable=False)
    title: Mapped[str] = mapped_column(String(256), nullable=False)
    content_type: Mapped[str] = mapped_column(String(16), default="HTML")
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    priority: Mapped[int] = mapped_column(Integer, default=0)

    versions: Mapped[list["SourceVersionModel"]] = relationship(
        back_populates="source", cascade="all, delete-orphan"
    )


class SourceVersionModel(Base):
    """Kaynak sürüm ve değişiklik geçmişi tablosu."""

    __tablename__ = "source_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sources.source_id", ondelete="CASCADE"), nullable=False
    )
    content_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    version: Mapped[int] = mapped_column(Integer, default=1)
    detected_at: Mapped[str] = mapped_column(String(32), nullable=False)
    superseded: Mapped[bool] = mapped_column(Boolean, default=False)
    effective_from: Mapped[str | None] = mapped_column(String(10), nullable=True)
    effective_to: Mapped[str | None] = mapped_column(String(10), nullable=True)

    source: Mapped["SourceModel"] = relationship(back_populates="versions")


class SupportProgramModel(Base):
    """Destekleme programları tablosu (Temel Destek, Planlı Üretim vb.)."""

    __tablename__ = "support_programs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)  # Örn: BASIC_SUPPORT_2026
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    year: Mapped[int] = mapped_column(Integer, default=2026)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    amounts: Mapped[list["SupportAmountModel"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )
    windows: Mapped[list["ApplicationWindowModel"]] = relationship(
        back_populates="program", cascade="all, delete-orphan"
    )


class SupportAmountModel(Base):
    """Destekleme birim tutarları (TL/da)."""

    __tablename__ = "support_amounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("support_programs.id", ondelete="CASCADE"), nullable=False
    )
    crop_name: Mapped[str] = mapped_column(String(64), nullable=False)
    category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    unit_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), default="TRY/da")
    source_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sources.source_id"), nullable=False
    )
    production_year: Mapped[int] = mapped_column(Integer, default=2026)
    legal_decision_number: Mapped[str | None] = mapped_column(String(64), default="11781", nullable=True)
    effective_from: Mapped[str | None] = mapped_column(String(10), default="2026-09-08", nullable=True)
    effective_to: Mapped[str | None] = mapped_column(String(10), nullable=True)
    geographic_scope: Mapped[str] = mapped_column(String(64), default="GENEL")
    verification_status: Mapped[str] = mapped_column(String(32), default="VERIFIED")  # VERIFIED, DRAFT, SUPERSEDED, REJECTED

    __table_args__ = (
        CheckConstraint("unit_amount >= 0", name="check_positive_amount"),
        UniqueConstraint("program_id", "crop_name", "production_year", "verification_status", name="uq_program_crop_year_status"),
    )

    program: Mapped["SupportProgramModel"] = relationship(back_populates="amounts")


class BasinCropRuleModel(Base):
    """Tarım havzaları bazında desteklenen ürün kuralları (Planlı Üretim)."""

    __tablename__ = "basin_crop_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    province: Mapped[str] = mapped_column(String(64), nullable=False)  # Örn: KONYA
    district: Mapped[str] = mapped_column(String(64), nullable=False)  # Örn: KARATAY
    basin_name: Mapped[str] = mapped_column(String(128), nullable=False)
    crop_name: Mapped[str] = mapped_column(String(64), nullable=False)  # Örn: BUĞDAY
    is_supported: Mapped[bool] = mapped_column(Boolean, default=True)
    year: Mapped[int] = mapped_column(Integer, default=2026)
    source_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sources.source_id"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("province", "district", "crop_name", "year", name="uq_basin_crop"),
    )


class ApplicationWindowModel(Base):
    """Başvuru başlangıç ve bitiş takvimi."""

    __tablename__ = "application_windows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("support_programs.id", ondelete="CASCADE"), nullable=False
    )
    year: Mapped[int] = mapped_column(Integer, default=2026)
    start_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    end_date: Mapped[str] = mapped_column(String(10), nullable=False)  # YYYY-MM-DD
    source_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sources.source_id"), nullable=False
    )

    program: Mapped["SupportProgramModel"] = relationship(back_populates="windows")


class WaterRestrictionModel(Base):
    """Yeraltı su kısıtı bulunan havzalar ve ürün kuralları."""

    __tablename__ = "water_restrictions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    province: Mapped[str] = mapped_column(String(64), nullable=False)
    district: Mapped[str] = mapped_column(String(64), nullable=False)
    is_water_restricted: Mapped[bool] = mapped_column(Boolean, default=True)
    extra_support_amount: Mapped[Decimal] = mapped_column(Numeric(10, 2), default=Decimal("0.00"))
    year: Mapped[int] = mapped_column(Integer, default=2026)
    source_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sources.source_id"), nullable=False
    )

    __table_args__ = (
        UniqueConstraint("province", "district", "year", name="uq_water_restriction"),
    )


class AgriculturalFAQModel(Base):
    """Genişletilmiş Tarımsal Soru-Cevap ve Sorun Kütüphanesi Tablosu."""

    __tablename__ = "agricultural_faqs"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    category: Mapped[str] = mapped_column(String(64), nullable=False)
    sub_category: Mapped[str | None] = mapped_column(String(64), nullable=True)
    question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    legal_citation: Mapped[str] = mapped_column(String(256), nullable=False)
    source_name: Mapped[str] = mapped_column(String(128), nullable=False)
    source_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    keywords: Mapped[str] = mapped_column(Text, nullable=False)
    verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)

    # Issue #4: Provenance, Diff, Moderasyon & Sürüm Alanları
    content_hash: Mapped[str | None] = mapped_column(String(64), nullable=True)
    effective_date: Mapped[str | None] = mapped_column(String(32), nullable=True)
    legal_span: Mapped[str | None] = mapped_column(String(256), nullable=True)
    moderation_status: Mapped[str] = mapped_column(String(32), default="APPROVED")
    harvested_at: Mapped[str | None] = mapped_column(String(32), nullable=True)
    source_domain: Mapped[str | None] = mapped_column(String(128), nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1)


class ModerationAuditLogModel(Base):
    """SSS ve Mevzuat moderasyon işlem denetim günlüğü."""

    __tablename__ = "moderation_audit_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(32), nullable=False)  # HARVEST, APPROVE, REJECT, SUPERSEDE
    faq_id: Mapped[str] = mapped_column(String(64), nullable=False)
    performed_by: Mapped[str] = mapped_column(String(64), nullable=False)
    timestamp: Mapped[str] = mapped_column(String(32), nullable=False)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
