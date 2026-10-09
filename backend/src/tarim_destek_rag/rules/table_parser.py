"""Resmî Mevzuat Ek Tabloları (EK-1, EK-2, EK-3) Fiyat ve Kural Matrisi Ayrıştırıcı.

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

import re
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from tarim_destek_rag.updates.legislation_models import AnnexTableInfo, TableKind

# Standartlaştırılmış ürün eşleme sözlüğü
CROP_CANONICAL_MAP = {
    "buğday": "BUĞDAY",
    "ekmeklik buğday": "BUĞDAY",
    "makarnalık buğday": "BUĞDAY",
    "bugday": "BUĞDAY",
    "arpa": "ARPA",
    "çavdar": "ÇAVDAR",
    "cavdar": "ÇAVDAR",
    "yulaf": "YULAF",
    "tritikale": "TRİTİKALE",
    "çeltik": "ÇELTİK",
    "celtik": "ÇELTİK",
    "dane mısır": "MISIR_DANE",
    "dane mısir": "MISIR_DANE",
    "mısır (dane)": "MISIR_DANE",
    "mısır dane": "MISIR_DANE",
    "misir dane": "MISIR_DANE",
    "mısır": "MISIR_DANE",
    "misir": "MISIR_DANE",
    "yağlık ayçiçeği": "AYÇİÇEĞİ_YAĞLIK",
    "ayçiçeği (yağlık)": "AYÇİÇEĞİ_YAĞLIK",
    "ayçiçeği": "AYÇİÇEĞİ_YAĞLIK",
    "aycicegi": "AYÇİÇEĞİ_YAĞLIK",
    "kütlü pamuk": "PAMUK_KÜTLÜ",
    "pamuk (kütlü)": "PAMUK_KÜTLÜ",
    "pamuk": "PAMUK_KÜTLÜ",
    "soya": "SOYA",
    "kanola": "KANOLA",
    "aspir": "ASPİR",
    "mercimek": "MERCİMEK",
    "kırmızı mercimek": "MERCİMEK",
    "yeşil mercimek": "MERCİMEK",
    "nohut": "NOHUT",
    "kuru fasulye": "FASULYE_KURU",
    "fasulye (kuru)": "FASULYE_KURU",
    "fasulye": "FASULYE_KURU",
    "patates": "PATATES",
    "kuru soğan": "SOĞAN_KURU",
    "soğan (kuru)": "SOĞAN_KURU",
    "soğan": "SOĞAN_KURU",
    "fındık": "FINDIK",
    "findik": "FINDIK",
    "zeytin": "ZEYTİN",
    "yem bitkileri": "YEM_BİTKİLERİ",
}

# Standart su kısıtı havzaları ve 52 ilçe (2025/42 ve 2024/39 uyarınca)
DEFAULT_WATER_RESTRICTION_BASINS: dict[str, list[str]] = {
    "AKSARAY": ["ESKİL", "GÜLAĞAÇ", "MERKEZ", "SULTANHANI"],
    "ANKARA": ["BALA", "GÖLBAŞI", "HAYMANA", "POLATLI", "ŞEREFLİKOÇHİSAR"],
    "ESKİŞEHİR": ["GÜNYÜZÜ", "MAHMUDİYE", "SİVRİHİSAR"],
    "KARAMAN": ["AYRANCI", "KAZIMKARABEKİR", "MERKEZ"],
    "KAYSERİ": ["DEVELİ", "İNCESU", "YEŞİLHİSAR"],
    "KIRIKKALE": ["BAHŞILI", "ÇELEBİ", "DELİCE", "KARAKEÇİLİ", "KESKİN"],
    "KIRŞEHİR": ["AKPINAR", "BOZTEPE", "MUCUR"],
    "KONYA": [
        "AKÖREN", "ALTINEKİN", "BOZKIR", "CİHANBEYLİ", "ÇELTİK", "ÇUMRA",
        "EMİRGAZİ", "EREĞLİ", "GÜNEYSINIR", "HALKAPINAR", "KADINHANI",
        "KARAPINAR", "KARATAY", "KULU", "MERAM", "SARAYÖNÜ", "SELÇUKLU",
        "YUNAK",
    ],
    "NEVŞEHİR": ["ACIGÖL", "DERİNKUYU", "GÜLŞEHİR", "KOZAKLI", "MERKEZ", "ÜRGÜP"],
    "NİĞDE": ["BOR", "ÇAMARDI", "MERKEZ"],
}


def normalize_crop_code(crop_name: str) -> str:
    """Ürün metnini standart büyük harfli ve kanonik ürün koduna dönüştürür."""
    s = crop_name.strip()
    tr_lower_map = {
        "İ": "i", "I": "ı", "Ç": "ç", "Ğ": "ğ", "Ö": "ö", "Ş": "ş", "Ü": "ü",
    }
    for tr_upper, tr_low in tr_lower_map.items():
        s = s.replace(tr_upper, tr_low)
    clean = s.lower().replace("\u0307", "")
    clean = (
        clean.replace("ı", "i")
        .replace("ğ", "g")
        .replace("ü", "u")
        .replace("ş", "s")
        .replace("ö", "o")
        .replace("ç", "c")
    )
    for raw_k, canonical in CROP_CANONICAL_MAP.items():
        norm_k = (
            raw_k.replace("ı", "i")
            .replace("ğ", "g")
            .replace("ü", "u")
            .replace("ş", "s")
            .replace("ö", "o")
            .replace("ç", "c")
            .replace("\u0307", "")
        )
        if norm_k == clean or norm_k in clean or clean in norm_k:
            return canonical
    # Bilinmeyen ise temizle ve döndür
    return re.sub(r"[^A-Z0-9_]", "", crop_name.strip().upper()) or "GENEL_URUN"


@dataclass(frozen=True)
class ExtractedRateRow:
    """EK-1 Temel Destek Katsayı Tablosundan çıkarılan satır."""

    crop_code: str
    crop_name: str
    category: int
    category_multiplier: Decimal
    base_coefficient: Decimal
    official_unit_amount: Decimal
    unit: str = "TRY/da"
    source_table: str = "EK-1"


@dataclass(frozen=True)
class PlannedCropRow:
    """EK-2 Planlı Üretim Destek Listesinden çıkarılan satır."""

    crop_code: str
    crop_name: str
    category_multiplier: Decimal
    base_coefficient: Decimal
    official_unit_amount: Decimal
    eligible_provinces: tuple[str, ...] = ("*",)
    eligible_districts: tuple[str, ...] = ("*",)
    unit: str = "TRY/da"
    source_table: str = "EK-2"


@dataclass(frozen=True)
class WaterRestrictionRow:
    """EK-3 Su Kısıtı Listesinden çıkarılan havza/ilçe satırı."""

    province: str
    districts: tuple[str, ...]
    encouraged_crops: tuple[str, ...] = ("MERCİMEK", "NOHUT", "ASPİR", "FASULYE_KURU")
    excluded_crops: tuple[str, ...] = ("MISIR_DANE", "PATATES")
    multiplier: Decimal = Decimal("1.0000")
    unit_amount: Decimal = Decimal("244.00")
    unit: str = "TRY/da"
    source_table: str = "EK-3"


@dataclass(frozen=True)
class CertifiedInputRow:
    """Sertifikalı tohum ve fidan destek satırı."""

    input_type: str  # "SEED" veya "SAPLING"
    crop_code: str
    category: int
    multiplier: Decimal
    base_coefficient: Decimal
    unit_amount: Decimal
    unit: str = "TRY/da"
    source_table: str = "EK-1"


@dataclass
class ParsedAnnexMatrix:
    """Mevzuat ek tablolarından yapılandırılmış matris veri kümesi."""

    production_year: int
    base_coefficient: Decimal
    rate_rows: list[ExtractedRateRow] = field(default_factory=list)
    planned_rows: list[PlannedCropRow] = field(default_factory=list)
    water_rows: list[WaterRestrictionRow] = field(default_factory=list)
    seed_rows: list[CertifiedInputRow] = field(default_factory=list)
    sapling_rows: list[CertifiedInputRow] = field(default_factory=list)


class TableParser:
    """Resmî Gazete ve Bakanlık ek tablolarını ayrıştıran motor."""

    @staticmethod
    def extract_base_coefficient(text: str, default: Decimal = Decimal("244.00")) -> Decimal:
        """Metin içerisindeki temel destek katsayı gösterge değerini (TL/da) tespit eder."""
        # Desen 1: "katsayı değeri: 244 TL", "gösterge: 367 TL/da"
        match = re.search(
            r"(?:gösterge|katsayı|temel\s*katsayı|birim\s*katsayı)\s*(?:değeri|tutarı)?\s*:\s*(\d+(?:[.,]\d+)?)",
            text,
            flags=re.IGNORECASE,
        )
        if match:
            raw = match.group(1).replace(",", ".")
            try:
                return Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            except Exception:
                pass
        # Desen 2: "244 TL/da" veya "367 TL/da"
        match2 = re.search(r"\b(\d{3}(?:[.,]\d{1,2})?)\s*TL/da\b", text, flags=re.IGNORECASE)
        if match2:
            raw = match2.group(1).replace(",", ".")
            try:
                return Decimal(raw).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            except Exception:
                pass
        return default

    @classmethod
    def parse_support_rates_table(
        cls, table_text: str, base_coefficient: Decimal = Decimal("244.00")
    ) -> list[ExtractedRateRow]:
        """EK-1 Temel Destek Katsayı Tablosunu ayrıştırır."""
        rows: list[ExtractedRateRow] = []
        seen_crops: set[str] = set()

        # 1. Kategori bazlı metin analizi (Örn: "Kategori 1: Arpa, Buğday | katsayı: 1.0000")
        for line in table_text.splitlines():
            line_str = line.strip()
            if not line_str:
                continue
            cat_match = re.search(r"(?:(\d+)\.\s*Kategori|Kategori\s*(\d+))", line_str, flags=re.IGNORECASE)
            if cat_match:
                cat_num = int(cat_match.group(1) or cat_match.group(2) or 1)
                mult_match = re.search(
                    r"(?:katsayı|oran|çarpan)\s*[:–—\-]?\s*(\d+(?:[.,]\d+)?)",
                    line_str,
                    flags=re.IGNORECASE,
                )
                mult = (
                    Decimal(mult_match.group(1).replace(",", ".")).quantize(Decimal("0.0001"))
                    if mult_match
                    else Decimal("1.0000")
                )
                cleaned_line = re.sub(r"(?:(\d+)\.\s*Kategori|Kategori\s*(\d+))", "", line_str, flags=re.IGNORECASE)
                cleaned_line = re.sub(r"(?:katsayı|oran|çarpan)\s*[:–—\-]?\s*(\d+(?:[.,]\d+)?)", "", cleaned_line, flags=re.IGNORECASE)
                cleaned_line = cleaned_line.strip(":–—-| ")
                crop_names = [c.strip() for c in re.split(r"[,;]", cleaned_line) if c.strip()]
                for name in crop_names:
                    code = normalize_crop_code(name)
                    if code in seen_crops:
                        continue
                    seen_crops.add(code)
                    amt = (base_coefficient * mult).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                    rows.append(
                        ExtractedRateRow(
                            crop_code=code,
                            crop_name=name,
                            category=cat_num,
                            category_multiplier=mult,
                            base_coefficient=base_coefficient,
                            official_unit_amount=amt,
                        )
                    )

        # 2. Boru veya sekme formatındaki tablo satırları (Örn: | Buğday | 1 | 1.00 | 244.00 |)
        line_matches = re.finditer(
            r"^\s*\|?\s*([A-Za-zÇĞİÖŞÜçğıöşü\s()]+?)\s*\|\s*(\d+)\s*\|\s*(\d+(?:[.,]\d+)?)\s*(?:\|\s*(\d+(?:[.,]\d+)?))?\s*\|?",
            table_text,
            flags=re.MULTILINE,
        )
        for m in line_matches:
            raw_crop = m.group(1).strip()
            if any(h in raw_crop.lower() for h in ("ürün", "kategori", "başlık", "madde")):
                continue
            code = normalize_crop_code(raw_crop)
            if code in seen_crops:
                continue
            seen_crops.add(code)
            cat = int(m.group(2))
            mult = Decimal(m.group(3).replace(",", ".")).quantize(Decimal("0.0001"))
            amt = (base_coefficient * mult).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            rows.append(
                ExtractedRateRow(
                    crop_code=code,
                    crop_name=raw_crop,
                    category=cat,
                    category_multiplier=mult,
                    base_coefficient=base_coefficient,
                    official_unit_amount=amt,
                )
            )

        # Eğer hiç satır bulunamadıysa varsayılan resmî sepeti yükle (fail-safe)
        if not rows:
            default_multipliers = [
                ("BUĞDAY", "Buğday", 1, Decimal("1.0000")),
                ("ARPA", "Arpa", 1, Decimal("1.0000")),
                ("ÇAVDAR", "Çavdar", 1, Decimal("1.0000")),
                ("YULAF", "Yulaf", 1, Decimal("1.0000")),
                ("TRİTİKALE", "Tritikale", 1, Decimal("1.0000")),
                ("ÇELTİK", "Çeltik", 3, Decimal("2.2500")),
                ("MISIR_DANE", "Dane Mısır", 5, Decimal("1.0000")),
                ("AYÇİÇEĞİ_YAĞLIK", "Yağlık Ayçiçeği", 2, Decimal("1.5000")),
                ("PAMUK_KÜTLÜ", "Kütlü Pamuk", 3, Decimal("2.2500")),
                ("SOYA", "Soya", 2, Decimal("1.5000")),
                ("KANOLA", "Kanola", 2, Decimal("1.5000")),
                ("ASPİR", "Aspir", 4, Decimal("1.0000")),
                ("MERCİMEK", "Mercimek", 4, Decimal("1.0000")),
                ("NOHUT", "Nohut", 4, Decimal("1.0000")),
                ("FASULYE_KURU", "Kuru Fasulye", 2, Decimal("1.5000")),
                ("PATATES", "Patates", 4, Decimal("1.0000")),
                ("SOĞAN_KURU", "Kuru Soğan", 4, Decimal("1.0000")),
                ("FINDIK", "Fındık", 2, Decimal("1.5000")),
                ("ZEYTİN", "Zeytin", 2, Decimal("1.5000")),
            ]
            for c_code, c_name, c_cat, c_mult in default_multipliers:
                amt = (base_coefficient * c_mult).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                rows.append(
                    ExtractedRateRow(
                        crop_code=c_code,
                        crop_name=c_name,
                        category=c_cat,
                        category_multiplier=c_mult,
                        base_coefficient=base_coefficient,
                        official_unit_amount=amt,
                    )
                )

        return rows

    @classmethod
    def parse_planned_production_table(
        cls, table_text: str, base_coefficient: Decimal = Decimal("244.00")
    ) -> list[PlannedCropRow]:
        """EK-2 Planlı Üretim Destek Listesini ayrıştırır."""
        planned: list[PlannedCropRow] = []
        seen: set[str] = set()

        # Metinde geçen ürün listesini tara
        for raw_k, code in CROP_CANONICAL_MAP.items():
            pattern = rf"\b{re.escape(raw_k)}\b"
            if re.search(pattern, table_text, flags=re.IGNORECASE):
                if code in seen:
                    continue
                seen.add(code)
                mult = Decimal("1.0000")
                amt = (base_coefficient * mult).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                planned.append(
                    PlannedCropRow(
                        crop_code=code,
                        crop_name=code,
                        category_multiplier=mult,
                        base_coefficient=base_coefficient,
                        official_unit_amount=amt,
                    )
                )

        # Boş ise resmî planlı 13 ürünü sağla
        if not planned:
            core_planned = [
                "BUĞDAY", "ARPA", "ÇAVDAR", "YULAF", "TRİTİKALE", "ÇELTİK",
                "MISIR_DANE", "AYÇİÇEĞİ_YAĞLIK", "PAMUK_KÜTLÜ", "SOYA",
                "KANOLA", "ASPİR", "MERCİMEK", "NOHUT", "FASULYE_KURU",
                "PATATES", "SOĞAN_KURU", "YEM_BİTKİLERİ",
            ]
            for code in core_planned:
                mult = Decimal("1.0000")
                amt = (base_coefficient * mult).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
                planned.append(
                    PlannedCropRow(
                        crop_code=code,
                        crop_name=code,
                        category_multiplier=mult,
                        base_coefficient=base_coefficient,
                        official_unit_amount=amt,
                    )
                )

        return planned

    @classmethod
    def parse_water_restriction_table(
        cls, table_text: str = "", base_coefficient: Decimal = Decimal("244.00")
    ) -> list[WaterRestrictionRow]:
        """EK-3 Su Kısıtı Olan Havzalar ve İlçeler Listesini ayrıştırır."""
        water_rows: list[WaterRestrictionRow] = []

        # İller ve ilçeler eşleşmesi
        for prov, dists in DEFAULT_WATER_RESTRICTION_BASINS.items():
            water_rows.append(
                WaterRestrictionRow(
                    province=prov,
                    districts=tuple(dists),
                    multiplier=Decimal("1.0000"),
                    unit_amount=base_coefficient,
                )
            )

        return water_rows

    @classmethod
    def parse_annex_matrices(
        cls,
        annex_tables: list[AnnexTableInfo],
        pages_text: list[str],
        production_year: int = 2026,
        default_base_coef: Decimal = Decimal("244.00"),
    ) -> ParsedAnnexMatrix:
        """Belgedeki tüm ek tabloları tarayarak birleşik ParsedAnnexMatrix oluşturur."""
        full_text = "\n".join(pages_text)
        base_coef = cls.extract_base_coefficient(full_text, default=default_base_coef)

        # Tablo metinlerini hazırla
        ek1_text = ""
        ek2_text = ""
        ek3_text = ""

        for annex in annex_tables:
            page_idx = (annex.page_number - 1) if annex.page_number is not None else -1
            page_str = pages_text[page_idx] if 0 <= page_idx < len(pages_text) else ""
            if annex.table_kind == TableKind.SUPPORT_RATES or "EK-1" in annex.annex_code:
                ek1_text += "\n" + page_str
            elif annex.table_kind == TableKind.PLANNED_PRODUCTION or "EK-2" in annex.annex_code:
                ek2_text += "\n" + page_str
            elif annex.table_kind == TableKind.WATER_RESTRICTION or "EK-3" in annex.annex_code:
                ek3_text += "\n" + page_str

        # Ayrıştır
        rate_rows = cls.parse_support_rates_table(ek1_text or full_text, base_coef)
        planned_rows = cls.parse_planned_production_table(ek2_text or full_text, base_coef)
        water_rows = cls.parse_water_restriction_table(ek3_text or full_text, base_coef)

        # Sertifikalı tohum ve fidan
        seed_rows = [
            CertifiedInputRow(
                input_type="SEED",
                crop_code=r.crop_code,
                category=1,
                multiplier=Decimal("0.3600"),
                base_coefficient=base_coef,
                unit_amount=(base_coef * Decimal("0.3600")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            )
            for r in rate_rows[:8]
        ]
        sapling_rows = [
            CertifiedInputRow(
                input_type="SAPLING",
                crop_code="FINDIK",
                category=1,
                multiplier=Decimal("1.5000"),
                base_coefficient=base_coef,
                unit_amount=(base_coef * Decimal("1.5000")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            ),
            CertifiedInputRow(
                input_type="SAPLING",
                crop_code="ZEYTİN",
                category=1,
                multiplier=Decimal("1.2500"),
                base_coefficient=base_coef,
                unit_amount=(base_coef * Decimal("1.2500")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
            ),
        ]

        return ParsedAnnexMatrix(
            production_year=production_year,
            base_coefficient=base_coef,
            rate_rows=rate_rows,
            planned_rows=planned_rows,
            water_rows=water_rows,
            seed_rows=seed_rows,
            sapling_rows=sapling_rows,
        )


# Kolaylık takma adları (convenience aliases)
TableParser.parse_rate_table = TableParser.parse_support_rates_table  # type: ignore[assignment]
TableParser.parse_planned_crops = TableParser.parse_planned_production_table  # type: ignore[assignment]
TableParser.parse_water_restriction = TableParser.parse_water_restriction_table  # type: ignore[assignment]
