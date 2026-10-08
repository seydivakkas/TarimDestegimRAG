"""Tıklanabilir Resmî Belge ve Mevzuat Bağlantıları Birim Testleri.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from tarim_destek_rag.citations.document_links import (
    DOCUMENT_LOCATIONS,
    format_citation_section_header,
    format_clickable_action,
    format_clickable_check,
    format_clickable_citation,
    get_article_preview,
    resolve_check_link,
)


def test_resolve_check_link_user_scenarios():
    """Kullanıcının talep ettiği tüm şart maddelerinin doğru belge konumunu bulduğunu doğrular."""
    # 1. ÇKS kontrolü
    cks_res = resolve_check_link("ÇKS kaydı aktif.")
    assert cks_res["url"] == DOCUMENT_LOCATIONS["CKS_M1"]["url"]
    assert "page=1" in cks_res["url"]
    assert "Resmî Gazete" in cks_res["title"]

    # 2. Havza ve planlı üretim ret gerekçesi
    havza_res = resolve_check_link(
        "FINDIK ürünü, TRABZON/AKÇAABAT havzasında planlı üretim kapsamında yer almamaktadır."
    )
    assert havza_res["url"] == DOCUMENT_LOCATIONS["HAVZA_M2"]["url"]
    assert "BUGEM" in havza_res["url"]

    # 3. Planlı üretim destek tutarı bulunamadı
    fiyat_res = resolve_check_link("FINDIK için planlı üretim destek tutarı bulunamadı.")
    assert fiyat_res["url"] == DOCUMENT_LOCATIONS["FIYAT_M2"]["url"]
    assert "page=2" in fiyat_res["url"]

    # 4. Sertifikalı tohum belgesi/faturası mevcut
    tohum_res = resolve_check_link("Sertifikalı tohum belgesi/faturası mevcut.")
    assert tohum_res["url"] == DOCUMENT_LOCATIONS["TOHUM_M3"]["url"]
    assert "page=2" in tohum_res["url"]

    # 5. Tohum desteği bulunmuyor
    tohum_ret = resolve_check_link("FINDIK için sertifikalı tohum desteği bulunmuyor.")
    assert tohum_ret["url"] == DOCUMENT_LOCATIONS["TOHUM_M3"]["url"]

    # 6. Su Kısıtı
    su_res = resolve_check_link("KONYA/KARATAY bölgesi yeraltı su kısıtı bölgesindedir.")
    assert su_res["url"] == DOCUMENT_LOCATIONS["SU_KISITI_M4"]["url"]

    # 7. Sertifikalı Fidan
    fidan_res = resolve_check_link("Sertifikalı fidan sertifikası mevcut.")
    assert fidan_res["url"] == DOCUMENT_LOCATIONS["FIDAN_M6"]["url"]

    # 8. Kadın & Genç
    kadin_res = resolve_check_link("Genç çiftçi (< 41 yaş) ilave desteği.")
    assert kadin_res["url"] == DOCUMENT_LOCATIONS["KADIN_GENC_M5"]["url"]


def test_format_clickable_check():
    """format_clickable_check'in geçerli target='_blank' ve rozetli HTML ürettiğini test eder."""
    html_pass = format_clickable_check("ÇKS kaydı aktif.", status_icon="✅")
    assert 'href="https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=1"' in html_pass
    assert 'target="_blank"' in html_pass
    assert 'rel="noopener noreferrer"' in html_pass
    assert "✅" in html_pass
    assert "doc-pass" in html_pass
    assert "doc-badge-pass" in html_pass
    assert "Resmî Gazete Md. 1 ↗" in html_pass

    html_fail = format_clickable_check(
        "FINDIK ürünü, TRABZON/AKÇAABAT havzasında planlı üretim kapsamında yer almamaktadır.",
        status_icon="❌",
    )
    assert 'href="https://www.tarimorman.gov.tr/BUGEM/Menu/14/Tarim-Havzalari-Uretim-Ve-Destekleme-Modeli"' in html_fail
    assert "❌" in html_fail
    assert "doc-fail" in html_fail
    assert "doc-badge-fail" in html_fail


def test_format_clickable_action():
    """format_clickable_action'ın başvuru adımları için doğru bağlantı ürettiğini test eder."""
    action_html = format_clickable_action(
        "Mevzuat koşullarını ve desteklenen havza/ürün kriterlerini inceleyiniz."
    )
    assert "📌" in action_html
    assert 'target="_blank"' in action_html
    assert "doc-action" in action_html


def test_format_citation_section_header():
    """'Resmî Mevzuat Maddesi ve Alıntı' başlığının tıklanabilirliğini test eder."""
    header_html = format_citation_section_header()
    assert "Resmî Mevzuat Maddesi ve Alıntı (Kanıt Zinciri)" in header_html
    assert 'target="_blank"' in header_html
    assert "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf" in header_html


