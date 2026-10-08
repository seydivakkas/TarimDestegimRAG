import re
from decimal import Decimal
from enum import StrEnum


class EligibilityStatusEnum(StrEnum):
    """Uygunluk değerlendirme durumları."""

    ELIGIBLE = "ELIGIBLE"  # Uygun görünüyor
    REVIEW = "REVIEW"  # Ek kontrol gerekiyor / Eksik bilgi
    NOT_ELIGIBLE = "NOT_ELIGIBLE"  # Uygun görünmüyor


class SupportUnitEnum(StrEnum):
    """Destek birimi türü."""

    TRY_PER_DA = "TRY/da"  # TL / Dekar
    TRY_PER_KG = "TRY/kg"  # TL / Kilogram
    TRY_PER_PIECE = "TRY/adet"  # TL / Adet


TURKISH_MONTHS: dict[str, str] = {
    "ocak": "01",
    "şubat": "02",
    "subat": "02",
    "mart": "03",
    "nisan": "04",
    "mayıs": "05",
    "mayis": "05",
    "haziran": "06",
    "temmuz": "07",
    "ağustos": "08",
    "agustos": "08",
    "eylül": "09",
    "eylul": "09",
    "ekim": "10",
    "kasım": "11",
    "kasim": "11",
    "aralık": "12",
    "aralik": "12",
}


def normalize_turkish_date(date_str: str) -> str:
    """'31 Temmuz 2026' veya '31.07.2026' biçimindeki tarihleri 'YYYY-MM-DD'ye çevirir."""
    text = date_str.strip().lower()

    # ISO Format: YYYY-MM-DD
    if re.match(r"^\d{4}-\d{2}-\d{2}$", text):
        return text

    # GG.AA.YYYY veya GG/AA/YYYY
    match_numeric = re.match(r"^(\d{1,2})[./](\d{1,2})[./](\d{4})$", text)
    if match_numeric:
        day, month, year = match_numeric.groups()
        return f"{year}-{int(month):02d}-{int(day):02d}"

    # GG Ay YYYY (Örn: 31 Temmuz 2026)
    match_text = re.match(r"^(\d{1,2})\s+([a-zçğıöşü]+)\s+(\d{4})$", text)
    if match_text:
        day, month_name, year = match_text.groups()
        if month_name in TURKISH_MONTHS:
            month_num = TURKISH_MONTHS[month_name]
            return f"{year}-{month_num}-{int(day):02d}"

    raise ValueError(f"Tanınmayan Türkçe tarih biçimi: {date_str}")


def normalize_turkish_currency(amount_str: str) -> Decimal:
    """'1.250,50 TL' veya '465' biçimindeki metinleri hassas Decimal'a çevirir."""
    # Harfleri ve boşlukları temizle
    cleaned = re.sub(r"[^\d,.]", "", amount_str.strip())
    if not cleaned:
        raise ValueError(f"Geçersiz sayı/para formatı: {amount_str}")

    # Türk formatı: 1.250,50 -> 1250.50
    if "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(".", "").replace(",", ".")
    elif "," in cleaned:
        cleaned = cleaned.replace(",", ".")

    try:
        val = Decimal(cleaned)
        if val < 0:
            raise ValueError("Destek tutarı negatif olamaz")
        return val
    except Exception as e:
        raise ValueError(f"Decimal dönüştürme hatası: {amount_str} - {e}") from e


# Ürün takma ad haritası
CROP_ALIAS_MAP: dict[str, str] = {
    "bugday": "BUĞDAY",
    "buğday": "BUĞDAY",
    "arpa": "ARPA",
    "misir": "MISIR",
    "mısır": "MISIR",  # Generic: DO NOT infer a legally specific crop.
    "mısır (dane)": "MISIR_DANE",
    "dane mısır": "MISIR_DANE",
    "misir (dane)": "MISIR_DANE",
    "ayçiçeği (yağlık)": "AYÇİÇEĞİ_YAĞLIK",
    "yağlık ayçiçeği": "AYÇİÇEĞİ_YAĞLIK",
    "fasulye (kuru)": "FASULYE_KURU",
    "kuru fasulye": "FASULYE_KURU",
    "kolza (kanola)": "KANOLA",
    "pamuk (kütlü)": "PAMUK_KÜTLÜ",
    "kütlü pamuk": "PAMUK_KÜTLÜ",
    "soğan (kuru)": "SOĞAN_KURU",
    "kuru soğan": "SOĞAN_KURU",
    "aycicegi": "AYÇİÇEĞİ",
    "ayçiçeği": "AYÇİÇEĞİ",
    "pamuk": "PAMUK",
    "findik": "FINDIK",
    "fındık": "FINDIK",
    "nohut": "NOHUT",
    "mercimek": "MERCİMEK",
    "kanola": "KANOLA",
    "soya": "SOYA",
    "zeytin": "ZEYTİN",
    "yem bitkileri": "YEM BİTKİLERİ",
}


def normalize_crop_name(crop_str: str) -> str:
    """Ürün ismini standart kanonik ada eşler."""
    key = crop_str.strip().lower()
    if key in CROP_ALIAS_MAP:
        return CROP_ALIAS_MAP[key]
    # Eşleşme yoksa büyük harfe çevir
    return crop_str.strip().upper()
