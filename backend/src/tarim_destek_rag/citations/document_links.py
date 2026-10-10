"""Mevzuat ve Kanıt Zinciri Tıklanabilir Belge Bağlantıları Modülü.

Kural motoru çıktılarındaki şart maddelerini (Sağlanan/Sağlanamayan) ve
atıf zincirlerini doğrudan Resmî Gazete, BÜGEM ve mevzuat portallarındaki
orijinal belge konumlarına bağlar.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

import re
from typing import Any

DOCUMENT_LOCATIONS: dict[str, dict[str, str]] = {
    "CKS_M1": {
        "title": "2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        "section": "MADDE 1 - Temel Destek ve ÇKS Zorunluluğu",
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=1",
        "badge": "Resmî Gazete Md. 1",
    },
    "HAVZA_M2": {
        "title": "Türkiye Tarım Havzaları Üretim ve Destekleme Modeli Listesi (BÜGEM)",
        "section": "MADDE 2 - Tarım Havzaları Planlı Üretim Desteği",
        "url": "https://www.tarimorman.gov.tr/BUGEM/Menu/14/Tarim-Havzalari-Uretim-Ve-Destekleme-Modeli",
        "badge": "Tarım Havzaları Listesi",
    },
    "FIYAT_M2": {
        "title": "2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        "section": "MADDE 2 & Ekli Birim Destek Tablosu",
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=2",
        "badge": "Resmî Gazete Destek Tablosu",
    },
    "TOHUM_M3": {
        "title": "2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        "section": "MADDE 3 - Sertifikalı Tohum Kullanım Desteği",
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=2",
        "badge": "Resmî Gazete Md. 3",
    },
    "SU_KISITI_M4": {
        "title": "Yeraltı Sularının Yetersiz Olduğu Havzalar Kararı ve Su Kısıtı Listesi",
        "section": "MADDE 4 - Yeraltı Su Kısıtı Olan Havzalar Desteği",
        "url": "https://www.tarimorman.gov.tr/BUGEM/Menu/17/Yeralti-Sularinin-Yetersiz-Oldugu-Havzalar",
        "badge": "Su Kısıtı Havza Listesi",
    },
    "KADIN_GENC_M5": {
        "title": "2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        "section": "MADDE 5 - Kadın ve Genç Çiftçi İlave Desteği",
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=2",
        "badge": "Resmî Gazete Md. 5",
    },
    "FIDAN_M6": {
        "title": "2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        "section": "MADDE 6 - Sertifikalı Fidan ve Kapama Bahçe Şartı",
        "url": "https://www.tarimorman.gov.tr/BUGEM/Menu/16/Sertifikali-Fidan-Kullanim-Destegi",
        "badge": "Resmî Gazete Md. 6",
    },
    "DEFAULT_RG": {
        "title": "2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        "section": "Resmî Gazete Sayı: 32647",
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf",
        "badge": "Resmî Gazete Kararı",
    },
}

# Legacy topic selector retained for UI compatibility. Never store fabricated
# legal paragraphs or rates: an unverified topic is NOT a quotation.
ARTICLE_PREVIEWS: dict[str, dict[str, str]] = {
    key: {
        "title": "Konu kaydı — özgün madde doğrulanmadı",
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf",
        "source": "8859 sayılı özgün belge (ilgili maddeyle eşleşme doğrulanmadı)",
        "text": "Bu konu için özgün kaynakta birebir madde, fıkra ve metin eşleşmesi henüz doğrulanmadı.",
    }
    for key in ("MADDE 1", "MADDE 2", "MADDE 3", "MADDE 4", "MADDE 5", "MADDE 6", "EK TABLO")
}

def resolve_check_link(check_text: str, support_id: str | None = None) -> dict[str, str]:
    """Herhangi bir kontrol şartı için en uygun belge URL'si ve atıf bilgisini çözer."""
    low = check_text.lower()

    # 1. ÇKS
    if "çks" in low:
        return DOCUMENT_LOCATIONS["CKS_M1"]

    # 2. Havza & Planlı Üretim Havza Uygunluğu
    if "havza" in low or "planlı üretim kapsamında" in low or "öncelikli ürünlerdendir" in low:
        return DOCUMENT_LOCATIONS["HAVZA_M2"]

    # 3. Birim Tutar / Fiyat Tablosu
    if "destek tutarı" in low or "birim desteği" in low or "birim fiyatı" in low or "temel destek tanımı" in low:
        return DOCUMENT_LOCATIONS["FIYAT_M2"]

    # 4. Tohum
    if "tohum" in low:
        return DOCUMENT_LOCATIONS["TOHUM_M3"]

    # 5. Fidan & Meyve Bahçesi
    if "fidan" in low or "bahçe" in low or "kapama" in low:
        return DOCUMENT_LOCATIONS["FIDAN_M6"]

    # 6. Su Kısıtı
    if "su kısıtı" in low or "yeraltı su" in low:
        return DOCUMENT_LOCATIONS["SU_KISITI_M4"]

    # 7. Kadın & Genç
    if "kadın" in low or "genç" in low:
        return DOCUMENT_LOCATIONS["KADIN_GENC_M5"]

    # 8. Üretim yılı ve alan kontrolleri
    if "üretim yılı" in low or "parsel alanı" in low:
        return DOCUMENT_LOCATIONS["CKS_M1"]

    # 9. support_id fallback
    if support_id == "BASIC_SUPPORT_2026":
        return DOCUMENT_LOCATIONS["CKS_M1"]
    if support_id == "PLANNED_PRODUCTION_2026":
        return DOCUMENT_LOCATIONS["HAVZA_M2"]
    if support_id == "CERTIFIED_SEED_2026":
        return DOCUMENT_LOCATIONS["TOHUM_M3"]
    if support_id == "CERTIFIED_SAPLING_2026":
        return DOCUMENT_LOCATIONS["FIDAN_M6"]
    if support_id == "WATER_RESTRICTION_2026":
        return DOCUMENT_LOCATIONS["SU_KISITI_M4"]

    return DOCUMENT_LOCATIONS["DEFAULT_RG"]