def test_format_clickable_citation():
    """Resmî mevzuat atfının başlık kartı ve alıntı metnini test eder."""
    citation = {
        "title": "2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        "section": "MADDE 2 - Tarım Havzaları Planlı Üretim Desteği",
        "year": 2026,
        "snippet": "Bakanlıkça ilan edilen Tarım Havzalarında öncelikli stratejik ürünleri üreten üreticilere...",
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=1",
    }
    hdr, snip = format_clickable_citation(citation)
    assert 'target="_blank"' in hdr
    assert 'href="https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=1"' in hdr
    assert "MADDE 2 - Tarım Havzaları Planlı Üretim Desteği" in hdr
    assert "Bakanlıkça ilan edilen Tarım Havzalarında" in snip


def test_get_article_preview():
    """Mevzuat önizleme metinlerinin tam ve doğru geldiğini test eder."""
    for key in ["MADDE 1", "MADDE 2", "MADDE 3", "MADDE 4", "MADDE 5", "MADDE 6", "EK TABLO"]:
        data = get_article_preview(key)
        assert data is not None
        assert "url" in data
        assert "text" in data
        assert "source" in data
        assert len(data["text"]) > 20


def test_highlight_legal_text_color_codes():
    """highlight_legal_text'in şartları, retleri, tutarları ve referansları doğru renk etiketleriyle işaretlediğini test eder."""
    from tarim_destek_rag.citations.document_links import highlight_legal_text

    # 1. Yeşil vurgu (Hak kazanma / sağlanan şart)
    text_pass = "2026 üretim yılında Çiftçi Kayıt Sistemi (ÇKS) kaydı aktif olan üreticilere temel girdi desteği (Temel Destek) ödenir."
    hl_pass = highlight_legal_text(text_pass)
    assert '<mark class="legal-hl-pass">' in hl_pass
    assert '<mark class="legal-hl-gold">2026 üretim yılında</mark>' in hl_pass

    # 2. Kırmızı vurgu (Ret gerekçesi / yasaklama)
    text_fail = "ÇKS kaydı bulunmayan veya kaydı pasif olan üreticiler hiçbir tarımsal destekleme ödemesinden yararlanamaz."
    hl_fail = highlight_legal_text(text_fail)
    assert '<mark class="legal-hl-fail">' in hl_fail

    # 3. Kehribar/Altın vurgu (Tutarlar ve tarihler)
    text_gold = "Buğday için 465 TL/da, su kısıtında ilave 250 TL verilir. Başvuru 1 Eylül 2026 - 31 Aralık 2026 arasındadır."
    hl_gold = highlight_legal_text(text_gold)
    assert '<mark class="legal-hl-gold">465 TL/da</mark>' in hl_gold
    assert '<mark class="legal-hl-gold">250 TL</mark>' in hl_gold
    assert '<mark class="legal-hl-gold">1 Eylül 2026 - 31 Aralık 2026</mark>' in hl_gold

    # 4. Mavi vurgu (Mevzuat madde referansı)
    text_ref = "MADDE 1 - (1) Resmî Gazete Sayı: 32647 uyarınca uygulanır."
    hl_ref = highlight_legal_text(text_ref)
    assert '<mark class="legal-hl-ref">' in hl_ref


def test_format_highlighted_citation_card():
    """format_highlighted_citation_card'ın geçerli kart HTML'i ve renkli alıntı ürettiğini test eder."""
    from tarim_destek_rag.citations.document_links import format_highlighted_citation_card

    citation = {
        "title": "2026 Bitkisel Üretim Destekleme Kararı",
        "section": "MADDE 1 - Temel Destek",
        "year": 2026,
        "snippet": "Çiftçi Kayıt Sistemi (ÇKS) kaydı aktif olan üreticilere temel girdi desteği (Temel Destek) ödenir.",
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=1",
    }
    card_html = format_highlighted_citation_card(citation, status="ELIGIBLE")
    assert '<div class="legal-quote-card pass">' in card_html
    assert 'class="legal-source-link"' in card_html
    assert 'href="https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=1"' in card_html
    assert '<mark class="legal-hl-pass">' in card_html


def test_render_document_viewer_html():
    """render_document_viewer_html'in güvenli yasal uyarı ve kaynak linki ürettiğini test eder."""
    from tarim_destek_rag.citations.document_links import render_document_viewer_html

    viewer_html = render_document_viewer_html("MADDE 1")
    assert 'class="legal-reader-container"' in viewer_html
    assert 'Mevzuat cümlesi doğrulanmadı' in viewer_html
    assert 'Kaynağın orijinal adresini incele' in viewer_html

