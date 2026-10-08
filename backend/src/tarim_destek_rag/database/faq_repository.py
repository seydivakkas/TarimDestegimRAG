"""Tarımsal Soru-Cevap ve Bilgi Tabanı Veritabanı Deposu (Repository).

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from tarim_destek_rag.database.models import AgriculturalFAQModel


class FAQRepository:
    """Tarımsal soru-cevap kayıtlarının CRUD ve filtreleme işlemlerini yönetir."""

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

    def list_faqs(
        self,
        category: str | None = None,
        search_query: str | None = None,
        limit: int = 500,
    ) -> list[AgriculturalFAQModel]:
        """Kategori ve metin filtrelerine göre soru-cevap listesi çeker."""
        stmt = select(AgriculturalFAQModel)

        if category and category != "Tümü":
            stmt = stmt.where(AgriculturalFAQModel.category == category)

        if search_query and search_query.strip():
            sq = f"%{search_query.strip().lower()}%"
            stmt = stmt.where(
                func.lower(AgriculturalFAQModel.question).like(sq)
                | func.lower(AgriculturalFAQModel.answer).like(sq)
                | func.lower(AgriculturalFAQModel.keywords).like(sq)
            )

        stmt = stmt.order_by(AgriculturalFAQModel.category, AgriculturalFAQModel.id).limit(limit)
        return list(self.session.execute(stmt).scalars().all())

    def get_categories(self) -> list[str]:
        """Sistemdeki benzersiz kategori isimlerini döner."""
        stmt = select(AgriculturalFAQModel.category).distinct().order_by(AgriculturalFAQModel.category)
        return list(self.session.execute(stmt).scalars().all())

    def get_stats(self) -> dict[str, Any]:
        """Veritabanındaki soru-cevap istatistiklerini hesaplar."""
        total_stmt = select(func.count(AgriculturalFAQModel.id))
        total_count = self.session.execute(total_stmt).scalar() or 0

        verified_stmt = select(func.count(AgriculturalFAQModel.id)).where(AgriculturalFAQModel.verified.is_(True))
        verified_count = self.session.execute(verified_stmt).scalar() or 0

        cat_stmt = (
            select(AgriculturalFAQModel.category, func.count(AgriculturalFAQModel.id))
            .group_by(AgriculturalFAQModel.category)
            .order_by(func.count(AgriculturalFAQModel.id).desc())
        )
        cat_counts = dict(self.session.execute(cat_stmt).all())

        return {
            "total_count": total_count,
            "verified_count": verified_count,
            "category_counts": cat_counts,
        }
