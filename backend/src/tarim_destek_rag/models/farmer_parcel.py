from decimal import Decimal
from enum import StrEnum

from pydantic import BaseModel, Field, field_validator

from tarim_destek_rag.normalization.normalizer import normalize_crop_name


class IrrigationStatusEnum(StrEnum):
    """Sulama durumu."""

    IRRIGATED = "IRRIGATED"  # Sulu tarım
    DRY = "DRY"  # Kuru tarım
    UNKNOWN = "UNKNOWN"  # Bilinmiyor


class FarmerProfile(BaseModel):
    """Çiftçi profil modeli (Hassas kimlik bilgisi içermez)."""

    farmer_id: str = Field(default="FARMER-001", description="Sistem içi anonim çiftçi kimliği")
    province: str = Field(..., min_length=2, description="İl adı (Örn: KONYA)")
    district: str = Field(..., min_length=2, description="İlçe adı (Örn: KARATAY)")
    cks_status: bool | None = Field(
        default=None, description="Çiftçi Kayıt Sistemi (ÇKS) aktiflik durumu"
    )
    age_group: str | None = Field(default=None, description="Yaş grubu (genç çiftçi primi için)")
    gender: str | None = Field(default=None, description="Cinsiyet (kadın çiftçi primi için)")

    @field_validator("province", "district")
    @classmethod
    def uppercase_names(cls, v: str) -> str:
        return v.strip().upper()


class Parcel(BaseModel):
    """Parsel / Üretim alanı modeli."""

    parcel_id: str = Field(default="PARCEL-001", description="Parsel tekil kimliği")
    farmer_id: str = Field(default="FARMER-001", description="İlişkili çiftçi kimliği")
    crop: str = Field(..., description="Ekilmiş veya ekilecek ürün (Örn: Buğday)")
    area_da: Decimal = Field(..., gt=Decimal("0.0"), description="Üretim alanı (dekar)")
    irrigation: IrrigationStatusEnum = Field(
        default=IrrigationStatusEnum.DRY, description="Sulama durumu"
    )
    production_year: int = Field(default=2026, description="Üretim yılı")
    drip_irrigation: bool | None = Field(
        default=None, description="Dane mısırda şart koşulan damla sulama beyanı"
    )

    # Özel destek gereksinim beyanları
    seed_certificate_available: bool | None = Field(
        default=None, description="Sertifikalı tohum kullanım beyanı / faturası"
    )
    sapling_certificate_available: bool | None = Field(
        default=None, description="Sertifikalı fidan kullanım beyanı"
    )
    is_closed_orchard: bool | None = Field(default=None, description="Kapama meyve bahçesi mi?")

    @field_validator("crop")
    @classmethod
    def canonical_crop(cls, v: str) -> str:
        return normalize_crop_name(v)
