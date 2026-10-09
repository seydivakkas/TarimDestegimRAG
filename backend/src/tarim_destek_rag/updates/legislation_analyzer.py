"""Resmî Mevzuat Yapısal Çözümleme ve Analiz Motoru (P0-10).

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

import hashlib
import io
import re
from datetime import UTC, datetime

from bs4 import BeautifulSoup
from tarim_destek_rag.updates.legislation_models import (
    AmendmentTarget,
    AnnexTableInfo,
    DiscoveredLegislation,
    EffectiveDateInfo,
    LegislationIdentity,
    LegislationType,
    TableKind,
)

TR_MONTHS = {
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


def _turkish_lower(text: str) -> str:
    """Türkçe karakterleri (İ, I, vb.) doğru biçimde küçük harfe dönüştürür."""
    if not text:
        return ""
    return (
        text.replace("İ", "i")
        .replace("I", "ı")
        .replace("Ğ", "ğ")
        .replace("Ü", "ü")
        .replace("Ş", "ş")
        .replace("Ö", "ö")
        .lower()
    )


def _normalize_turkish_date(day_str: str, month_str: str, year_str: str) -> str:
    """Gün, Türkçe ay adı ve yıldan ISO formatında (YYYY-MM-DD) tarih oluşturur."""
    day = int(day_str)
    year = int(year_str)
    m_clean = _turkish_lower(month_str.strip())
    month = TR_MONTHS.get(m_clean, "01")
    return f"{year:04d}-{month}-{day:02d}"


def _normalize_slash_date(slash_date: str) -> str:
    """D/M/YYYY veya DD/MM/YYYY formatındaki tarihi ISO formatına (YYYY-MM-DD) çevirir."""
    parts = slash_date.strip().split("/")
    if len(parts) == 3:
        day = int(parts[0])
        month = int(parts[1])
        year = int(parts[2])
        return f"{year:04d}-{month:02d}-{day:02d}"
    return slash_date


class LegislationAnalyzer:
    """Resmî Gazete ve Bakanlık belgelerini sınıflandıran ve ayrıştıran motor."""

    @classmethod
    def extract_pages(cls, raw_bytes: bytes, mime_type: str = "application/pdf") -> list[str]:
        """PDF veya HTML içeriğini sayfa/bölüm bazlı metin listesine dönüştürür."""
        if mime_type == "application/pdf" or raw_bytes.startswith(b"%PDF-"):
            # Önce PyMuPDF dene, yoksa veya hata verirse pypdf'e dön
            try:
                import pymupdf

                doc = pymupdf.open(stream=raw_bytes, filetype="pdf")
                pages = [page.get_text() for page in doc]
                doc.close()
                if pages:
                    return pages
            except Exception:
                pass

            try:
                from pypdf import PdfReader

                reader = PdfReader(io.BytesIO(raw_bytes))
                return [page.extract_text() or "" for page in reader.pages]
            except Exception:
                return [""]

        # HTML
        try:
            soup = BeautifulSoup(raw_bytes, "html.parser")
            # Ana içerik veya gövde
            body = soup.find("body") or soup
            return [body.get_text(separator="\n", strip=True)]
        except Exception:
            return [""]


    @classmethod
    def classify_type(cls, text: str) -> LegislationType:
        """Classify the issuing document from its heading, not cited legislation.

        Mentions such as a Presidential Decision inside a Communique's body
        are cross-references, never the issuing document's own type.
        """
        folded = _turkish_lower(text)
        start_body = re.search(r"\bmadde\s+1\s*[-–—]", folded)
        heading = folded[:start_body.start()] if start_body else folded[:4000]
        heading = re.sub(r"\s+", " ", heading).strip()

        if re.search(
            r"değişiklik\s+yapılmasına\s+dair\s+tebliğ"
            r"|degisiklik\s+yapilmasina\s+dair\s+teblig",
            heading,
        ):
            return LegislationType.DEGISIKLIK_TEBLIGI
        if (
            re.search(r"\btebliğ\s+no\s*:", heading)
            or re.search(r"\bdair\s+tebliğ\b", heading)
            or re.search(r"\btebliğ\b", heading)
        ):
            return LegislationType.BAKANLIK_TEBLIGI
        if "cumhurbaşkanı kararı" in heading or re.search(
            r"\bkarar\s+sayısı\s*:\s*\d+", heading
        ):
            return LegislationType.CUMHURBASKANI_KARARI
        if "yönetmeli" in heading or "yonetmeli" in heading:
            return LegislationType.YONETMELIK
        if "genelge" in heading or "talimat" in heading:
            return LegislationType.GENELGE
        if re.match(r"^ek\s*[-–—]?\s*\d+", heading):
            return LegislationType.EK_TABLO
        return LegislationType.BILINMEYEN


    @classmethod
    def extract_identity(cls, full_text: str) -> LegislationIdentity:
        """Extract the *issuing* document identity from the header region."""
        leg_type = cls.classify_type(full_text)
        lower_text = _turkish_lower(full_text)
        first_article = re.search(r"\bmadde\s+1\s*[-–—]", lower_text)
        header = (
            lower_text[:first_article.start()]
            if first_article else lower_text[:4000]
        )
        flat_header = re.sub(r"\s+", " ", header)

        number = None
        heading_teblig_numbers = re.findall(
            r"tebliğ\s*no\s*:\s*(\d{4}/\d+|\d+)", flat_header
        )
        if leg_type == LegislationType.DEGISIKLIK_TEBLIGI:
            # Real 2025/42 header names the AMENDED 2024/39 first, then
            # introduces its own final "(Tebliğ No: 2025/42)".
            if heading_teblig_numbers:
                number = heading_teblig_numbers[-1]
        elif leg_type == LegislationType.BAKANLIK_TEBLIGI:
            if heading_teblig_numbers:
                number = heading_teblig_numbers[0]
        elif leg_type == LegislationType.CUMHURBASKANI_KARARI:
            karar_m = re.search(r"karar\s*sayısı\s*:\s*(\d+)", flat_header)
            if karar_m:
                number = karar_m.group(1)
            else:
                sayili_m = re.search(
                    r"(\d{4}/\d+|\d{4})\s*sayılı", flat_header
                )
                if sayili_m:
                    number = sayili_m.group(1)

        rg_date = None
        rg_number = None
        # Synthetic and legacy primary header format:
        # "24 Ağustos 2024 TARİHLİ VE 32642 SAYILI RESMÎ GAZETE".
        primary_rg = re.search(
            r"(\d{1,2})\s+([a-zçğıöşü]+)\s+(\d{4})\s+tarihli"
            r"\s+ve\s+(\d+)\s+sayılı\s+resm[iî]\s+gazete",
            flat_header,
        )
        primary_slash = re.search(
            r"(\d{1,2}/\d{1,2}/\d{4})\s+tarihli\s+ve\s+"
            r"(\d+)\s+sayılı\s+resm[iî]\s+gazete",
            flat_header,
        )
        if primary_rg:
            rg_date = _normalize_turkish_date(
                primary_rg.group(1), primary_rg.group(2), primary_rg.group(3)
            )
            rg_number = primary_rg.group(4)
        elif primary_slash:
            rg_date = _normalize_slash_date(primary_slash.group(1))
            rg_number = primary_slash.group(2)
        else:
            # Real Gazette HTML has: "30 Aralık 2025 SALI  Resmî Gazete  Sayı : 33123".
            actual_heading = re.search(
                r"(\d{1,2})\s+([a-zçğıöşü]+)\s+(\d{4})"
                r"(?:\s+(?:pazartesi|salı|çarşamba|perşembe|cuma|cumartesi|pazar))?"
                r"\s+resm[iî]\s+gazete",
                flat_header,
            )
            if actual_heading:
                rg_date = _normalize_turkish_date(
                    actual_heading.group(1),
                    actual_heading.group(2),
                    actual_heading.group(3),
                )
            issue = re.search(r"sayı\s*:\s*(\d{5})", flat_header)
            if issue:
                rg_number = issue.group(1)

        lines = [line.strip() for line in full_text.splitlines() if line.strip()]
        title = "Resmî Mevzuat Belgesi"
        for line in lines[:20]:
            line_fold = _turkish_lower(line)
            if any(
                term in line_fold
                for term in ("karar", "tebliğ", "yönetmelik", "destekleme", "bitkisel")
            ):
                if len(line) > 10 and not line_fold.startswith("sayı"):
                    title = line
                    break
        authority = (
            "T.C. CUMHURBAŞKANLIĞI"
            if leg_type == LegislationType.CUMHURBASKANI_KARARI
            else "T.C. TARIM VE ORMAN BAKANLIĞI"
        )
        return LegislationIdentity(
            legislation_type=leg_type,
            title=title,
            number=number,
            rg_date=rg_date,
            rg_number=rg_number,
            authority=authority,
        )


    @classmethod
    def extract_effective_dates(
        cls, full_text: str, default_rg_date: str | None = None
    ) -> EffectiveDateInfo:
        """Only a real effective-date clause can establish legal effectiveness.

        Gazette publication time is not an effective-date fallback. When a
        clause names an exception (e.g. 10th Article May 1 vs other articles
        January 1), preserve that difference rather than invent one date
        for every provision.
        """
        lower_text = _turkish_lower(full_text)
        flat_text = re.sub(r"\s+", " ", lower_text)
        effective_date = None
        is_pub_date = False
        effective_clause = None
        exceptions: dict[str, str] = {}

        articles = re.finditer(
            r"\bmadde\s+(\d+)\s*[-–—]\s*(.*?)"
            r"(?=\bmadde\s+\d+\s*[-–—]|$)",
            flat_text,
            flags=re.DOTALL,
        )
        for article in articles:
            clause = article.group(2)
            if "yürürlüğe girer" not in clause:
                continue
            effective_clause = f"MADDE {article.group(1)} - {clause}"
            effective_date = None
            exceptions = {}
            is_pub_date = False

            if "yayımı tarihinde" in clause or "yayimi tarihinde" in clause:
                is_pub_date = True
                effective_date = default_rg_date
                continue

            explicit_dates = re.findall(
                r"(\d{1,2}/\d{1,2}/\d{4})\s+tarihinde", clause
            )
            for special in re.finditer(
                r"\b(\d+)\s+(?:inci|ıncı|uncu|üncü|nci|ncı)"
                r"\s+maddesi\s+(\d{1,2}/\d{1,2}/\d{4})\s+tarihinde",
                clause,
            ):
                exceptions[f"MADDE {int(special.group(1))}"] = (
                    _normalize_slash_date(special.group(2))
                )
            general = re.search(
                r"diğer\s+maddeleri\s+"
                r"(\d{1,2}/\d{1,2}/\d{4})\s+tarihinde",
                clause,
            )
            if general:
                effective_date = _normalize_slash_date(general.group(1))
            elif len(explicit_dates) == 1:
                effective_date = _normalize_slash_date(explicit_dates[0])
            # Multiple non-qualified dates are ambiguous; never guess.

        production_years: list[int] = []
        range_match = re.search(
            r"(\d{4})\s*[-–—]\s*(\d{4})\s+üretim\s+yılları",
            lower_text,
        )
        if range_match:
            start_y, end_y = int(range_match.group(1)), int(range_match.group(2))
            if 2020 <= start_y <= end_y <= 2100:
                production_years = list(range(start_y, end_y + 1))
        else:
            single_year_matches = set(
                re.findall(
                    r"\b(202[4-9]|203\d)\s+(?:üretim\s+yılı|yılı)",
                    lower_text,
                )
            )
            if single_year_matches:
                production_years = sorted(int(y) for y in single_year_matches)

        return EffectiveDateInfo(
            effective_date=effective_date,
            effective_clause_text=effective_clause,
            valid_production_years=production_years,
            is_publication_date=is_pub_date,
            retroactive=False,
            article_effective_dates=exceptions,
        )

    @classmethod
    def extract_amendment_target(cls, full_text: str) -> AmendmentTarget | None:
        """Değişiklik tebliğlerinin hangi tebliği ve hangi maddeleri değiştirdiğini tespit eder."""
        leg_type = cls.classify_type(full_text)
        if leg_type != LegislationType.DEGISIKLIK_TEBLIGI:
            return None

        lower_text = _turkish_lower(full_text)

        # Hedeflenen ana tebliğ referansı:
        # Örn: 24/8/2024 tarihli ve 32642 sayılı Resmî Gazete'de yayımlanan Bitkisel Üretime Destekleme Ödemesi Yapılmasına Dair Tebliğ (Tebliğ No: 2024/39)

        ref_match = re.search(
            r"(\d{1,2}/\d{1,2}/\d{4})\s+tarihli\s+ve\s+"
            r"(\d{4,6})"
            r"(?:\s+(?:(?:birinci|ikinci|üçüncü|dördüncü|beşinci|"
            r"altıncı|yedinci|sekizinci|dokuzuncu|onuncu|\d+\.)\s+)?mükerrer)?"
            r"\s+sayılı\s+resm[iî]\s+gazete\s*['’]de"
            r"\s+yayımlanan\s+(.{8,500}?)\s*"
            r"\(\s*tebliğ\s*no\s*:\s*(\d{4}/\d+|\d+)\s*\)",
            lower_text,
            flags=re.DOTALL,
        )

        base_rg_date = None
        base_rg_number = None
        base_title = None
        base_no = None

        if ref_match:
            base_rg_date = _normalize_slash_date(ref_match.group(1))
            base_rg_number = ref_match.group(2)
            start, end = ref_match.span(3)
            base_title = full_text[start:end].strip()
            base_no = ref_match.group(4).strip()
        else:
            # Alternatif eşleşme: "... sayılı Tebliğ"
            alt_match = re.search(
                r"(\d{4}/\d+|\d+)\s*sayılı\s*tebliğ", lower_text
            )
            if alt_match:
                base_no = alt_match.group(1).strip()

        # Değiştirilen maddeler
        modified_articles: list[str] = []
        for m in re.finditer(
            r"(?:aynı\s+tebliğin|tebliğ[^\n]*?['’]in)\s+(\d+)\s*(?:nci|ncı|uncu|üncü)?\s*maddesi",
            lower_text,
        ):
            art_name = f"MADDE {m.group(1)}"
            if art_name not in modified_articles:
                modified_articles.append(art_name)

        for m_alt in re.finditer(
            r"\b(\d+)\s*(?:nci|ncı|uncu|üncü)?\s*maddesi[^\n.]*?(?:değiştirilmiştir|yürürlükten kaldırılmıştır)",
            lower_text,
        ):
            art_name = f"MADDE {m_alt.group(1)}"
            if art_name not in modified_articles:
                modified_articles.append(art_name)

        # Ek tablo değişiklikleri
        for ek_m in re.finditer(
            r"(?:aynı\s+tebliğin|tebliğ[^\n]*?)\s+(ek\s*[-–—]?\s*\d+)",
            lower_text,
        ):
            ek_name = re.sub(r"\s+", "", ek_m.group(1).upper()).replace("—", "-").replace("–", "-")
            if ek_name not in modified_articles:
                modified_articles.append(ek_name)

        return AmendmentTarget(
            base_legislation_title=base_title,
            base_legislation_no=base_no,
            base_rg_date=base_rg_date,
            base_rg_number=base_rg_number,
            modified_articles=modified_articles,
            amendment_summary=f"{base_no or 'Temel mevzuat'} üzerinde {len(modified_articles)} madde değişikliği",
        )

    @classmethod
    def extract_annex_tables(cls, pages_text: list[str]) -> list[AnnexTableInfo]:
        """Sayfa metinleri taranarak ek tabloları ve türlerini tespit eder."""
        annexes: list[AnnexTableInfo] = []
        seen_codes: set[str] = set()

        for idx, page_content in enumerate(pages_text, start=1):
            # EK-1, EK-2, EK-3 desenleri
            matches = re.finditer(
                r"\b(EK\s*[-–—]?\s*([0-9A-ZÇĞİÖŞÜ]+))\s*[\n\r–—\-:]*\s*([^\n\r]+)",
                page_content,
                flags=re.IGNORECASE,
            )
            for m in matches:
                full_code = re.sub(r"\s+", "", m.group(1).upper()).replace("—", "-").replace("–", "-")
                if "-" not in full_code:
                    full_code = f"EK-{m.group(2).upper()}"

                title_raw = m.group(3).strip()
                if len(title_raw) < 4:
                    continue

                if full_code in seen_codes:
                    continue
                seen_codes.add(full_code)

                # Tablo türü sınıflandırması (Türkçe küçük harf ile)
                title_fold = _turkish_lower(title_raw)
                kind = TableKind.GENERAL
                if "katsayı" in title_fold or "temel destek" in title_fold or "tutar" in title_fold:
                    kind = TableKind.SUPPORT_RATES
                elif "su kısıtı" in title_fold or "su kisiti" in title_fold:
                    kind = TableKind.WATER_RESTRICTION
                elif (
                    "planlı" in title_fold
                    or "planli" in title_fold
                    or "ürün listesi" in title_fold
                    or "urun listesi" in title_fold
                ):
                    kind = TableKind.PLANNED_PRODUCTION
                elif "tohum" in title_fold or "fidan" in title_fold:
                    kind = TableKind.SEED_SAPLING

                annexes.append(
                    AnnexTableInfo(
                        annex_code=full_code,
                        title=title_raw,
                        table_kind=kind,
                        page_number=idx,
                        # An EK-n reference or a page's text is NOT the
                        # independently acquired annex. Never forge its digest.
                        content_sha256=None,
                    )
                )

        return annexes

    @classmethod
    def analyze_document(
        cls,
        raw_bytes: bytes,
        source_url: str,
        mime_type: str = "application/pdf",
    ) -> DiscoveredLegislation:
        """Belgeyi uçtan uca analiz eder ve yapılandırılmış DiscoveredLegislation nesnesi döndürür."""
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        pages = cls.extract_pages(raw_bytes, mime_type)
        full_text = "\n".join(pages)

        # 1. Kimlik ve tür tespiti
        identity = cls.extract_identity(full_text)

        # 2. Yürürlük ve geçerlilik tarihleri
        dates = cls.extract_effective_dates(full_text, default_rg_date=identity.rg_date)

        # 3. Değişiklik hedefi
        amendment = cls.extract_amendment_target(full_text)

        # 4. Ek tablolar
        tables = cls.extract_annex_tables(pages)

        # 5. Tespit edilen maddeler listesi
        articles = [
            f"MADDE {m.group(1)}"
            for m in re.finditer(r"\bMADDE\s+(\d+)\b", full_text, flags=re.IGNORECASE)
        ]
        # Tekilleştir ve sırala
        unique_articles = sorted(
            list(set(articles)),
            key=lambda x: int(x.replace("MADDE ", "")) if x.replace("MADDE ", "").isdigit() else 999,
        )

        return DiscoveredLegislation(
            document_sha256=sha256,
            source_url=source_url,
            identity=identity,
            effective_dates=dates,
            amendment_target=amendment,
            annex_tables=tables,
            articles_found=unique_articles,
            discovered_at_utc=datetime.now(UTC).isoformat(),
            review_status="DRAFT_DISCOVERED",
        )
