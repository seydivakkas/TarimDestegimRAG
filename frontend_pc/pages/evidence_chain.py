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
                btn_m1 = gr.Button("🏛️ Karar 8859: Başlık & İmza (S.1)", variant="secondary", size="sm")
                btn_m2 = gr.Button("🟢 MADDE 1: Amaç & Temel Destek (S.2)", variant="secondary", size="sm")
                btn_m3 = gr.Button("🌱 MADDE 2: Planlı Üretim & Havza (S.3)", variant="secondary", size="sm")
                btn_tablo = gr.Button("📊 TABLO 2: Planlı Katsayılar (S.3)", variant="secondary", size="sm")
                btn_m4 = gr.Button("💧 TABLO 3: Su Kısıtı Desteği (S.3)", variant="secondary", size="sm")

            with gr.Row():
                btn_m5 = gr.Button("🌾 TABLO 5: Yerli Islah Tohum (S.4)", variant="secondary", size="sm")
                btn_m6 = gr.Button("🌿 TABLO 8: İyi Tarım Desteği (S.5)", variant="secondary", size="sm")
                btn_genc = gr.Button("🧑‍🌾 Genç/Kadın Çiftçi Şartları (S.6)", variant="secondary", size="sm")
                btn_ceza = gr.Button("⚖️ Cezai Hükümler & Md. 10 (S.8)", variant="secondary", size="sm")
                btn_11781 = gr.Button("📜 KARAR 11781: 367 TL Katsayı (S.1)", variant="secondary", size="sm")
                btn_teblig = gr.Button("📋 TEBLİĞ 2024/39: Askı & İtiraz (S.1)", variant="secondary", size="sm")

            with gr.Row():
                article_selector = gr.Dropdown(
                    choices=[
                        "Sayfa 1 - Cumhurbaşkanı Kararı (Karar 8859, Sayı: 32647) — Recep Tayyip Erdoğan İmzası",
                        "Sayfa 2 - MADDE 1 (Amaç ve Kapsam), MADDE 2 (Temel Destek) & TABLO 1 (Temel Katsayılar)",
                        "Sayfa 3 - MADDE 2 (Planlı Üretim), TABLO 2 (Katsayılar), Süt Havzaları & TABLO 3 (Su Kısıtı)",
                        "Sayfa 4 - TABLO 4 & TABLO 5 (Yerli Islah Tohum Desteği), TABLO 6 (Sertifikalı Fidan), TABLO 7",
                        "Sayfa 5 - TABLO 8 (İyi Tarım Uygulamaları Katsayıları), TABLO 9 (Biyolojik Mücadele: 3.825 TL)",
                        "Sayfa 6 - ÇKS Şartları, Genç ve Kadın Çiftçi İlave Katsayısı, MADDE 3 (ÇMVA), MADDE 4 (Ar-Ge)",
                        "Sayfa 7 - MADDE 6 (Yararlanamayacaklar), MADDE 7 (Denetim & Tedbirler), Ziraat Bankası Protokolü",
                        "Sayfa 8 - Cezai Hükümler (6183 SK, 5 Yıl Men Cezası), MADDE 9 (Yürürlük), MADDE 10 (Yürütme)",
                        "KARAR 11781 - 2026 Destekleme Katsayısı Güncellemesi (367 TL/da S.1)",
                        "TEBLİĞ 2024/39 - Askı İcmalleri, 5 Günlük İtiraz ve ÇKS Süreçleri",
                    ],
                    value="Sayfa 2 - MADDE 1 (Amaç ve Kapsam), MADDE 2 (Temel Destek) & TABLO 1 (Temel Katsayılar)",
                    label="📄 Taranmış Resmî Gazete Sayfaları & OCR Cetvel Seçici (#page=X)",
                    scale=7,
                )
                page_search_input = gr.Textbox(
                    placeholder="Belge ve tablolarda ara (Örn: Buğday, 310, Su Kısıtı, 367, Mısır, Askı)...",
                    label="🔍 Resmî Belge İçi Hızlı Arama",
                    scale=4,
                )
                btn_page_search = gr.Button("🔍 Sayfayı Bul", scale=2, variant="secondary")

            article_display = gr.HTML(
                value=render_evidence_by_key("Sayfa 2")
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
            v_p1 = "Sayfa 1 - Cumhurbaşkanı Kararı (Karar 8859, Sayı: 32647) — Recep Tayyip Erdoğan İmzası"
            v_p2 = "Sayfa 2 - MADDE 1 (Amaç ve Kapsam), MADDE 2 (Temel Destek) & TABLO 1 (Temel Katsayılar)"
            v_p3 = "Sayfa 3 - MADDE 2 (Planlı Üretim), TABLO 2 (Katsayılar), Süt Havzaları & TABLO 3 (Su Kısıtı)"
            v_tablo2 = "Sayfa 3 - MADDE 2 (Planlı Üretim), TABLO 2 (Katsayılar), Süt Havzaları & TABLO 3 (Su Kısıtı)"
            v_sukisiti = "Sayfa 3 - MADDE 2 (Planlı Üretim), TABLO 2 (Katsayılar), Süt Havzaları & TABLO 3 (Su Kısıtı)"
            v_p4 = "Sayfa 4 - TABLO 4 & TABLO 5 (Yerli Islah Tohum Desteği), TABLO 6 (Sertifikalı Fidan), TABLO 7"
            v_p5 = "Sayfa 5 - TABLO 8 (İyi Tarım Uygulamaları Katsayıları), TABLO 9 (Biyolojik Mücadele: 3.825 TL)"
            v_p6 = "Sayfa 6 - ÇKS Şartları, Genç ve Kadın Çiftçi İlave Katsayısı, MADDE 3 (ÇMVA), MADDE 4 (Ar-Ge)"
            v_p8 = "Sayfa 8 - Cezai Hükümler (6183 SK, 5 Yıl Men Cezası), MADDE 9 (Yürürlük), MADDE 10 (Yürütme)"
            v_11781 = "KARAR 11781 - 2026 Destekleme Katsayısı Güncellemesi (367 TL/da S.1)"
            v_teblig = "TEBLİĞ 2024/39 - Askı İcmalleri, 5 Günlük İtiraz ve ÇKS Süreçleri"

            btn_m1.click(lambda: v_p1, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_m2.click(lambda: v_p2, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_m3.click(lambda: v_p3, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_tablo.click(lambda: v_tablo2, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_m4.click(lambda: v_sukisiti, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_m5.click(lambda: v_p4, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_m6.click(lambda: v_p5, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_genc.click(lambda: v_p6, outputs=[article_selector]).then(
                update_article_view, inputs=[article_selector, page_search_input], outputs=[article_display]
            )
            btn_ceza.click(lambda: v_p8, outputs=[article_selector]).then(
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
