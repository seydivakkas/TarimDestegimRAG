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

ARTICLE_PREVIEWS: dict[str, dict[str, str]] = {}  # synthetic quotes removed

def resolve_check_link(check_text: str, support_id: str | None = None) -> dict[str, str]:
    """A rule/check keyword is NEVER proof of a Gazette article or page."""
    return {
        "title": "Kural açıklaması (resmî alıntı değil)",
        "section": "Madde ve pasaj bağımsız doğrulanmadı",
        "url": "",
        "badge": "HOLD",
    }


def format_clickable_check(
    check_text: str, status_icon: str = "✅",
    support_id: str | None = None,
) -> str:
    """Display rule/farmer condition without inventing a source hyperlink."""
    from html import escape

    css = "doc-fail" if status_icon in ("❌", "⚠️") else "doc-pass"
    return (
        f'<div class="doc-link-item {css}">'
        f'{escape(status_icon)} {escape(check_text)} '
        '<span class="doc-badge-tag">Kaynak pasajı: HOLD</span></div>'
    )


def format_clickable_action(action_text: str, support_id: str | None = None) -> str:
    """Actions are advisory; no guessed official source URLs."""
    from html import escape

    return (
        '<div class="doc-link-item doc-action">'
        + escape(action_text)
        + '<span class="doc-badge-tag">Kaynak pasajı: HOLD</span></div>'
    )


def format_citation_section_header(url: str | None = None) -> str:
    """Never assert a 'verified original quote' based on a generic document URL."""
    return '<strong>Kaynak pasajları — tekil doğrulama bekliyor (HOLD)</strong>'


def format_clickable_citation(
    citation: dict[str, Any],
    default_support_id: str | None = None,
) -> tuple[str, str]:
    """No law quotes from an unverified retrieval snippet or guessed page."""
    from html import escape

    title = escape(str(citation.get("title") or "Kaynak"))
    section = escape(str(citation.get("section") or "Madde bilinmiyor"))
    snippet = escape(str(citation.get("snippet") or ""))
    heading = (
        f'<span class="doc-citation-header-link">{title} — {section} '
        '(Birebir pasaj konumu: HOLD)</span>'
    )
    return heading, snippet


def get_article_preview(article_key: str) -> dict[str, str]:
    """Legacy arbitrary article previews are quarantined, not official quotes."""
    return {
        "title": "Özgün mevzuat sayfası arşiv incelemesi",
        "source": "SHA-256 doğrulanmış belge gerekir",
        "url": "",
        "text": "",
        "status": "HOLD",
    }


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


def format_highlighted_citation_card(
    citation: dict[str, Any],
    status: str = "ELIGIBLE",
    support_id: str | None = None,
) -> str:
    """Only dedicated byte/span verifier may issue yellow original highlights."""
    from html import escape

    title = escape(str(citation.get("title") or "Kaynak notu"))
    section = escape(str(citation.get("section") or "Madde belirtilmemiş"))
    return (
        '<div class="legal-quote-card warn">'
        f'<strong>{title} — {section}</strong>'
        '<p>HOLD — Birebir resmî alıntı, sayfa, görsel vurgu ve yıl geçerliliği '
        'bu atıf için doğrulanmadı.</p>'
        '</div>'
    )


def render_document_viewer_html(article_key: str) -> str:
    """Never import RAG / guess a page for arbitrary article names."""
    if not isinstance(article_key, str) or not re.fullmatch(
        r"[A-Z][A-Z0-9_]+:[1-9][0-9]*", article_key,
    ):
        return (
            '<p>HOLD — Özgün PDF, birebir pasaj ve gerçek sayfa '
            'bağımsız olarak doğrulanmadı.</p>'
        )
    try:
        from tarim_destek_rag.citations.pdf_page_indexer import render_evidence_by_key

        return render_evidence_by_key(article_key)
    except (ImportError, OSError, ValueError):
        return '<p>HOLD — Gerçek kaynak arşivi kullanılamıyor.</p>'
