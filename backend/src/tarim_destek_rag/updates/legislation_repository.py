"""Keşfedilen Resmî Mevzuat Depolama ve Sorgulama Deposu (P0-10).

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır.

YASAKLAR:
  1. Kopyalanamaz, çoğaltılamaz, dağıtılamaz veya yeniden yayınlanamaz.
  2. Ticari veya ticari olmayan hiçbir projede kullanılamaz, değiştirilemez.
  3. Alt lisanslanamaz, satılamaz veya devredilemez.
  4. Tersine mühendislik yapılamaz.

İZİN VERİLEN KULLANIM:
  - GitHub üzerinde görüntüleme ve okuma.
  - Kişisel öğrenim amacıyla kodu inceleme (kopyalamadan).

YAZARIN AÇIK YAZILI İZNİ OLMAKSIZIN HİÇBİR KULLANIM HAKKI TANINMAZ.
İzin talepleri için: GitHub @seydivakkas
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from tarim_destek_rag.updates.legislation_models import (
    AmendmentTarget,
    AnnexTableInfo,
    DiscoveredLegislation,
    EffectiveDateInfo,
    LegislationIdentity,
    LegislationType,
    TableKind,
)


def _atomic_write_json(path: Path, data: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    serialized = (json.dumps(data, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8")
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=str(path.parent), prefix=".stage_", delete=False
    ) as f:
        temp_path = Path(f.name)
        try:
            f.write(serialized)
            f.flush()
            os.fsync(f.fileno())
        except BaseException:
            temp_path.unlink(missing_ok=True)
            raise
    try:
        os.replace(temp_path, path)
    finally:
        temp_path.unlink(missing_ok=True)


class LegislationCatalogRepository:
    """Arşivlenmiş ve çözümlenmiş resmî mevzuat katalog deposu."""

    def __init__(self, archive_root: Path | str) -> None:
        self.archive_root = Path(archive_root).resolve()
        self.catalog_dir = self.archive_root / "legislation_catalog"
        self.catalog_dir.mkdir(parents=True, exist_ok=True)

    def save(self, legislation: DiscoveredLegislation) -> Path:
        """Mevzuatı atomik olarak katalog dizinine kaydeder."""
        target_path = self.catalog_dir / f"{legislation.document_sha256}.json"
        _atomic_write_json(target_path, legislation.to_dict())
        return target_path

    def load(self, document_sha256: str) -> DiscoveredLegislation | None:
        """SHA-256 özeti verilen mevzuatın yapısal kaydını yükler."""
        file_path = self.catalog_dir / f"{document_sha256}.json"
        if not file_path.is_file():
            return None
        try:
            raw = json.loads(file_path.read_text(encoding="utf-8"))
            ident_data = raw["identity"]
            ident = LegislationIdentity(
                legislation_type=LegislationType(ident_data.get("legislation_type", "BILINMEYEN")),
                title=ident_data.get("title", ""),
                number=ident_data.get("number"),
                rg_date=ident_data.get("rg_date"),
                rg_number=ident_data.get("rg_number"),
                authority=ident_data.get("authority", "T.C. TARIM VE ORMAN BAKANLIĞI"),
            )
            dates_data = raw.get("effective_dates", {})
            dates = EffectiveDateInfo(
                effective_date=dates_data.get("effective_date"),
                effective_clause_text=dates_data.get("effective_clause_text"),
                valid_production_years=dates_data.get("valid_production_years", []),
                is_publication_date=dates_data.get("is_publication_date", False),
                retroactive=dates_data.get("retroactive", False),
                article_effective_dates=dates_data.get("article_effective_dates", {}),
            )
            amend_data = raw.get("amendment_target")
            amend = None
            if amend_data:
                amend = AmendmentTarget(
                    base_legislation_title=amend_data.get("base_legislation_title"),
                    base_legislation_no=amend_data.get("base_legislation_no"),
                    base_rg_date=amend_data.get("base_rg_date"),
                    base_rg_number=amend_data.get("base_rg_number"),
                    modified_articles=amend_data.get("modified_articles", []),
                    amendment_summary=amend_data.get("amendment_summary"),
                )
            annexes = []
            for a_raw in raw.get("annex_tables", []):
                t_kind_str = a_raw.get("table_kind", "GENERAL")
                try:
                    t_kind = TableKind(t_kind_str)
                except ValueError:
                    t_kind = TableKind.GENERAL
                annexes.append(
                    AnnexTableInfo(
                        annex_code=a_raw.get("annex_code", ""),
                        title=a_raw.get("title", ""),
                        table_kind=t_kind,
                        page_number=a_raw.get("page_number"),
                        article_reference=a_raw.get("article_reference"),
                        content_sha256=a_raw.get("content_sha256"),
                    )
                )
            return DiscoveredLegislation(
                document_sha256=raw["document_sha256"],
                source_url=raw.get("source_url", ""),
                identity=ident,
                effective_dates=dates,
                amendment_target=amend,
                annex_tables=annexes,
                articles_found=raw.get("articles_found", []),
                discovered_at_utc=raw.get("discovered_at_utc", ""),
                review_status=raw.get("review_status", "DRAFT_DISCOVERED"),
            )
        except Exception:
            return None

    def list_all(
        self,
        year: int | None = None,
        legislation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Katalogdaki tüm mevzuatları filtreleyerek özet liste halinde döner."""
        items: list[dict[str, Any]] = []
        for file in self.catalog_dir.glob("*.json"):
            try:
                data = json.loads(file.read_text(encoding="utf-8"))
                if year is not None:
                    valid_years = data.get("effective_dates", {}).get("valid_production_years", [])
                    eff_date = data.get("effective_dates", {}).get("effective_date", "")
                    if year not in valid_years and not (eff_date and str(year) in eff_date):
                        continue
                if legislation_type is not None:
                    if data.get("identity", {}).get("legislation_type") != legislation_type:
                        continue
                items.append({
                    "document_sha256": data.get("document_sha256"),
                    "source_url": data.get("source_url"),
                    "legislation_type": data.get("identity", {}).get("legislation_type"),
                    "number": data.get("identity", {}).get("number"),
                    "title": data.get("identity", {}).get("title"),
                    "rg_date": data.get("identity", {}).get("rg_date"),
                    "rg_number": data.get("identity", {}).get("rg_number"),
                    "effective_date": data.get("effective_dates", {}).get("effective_date"),
                    "valid_production_years": data.get("effective_dates", {}).get("valid_production_years", []),
                    "amendment_target": (
                        data.get("amendment_target", {}).get("base_legislation_no")
                        if data.get("amendment_target")
                        else None
                    ),
                    "annex_tables_count": len(data.get("annex_tables", [])),
                    "review_status": data.get("review_status", "DRAFT_DISCOVERED"),
                })
            except Exception:
                continue
        # Tarihe veya numaraya göre sırala
        items.sort(key=lambda x: (x.get("rg_date") or "", x.get("number") or ""), reverse=True)
        return items

    def find_amendments_for_base(self, base_no: str) -> list[dict[str, Any]]:
        """Belirli bir ana tebliğe/karara ait değişiklik tebliğlerini bulur."""
        clean_base = base_no.strip()
        all_items = self.list_all(legislation_type=LegislationType.DEGISIKLIK_TEBLIGI.value)
        return [
            item for item in all_items
            if item.get("amendment_target") and clean_base in str(item.get("amendment_target"))
        ]
