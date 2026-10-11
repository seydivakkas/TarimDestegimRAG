"""Resmî Gazete Sayfa Bazlı OCR, Tablo, Grafik ve Kanıt İndeksleme Birim Testleri.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from tarim_destek_rag.citations.pdf_page_indexer import (
    OfficialGazettePageRecord,
    OfficialPdfIndexer,
    PageGraphicsData,
    PageTableData,
    get_global_pdf_indexer,
    get_page_dropdown_choices,
    normalize_tr,
    render_evidence_by_key,
    render_page_evidence_card,
)


@pytest.fixture(scope="module")
def indexed_engine():
    """Test için indekslenmiş Resmî Gazete motorunu döner."""
    indexer = get_global_pdf_indexer()
    if not indexer.get_all_pages():
        indexer.seed_default_gazette_documents()
    return indexer


def test_normalize_tr():
    """Türkçe fonetik ve karakter normalizasyonunu test eder."""
    assert normalize_tr("Buğday") == "bugday"
    assert normalize_tr("ÇKS") == "cks"
    assert normalize_tr("Mısır") == "misir"
    assert normalize_tr("Su Kısıtı") == "su kisiti"
    assert normalize_tr("ÖNCELİKLİ ÜRÜN") == "oncelikli urun"


def test_indexer_initialization_and_seeding(indexed_engine: OfficialPdfIndexer):
    """İndeksleyicinin başlatıldığını ve belgelerin sayfa sayfa indekslendiğini doğrular."""
    pages = indexed_engine.get_all_pages()
    assert len(pages) >= 4, f"En az 4 sayfa indekslenmiş olmalı, bulunan: {len(pages)}"

    doc_ids = {p.doc_id for p in pages}
    assert "RG_DECISION_8859" in doc_ids
    assert "RG_DECISION_11781" in doc_ids
    assert "RG_COMMUNIQUE_2024_39" in doc_ids


def test_exact_page_retrieval(indexed_engine: OfficialPdfIndexer):
    """Belirli belge ve sayfa numarasına göre doğrudan erişimi test eder."""
    p1 = indexed_engine.get_page("RG_DECISION_8859", 1)
    assert p1 is not None
    assert p1.page_number == 1
    assert p1.total_pages == 2
    assert p1.gazette_issue == "32647"
    assert "MADDE 1" in p1.articles_contained
    assert "MADDE 2" in p1.articles_contained
    assert "#page=1" in p1.official_url

    p2 = indexed_engine.get_page("RG_DECISION_8859", 2)
    assert p2 is not None
    assert p2.page_number == 2
    assert "MADDE 3" in p2.articles_contained
    assert "MADDE 4" in p2.articles_contained
    assert "MADDE 5" in p2.articles_contained
    assert "MADDE 6" in p2.articles_contained
    assert "#page=2" in p2.official_url


def test_table_extraction_on_page_2(indexed_engine: OfficialPdfIndexer):
    """Karar 8859 Sayfa 2'deki Birim Fiyat Tablosunun çıkarıldığını test eder."""
    p2 = indexed_engine.get_page("RG_DECISION_8859", 2)
    assert p2 is not None
    assert len(p2.tables) >= 1, "Sayfa 2'de en az bir tablo tespit edilmeli"

    tab = p2.tables[0]
    assert isinstance(tab, PageTableData)
    assert tab.row_count >= 10, f"En az 10 ürün satırı olmalı, bulunan: {tab.row_count}"
    assert tab.col_count >= 6, f"En az 6 sütun olmalı, bulunan: {tab.col_count}"

    # Tablo Markdown içeriği kontrolü
    assert "|" in tab.markdown
    assert "---" in tab.markdown

    # Tablo içeriğinde buğday, mısır, 310 TL, 465 TL doğrulaması
    flat_rows = " ".join(" ".join(r) for r in tab.rows)
    assert any("bugday" in normalize_tr(flat_rows) for _ in [1])
    assert "310" in flat_rows
    assert "465" in flat_rows