def format_clickable_check(
    check_text: str,
    status_icon: str = "✅",
    support_id: str | None = None,
) -> str:
    """Show rule outcome, but NEVER invent a legal clause/page from keywords.

    An exact original-PDF evidence link appears in the separately verified
    citation card only after source SHA, quote, article and page validation.
    """
    from html import escape

    is_fail = status_icon in ("❌", "⚠️")
    extra = "doc-fail" if is_fail else "doc-pass"
    safe_icon = escape(status_icon)
    safe_check = escape(check_text)
    return (
        f'<div class="doc-link-item {extra}">'
        f'<span class="doc-icon">{safe_icon}</span>'
        f'<span class="doc-text">{safe_check}</span>'
        '<span class="doc-badge-tag">Madde/pasaj henüz doğrulanmadı</span>'
        '</div>'
    )


def format_clickable_action(action_text: str, support_id: str | None = None) -> str:
    """A next step is guidance, never a guessed legal source link."""
    from html import escape

    safe_action = escape(action_text)
    return (
        '<div class="doc-link-item doc-action">'
        '<span class="doc-icon">📌</span>'
        f'<span class="doc-text">{safe_action}</span>'
        '<span class="doc-badge-tag">Başvuru önerisi — madde doğrulanmadı</span>'
        '</div>'
    )


def format_citation_section_header(url: str | None = None) -> str:
    """Use a non-clickable heading; only validated citations get proof links."""
    return (
        '<span class="doc-citation-header-link">'
        '<b>Mevzuat kaynakları ve kanıt doğrulama durumu</b> '
        '<span class="doc-badge-tag">Doğrulanan pasajlar ayrı işaretlidir</span>'
        '</span>'
    )


def format_clickable_citation(
    citation: dict[str, Any],
    default_support_id: str | None = None,
) -> tuple[str, str]:
    """Legacy entry point delegates to the same fail-closed evidence renderer."""
    from html import escape

    return (
        format_highlighted_citation_card(citation, status="REVIEW", support_id=default_support_id),
        escape(str(citation.get("snippet") or "")),
    )


def get_article_preview(article_key: str) -> dict[str, str]:
    """Return only an unverified topic record, never a guessed article text."""
    for key, data in ARTICLE_PREVIEWS.items():
        if key.lower() in article_key.lower():
            return data
    return ARTICLE_PREVIEWS["MADDE 1"]


