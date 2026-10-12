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

        gr.HTML("""
        <div style="background: #f0fdf4; border: 1px solid #bbf7d0; border-left: 5px solid #16a34a; border-radius: 8px; padding: 12px 18px; margin: 12px 0 16px 0;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h4 style="margin: 0; color: #166534; font-size: 1.05rem;">
                        ⚖️ Kanıt Zinciri & Resmî Gazete Madde Gezgini Ayrı Bölüme Taşındı
                    </h4>
                    <p style="margin: 4px 0 0 0; color: #374151; font-size: 0.92rem;">
                        Kural motorunun işletim gerekçeleri, sağlanan/sağlanamayan koşullar ve Resmî Gazete sayfa/tablo OCR kanıtları 
                        üst menüdeki <b>'⚖️ Kanıt Zinciri'</b> sekmesinde detaylı olarak sunulmaktadır.
                    </p>
                </div>
            </div>
        </div>
        """)

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
        "btn_report": btn_report,
        "file_report": file_report,
        "out_disclaimer": out_disclaimer,
    }

