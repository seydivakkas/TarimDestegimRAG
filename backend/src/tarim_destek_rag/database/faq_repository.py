"""Tarımsal Soru-Cevap ve Bilgi Tabanı Veritabanı Deposu (Repository).

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tarim_destek_rag.database.models import (
    AgriculturalFAQModel,
    ModerationAuditLogModel,
)


class FAQRepository:
    """Tarımsal soru-cevap kayıtlarının CRUD, filtreleme ve moderasyon işlemlerini yönetir."""

    def __init__(self, session: Session) -> None:
        self.session = session

    def upsert(self, faq_model: AgriculturalFAQModel) -> AgriculturalFAQModel:
        """Kayıt varsa günceller, yoksa ekler."""
        merged = self.session.merge(faq_model)
        self.session.commit()
        return merged

    def bulk_upsert(self, faq_models: list[AgriculturalFAQModel]) -> int:
        """Toplu kayıt ekler veya günceller."""
        count = 0
        for faq in faq_models:
            self.session.merge(faq)
            count += 1
        self.session.commit()
        return count

    def get_by_id(self, faq_id: str) -> AgriculturalFAQModel | None:
        """ID'ye göre tekil soru-cevap döner."""
        stmt = select(AgriculturalFAQModel).where(AgriculturalFAQModel.id == faq_id)
        return self.session.execute(stmt).scalar_one_or_none()

    def get_by_content_hash(self, content_hash: str) -> AgriculturalFAQModel | None:
        """İçerik SHA-256 hash'ine göre kayıt döner (tekilleştirme kontrolü)."""
        stmt = select(AgriculturalFAQModel).where(AgriculturalFAQModel.content_hash == content_hash)
        return self.session.execute(stmt).scalar_one_or_none()

    def list_faqs(
        self,
        category: str | None = None,
        search_query: str | None = None,
        only_verified: bool | None = None,
        moderation_status: str | None = None,
        limit: int = 500,
    ) -> list[AgriculturalFAQModel]:
        """Kategori ve metin filtrelerine göre soru-cevap listesi çeker."""
        stmt = select(AgriculturalFAQModel)

        if category and category != "Tümü":
            stmt = stmt.where(AgriculturalFAQModel.category == category)

        if only_verified is not None:
            stmt = stmt.where(AgriculturalFAQModel.verified.is_(only_verified))

        if moderation_status is not None:
            stmt = stmt.where(AgriculturalFAQModel.moderation_status == moderation_status)

        if search_query and search_query.strip():
            sq = f"%{search_query.strip().lower()}%"
            stmt = stmt.where(
                func.lower(AgriculturalFAQModel.question).like(sq)
                | func.lower(AgriculturalFAQModel.answer).like(sq)
                | func.lower(AgriculturalFAQModel.keywords).like(sq)
            )

        stmt = stmt.order_by(AgriculturalFAQModel.category, AgriculturalFAQModel.id).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def list_moderation_queue(
        self, status: str = "PENDING", limit: int = 100
    ) -> list[AgriculturalFAQModel]:
        """Moderasyon inceleme kuyruğundaki kayıtları döner."""
        stmt = (
            select(AgriculturalFAQModel)
            .where(AgriculturalFAQModel.moderation_status == status)
            .order_by(AgriculturalFAQModel.created_at.desc())
            .limit(limit)
        )
        return list(self.session.execute(stmt).scalars().all())

    def approve_faq(self, faq_id: str, admin_user: str = "admin") -> AgriculturalFAQModel | None:
        """Kayıt bağımsız uzman/moderatör tarafından onaylandığında doğrulanmış statüsüne geçirilir."""
        faq = self.get_by_id(faq_id)
        if not faq:
            return None
        faq.moderation_status = "APPROVED"
        faq.verified = True
        self.session.commit()

        self.log_audit(
            action="APPROVE",
            faq_id=faq_id,
            performed_by=admin_user,
            details=f"Onaylandı: {faq.question[:80]}",
        )
        return faq

    def reject_faq(
        self, faq_id: str, reason: str, admin_user: str = "admin"
    ) -> AgriculturalFAQModel | None:
        """Kayıt reddedilir ve yayından kaldırılır."""
        faq = self.get_by_id(faq_id)
        if not faq:
            return None
        faq.moderation_status = "REJECTED"
        faq.verified = False
        self.session.commit()

        self.log_audit(
            action="REJECT",
            faq_id=faq_id,
            performed_by=admin_user,
            details=f"Reddedildi: {reason}",
        )
        return faq

    def supersede_faq(self, faq_id: str, admin_user: str = "system") -> AgriculturalFAQModel | None:
        """Mevzuat veya içerik değiştiğinde eski kayıt superseded durumuna alınır."""
        faq = self.get_by_id(faq_id)
        if not faq:
            return None
        faq.moderation_status = "SUPERSEDED"
        faq.verified = False
        self.session.commit()

        self.log_audit(
            action="SUPERSEDE",
            faq_id=faq_id,
            performed_by=admin_user,
            details=f"Eski sürüm yürürlükten kalktı: {faq.id} v{faq.version}",
        )
        return faq

    def log_audit(
        self, action: str, faq_id: str, performed_by: str, details: str | None = None
    ) -> None:
        """Moderasyon ve kaynak toplama işlemini denetim kütüğüne işler."""
        now_iso = datetime.now(UTC).isoformat()
        audit_log = ModerationAuditLogModel(
            action=action,
            faq_id=faq_id,
            performed_by=performed_by,
            timestamp=now_iso,
            details=details,
        )
        self.session.add(audit_log)
        self.session.commit()

    def get_audit_logs(self, limit: int = 100) -> list[ModerationAuditLogModel]:
        """Denetim kütüğü kayıtlarını listeler."""
        stmt = select(ModerationAuditLogModel).order_by(ModerationAuditLogModel.id.desc()).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def get_categories(self) -> list[str]:
        """Sistemdeki benzersiz kategori isimlerini döner."""
        stmt = select(AgriculturalFAQModel.category).distinct().order_by(AgriculturalFAQModel.category)
        return list(self.session.execute(stmt).scalars().all())

    def get_stats(self) -> dict[str, Any]:
        """Veritabanındaki soru-cevap ve moderasyon istatistiklerini hesaplar."""
        total_stmt = select(func.count(AgriculturalFAQModel.id))
        total_count = self.session.execute(total_stmt).scalar() or 0

        verified_stmt = select(func.count(AgriculturalFAQModel.id)).where(AgriculturalFAQModel.verified.is_(True))
        verified_count = self.session.execute(verified_stmt).scalar() or 0

        pending_stmt = select(func.count(AgriculturalFAQModel.id)).where(AgriculturalFAQModel.moderation_status == "PENDING")
        pending_count = self.session.execute(pending_stmt).scalar() or 0

        live_stmt = select(func.count(AgriculturalFAQModel.id)).where(AgriculturalFAQModel.harvested_at.is_not(None))
        live_count = self.session.execute(live_stmt).scalar() or 0

        cat_stmt = (
            select(AgriculturalFAQModel.category, func.count(AgriculturalFAQModel.id))
            .group_by(AgriculturalFAQModel.category)
            .order_by(func.count(AgriculturalFAQModel.id).desc())
        )
        cat_counts = dict(self.session.execute(cat_stmt).all())

        return {
            "total_count": total_count,
            "verified_count": verified_count,
            "pending_moderation_count": pending_count,
            "live_harvested_count": live_count,
            "category_counts": cat_counts,
        }