def highlight_legal_text(text: str, status: str | None = None) -> str:
    """Mevzuat ve alıntı metinlerindeki ilgili şartları, tutarları ve ret gerekçelerini renkli işaretler.

    Renk Kodları:
    - 🟢 Yeşil (.legal-hl-pass): Sağlanan şartlar, hak kazanma hükümleri, zorunluluklar
    - 🔴 Kırmızı (.legal-hl-fail): Ret gerekçeleri, yasal yasaklar, kısıtlamalar
    - 🟡 Kehribar (.legal-hl-gold): Dekar başı tutarlar, katsayılar, alan ve yaş kriterleri, başvuru tarihleri
    - 🔵 Mavi (.legal-hl-ref): Resmî Gazete sayıları, madde numaraları, kanun ve kurum atıfları
    """
    if not text:
        return ""

    escaped = (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )

    # 1. Kırmızı Vurgu: Ret, yasak ve kısıtlama cümleleri
    fail_phrases = [
        "ÇKS kaydı bulunmayan veya kaydı pasif olan üreticiler hiçbir tarımsal destekleme ödemesinden yararlanamaz",
        "planlı üretim desteği ödenmez ve birim destek katsayısı uygulanmaz",
        "Sertifikasız tohum kullanan veya faturası bulunmayan parsellere tohum desteği ödenmez",
        "üçüncü yıl destekleme yapılmaz",
        "yüksek su tüketen ürünlerin (dane mısır vb.) ekilmesi durumunda planlı destekler ödenmez",
        "Münferit ağaç dikimlerine veya dağınık dikimlere fidan desteği ödenmez",
        "hiçbir tarımsal destekleme ödemesinden yararlanamaz",
        "destekten yararlanamaz",
        "destek ödenmez",
        "destekleme yapılmaz",
        "destek verilmez",
        "haczedilemez",
    ]
    for ph in fail_phrases:
        if ph in escaped:
            escaped = escaped.replace(
                ph, f'<mark class="legal-hl-fail">{ph}</mark>'
            )

    # 2. Yeşil Vurgu: Hak kazanma, sağlanan şartlar ve pozitif yükümlülükler
    pass_phrases = [
        "Çiftçi Kayıt Sistemi (ÇKS) kaydı aktif olan ve tarımsal üretim yapan çiftçilere",
        "Çiftçi Kayıt Sistemi (ÇKS) kaydı aktif olan üreticilere",
        "Çiftçi Kayıt Sistemi (ÇKS) kaydı aktif olan",
        "temel girdi desteği (Temel Destek) ödenir",
        "Planlı Üretim Desteği ödenir",
        "Yetkili tohumluk bayilerinden faturalı sertifikalı tohum satın alarak ekim yapan ÇKS kayıtlı üreticilere Sertifikalı Tohum Kullanım Desteği verilir",
        "Sertifikalı Tohum Kullanım Desteği verilir",
        "Tohum faturasının ve sertifika etiket kopyasının ÇKS başvuru dosyasına eklenmesi zorunludur",
        "ilave Su Kısıtı Desteği verilir",
        "ilave genç çiftçi desteği ödenir",
        "temel destek tutarının %50'si oranında ilave destek ödenir",
        "kapama meyve bahçesi tesis eden üreticilere fidan kullanım desteği verilir",
        "fidan kullanım desteği verilir",
        "Temel Destek ödenir",
        "öncelikli stratejik ürünleri üreten üreticilere",
        "her iki avantajdan birleşerek yararlanır",
        "su tüketimi az olan münavebe ürünlerini",
    ]
    for ph in pass_phrases:
        if ph in escaped and f'<mark class="legal-hl-pass">{ph}</mark>' not in escaped and f'<mark class="legal-hl-fail">{ph}</mark>' not in escaped:
            escaped = escaped.replace(
                ph, f'<mark class="legal-hl-pass">{ph}</mark>'
            )

    # 3. Kehribar/Altın Vurgu: Tutarlar, katsayılar, alanlar, yaş ve süreler
    gold_patterns = [
        r"(\b\d+\s*TL(?:/da)?\b)",
        r"(%\s*50(?:'si)?(?:\s*oranında)?)",
        r"(1\s+Eylül\s+2026\s*-\s*31\s+Aralık\s+2026)",
        r"(\ben\s+az\s+5\s+dekar\b)",
        r"(\b41\s+yaşından\s+gün\s+almamış\b)",
        r"(\b2026\s+üretim\s+yılı(?:nda)?\b)",
    ]
    for pat in gold_patterns:
        escaped = re.sub(
            pat,
            r'<mark class="legal-hl-gold">\1</mark>',
            escaped,
        )

    # 4. Mavi Vurgu: Resmi Karar Başlıkları ve Kanun Referansları
    ref_patterns = [
        r"(MADDE\s+\d+\s*-\s*\(\d+\))",
        r"(MADDE\s+\d+)",
        r"(Resmî\s+Gazete\s+Sayı:\s*\d+)",
        r"(5488\s+sayılı\s+Tarım\s+Kanunu)",
        r"(Türkiye\s+Tarım\s+Havzaları\s+Üretim\s+ve\s+Destekleme\s+Modeli)",
    ]
    for pat in ref_patterns:
        escaped = re.sub(
            pat,
            r'<mark class="legal-hl-ref">\1</mark>',
            escaped,
        )

    return escaped


