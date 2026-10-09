"""Resmî Mevzuat Keşif ve Yapısal Sınıflandırma Modelleri (P0-10).

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

from dataclasses import asdict, dataclass, field
from enum import StrEnum
from typing import Any


class LegislationType(StrEnum):
    """Resmî mevzuat metin türleri."""

    CUMHURBASKANI_KARARI = "CUMHURBASKANI_KARARI"
    BAKANLIK_TEBLIGI = "BAKANLIK_TEBLIGI"
    DEGISIKLIK_TEBLIGI = "DEGISIKLIK_TEBLIGI"
    YONETMELIK = "YONETMELIK"
    EK_TABLO = "EK_TABLO"
    GENELGE = "GENELGE"
    BILINMEYEN = "BILINMEYEN"


class TableKind(StrEnum):
    """Ek tablo ve liste kategorileri."""

    SUPPORT_RATES = "SUPPORT_RATES"            # Temel/Planlı destek birim tutarları ve katsayılar
    WATER_RESTRICTION = "WATER_RESTRICTION"    # Su kısıtı olan havzalar/ilçeler ve istisnalar
    PLANNED_PRODUCTION = "PLANNED_PRODUCTION"  # Planlı üretim kapsamındaki ürünler
    SEED_SAPLING = "SEED_SAPLING"              # Sertifikalı tohum ve fidan destekleri
    GENERAL = "GENERAL"                        # Diğer idari ve teknik tablolar


@dataclass(frozen=True)
class LegislationIdentity:
    """Resmî mevzuat kimlik göstergeleri."""

    legislation_type: LegislationType
    title: str
    number: str | None = None
    rg_date: str | None = None       # YYYY-MM-DD formatında Resmî Gazete tarihi
    rg_number: str | None = None     # Resmî Gazete sayısı (örn: "32642")
    authority: str = "T.C. TARIM VE ORMAN BAKANLIĞI"


@dataclass(frozen=True)
class EffectiveDateInfo:
    """Yürürlük ve geçerlilik süresi metaverisi."""

    effective_date: str | None = None              # YYYY-MM-DD
    effective_clause_text: str | None = None       # Özgün yürürlük maddesi alıntısı
    valid_production_years: list[int] = field(default_factory=list)  # [2025, 2026, 2027]
    is_publication_date: bool = False              # Yayımı tarihinde mi yürürlüğe giriyor?
    retroactive: bool = False                      # Geriye dönük hüküm var mı?


@dataclass(frozen=True)
class AmendmentTarget:
    """Değişiklik tebliğlerinin hedef aldığı ana mevzuat ve değiştirilen maddeler."""

    base_legislation_title: str | None = None
    base_legislation_no: str | None = None         # Örn: "2024/39"
    base_rg_date: str | None = None                # Örn: "2024-08-24"
    base_rg_number: str | None = None              # Örn: "32642"
    modified_articles: list[str] = field(default_factory=list)  # ["MADDE 6", "MADDE 16"]
    amendment_summary: str | None = None


@dataclass(frozen=True)
class AnnexTableInfo:
    """Mevzuata ekli tablolar, listeler ve cetveller."""

    annex_code: str                                # Örn: "EK-1", "EK-2", "EK-3"
    title: str                                     # Örn: "Temel Destek Katsayı Tablosu"
    table_kind: TableKind
    page_number: int | None = None                 # PDF sayfa numarası (1-indexed)
    article_reference: str | None = None           # Tabloya atıf yapan madde (örn: "Madde 6(2)")
    content_sha256: str | None = None


@dataclass
class DiscoveredLegislation:
    """Yapısal olarak çözümlenmiş ve doğrulanmış resmî mevzuat kaydı."""

    document_sha256: str
    source_url: str
    identity: LegislationIdentity
    effective_dates: EffectiveDateInfo
    amendment_target: AmendmentTarget | None = None
    annex_tables: list[AnnexTableInfo] = field(default_factory=list)
    articles_found: list[str] = field(default_factory=list)
    discovered_at_utc: str = ""
    review_status: str = "DRAFT_DISCOVERED"        # Her zaman DRAFT, asla doğrudan ACTIVE değil!

    def to_dict(self) -> dict[str, Any]:
        data = asdict(self)
        data["identity"]["legislation_type"] = self.identity.legislation_type.value
        for annex in data.get("annex_tables", []):
            if isinstance(annex.get("table_kind"), TableKind):
                annex["table_kind"] = annex["table_kind"].value
            elif isinstance(annex.get("table_kind"), str):
                pass
        return data
