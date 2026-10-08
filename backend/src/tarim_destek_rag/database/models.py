from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
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
    legal_decision_number: Mapped[str | None] = mapped_column(String(64), default=None, nullable=True)
    effective_from: Mapped[str | None] = mapped_column(String(10), default=None, nullable=True)
    effective_to: Mapped[str | None] = mapped_column(String(10), nullable=True)
    geographic_scope: Mapped[str] = mapped_column(String(64), default="GENEL")
    verification_status: Mapped[str] = mapped_column(String(32), default="DRAFT")  # VERIFIED, DRAFT, SUPERSEDED, REJECTED

    __table_args__ = (
        CheckConstraint("unit_amount >= 0", name="check_positive_amount"),
        UniqueConstraint("program_id", "crop_name", "production_year", "verification_status", name="uq_program_crop_year_status"),
    )

    program: Mapped["SupportProgramModel"] = relationship(back_populates="amounts")


class VerifiedSupportRateModel(Base):
    """Reviewed legal rate component; legacy support_amounts are never payment authority.

    Each row is a distinct legal/document version and is non-destructively retained.
    An effective version is only usable if its source document version and approval
    pass SupportRepository.get_amount's provenance checks.
    """

    __tablename__ = "verified_support_rates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("support_programs.id"), nullable=False
    )
    crop_name: Mapped[str] = mapped_column(String(64), nullable=False)
    production_year: Mapped[int] = mapped_column(Integer, nullable=False)
    # Explicit national scope uses "*" for both fields, not nullable SQL uniqueness.
    province: Mapped[str] = mapped_column(String(64), nullable=False, default="*")
    district: Mapped[str] = mapped_column(String(64), nullable=False, default="*")
    unit_amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="TRY/da")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("source_versions.id"), nullable=False
    )
    legal_clause: Mapped[str] = mapped_column(String(256), nullable=False)
    review_status: Mapped[str] = mapped_column(
        String(16), nullable=False, default="DRAFT"
    )
    approved_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source_version: Mapped["SourceVersionModel"] = relationship()

    __table_args__ = (
        CheckConstraint("unit_amount > 0", name="ck_verified_rate_positive"),
        CheckConstraint(
            "review_status IN ('DRAFT','VERIFIED','REVOKED')",
            name="ck_verified_rate_review_status",
        ),
        CheckConstraint(
            "(province = '*' AND district = '*') OR (province <> '*' AND district <> '*')",
            name="ck_verified_rate_geo_scope",
        ),
        UniqueConstraint(
            "program_id", "crop_name", "production_year", "province", "district",
            "source_version_id", name="uq_rate_component_source_version",
        ),
    )



class ReviewedBasinSnapshotModel(Base):
    """Complete, versioned province/district crop set; NOT the old demo basin rows.

    Only a reviewed, explicitly complete snapshot is eligible to provide
    either positive or negative product membership evidence.
    """

    __tablename__ = "reviewed_basin_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    province: Mapped[str] = mapped_column(String(64), nullable=False)
    district: Mapped[str] = mapped_column(String(64), nullable=False)
    production_year: Mapped[int] = mapped_column(Integer, nullable=False)
    crop_codes_json: Mapped[str] = mapped_column(Text, nullable=False)
    drip_required_for_grain_maize: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    document_page: Mapped[int] = mapped_column(Integer, nullable=False)
    source_version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("source_versions.id"), nullable=False
    )
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    coverage_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    review_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source_version: Mapped["SourceVersionModel"] = relationship()

    __table_args__ = (
        CheckConstraint("document_page > 0", name="ck_basin_snapshot_page"),
        CheckConstraint(
            "review_status IN ('DRAFT','VERIFIED','REVOKED')",
            name="ck_basin_snapshot_review_status",
        ),
        UniqueConstraint(
            "province", "district", "production_year", "source_version_id",
            name="uq_basin_district_source_version",
        ),
    )



class LegalApprovalAttestationModel(Base):
    """Externally Ed25519-signed, append-only review/approval attestations.

    Subject remains inert until both signatures validate under the deployment's
    independently configured public-key trust store.
    """

    __tablename__ = "legal_approval_attestations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    role: Mapped[str] = mapped_column(String(16), nullable=False)
    principal_id: Mapped[str] = mapped_column(String(128), nullable=False)
    subject_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    signed_at: Mapped[str] = mapped_column(String(32), nullable=False)
    signature_b64: Mapped[str] = mapped_column(String(128), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "subject_type IN ('RATE','BASIN')", name="ck_approval_subject_type"
        ),
        CheckConstraint(
            "role IN ('REVIEWER','APPROVER')", name="ck_approval_role"
        ),
        UniqueConstraint(
            "subject_type", "subject_id", "role",
            name="uq_legal_approval_subject_role",
        ),
    )


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
    verified: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[str] = mapped_column(String(32), nullable=False)