def test_graphics_and_vector_analysis(indexed_engine: OfficialPdfIndexer):
    """Sayfalardaki vektör çizimleri ve mühür göstergelerini test eder."""
    p2 = indexed_engine.get_page("RG_DECISION_8859", 2)
    assert p2 is not None
    assert isinstance(p2.graphics, PageGraphicsData)
    assert p2.graphics.drawings_count > 5, "Tablo ızgarası için çizimler tespit edilmeli"
    assert p2.graphics.has_table_borders is True
    assert p2.graphics.has_official_seal is True


def test_high_res_image_rendering(indexed_engine: OfficialPdfIndexer):
    """Sayfa görselinin (144 DPI) oluşturulduğunu ve Base64 verisinin geçerli olduğunu test eder."""
    p1 = indexed_engine.get_page("RG_DECISION_8859", 1)
    assert p1 is not None
    assert p1.image_base64 is not None
    assert p1.image_base64.startswith("data:image/png;base64,")
    assert len(p1.image_base64) > 1000, "Geçerli Base64 görsel verisi olmalı"

    if p1.image_path:
        assert Path(p1.image_path).exists()


def test_search_pages_functionality(indexed_engine: OfficialPdfIndexer):
    """Farklı tarımsal ve mevzuat arama terimlerinin doğru sayfaları döndürdüğünü test eder."""
    # 1. Buğday araması
    results_wheat = indexed_engine.search_pages("buğday", top_k=2)
    assert len(results_wheat) > 0
    assert any(r.page_number == 2 for r in results_wheat)

    # 2. Su Kısıtı araması -> Madde 4 Sayfa 2
    results_water = indexed_engine.search_pages("su kısıtı", top_k=2)
    assert len(results_water) > 0
    top_w = results_water[0]
    assert top_w.page_number == 2
    assert "MADDE 4" in top_w.articles_contained

    # 3. 367 TL katsayı güncellemesi -> Karar 11781
    results_367 = indexed_engine.search_pages("367", top_k=2)
    assert len(results_367) > 0
    assert any(r.doc_id == "RG_DECISION_11781" for r in results_367)

    # 4. Askı İcmali ve 5 gün araması -> Tebliğ 2024/39
    results_aski = indexed_engine.search_pages("askı icmali", top_k=2)
    assert len(results_aski) > 0
    assert any(r.doc_id == "RG_COMMUNIQUE_2024_39" for r in results_aski)


def test_render_page_evidence_card(indexed_engine: OfficialPdfIndexer):
    """HTML sayfa kanıt kartı üretimini ve bileşenlerini doğrular."""
    p2 = indexed_engine.get_page("RG_DECISION_8859", 2)
    assert p2 is not None

    card_html = render_page_evidence_card(p2)
    assert "legal-reader-container" in card_html
    assert "Resmî Gazete Sayfa 2 / 2" in card_html
    assert "#page=2" in card_html
    assert "Sayfadan OCR/Yerleşim ile Çıkarılan Resmî Tablo" in card_html
    assert "Grafik &amp; Düzen Analizi" in card_html
    assert "data:image/png;base64," in card_html
    assert "Orijinal Resmî Gazete Sayfası Görsel Delili" in card_html


def test_render_evidence_by_key(indexed_engine: OfficialPdfIndexer):
    """render_evidence_by_key yardımcı fonksiyonunun anahtara ve aramaya göre çalıştığını doğrular."""
    # 1. Anahtara göre
    html_by_key = render_evidence_by_key("RG_DECISION_8859:1")
    assert "Resmî Gazete Sayfa 1 / 2" in html_by_key
    assert "MADDE 1" in html_by_key

    # 2. Madde adına göre
    html_by_art = render_evidence_by_key("MADDE 4")
    assert "Resmî Gazete Sayfa 2 / 2" in html_by_art

    # 3. Arama sorgusuna göre
    html_by_search = render_evidence_by_key("", search_query="367 TL")
    assert "Karar: 11781" in html_by_search


def test_dropdown_choices_format(indexed_engine: OfficialPdfIndexer):
    """Açılır kutu seçeneklerinin geçerli formatta üretildiğini test eder."""
    choices = get_page_dropdown_choices()
    assert len(choices) >= 4
    for label, val in choices:
        assert ":" in val
        assert len(label) > 10
