"""Mevzuat ve Kanıt Zinciri Tıklanabilir Belge Bağlantıları Modülü.

Kural motoru çıktılarındaki şart maddelerini (Sağlanan/Sağlanamayan) ve
atıf zincirlerini doğrudan Resmî Gazete, BÜGEM ve mevzuat portallarındaki
orijinal belge konumlarına bağlar.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

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

ARTICLE_PREVIEWS: dict[str, dict[str, str]] = {
    "MADDE 1": {
        "title": "2026 Resmî Gazete Kararı — MADDE 1: Temel Destek ve ÇKS Esasları",
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=1",
        "source": "Resmî Gazete Sayı: 32647",
        "text": (
            "MADDE 1 - (1) 2026 üretim yılında Çiftçi Kayıt Sistemi (ÇKS) kaydı aktif olan ve tarımsal "
            "üretim yapan çiftçilere, mazot ve gübre maliyetlerini karşılamak amacıyla temel girdi desteği "
            "(Temel Destek) ödenir.\n"
            "(2) Temel destekleme başvuruları ve ÇKS güncellemeleri 1 Eylül 2026 - 31 Aralık 2026 tarihleri "
            "arasında İl/İlçe Tarım ve Orman Müdürlüklerine veya e-Devlet kapısı üzerinden yapılır.\n"
            "(3) ÇKS kaydı bulunmayan veya kaydı pasif olan üreticiler hiçbir tarımsal destekleme ödemesinden yararlanamaz."
        ),
    },
    "MADDE 2": {
        "title": "2026 Resmî Gazete Kararı & BÜGEM — MADDE 2: Tarım Havzaları Planlı Üretim Desteği",
        "url": "https://www.tarimorman.gov.tr/BUGEM/Menu/14/Tarim-Havzalari-Uretim-Ve-Destekleme-Modeli",
        "source": "BÜGEM Tarım Havzaları Tebliği & RG Sayı: 32647",
        "text": (
            "MADDE 2 - (1) Bakanlıkça ilan edilen Türkiye Tarım Havzaları Üretim ve Destekleme Modeli "
            "kapsamında, belirlenen havzalarda öncelikli stratejik ürünleri (Buğday, Arpa, Mısır, Ayçiçeği, "
            "Pamuk, Soya, Mercimek, Nohut vb.) üreten üreticilere temel desteğe ilave olarak Planlı Üretim Desteği ödenir.\n"
            "(2) İlgili il/ilçe havzasında planlı üretim kapsamında yer almayan ürünlerin ekilmesi durumunda, üreticiye "
            "planlı üretim desteği ödenmez ve birim destek katsayısı uygulanmaz.\n"
            "(3) Münavebe şartı: Üst üste üç yıl aynı parselde aynı tek yıllık ürünün ekilmesi durumunda üçüncü yıl destekleme yapılmaz."
        ),
    },
    "MADDE 3": {
        "title": "2026 Resmî Gazete Kararı — MADDE 3: Sertifikalı Tohum Kullanım Desteği",
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=2",
        "source": "Resmî Gazete Sayı: 32647",
        "text": (
            "MADDE 3 - (1) Yetkili tohumluk bayilerinden faturalı sertifikalı tohum satın alarak ekim yapan "
            "ÇKS kayıtlı üreticilere Sertifikalı Tohum Kullanım Desteği verilir.\n"
            "(2) Tohum faturasının ve sertifika etiket kopyasının ÇKS başvuru dosyasına eklenmesi zorunludur.\n"
            "(3) Sertifikasız tohum kullanan veya faturası bulunmayan parsellere tohum desteği ödenmez."
        ),
    },
    "MADDE 4": {
        "title": "2026 Resmî Gazete Kararı & BÜGEM — MADDE 4: Yeraltı Su Kısıtı Olan Havzalar Desteği",
        "url": "https://www.tarimorman.gov.tr/BUGEM/Menu/17/Yeralti-Sularinin-Yetersiz-Oldugu-Havzalar",
        "source": "DSİ & BÜGEM Yeraltı Su Kısıtı Havzalar Kararı",
        "text": (
            "MADDE 4 - (1) Yeraltı su seviyesinin yetersiz olduğu ilan edilen havzalarda, su tüketimi az olan "
            "münavebe ürünlerini (Mercimek, Nohut vb.) eken çiftçilere dekar başına 250 TL ilave Su Kısıtı Desteği verilir.\n"
            "(2) Bu havzalarda sulu şartlarda yüksek su tüketen ürünlerin (dane mısır vb.) ekilmesi durumunda planlı destekler ödenmez."
        ),
    },
    "MADDE 5": {
        "title": "2026 Resmî Gazete Kararı — MADDE 5: Kadın ve Genç Çiftçi İlave Desteği",
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=2",
        "source": "Resmî Gazete Sayı: 32647",
        "text": (
            "MADDE 5 - (1) Başvuru tarihi itibarıyla 41 yaşından gün almamış genç çiftçilere temel destek tutarının "
            "%50'si oranında ilave genç çiftçi desteği ödenir.\n"
            "(2) ÇKS kaydı bulunan kadın çiftçilere temel destek tutarının %50'si oranında ilave destek ödenir.\n"
            "(3) Hem genç hem kadın olan üreticiler her iki avantajdan birleşerek yararlanır."
        ),
    },
    "MADDE 6": {
        "title": "2026 Resmî Gazete Kararı & BÜGEM — MADDE 6: Sertifikalı Fidan ve Kapama Bahçe Şartı",
        "url": "https://www.tarimorman.gov.tr/BUGEM/Menu/16/Sertifikali-Fidan-Kullanim-Destegi",
        "source": "BÜGEM Sertifikalı Fidan Kullanım Rehberi",
        "text": (
            "MADDE 6 - (1) Yetkili fidan üreticilerinden temin edilen sertifikalı/standart fidanlar ile en az 5 dekar "
            "alanda kapama meyve bahçesi tesis eden üreticilere fidan kullanım desteği verilir.\n"
            "(2) Münferit ağaç dikimlerine veya dağınık dikimlere fidan desteği ödenmez."
        ),
    },
    "EK TABLO": {
        "title": "2026 Destekleme Kararı Ek Tablo — Ürün Bazlı Birim Fiyat Kataloğu",
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=2",
        "source": "Resmî Gazete Sayı: 32647 Ek Tablo",
        "text": (
            "2026 ÜRETİM YILI BİRİM DESTEKLEME TUTARLARI (TL/da):\n"
            "• BUĞDAY / ARPA: Temel Destek 310 TL/da, Planlı Üretim 465 TL/da\n"
            "• MISIR: Temel Destek 310 TL/da, Planlı Üretim 465 TL/da\n"
            "• AYÇİÇEĞİ: Temel Destek 310 TL/da, Planlı Üretim 465 TL/da\n"
            "• PAMUK (KÜTLÜ): Temel Destek 310 TL/da, Planlı Üretim 540 TL/da\n"
            "• FINDIK: Temel Destek 310 TL/da (Geleneksel üretim havzaları)\n"
            "• MERCİMEK / NOHUT: Temel Destek 310 TL/da, Planlı Üretim 465 TL/da, Su Kısıtı İlave 250 TL/da"
        ),
    },
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
    """Kontrol maddesini tıklanabilir HTML bağlantısına dönüştürür.

    Kullanıcı tıkladığında doğrudan ilgili belgenin ilgili maddesini yeni sekmede açar.
    """
    loc = resolve_check_link(check_text, support_id)
    url = loc["url"]
    badge = loc["badge"]
    title = f"{loc['title']} — {loc['section']}"

    is_fail = status_icon in ["❌", "⚠️"]
    extra_class = "doc-fail" if is_fail else "doc-pass"
    badge_class = "doc-badge-fail" if is_fail else "doc-badge-pass"

    return (
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="doc-link-item {extra_class}" '
        f'title="{title} — Resmî Belgeyi Aç">\n'
        f'  <span class="doc-icon">{status_icon}</span>\n'
        f'  <span class="doc-text">{check_text}</span>\n'
        f'  <span class="doc-badge-tag {badge_class}">{badge} ↗</span>\n'
        f'</a>'
    )


def format_clickable_action(action_text: str, support_id: str | None = None) -> str:
    """Yapılması gereken başvuru adımını tıklanabilir rehber bağlantısına dönüştürür."""
    loc = resolve_check_link(action_text, support_id)
    url = loc["url"]
    badge = loc["badge"]
    title = f"{loc['title']} — {loc['section']}"

    return (
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="doc-link-item doc-action" '
        f'title="{title} — Başvuru ve Mevzuat Rehberini Aç">\n'
        f'  <span class="doc-icon">📌</span>\n'
        f'  <span class="doc-text">{action_text}</span>\n'
        f'  <span class="doc-badge-tag doc-badge-action">{badge} ↗</span>\n'
        f'</a>'
    )


def format_citation_section_header(url: str | None = None) -> str:
    """'Resmî Mevzuat Maddesi ve Alıntı (Kanıt Zinciri)' başlığını tıklanabilir yapar."""
    target_url = url or DOCUMENT_LOCATIONS["DEFAULT_RG"]["url"]
    return (
        f'<a href="{target_url}" target="_blank" rel="noopener noreferrer" class="doc-citation-header-link" '
        f'title="2026 Bitkisel Üretim Destekleme Resmî Mevzuatı — Belgeyi Aç">\n'
        f'  <b>Resmî Mevzuat Maddesi ve Alıntı (Kanıt Zinciri)</b> <span class="doc-badge-tag">Resmî Belge ↗</span>\n'
        f'</a>'
    )


def format_clickable_citation(
    citation: dict[str, Any],
    default_support_id: str | None = None,
) -> tuple[str, str]:
    """Resmî mevzuat atfını tıklanabilir başlık kartı ve alıntı metnine dönüştürür."""
    title = citation.get("title", "2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)")
    sec = citation.get("section", "Madde")
    year = citation.get("year", 2026)
    snip = citation.get("snippet", "")
    url = citation.get("url")

    if not url:
        sec_low = sec.lower()
        if "madde 1" in sec_low or "temel" in sec_low:
            url = DOCUMENT_LOCATIONS["CKS_M1"]["url"]
        elif "madde 2" in sec_low or "havza" in sec_low:
            url = DOCUMENT_LOCATIONS["HAVZA_M2"]["url"]
        elif "madde 3" in sec_low or "tohum" in sec_low:
            url = DOCUMENT_LOCATIONS["TOHUM_M3"]["url"]
        elif "madde 4" in sec_low or "su kısıt" in sec_low:
            url = DOCUMENT_LOCATIONS["SU_KISITI_M4"]["url"]
        elif "madde 5" in sec_low or "kadın" in sec_low or "genç" in sec_low:
            url = DOCUMENT_LOCATIONS["KADIN_GENC_M5"]["url"]
        elif "madde 6" in sec_low or "fidan" in sec_low:
            url = DOCUMENT_LOCATIONS["FIDAN_M6"]["url"]
        else:
            loc = resolve_check_link(sec, default_support_id)
            url = loc["url"]

    header_html = (
        f'<a href="{url}" target="_blank" rel="noopener noreferrer" class="doc-citation-link" '
        f'title="{title} — Resmî Belgeyi Aç">'
        f'🏛️ <b>{title} ({year}) — {sec}</b> <span class="doc-badge-tag">Resmî Belgeyi Aç ↗</span>'
        f'</a>'
    )
    return header_html, snip


def get_article_preview(article_key: str) -> dict[str, str]:
    """Belirtilen madde veya ek tablonun tam metnini ve bağlantısını döner."""
    for key, data in ARTICLE_PREVIEWS.items():
        if key.lower() in article_key.lower():
            return data
    return ARTICLE_PREVIEWS["MADDE 1"]
