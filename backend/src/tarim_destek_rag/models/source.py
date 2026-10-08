from enum import StrEnum
from typing import Annotated

from pydantic import BaseModel, Field, HttpUrl


class AuthorityEnum(StrEnum):
    """Resmî kaynak öncelik hiyerarşisi (P0 en yüksek öncelik)."""

    OFFICIAL_GAZETTE = "OFFICIAL_GAZETTE"  # P0 — Resmî Gazete
    MINISTRY = "MINISTRY"  # P1 — Tarım ve Orman Bakanlığı
    GENERAL_DIRECTORATE = "GENERAL_DIRECTORATE"  # P2 — BÜGEM vb. Genel Müdürlükler
    PROVINCIAL_DIRECTORATE = "PROVINCIAL_DIRECTORATE"  # P3 — İl/İlçe Müdürlükleri


class ContentTypeEnum(StrEnum):
    """Kaynak içerik türü."""

    HTML = "HTML"
    PDF = "PDF"
    JSON = "JSON"


# Öncelik sözlüğü (Küçük sayı = daha yüksek öncelik)
AUTHORITY_PRIORITY_MAP: dict[AuthorityEnum, int] = {
    AuthorityEnum.OFFICIAL_GAZETTE: 0,
    AuthorityEnum.MINISTRY: 1,
    AuthorityEnum.GENERAL_DIRECTORATE: 2,
    AuthorityEnum.PROVINCIAL_DIRECTORATE: 3,
}


class SourceDefinition(BaseModel):
    """Resmî kaynak tanımlama sözleşmesi (Source Contract)."""

    id: str = Field(..., description="Tekil kaynak kimliği (örn. RG-2026-BITKISEL)")
    url: HttpUrl = Field(..., description="Kaynağın resmî URL adresi")
    authority: AuthorityEnum = Field(..., description="Yetkili kurum kademesi")
    title: str = Field(..., description="Mevzuat veya kaynak başlığı")
    content_type: ContentTypeEnum = Field(
        default=ContentTypeEnum.HTML, description="İçerik formatı"
    )
    active: bool = Field(default=True, description="Kaynağın kullanımda olup olmadığı")
    priority: Annotated[int, Field(ge=0, le=3)] = Field(
        default=0, description="0 (P0 en yüksek) ile 3 (P3) arası öncelik puanı"
    )

    def model_post_init(self, __context) -> None:
        """Authority'ye göre priority'yi otomatik senkronize et."""
        expected_priority = AUTHORITY_PRIORITY_MAP.get(self.authority, 3)
        object.__setattr__(self, "priority", expected_priority)
