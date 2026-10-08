"""Resmî Kaynak Taraması, Provenans, Diff ve Moderasyon Hattı (Harvest & Moderation Pipeline).

Mimari Akış:
SourceRegistry -> AllowlistedFetcher -> OfficialFAQParser -> Provenance & Diff -> Review Queue -> Approved Knowledge Base -> Retriever Index.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

import hashlib
import json
import re
from datetime import UTC, datetime
from typing import Any
from urllib.parse import urlparse

import bs4
import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from tarim_destek_rag.database.faq_repository import FAQRepository
from tarim_destek_rag.database.models import AgriculturalFAQModel
from tarim_destek_rag.logging.logger import logger
from tarim_destek_rag.retrieval.models import DocumentChunk
from tarim_destek_rag.scraper.source_registry import SourceRegistry


class AllowlistedFetcher:
    """Yalnızca izin verilen resmî sitelerden veri çeken güvenli istemci."""

    def __init__(self, registry: type[SourceRegistry] = SourceRegistry) -> None:
        self.registry = registry

    def fetch(self, url: str, override_html: str | None = None) -> tuple[str, str, str]:
        """URL içeriğini çeker, güvenlik kontrollerini yapar ve SHA-256 parmak izini hesaplar.
        
        Döner: (raw_text, sha256_hash, source_domain)
        """
        is_allowed, reason = self.registry.validate_url(url)
        if not is_allowed:
            raise ValueError(f"Güvenlik İhlali: {reason}")

        parsed = urlparse(url)
        domain = parsed.hostname or "unknown"

        if override_html is not None:
            raw_text = override_html
        else:
            headers = {"User-Agent": self.registry.USER_AGENT}
            try:
                with httpx.Client(
                    timeout=self.registry.REQUEST_TIMEOUT_SECONDS,
                    follow_redirects=True,
                ) as client:
                    resp = client.get(url, headers=headers)
                    resp.raise_for_status()

                    # Boyut sınırı kontrolü
                    if len(resp.content) > self.registry.MAX_CONTENT_LENGTH:
                        raise ValueError(f"Boyut sınırı aşıldı: {len(resp.content)} byte")

                    raw_text = resp.text
            except Exception as e:
                logger.error("Web kaynağı çekilemedi: %s - %s", url, e)
                raise RuntimeError(f"Kaynak çekme hatası ({url}): {e}") from e

        content_hash = hashlib.sha256(raw_text.encode("utf-8")).hexdigest()
        return raw_text, content_hash, domain


class OfficialFAQParser:
    """HTML ve metin belgelerinden yapılandırılmış SSS ve mevzuat maddelerini ayrıştırır."""

    @staticmethod
    def parse_html(
        raw_html: str, source_url: str, default_source_name: str = "Resmî Portal"
    ) -> list[dict[str, Any]]:
        """HTML dokümanından SSS, mevzuat maddeleri ve kanıt aralıklarını çıkarır."""
        soup = bs4.BeautifulSoup(raw_html, "html.parser")
        extracted_items: list[dict[str, Any]] = []

        # 1. <article class="faq-item"> veya benzeri yapıları ara
        articles = soup.find_all(["article", "div"], class_=re.compile(r"faq|item|question", re.I))
        seen_hashes: set[str] = set()

        for art in articles:
            # Eğer bu öğenin içinde başka bir faq/item öğesi varsa bu bir kapsayıcıdır (container/wrapper); atla
            if art.find(["article", "div"], class_=re.compile(r"faq|item", re.I)):
                continue

            q_elem = art.find(["h2", "h3", "h4", "strong", "dt", "p"], class_=re.compile(r"question|title", re.I))
            a_elem = art.find(["div", "dd", "p"], class_=re.compile(r"answer|body|content", re.I))

            if q_elem and a_elem:
                q_text = q_elem.get_text(strip=True)
                a_text = a_elem.get_text(strip=True)
                if len(q_text) > 5 and len(a_text) > 10:
                    cit_elem = art.find(class_=re.compile(r"citation|dayanak|kaynak", re.I))
                    citation = cit_elem.get_text(strip=True) if cit_elem else "Resmî Gazete / Bakanlık Tebliği"

                    # Madde / fıkra ayrıştırma
                    span_match = re.search(r"(Madde\s*\d+(?:,\s*Fıkra\s*\d+)?)", f"{q_text} {citation}", re.I)
                    legal_span = span_match.group(1) if span_match else "Genel Hüküm"

                    item_hash = hashlib.sha256(f"{q_text}::{a_text}::{citation}".encode("utf-8")).hexdigest()
                    if item_hash in seen_hashes:
                        continue
                    seen_hashes.add(item_hash)

                    extracted_items.append({
                        "question": q_text,
                        "answer": a_text,
                        "legal_citation": citation,
                        "legal_span": legal_span,
                        "source_name": default_source_name,
                        "source_url": source_url,
                        "category": "🌾 Resmî Mevzuat & Destekler",
                        "content_hash": item_hash,
                    })

        # 2. Tanım Listesi (<dl><dt><dd>) yapısı
        dl_elements = soup.find_all("dl")
        for dl in dl_elements:
            dts = dl.find_all("dt")
            for dt in dts:
                dd = dt.find_next_sibling("dd")
                if dd:
                    q_text = dt.get_text(strip=True)
                    a_text = dd.get_text(strip=True)
                    if len(q_text) > 5 and len(a_text) > 10:
                        cit_match = re.search(r"(Resmî\s*Gazete.*?Karar\s*No:\s*\d+[^<\n]*)", a_text, re.I)
                        citation = cit_match.group(1) if cit_match else "Resmî Karar"
                        span_match = re.search(r"(Madde\s*\d+(?:,\s*Fıkra\s*\d+)?)", f"{q_text} {a_text}", re.I)
                        legal_span = span_match.group(1) if span_match else "Genel Hüküm"

                        item_hash = hashlib.sha256(f"{q_text}::{a_text}::{citation}".encode("utf-8")).hexdigest()
                        extracted_items.append({
                            "question": q_text,
                            "answer": a_text,
                            "legal_citation": citation,
                            "legal_span": legal_span,
                            "source_name": default_source_name,
                            "source_url": source_url,
                            "category": "🌾 Resmî Mevzuat & Destekler",
                            "content_hash": item_hash,
                        })

        return extracted_items


class HarvestModerationService:
    """Taramayı, içerik farkı (diff) yönetimini ve bağımsız moderatör onayını yönetir."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repo = FAQRepository(session)
        self.fetcher = AllowlistedFetcher()
        self.parser = OfficialFAQParser()

    def harvest_from_source(
        self,
        url: str,
        admin_user: str = "admin",
        override_html: str | None = None,
        source_name: str = "Resmî Tarım Portalı",
    ) -> dict[str, Any]:
        """Resmî kaynaktan veri çeker, diff analizi yapar ve inceleme kuyruğuna (PENDING) yönlendirir."""
        raw_text, _, domain = self.fetcher.fetch(url, override_html=override_html)
        items = self.parser.parse_html(raw_text, source_url=url, default_source_name=source_name)

        total_extracted = len(items)
        new_pending_count = 0
        superseded_count = 0
        skipped_duplicates = 0
        now_iso = datetime.now(UTC).isoformat()

        for item in items:
            q = item["question"]
            chash = item["content_hash"]

            # 1. Birebir aynı içerik hash'i var mı? (İdempotent koruma)
            existing_same_hash = self.repo.get_by_content_hash(chash)
            if existing_same_hash:
                skipped_duplicates += 1
                continue

            # 2. Soru metniyle eşleşen mevcut kayıt var mı?
            stmt = select(AgriculturalFAQModel).where(
                AgriculturalFAQModel.question == q,
                AgriculturalFAQModel.moderation_status.in_(["APPROVED", "PENDING"]),
            )
            existing_version = self.session.execute(stmt).scalars().first()

            if existing_version:
                # İçerik değişmiş -> Eski sürümü SUPERSEDED yap, yeni sürümü versiyonla
                self.repo.supersede_faq(existing_version.id, admin_user=admin_user)
                superseded_count += 1
                new_version = existing_version.version + 1
                fid = f"{existing_version.id.split('_v')[0]}_v{new_version}"
            else:
                new_version = 1
                fid = f"faq_live_{hashlib.md5(q.encode()).hexdigest()[:8]}"

            # Yeni sürüm PENDING (Onay Bekliyor) olarak kaydedilir; ASLA otomatik verified=True yapılmaz!
            faq_model = AgriculturalFAQModel(
                id=fid,
                category=item["category"],
                sub_category="Canlı Taranan Mevzuat",
                question=q,
                answer=item["answer"],
                legal_citation=item["legal_citation"],
                source_name=source_name,
                source_url=url,
                keywords=json.dumps(["mevzuat", "canlı", "resmî"], ensure_ascii=False),
                verified=False,  # Bağımsız uzman onayı olmadan doğrulanmış sayılmaz!
                created_at=now_iso,
                content_hash=chash,
                effective_date="2026-09-08",
                legal_span=item["legal_span"],
                moderation_status="PENDING",
                harvested_at=now_iso,
                source_domain=domain,
                version=new_version,
            )
            self.session.add(faq_model)
            new_pending_count += 1

        self.session.commit()

        self.repo.log_audit(
            action="HARVEST",
            faq_id=url,
            performed_by=admin_user,
            details=(
                f"Toplam: {total_extracted}, Yeni İnceleme: {new_pending_count}, "
                f"Güncellenen/Superseded: {superseded_count}, Tekrar Eden/Atlanan: {skipped_duplicates}"
            ),
        )

        return {
            "status": "SUCCESS",
            "source_url": url,
            "total_extracted": total_extracted,
            "new_pending": new_pending_count,
            "superseded_count": superseded_count,
            "skipped_duplicates": skipped_duplicates,
        }

    def approve_item(
        self, faq_id: str, admin_user: str = "admin", retriever: Any | None = None
    ) -> AgriculturalFAQModel:
        """Moderatör onayı verir, verified=True yapar ve arama motoruna ekler."""
        faq = self.repo.approve_faq(faq_id, admin_user=admin_user)
        if not faq:
            raise ValueError(f"FAQ bulunamadı: {faq_id}")

        # Eğer RAG Retriever verildiyse onaylanan kaydı indekse ekle
        if retriever and hasattr(retriever, "add_chunks"):
            chunk = DocumentChunk(
                chunk_id=f"chunk_mod_{faq.id}",
                source_id=faq.source_name[:32],
                title=f"{faq.category} — {faq.question[:64]}",
                section=f"{faq.category} / Moderasyon Onaylı",
                text=f"Soru: {faq.question}\n\nCevap: {faq.answer}\n\nYasal Dayanak: {faq.legal_citation}",
                year=2026,
            )
            retriever.add_chunks([chunk])

        return faq

    def reject_item(
        self, faq_id: str, reason: str, admin_user: str = "admin"
    ) -> AgriculturalFAQModel:
        """Moderatörün kaydı uygunsuz/hatalı bularak reddetmesi."""
        faq = self.repo.reject_faq(faq_id, reason=reason, admin_user=admin_user)
        if not faq:
            raise ValueError(f"FAQ bulunamadı: {faq_id}")
        return faq
