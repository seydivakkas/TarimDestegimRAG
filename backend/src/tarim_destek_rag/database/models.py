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
            "subject_type IN ('RATE','BASIN','WATER')", name="ck_approval_subject_type"
        ),
        CheckConstraint(
            "role IN ('REVIEWER','APPROVER')", name="ck_approval_role"
        ),
        UniqueConstraint(
            "subject_type", "subject_id", "role",
            name="uq_legal_approval_subject_role",
        ),
    )




class LegalAuditReceiptModel(Base):
    """Evidence receipt for remote Object Lock COMPLIANCE WORM object versions.

    Signed legal records alone are not production approval until their exact
    immutable audit objects are read back and checked on every decision.
    """

    __tablename__ = "legal_audit_receipts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    event_role: Mapped[str] = mapped_column(String(16), nullable=False)
    object_bucket: Mapped[str] = mapped_column(String(255), nullable=False)
    object_key: Mapped[str] = mapped_column(String(512), nullable=False)
    object_version: Mapped[str] = mapped_column(String(255), nullable=False)
    payload_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    retain_until: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    __table_args__ = (
        CheckConstraint(
            "subject_type IN ('RATE','BASIN','WATER')",
            name="ck_audit_subject_kind",
        ),
        CheckConstraint(
            "event_role IN ('REVIEWER','APPROVER','REVOCATION')",
            name="ck_audit_event_role",
        ),
        UniqueConstraint(
            "subject_type", "subject_id", "event_role",
            name="uq_audit_subject_event_role",
        ),
        UniqueConstraint(
            "object_bucket", "object_key", "object_version",
            name="uq_audit_object_version",
        ),
    )


class LegalApprovalRevocationModel(Base):
    """Append-only tombstone that blocks a subject from ever becoming active again."""

    __tablename__ = "legal_approval_revocations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False)
    subject_id: Mapped[int] = mapped_column(Integer, nullable=False)
    subject_digest: Mapped[str] = mapped_column(String(64), nullable=False)
    source_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    principal_id: Mapped[str] = mapped_column(String(128), nullable=False)
    signed_at: Mapped[str] = mapped_column(String(32), nullable=False)
    reason: Mapped[str] = mapped_column(String(512), nullable=False)
    signature_b64: Mapped[str] = mapped_column(String(128), nullable=False)

    __table_args__ = (
        UniqueConstraint(
            "subject_type", "subject_id", name="uq_legal_revocation_subject"
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



class ReviewedWaterRestrictionScopeModel(Base):
    """A COMPLETE nationally reviewed 2026 2024/39 m.6/3(a) district enumeration.

    Distinct from 945 planning basins: source-and-amendment linked, never
    automatically elevated from the educational guide / seed.
    """

    __tablename__ = "reviewed_water_restriction_scopes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    production_year: Mapped[int] = mapped_column(Integer, nullable=False)
    district_keys_json: Mapped[str] = mapped_column(Text, nullable=False)
    coverage_complete: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    source_version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("source_versions.id"), nullable=False
    )
    amendment_source_version_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("source_versions.id"), nullable=False
    )
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")
    reviewed_by: Mapped[str | None] = mapped_column(String(128), nullable=True)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    review_reference: Mapped[str | None] = mapped_column(String(256), nullable=True)
    source_version: Mapped["SourceVersionModel"] = relationship(
        foreign_keys=[source_version_id]
    )
    amendment_source_version: Mapped["SourceVersionModel"] = relationship(
        foreign_keys=[amendment_source_version_id]
    )

    __table_args__ = (
        CheckConstraint("production_year = 2026", name="ck_water_scope_year_2026"),
        CheckConstraint(
            "review_status IN ('DRAFT','VERIFIED','REVOKED')",
            name="ck_water_scope_review_status",
        ),
        UniqueConstraint(
            "production_year", "source_version_id", "amendment_source_version_id",
            name="uq_water_scope_source_versions",
        ),
    )


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