def _verified_highlight_path(
    citation: dict[str, Any], support_id: str | None,
) -> str | None:
    """Only allow exact backend proof routes with matching digest and arguments.

    Route checks never replace backend SHA/source/position verification; they
    prevent a status label or partial SHA substring becoming a fake UI citation.
    """
    from urllib.parse import parse_qs, urlsplit

    sha = citation.get("document_sha256")
    link = citation.get("highlighted_pdf_url")
    if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
        return None
    if not isinstance(link, str) or not link.startswith("/evidence/highlight/"):
        return None
    parts = urlsplit(link)
    if parts.scheme or parts.netloc or parts.path.startswith("//"):
        return None
    params = parse_qs(parts.query, keep_blank_values=True)
    if any(len(values) != 1 for values in params.values()):
        return None

    verification = citation.get("verification_status")
    if verification == "ORIGINAL_HTML_TEXT_LOCATED_PENDING_LEGAL_REVIEW":
        if (parts.path != f"/evidence/highlight/html/{sha}"
            or set(params) != {"support_id"}
            or parts.fragment != "tarim-evidence-highlight"):
            return None
        actual_support = params["support_id"][0]
        if not actual_support or (support_id is not None and actual_support != support_id):
            return None
    elif verification == "VISUAL_SOURCE_LOCATED_PENDING_SECOND_REVIEW":
        page = citation.get("page_number")
        if (type(page) is not int or page < 1
            or parts.path != f"/evidence/highlight/visual/{sha}"
            or set(params) != {"support_id"}
            or parts.fragment != f"page={page}"):
            return None
        actual_support = params["support_id"][0]
        if not actual_support or (support_id is not None and actual_support != support_id):
            return None
    elif verification == "EXACT_PDF_MATCH_PENDING_LEGAL_REVIEW":
        page = citation.get("page_number")
        if (type(page) is not int or page < 1
            or parts.path != f"/evidence/highlight/{sha}"
            or set(params) != {"page", "quote"}
            or parts.fragment
            or params["page"][0] != str(page)
            or params["quote"][0] != str(citation.get("snippet") or "")
            or not params["quote"][0]):
            return None
    else:
        return None
    return link


