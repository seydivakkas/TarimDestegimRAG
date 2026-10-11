"""Sayfa 2: Destek Analizi (Kartlar, Formül, Mevzuat Gerekçesi, Eksik Belgeler ve Raporlama)."""

from __future__ import annotations

import gradio as gr
import pandas as pd

from tarim_destek_rag.citations.document_links import render_document_viewer_html


def render_support_analysis_tab() -> dict[str, gr.components.Component]:
    """Destek Analizi sekmesini inşa eder ve bileşen sözlüğünü döner."""
    with gr.TabItem("📊 Destek Analizi", id="tab_support_analysis"):
        out_kpi = gr.HTML(
            "<div class='kpi-container'><div class='kpi-card'><div class='kpi-title'>Tahmini Destek</div><div class='kpi-value'>Hesaplama Bekleniyor</div></div></div>"
        )
        out_cards = gr.HTML(
            "<p style='color: #64748b;'>Lütfen 'Çiftçi & Parsellerim' sekmesinden bilgilerinizi girip 'Destekleri ve Hak Edişi Hesapla' butonuna tıklayınız.</p>"
        )

        with gr.Accordion("📊 Destek Kalemleri Detay Tablosu (Birim Fiyatlar & Formüller)", open=True):
            out_table = gr.DataFrame(
                headers=[
                    "Destek Programı",
                    "Durum",
                    "Birim Fiyat (TL/da)",
                    "Alan (da)",
                    "Tahmini Tutar",
                    "Hesaplama Formülü",
                    "Başvuru Dönemi",
                    "Dayanak",
                ],
                datatype=["str", "str", "str", "str", "str", "str", "str", "str"],
                interactive=False,
            )

        with gr.Accordion("⚖️ Kanıt Zinciri & Renkli Resmî Gazete Madde Önizleme (Neden?)", open=True):
            gr.Markdown(
                "**Özgün sayfa görüntüsü:** Belge dosyası SHA-256 ile doğrulanmadan "
                "hiçbir sayfa gösterilmez. Metin katmanı/OCR sonucunun doğruluğu "
                "ayrı inceleme gerektirir; otomatik hak ediş onayı yoktur."
            )
            out_reasons = gr.Markdown(
                "Buradaki hesaplama açıklamaları resmî alıntı değildir; "
                "hukukî kaynak bağlantıları bağımsız olarak doğrulanmalıdır."
            )
            from tarim_destek_rag.citations.pdf_page_indexer import (
                get_page_dropdown_choices,
                render_evidence_by_key,
            )

            gr.Markdown(
                "Yalnız **gerçek arşiv dosyasından çıkarılmış sayfalar** listelenir. "
                "Metin araması, doğrulanmamış OCR üzerinden tahmini sayfa üretmez."
            )
            with gr.Row():
                article_selector = gr.Dropdown(
                    choices=get_page_dropdown_choices(),
                    value=None,
                    label="Özgün PDF / gerçek sayfa",
                    scale=7,
                )
                page_search_input = gr.Textbox(
                    placeholder="Kaynak metin katmanında ara; bulunamazsa HOLD",
                    label="Kaynak içinde ara",
                    scale=4,
                )
                btn_page_search = gr.Button("Gerçek sayfayı göster", scale=2)

            article_display = gr.HTML(
                value="<p>Henüz kaynak kanıtı seçilmedi. "
                "Belge arşivi yoksa sayfa gösterilmez.</p>"
            )

            def update_article_view(choice: str | None, query: str = "") -> str:
                return render_evidence_by_key(choice or "", query or "")

            article_selector.change(
                update_article_view,
                inputs=[article_selector, page_search_input],
                outputs=[article_display],
            )
            btn_page_search.click(
                update_article_view,
                inputs=[article_selector, page_search_input],
                outputs=[article_display],
            )
            page_search_input.submit(
                update_article_view,
                inputs=[article_selector, page_search_input],
                outputs=[article_display],
            )

        with gr.Accordion("📁 Başvuru İçin Gerekli Belgeler & Ön Değerlendirme Raporu", open=True):
            gr.Markdown("""
            #### 📁 Başvuru İçin Gerekli Belgeler Kontrol Listesi
            - ✅ **Çiftçi Kayıt Sistemi (ÇKS) Belgesi:** Güncel 2026 üretim yılı için İlçe Tarım Müdürlüğünden veya e-Devlet kapısından onaylı.
            - ✅ **Sertifikalı Tohum / Fidan Faturası:** Bakanlık yetkili tohum/fidan bayisinden alınmış kaşeli orijinal fatura ve etiket kopyası.
            - ✅ **Tapu / Kira / Muvafakatname:** Parselin mülkiyet veya intifa hakkını tevsik eden belge.
            - ✅ **Başvuru Dilekçesi & Taahhütname:** İlgili destekleme programı için standart form.

            #### 📌 Eksik Evrak / İnceleme Durumunda Yapılması Gerekenler
            1. ÇKS kaydınız henüz aktifleşmediyse İlçe Tarım ve Orman Müdürlüğüne 2026 başvuru formunuzu teslim ediniz.
            2. Sertifikalı tohum veya fidan desteği için faturanızın üretim yılı (2026) ile uyumlu olduğunu kontrol ediniz.
            3. Askı icmalleri yayımlandığında 5 günlük yasal itiraz süresini kaçırmamak için köy muhtarlığı panosunu takip ediniz.
            """)

            with gr.Row():
                btn_report = gr.Button(
                    "📄 Resmî Ön Değerlendirme Raporu Oluştur & İndir (.md)",
                    variant="primary",
                    size="lg",
                )
            file_report = gr.File(label="İndirilebilir Rapor Dosyası", visible=False)

        out_disclaimer = gr.HTML("")

    return {
        "out_kpi": out_kpi,
        "out_cards": out_cards,
        "out_table": out_table,
        "out_reasons": out_reasons,
        "article_selector": article_selector,
        "article_display": article_display,
        "btn_report": btn_report,
        "file_report": file_report,
        "out_disclaimer": out_disclaimer,
    }