# P0-8B: additive provenance staging; none of the following tables is a
# source for the current farmer payment engine until an independently reviewed
# release is explicitly bridged to VerifiedSupportRateModel.
class SourceDocumentModel(Base):
    """Original PDF byte-hash and publication provenance, not legal approval."""

    __tablename__ = "source_documents"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    source_id: Mapped[str] = mapped_column(
        String(64), ForeignKey("sources.source_id"), nullable=False
    )
    source_version_id: Mapped[int | None] = mapped_column(
        Integer, ForeignKey("source_versions.id"), nullable=True
    )
    production_year: Mapped[int] = mapped_column(Integer, nullable=False)
    document_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    original_url: Mapped[str] = mapped_column(String(1024), nullable=False)
    archive_relative_path: Mapped[str] = mapped_column(String(256), nullable=False)
    content_type: Mapped[str] = mapped_column(String(32), nullable=False, default="application/pdf")
    discovered_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")

    __table_args__ = (
        CheckConstraint("production_year BETWEEN 2020 AND 2100", name="ck_source_doc_year"),
        CheckConstraint("review_status IN ('DRAFT','REVIEW','REJECTED')", name="ck_source_doc_review_only"),
    )


class SentenceBoundingBoxModel(Base):
    """Exact text location on the original immutable PDF, not inferred law."""

    __tablename__ = "sentence_bounding_boxes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    document_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("source_documents.id"), nullable=False
    )
    page_number: Mapped[int] = mapped_column(Integer, nullable=False)
    exact_text: Mapped[str] = mapped_column(Text, nullable=False)
    article_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    paragraph_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    clause_no: Mapped[str | None] = mapped_column(String(64), nullable=True)
    bounding_boxes_json: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_quads_json: Mapped[str] = mapped_column(Text, nullable=False)
    text_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")

    __table_args__ = (
        CheckConstraint("page_number > 0", name="ck_sentence_bbox_page"),
        CheckConstraint("review_status IN ('DRAFT','REVIEW','REJECTED')", name="ck_sentence_bbox_review_only"),
        UniqueConstraint(
            "document_id", "page_number", "text_sha256",
            name="uq_document_page_exact_sentence",
        ),
    )


class DynamicRateModel(Base):
    """Year-independent extracted candidate; NEVER directly payment-authoritative.

    A separately governed release must validate legal effect, source binding,
    geographical coverage, other eligibility conditions and signatures.
    """

    __tablename__ = "dynamic_rate_candidates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    program_key: Mapped[str] = mapped_column(String(96), nullable=False)
    crop_code: Mapped[str] = mapped_column(String(96), nullable=False)
    production_year: Mapped[int] = mapped_column(Integer, nullable=False)
    province: Mapped[str] = mapped_column(String(64), nullable=False, default="*")
    district: Mapped[str] = mapped_column(String(64), nullable=False, default="*")
    base_coefficient: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    category_multiplier: Mapped[Decimal] = mapped_column(Numeric(12, 4), nullable=False)
    proposed_unit_amount: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    unit: Mapped[str] = mapped_column(String(16), nullable=False, default="TRY/da")
    effective_from: Mapped[date] = mapped_column(Date, nullable=False)
    effective_to: Mapped[date | None] = mapped_column(Date, nullable=True)
    source_sentence_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("sentence_bounding_boxes.id"), nullable=False
    )
    review_status: Mapped[str] = mapped_column(String(16), nullable=False, default="DRAFT")

    __table_args__ = (
        CheckConstraint("production_year BETWEEN 2020 AND 2100", name="ck_dynamic_rate_year"),
        CheckConstraint("base_coefficient > 0 AND category_multiplier > 0", name="ck_dynamic_rate_positive"),
        CheckConstraint("proposed_unit_amount > 0", name="ck_dynamic_rate_amount_positive"),
        CheckConstraint("review_status IN ('DRAFT','REVIEW','REJECTED')", name="ck_dynamic_rate_never_payment"),
        UniqueConstraint(
            "program_key", "crop_code", "production_year",
            "province", "district", "source_sentence_id",
            name="uq_year_dynamic_candidate_sentence",
        ),
    )
