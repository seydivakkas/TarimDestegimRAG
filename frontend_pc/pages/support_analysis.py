"""Sayfa 2: Destek Analizi (Kartlar, Formül, Mevzuat Gerekçesi, Eksik Belgeler ve Raporlama)."""

from __future__ import annotations

import gradio as gr
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
            gr.HTML("""
            <div class="legal-reader-container" style="margin-top: 4px; margin-bottom: 16px; border-left: 6px solid #047857;">
                <div style="display: flex; justify-content: space-between; align-items: center;">
                    <h4 style="margin: 0; color: #064e3b; font-size: 1.15rem;">
                        ⚖️ Kanıt Durumu & Resmî Belge İnceleme
                    </h4>
                    <span class="doc-badge-tag doc-badge-pass">Sıfır LLM &middot; Birebir kaynak denetimi</span>
                </div>
                <p style="margin: 8px 0 12px 0; font-size: 0.92rem; color: #334155; line-height: 1.55;">
                    Kuralların Türkçe açıklaması ile resmî mevzuatın birebir alıntısı ayrı gösterilir.
                    <b>Yalnızca özgün PDF'de SHA-256, sayfa ve cümle eşleşmesi doğrulanan</b> kanıtlar
                    işaretli PDF bağlantısıyla açılır. Diğer metinler <b>ön değerlendirme açıklamasıdır</b>;
                    geçerli hukukî sonuç ya da birebir alıntı olarak sunulmaz.
                </p>
                <div class="legal-legend-bar" style="margin-bottom: 0;">
                    <span class="legend-item"><span class="legend-dot dot-pass"></span> 🟢 <b>Yeşil Vurgu:</b> Sağlanan Şartlar & Hak Kazanma Hükmü</span>
                    <span class="legend-item"><span class="legend-dot dot-fail"></span> 🔴 <b>Kırmızı Vurgu:</b> Ret Gerekçesi & Yasal Yasaklar</span>
                    <span class="legend-item"><span class="legend-dot dot-gold"></span> 🟡 <b>Kehribar Vurgu:</b> Birim Destek Tutarları & Katsayılar</span>
                    <span class="legend-item"><span class="legend-dot dot-ref"></span> 🔵 <b>Mavi Vurgu:</b> Resmî Gazete / Madde Numarası Dayanağı</span>
                </div>
            </div>
            """)

            out_reasons = gr.Markdown(
                "Hesaplama yapıldığında kural motorunun işletim gerekçeleri, sağlanan/sağlanamayan koşullar ve Resmî Gazete yasal madde atıfları burada listelenecektir."
            )

            gr.Markdown(
                "Aşağıdaki konu bağlantıları henüz birebir madde alıntısı değildir. "
                "Doğrulanmış kanıt varsa yukarıdaki gerekçe kartında işaretli PDF bağlantısı bulunur:"
            )
            article_selector = gr.Dropdown(
                choices=[
                    "MADDE 1 - Temel Destek ve ÇKS Zorunluluğu",
                    "MADDE 2 - Tarım Havzaları Planlı Üretim Desteği",
                    "MADDE 3 - Sertifikalı Tohum Kullanım Desteği",
                    "MADDE 4 - Yeraltı Su Kısıtı Olan Havzalar Desteği",
                    "MADDE 5 - Kadın ve Genç Çiftçi İlave Desteği",
                    "MADDE 6 - Sertifikalı Fidan ve Kapama Bahçe Şartı",
                    "EK TABLO - Ürün Bazlı Birim Fiyat Kataloğu",
                ],
                value="MADDE 1 - Temel Destek ve ÇKS Zorunluluğu",
                label="İncelenecek Resmî Mevzuat Maddesi",
            )

            article_display = gr.HTML(
                value=render_document_viewer_html("MADDE 1")
            )

            def update_article_view(choice: str) -> str:
                return render_document_viewer_html(choice)

            article_selector.change(
                update_article_view, inputs=[article_selector], outputs=[article_display]
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