def format_highlighted_citation_card(
    citation: dict[str, Any],
    status: str = "ELIGIBLE",
    support_id: str | None = None,
) -> str:
    """Render confirmed proof routes; label every other text as non-quotation."""
    from html import escape
    from os import getenv
    from urllib.parse import urlsplit

    title = escape(str(citation.get("title") or "Mevzuat kaynağı"))
    section = escape(str(citation.get("section") or "Madde"))
    year = escape(str(citation.get("year") or ""))
    status_code = str(citation.get("verification_status") or "")
    visual = status_code == "VISUAL_SOURCE_LOCATED_PENDING_SECOND_REVIEW"
    html = status_code == "ORIGINAL_HTML_TEXT_LOCATED_PENDING_LEGAL_REVIEW"
    proof_path = _verified_highlight_path(citation, support_id)
    located = proof_path is not None
    original_url = str(citation.get("url") or "")
    # Without confirmed page/phrase grounding, a generic source URL must not
    # imply the guessed article position is correct.
    if not located:
        original_url = original_url.split("#", 1)[0]
    source_link = ""
    if (original_url.startswith("https://") and
            (urlsplit(original_url).hostname or "") in (
                "www.resmigazete.gov.tr", "resmigazete.gov.tr", "www.tarimorman.gov.tr",
            )):
        clean_url = escape(original_url, quote=True)
        source_link = (
            f'<a href="{clean_url}" target="_blank" rel="noopener noreferrer" '
            'class="legal-source-link">'
            + ('Özgün kaynağı aç ↗' if located else 'Genel belgeyi aç (madde doğrulanmadı) ↗')
            + '</a>'
        )
    label = "Ön değerlendirme açıklaması — resmî alıntı değildir"
    text = escape(str(citation.get("snippet") or ""))
    if located:
        public_api = getenv("API_PUBLIC_BASE_URL", "http://127.0.0.1:8000").rstrip("/")
        proof_link = escape(public_api + proof_path, quote=True)
        if html:
            label = "Özgün Resmî Gazete HTML metninde birebir bulunan fıkra — hukukî onay bekliyor"
        elif visual:
            label = (
                "Özgün PDF görüntüsünde konumu işaretlenen pasaj — "
                "metin ve hukukî inceleme bekliyor"
            )
        else:
            label = "Özgün PDF'de birebir bulunan pasaj — hukukî onay bekliyor"
            text = highlight_legal_text(str(citation.get("snippet") or ""), status)
        mark_label = (
            "HTML’de işaretli fıkrayı aç ↗" if html
            else "PDF’de işaretli cümleyi aç ↗"
        )
        source_link = (
            f'<a href="{proof_link}" target="_blank" rel="noopener noreferrer" '
            f'class="legal-source-link">{mark_label}</a> '
            + source_link
        )
    card_class = "pass" if status == "ELIGIBLE" else ("warn" if status == "REVIEW" else "fail")
    body = (
        f'📜 <i>“{text}”</i>' if located and not visual
        else f'📝 {text}'
    )
    return (
        f'<div class="legal-quote-card {card_class}">\n'
        f'  <div class="legal-quote-header">\n'
        f'    <span class="legal-doc-badge">🏛️ {title} ({year}) — {section}</span>\n'
        f'    {source_link}\n'
        f'  </div>\n'
        f'  <div class="legal-quote-body">\n'
        f'    <strong>{label}</strong><div>{body}</div>\n'
        f'  </div>\n'
        f'</div>'
    )

def render_document_viewer_html(article_key: str) -> str:
    """Yalnız resmî belge bağlantısını gösterir; sentetik özetleri alıntı gibi sunmaz."""
    from html import escape

    data = get_article_preview(article_key)
    # Legacy ARTICLE_PREVIEWS has hand-written topic summaries, not original
    # Gazette clause titles. Never show their guessed article titles as fact.
    title = escape("Konu kaydı — madde/pasaj henüz eşleştirilmedi")
    source = escape("İlgili resmî kaynak (doğrulanmış madde bağlantısı değildir)")
    url = escape(str(data.get("url", "")), quote=True)
    return (
        '<div class="legal-reader-container">'
        '<div class="legal-reader-header">'
        f'<h4 class="legal-reader-title">{title}</h4>'
        f'<span class="legal-source-sub">Kaynak kaydı: {source}</span>'
        '</div>'
        '<p class="legal-reader-paragraph">'
        '<strong>Mevzuat cümlesi doğrulanmadı.</strong> '
        'Önceki örnek önizlemeler resmî PDF metniyle birebir eşleştirilmediğinden, '
        'doğrulanmış yasal madde alıntısı olarak sunulmaz. '
        'Genel kaynak belgesini bağımsız olarak inceleyiniz.'
        '</p>'
        f'<a class="legal-source-link" href="{url}" '
        'target="_blank" rel="noopener noreferrer">Genel belgeyi aç (madde doğrulanmadı) ↗</a>'
        '</div>'
    )
