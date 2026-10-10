"""Sayfa 3: Mevzuat Asistanı (Sıfır LLM Doğrulanmış Soru-Cevap & SSS Rehberi)."""

from __future__ import annotations

import gradio as gr
import pandas as pd

from frontend_pc.services.faq_service import (
    ask_assistant,
    get_faq_banner_text,
    get_faq_categories,
    get_faq_table,
)


def render_legal_assistant_tab() -> dict[str, gr.components.Component]:
    """Mevzuat Asistanı sekmesini inşa eder ve bileşen sözlüğünü döner."""
    with gr.TabItem("💬 Mevzuat Asistanı", id="tab_legal_assistant"):
        gr.Markdown("""
        ### 🌾 2026 Tarımsal Destek Ön Bilgi Asistanı (Sıfır LLM — Kaynak Doğrulaması Gereklidir)
        Sorunuzu doğrudan doğal dille yazın. Sistem yürürlükteki 2026 Resmî Gazete destekleme mevzuatı,
        5488 sayılı Tarım Kanunu, ÇKS yönetmeliği ve mevcut veritabanından kaynaklı ön bilgi sunar; güncel mevzuatla bağımsız teyit edilmelidir.
        """)
        chatbot = gr.Chatbot(height=420, label="Mevzuat & Soru-Cevap Sohbeti")
        with gr.Row():
            chat_input = gr.Textbox(
                placeholder="Örn: 'Destekleme parasına haciz konulur mu?', 'Kiralık arazide ÇKS olur mu?', '2026 Buğday desteği ne kadar?'",
                scale=8,
                show_label=False,
            )
            chat_submit = gr.Button("Sor 🚀", scale=2, variant="primary")
            chat_clear = gr.Button("🗑️ Temizle", scale=1, variant="secondary")

        gr.Markdown("**💡 En Sık Sorulan Çiftçi Soruları (Tek Tıkla Sor):**")
        with gr.Row():
            q1 = gr.Button("🌾 2026 Buğday & Arpa Destek Tutarları", size="sm")
            q2 = gr.Button("📑 ÇKS Kaydı Nasıl Yapılır & Evraklar", size="sm")
            q3 = gr.Button("👩‍🌾 Kadın ve Genç Çiftçi İlave Desteği", size="sm")
        with gr.Row():
            q4 = gr.Button("🚫 Destekleme Parasına Haciz Konur mu?", size="sm")
            q5 = gr.Button("📝 Kiralık Arazide ÇKS ve Destek Alınır mı?", size="sm")
            q6 = gr.Button("🤝 Hisseli Tapuda İmza Vermeyen Hissedar", size="sm")
        with gr.Row():
            q7 = gr.Button("💧 Yeraltı Su Kısıtı Olan Havzalar Desteği", size="sm")
            q8 = gr.Button("🌿 Organik Tarım & Biyolojik Mücadele", size="sm")
            q9 = gr.Button("🔄 2026 Yeni Destek Modelinde Ne Değişti?", size="sm")
        with gr.Row():
            q10 = gr.Button("🌱 Sertifikalı Tohum & Fidan Şartları", size="sm")
            q11 = gr.Button("⚖️ Askı İcmali Nedir & 5 Günlük İtiraz", size="sm")
            q12 = gr.Button("💳 Destekler Ne Zaman & Nereye Yatar?", size="sm")
        with gr.Row():
            q13 = gr.Button("🐛 Kahverengi Kokarca & Zirai Mücadele", size="sm")
            q14 = gr.Button("🛡️ TARSİM Sigortası & Don İhbar Süresi", size="sm")
            q15 = gr.Button("☀️ Güneş Enerjisi (GES) & Sulama Hibesi", size="sm")

        with gr.Accordion("📚 2026 Resmî Çiftçi Sıkça Sorulan Sorular (SSS) Kütüphanesi & Rehberi", open=True):
            gr.Markdown("Aşağıdaki resmi SSS tablosundan merak ettiğiniz konuyu seçip doğrudan asistana sorabilir veya arama yapabilirsiniz:")
            faq_banner_md = gr.Markdown(get_faq_banner_text())
            with gr.Row():
                faq_cat_dropdown = gr.Dropdown(
                    choices=get_faq_categories(),
                    value="Tümü",
                    label="Kategoriye Göre Filtrele",
                    scale=4,
                )
                faq_search_input = gr.Textbox(
                    placeholder="Anahtar kelimeyle ara (haciz, kira, kokarca, tarsim, hibe, organik)...",
                    label="SSS Kütüphanesinde Ara",
                    scale=6,
                )
                btn_filter_faq = gr.Button("🔍 Filtrele / Ara", scale=2, variant="secondary")

            faq_df = gr.DataFrame(value=get_faq_table(), interactive=False)

            def update_faq_view(cat: str, search_txt: str) -> tuple[pd.DataFrame, str]:
                table = get_faq_table(cat, search_txt)
                banner = get_faq_banner_text()
                return table, banner

            faq_cat_dropdown.change(
                update_faq_view,
                inputs=[faq_cat_dropdown, faq_search_input],
                outputs=[faq_df, faq_banner_md],
            )
            btn_filter_faq.click(
                update_faq_view,
                inputs=[faq_cat_dropdown, faq_search_input],
                outputs=[faq_df, faq_banner_md],
            )
            faq_search_input.submit(
                update_faq_view,
                inputs=[faq_cat_dropdown, faq_search_input],
                outputs=[faq_df, faq_banner_md],
            )

            def on_faq_click(evt: gr.SelectData, df: pd.DataFrame, history: list[dict[str, str]]):
                if evt is not None and hasattr(evt, "index"):
                    row_idx = evt.index[0]
                    if row_idx < len(df):
                        q_val = str(df.iloc[row_idx]["Soru"])
                        return ask_assistant(q_val, history)
                return "", history

            faq_df.select(
                on_faq_click,
                inputs=[faq_df, chatbot],
                outputs=[chat_input, chatbot],
            )

        chat_submit.click(
            ask_assistant,
            inputs=[chat_input, chatbot],
            outputs=[chat_input, chatbot],
        )
        chat_input.submit(
            ask_assistant,
            inputs=[chat_input, chatbot],
            outputs=[chat_input, chatbot],
        )
        chat_clear.click(lambda: ("", []), outputs=[chat_input, chatbot])

        def make_quick_ask(prompt: str):
            def _h(history: list[dict[str, str]] | None = None):
                return ask_assistant(prompt, history or [])
            return _h

        q1.click(make_quick_ask("2026 yılında buğday ve arpa desteği ne kadar?"), inputs=[chatbot], outputs=[chat_input, chatbot])
        q2.click(make_quick_ask("ÇKS kaydı nasıl yapılır ve başvuru için hangi evraklar gerekir?"), inputs=[chatbot], outputs=[chat_input, chatbot])
        q3.click(make_quick_ask("Kadın çiftçilere ve genç çiftçilere ilave destek var mı?"), inputs=[chatbot], outputs=[chat_input, chatbot])
        q4.click(make_quick_ask("Tarımsal destekleme ödemelerine banka borcundan veya icradan haciz konulabilir mi?"), inputs=[chatbot], outputs=[chat_input, chatbot])
        q5.click(make_quick_ask("Kiralık arazide ÇKS kaydı ve tarımsal destek alınabilir mi?"), inputs=[chatbot], outputs=[chat_input, chatbot])
        q6.click(make_quick_ask("Hisseli tapulu arazide diğer hissedarlar imza vermezse ÇKS nasıl yapılır?"), inputs=[chatbot], outputs=[chat_input, chatbot])
        q7.click(make_quick_ask("Yeraltı su kısıtı olan havzalar desteği nedir ve hangi ürünlere verilir?"), inputs=[chatbot], outputs=[chat_input, chatbot])
        q8.click(make_quick_ask("Organik tarım ve biyolojik mücadele desteği kimlere verilir?"), inputs=[chatbot], outputs=[chat_input, chatbot])
        q9.click(make_quick_ask("2026 Yeni Destekleme Modeli'nde eski sisteme göre ne değişti?"), inputs=[chatbot], outputs=[chat_input, chatbot])
        q10.click(make_quick_ask("Sertifikalı tohum ve sertifikalı fidan destekleme şartları nelerdir?"), inputs=[chatbot], outputs=[chat_input, chatbot])
        q11.click(make_quick_ask("Askı icmali nedir, kaç gün askıda kalır ve itiraz süresi ne kadardır?"), inputs=[chatbot], outputs=[chat_input, chatbot])
        q12.click(make_quick_ask("Tarımsal destekleme ödemeleri ne zaman ve hangi bankaya yatar?"), inputs=[chatbot], outputs=[chat_input, chatbot])
        q13.click(make_quick_ask("Kahverengi kokarca zararlısıyla nasıl mücadele edilir ve ilaçlama desteği var mı?"), inputs=[chatbot], outputs=[chat_input, chatbot])
        q14.click(make_quick_ask("TARSİM tarım sigortasında don ve kuraklık hasarı ihbar süresi kaç gündür?"), inputs=[chatbot], outputs=[chat_input, chatbot])
        q15.click(make_quick_ask("Tarımsal sulamada güneş enerjisi (GES) ve modern damla sulama için hibe desteği var mı?"), inputs=[chatbot], outputs=[chat_input, chatbot])

    return {
        "chatbot": chatbot,
        "chat_input": chat_input,
        "chat_submit": chat_submit,
        "chat_clear": chat_clear,
        "faq_df": faq_df,
    }
