"""Sayfa: Kanıt Zinciri & Resmî Gazete Sayfa, Tablo ve Görsel Gezgini (Neden?).

Kural motorunun gerekçelerini, sağlanan/sağlanamayan şartları,
Resmî Gazete sayfa bazlı OCR, tablo ve grafik kanıtlarını bağımsız sekmede sunar.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

import gradio as gr

from tarim_destek_rag.citations.pdf_page_indexer import render_evidence_by_key


def render_evidence_chain_tab() -> dict[str, gr.components.Component]:
    """Kanıt Zinciri sekmesini inşa eder ve bileşen sözlüğünü döner."""
    with gr.TabItem("⚖️ Kanıt Zinciri", id="tab_evidence_chain"):
        gr.HTML("""
        <div class="legal-reader-container" style="margin-top: 4px; margin-bottom: 16px; border-left: 6px solid #047857;">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <h4 style="margin: 0; color: #064e3b; font-size: 1.18rem;">
                    ⚖️ %100 Belgeye Dayanan Şeffaf Karar & Renkli İşaretleme Mimarisi (Neden?)
                </h4>
                <span class="doc-badge-tag doc-badge-pass">Sıfır LLM &middot; %100 Doğrulanabilir</span>
            </div>
            <p style="margin: 8px 0 12px 0; font-size: 0.94rem; color: #334155; line-height: 1.55;">
                Bu sistemde üreticiye sunulan her karar, dekar başı hesaplama ve hak ediş gerekçesi doğrudan
                <b>Resmî Gazete</b> ve <b>BÜGEM</b> mevzuatındaki orijinal metinle delillendirilir. İlgili kanun maddesindeki
                şartlar ve ret gerekçeleri sistem tarafından <b>renk kodlarıyla işaretlenmiştir</b>.
            </p>
            <div class="legal-legend-bar" style="margin-bottom: 0;">
                <span class="legend-item"><span class="legend-dot dot-pass"></span> 🟢 <b>Yeşil Vurgu:</b> Sağlanan Şartlar & Hak Kazanma Hükmü</span>
                <span class="legend-item"><span class="legend-dot dot-fail"></span> 🔴 <b>Kırmızı Vurgu:</b> Ret Gerekçesi & Yasal Yasaklar</span>
                <span class="legend-item"><span class="legend-dot dot-gold"></span> 🟡 <b>Kehribar Vurgu:</b> Birim Destek Tutarları & Katsayılar</span>
                <span class="legend-item"><span class="legend-dot dot-ref"></span> 🔵 <b>Mavi Vurgu:</b> Resmî Gazete / Madde Numarası Dayanağı</span>
            </div>
        </div>
        """)

        with gr.Accordion("📜 Kural Motoru İşletim Gerekçeleri & Ret / Kabul Nedenleri", open=True):
            out_reasons = gr.Markdown(
                "Hesaplama yapıldığında kural motorunun işletim gerekçeleri, sağlanan/sağlanamayan koşullar ve Resmî Gazete yasal madde atıfları burada listelenecektir. "
                "Lütfen **'Çiftçi & Parsellerim'** sekmesinden bilgilerinizi girip **'Destekleri ve Hak Edişi Hesapla'** butonuna tıklayınız."
            )

        with gr.Accordion("📄 Resmî Gazete Sayfa, Tablo ve Görsel Kanıt Gezgini (OCR & Sayfa İndeksi)", open=True):
            gr.Markdown(
                "Aşağıdaki listeden incelemek istediğiniz **Resmî Gazete sayfasını, tablosunu veya mevzuat maddesini** seçiniz "
                "ya da belge içi arama kutusuna ürün, katsayı veya konu yazınız. Sistem ilgili sayfayı, çıkarılan tabloyu, "
                "grafik analizini ve **yüksek çözünürlüklü sayfa görselini** sunar:"
            )
            with gr.Row():
                article_selector = gr.Dropdown(
                    choices=[
                        "MADDE 1 - Temel Destek ve ÇKS Zorunluluğu (Karar 8859 S.1)",
                        "MADDE 2 - Tarım Havzaları Planlı Üretim Desteği (Karar 8859 S.1)",
                        "MADDE 3 - Sertifikalı Tohum Kullanım Desteği (Karar 8859 S.2)",
                        "MADDE 4 - Yeraltı Su Kısıtı Olan Havzalar Desteği (Karar 8859 S.2)",
                        "MADDE 5 - Kadın ve Genç Çiftçi İlave Desteği (Karar 8859 S.2)",
                        "MADDE 6 - Sertifikalı Fidan ve Kapama Bahçe Şartı (Karar 8859 S.2)",
                        "EK TABLO - 2026 Birim Destek Katsayıları & Fiyat Cetveli (Karar 8859 S.2)",
                        "KARAR 11781 - 2026 Destekleme Katsayısı Güncellemesi (367 TL/da S.1)",
                        "TEBLİĞ 2024/39 - Askı İcmalleri, 5 Günlük İtiraz ve ÇKS Süreçleri",
                    ],
                    value="MADDE 1 - Temel Destek ve ÇKS Zorunluluğu (Karar 8859 S.1)",
                    label="📄 Resmî Gazete Belgesi, Sayfası ve Madde Seçimi (#page=X)",
                    scale=7,
                )
                page_search_input = gr.Textbox(
                    placeholder="Belge ve tablolarda ara (Örn: Buğday, 310, Su Kısıtı, 367, Mısır, Askı)...",
                    label="🔍 Resmî Belge İçi Hızlı Arama",
                    scale=4,
                )
                btn_page_search = gr.Button("🔍 Sayfayı Bul", scale=2, variant="secondary")

            article_display = gr.HTML(
                value=render_evidence_by_key("MADDE 1")
            )

            def update_article_view(choice: str, query: str = "") -> str:
                return render_evidence_by_key(choice, query)

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

    return {
        "out_reasons": out_reasons,
        "article_selector": article_selector,
        "page_search_input": page_search_input,
        "btn_page_search": btn_page_search,
        "article_display": article_display,
    }
