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
