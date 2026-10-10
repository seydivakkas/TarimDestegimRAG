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
    """A rule status is NOT a verified official article or paragraph citation."""
    html_pass = format_clickable_check("ÇKS kaydı aktif.", status_icon="✅")
    assert "ÇKS kaydı aktif" in html_pass
    assert "doc-pass" in html_pass
    assert "Madde/pasaj henüz doğrulanmadı" in html_pass
    assert "href=" not in html_pass
    assert "Resmî Gazete Md." not in html_pass

    html_fail = format_clickable_check(
        "FINDIK ürünü, TRABZON/AKÇAABAT havzasında planlı üretim kapsamında yer almamaktadır.",
        status_icon="❌",
    )
    assert "doc-fail" in html_fail
    assert "Madde/pasaj henüz doğrulanmadı" in html_fail
    assert "href=" not in html_fail


def test_format_clickable_action():
    """Unverified follow-up guidance must not create a guessed article link."""
    action_html = format_clickable_action(
        "Mevzuat koşullarını ve desteklenen havza/ürün kriterlerini inceleyiniz."
    )
    assert "📌" in action_html
    assert 'class="doc-link-item doc-action"' in action_html
    assert "madde doğrulanmadı" in action_html
    assert "href=" not in action_html
    assert "&lt;script&gt;" in format_clickable_action("<script>")


def test_format_citation_section_header():
    """A section label alone is not proof of a paragraph in any source."""
    header_html = format_citation_section_header()
    assert "Mevzuat kaynakları ve kanıt doğrulama durumu" in header_html
    assert "href=" not in header_html


def test_format_clickable_citation():
    """Legacy citation rendering must reject guessed page-and-article anchors."""
    citation = {
        "title": "2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        "section": "MADDE 2 - Tarım Havzaları Planlı Üretim Desteği",
        "year": 2026,
        "snippet": "Konuya ilişkin açıklama; birebir resmî alıntı değildir.",
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=1",
    }
    hdr, snip = format_clickable_citation(citation)
    assert "resmî alıntı değildir" in hdr
    assert "PDF’de işaretli cümleyi aç" not in hdr
    assert "#page=1" not in hdr
    assert "href=" in hdr  # general source only, not a guessed location
    assert "birebir resmî alıntı değildir" in snip


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
    assert 'href="https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf"' in card_html
    assert "#page=1" not in card_html
    assert "resmî alıntı değildir" in card_html
    assert "PDF’de işaretli cümleyi aç" not in card_html
    assert '<mark class="legal-hl-pass">' not in card_html


def test_render_document_viewer_html():
    """Sentetik mevzuat özetleri birebir resmî belge pasajı gibi sunulmamalıdır."""
    from tarim_destek_rag.citations.document_links import render_document_viewer_html

    viewer_html = render_document_viewer_html("MADDE 1")
    assert '<div class="legal-reader-container">' in viewer_html
    assert 'Genel belgeyi aç (madde doğrulanmadı)' in viewer_html
    assert 'doğrulanmış' in viewer_html
    assert 'href="https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf"' in viewer_html
    assert '<mark class=' not in viewer_html

def test_only_exact_sha_and_route_arguments_enable_yellow_source_links():
    """Fail closed for forged status, wrong quote/page, or SHA substring links."""
    from tarim_destek_rag.citations.document_links import format_highlighted_citation_card

    sha = "a" * 64
    quote = "Özgün PDF'de tam karşılığı bulunan örnek cümle."
    valid = {
        "title": "Özgün belgeden test alıntısı",
        "section": "MADDE 2",
        "snippet": quote,
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf",
        "verification_status": "EXACT_PDF_MATCH_PENDING_LEGAL_REVIEW",
        "document_sha256": sha,
        "page_number": 2,
        "highlighted_pdf_url": f"/evidence/highlight/{sha}?page=2&quote=%C3%96zg%C3%BCn%20PDF%27de%20tam%20kar%C5%9F%C4%B1l%C4%B1%C4%9F%C4%B1%20bulunan%20%C3%B6rnek%20c%C3%BCmle.",
    }
    assert "PDF’de işaretli cümleyi aç" in format_highlighted_citation_card(valid)
    for key, replacement in (
        ("highlighted_pdf_url", f"/evidence/highlight/visual/{sha}?page=2&quote=wrong"),
        ("highlighted_pdf_url", f"/evidence/highlight/{sha}?page=3&quote=wrong"),
        ("document_sha256", "b" * 64),
        ("page_number", 1),
        ("verification_status", "UNVERIFIED_EXPLANATION"),
    ):
        forged = dict(valid, **{key: replacement})
        shown = format_highlighted_citation_card(forged)
        assert "PDF’de işaretli cümleyi aç" not in shown
        assert "resmî alıntı değildir" in shown
        assert "📜 <i>" not in shown
        assert "#page=" not in shown


def test_visual_source_is_a_located_image_not_an_exact_quote():
    from tarim_destek_rag.citations.document_links import format_highlighted_citation_card

    sha = "b" * 64
    base = {
        "snippet": "İnsan denetimi bekleyen görsel pasajın transkripsiyonu",
        "verification_status": "VISUAL_SOURCE_LOCATED_PENDING_SECOND_REVIEW",
        "document_sha256": sha,
        "page_number": 2,
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf",
        "highlighted_pdf_url": (
            f"/evidence/highlight/visual/{sha}?support_id=BASIC_SUPPORT_2026#page=2"
        ),
    }
    card = format_highlighted_citation_card(base, support_id="BASIC_SUPPORT_2026")
    assert "PDF’de işaretli cümleyi aç" in card
    assert "📜 <i>" not in card
    assert "metin ve hukukî inceleme bekliyor" in card
    assert "PDF’de işaretli cümleyi aç" not in format_highlighted_citation_card(
        base, support_id="CERTIFIED_SEED_2026"
    )


def test_html_evidence_must_have_exact_anchor_and_support_identifier():
    from tarim_destek_rag.citations.document_links import format_highlighted_citation_card

    sha = "c" * 64
    data = {
        "snippet": "Özgün Tebliğ metninde birebir geçen örnek",
        "verification_status": "ORIGINAL_HTML_TEXT_LOCATED_PENDING_LEGAL_REVIEW",
        "document_sha256": sha,
        "url": "https://resmigazete.gov.tr/eskiler/2024/12/20241231M5-8.htm",
        "highlighted_pdf_url": (
            f"/evidence/highlight/html/{sha}?support_id=BASIC_SUPPORT_2026"
            "#tarim-evidence-highlight"
        ),
    }
    assert "HTML’de işaretli fıkrayı aç" in format_highlighted_citation_card(
        data, support_id="BASIC_SUPPORT_2026"
    )
    wrong = dict(data, highlighted_pdf_url=data["highlighted_pdf_url"].replace(
        "#tarim-evidence-highlight", "#wrong-anchor"
    ))
    assert "HTML’de işaretli fıkrayı aç" not in format_highlighted_citation_card(wrong)
