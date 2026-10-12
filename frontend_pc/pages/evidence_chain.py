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
                "Aşağıdaki **madde butonlarına doğrudan tıklayarak** ilgili Resmî Gazete sayfasını, tablosunu ve orijinal sayfa görselini anında aşağıda açabilirsiniz:"
            )

            with gr.Row():
                btn_m1 = gr.Button("🟢 MADDE 1: Temel Destek & ÇKS (S.1)", variant="secondary", size="sm")
                btn_m2 = gr.Button("🟢 MADDE 2: Planlı Üretim & Havza (S.1)", variant="secondary", size="sm")
                btn_m3 = gr.Button("🟢 MADDE 3: Sertifikalı Tohum (S.2)", variant="secondary", size="sm")
                btn_m4 = gr.Button("🟢 MADDE 4: Su Kısıtı Havzaları (S.2)", variant="secondary", size="sm")

            with gr.Row():
                btn_m5 = gr.Button("🟢 MADDE 5: Genç & Kadın Çiftçi (S.2)", variant="secondary", size="sm")
                btn_m6 = gr.Button("🟢 MADDE 6: Sertifikalı Fidan (S.2)", variant="secondary", size="sm")
                btn_tablo = gr.Button("📊 EK TABLO: 2026 Destek Tutarları (S.2)", variant="secondary", size="sm")
                btn_11781 = gr.Button("📜 KARAR 11781: 367 TL Katsayı (S.1)", variant="secondary", size="sm")
                btn_teblig = gr.Button("📋 TEBLİĞ 2024/39: Askı & İtiraz (S.1)", variant="secondary", size="sm")

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

            # Doğrudan Tıklanabilir Madde Butonları Bağlantıları
            v_m1 = "MADDE 1 - Temel Destek ve ÇKS Zorunluluğu (Karar 8859 S.1)"
            v_m2 = "MADDE 2 - Tarım Havzaları Planlı Üretim Desteği (Karar 8859 S.1)"
            v_m3 = "MADDE 3 - Sertifikalı Tohum Kullanım Desteği (Karar 8859 S.2)"
            v_m4 = "MADDE 4 - Yeraltı Su Kısıtı Olan Havzalar Desteği (Karar 8859 S.2)"
            v_m5 = "MADDE 5 - Kadın ve Genç Çiftçi İlave Desteği (Karar 8859 S.2)"
            v_m6 = "MADDE 6 - Sertifikalı Fidan ve Kapama Bahçe Şartı (Karar 8859 S.2)"
            v_tablo = "EK TABLO - 2026 Birim Destek Katsayıları & Fiyat Cetveli (Karar 8859 S.2)"
            v_11781 = "KARAR 11781 - 2026 Destekleme Katsayısı Güncellemesi (367 TL/da S.1)"
            v_teblig = "TEBLİĞ 2024/39 - Askı İcmalleri, 5 Günlük İtiraz ve ÇKS Süreçleri"

            btn_m1.click(lambda: v_m1, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_m2.click(lambda: v_m2, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_m3.click(lambda: v_m3, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_m4.click(lambda: v_m4, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_m5.click(lambda: v_m5, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_m6.click(lambda: v_m6, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_tablo.click(lambda: v_tablo, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_11781.click(lambda: v_11781, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_teblig.click(lambda: v_teblig, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )


    return {
        "out_reasons": out_reasons,
        "article_selector": article_selector,
        "page_search_input": page_search_input,
        "btn_page_search": btn_page_search,
        "article_display": article_display,
    }
