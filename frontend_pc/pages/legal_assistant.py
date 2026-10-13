"""Belge Analizi & RAG Asistanı: source-first retrieval, no decisions."""
from __future__ import annotations

import gradio as gr
import pandas as pd

from frontend_pc.api_client import ApiClient
from frontend_pc.services.faq_service import (
    ask_assistant,
    ask_assistant_filtered,
    get_faq_categories,
    get_faq_table,
)


def _corpus_status() -> str:
    data = ApiClient().get_document_analysis_status()
    if data.get("status") == "UNAVAILABLE":
        return "Belge analiz servisine erişilemiyor. Backend çalışmıyor olabilir."
    return (
        "**Aranabilir belge:** "
        f"{data.get('source_count', 0)} · "
        "**Aranabilir pasaj:** "
        f"{data.get('passage_count', 0)} · "
        "**Yapısal PDF tablo pasajı:** "
        f"{data.get('native_table_passage_count', 0)} · "
        "**OCR eksik sayfa:** "
        f"{data.get('pdf_pages_without_ocr', 0)} · "
        "**Arama:** "
        f"{data.get('search_mode', 'BELİRSİZ')}. "
        "Kaynak dosyası olmayan belgeler uydurma içerikle tamamlanmaz."
    )


def _document_choices() -> list[tuple[str, str]]:
    docs = ApiClient().get_document_analysis_status().get("indexed_documents") or []
    return [("Tüm indekslenmiş belgeler", "")] + [
        (str(d.get("title") or d.get("source_id") or "Belge"), str(d["source_id"]))
        for d in docs
        if isinstance(d, dict) and isinstance(d.get("source_id"), str)
    ]


def render_legal_assistant_tab() -> dict[str, gr.components.Component]:
    """Minimal RAG-only document question/answer interface."""
    with gr.TabItem("Belge Analizi & RAG", id="tab_legal_assistant"):
        gr.Markdown(
            "### Belge Analizi — Kaynaklı Soru-Cevap\n"
            "Soru yazın. Sistem yalnızca indekslenmiş **gerçek PDF/HTML belge "
            "parçaları ve varsa OCR metni** içinde arar. Yanıtta ilgili "
            "belgenin adını, sayfasını veya maddesini ve kaynak bağlantısını "
            "görürsünüz. Belgede bulunmayan şeyi biliyormuş gibi cevaplamaz."
        )
        with gr.Row():
            status_display = gr.Markdown(value=_corpus_status())
            refresh_status = gr.Button("Belge listesini yenile", size="sm")
        document_selector = gr.Dropdown(
            choices=_document_choices(),
            value="",
            label="Arama kapsamı — belirli belge veya tüm belgeler",
            interactive=True,
        )
        refresh_status.click(
            lambda: (
                _corpus_status(),
                gr.update(choices=_document_choices(), value=""),
            ),
            outputs=[status_display, document_selector],
        )

        with gr.Accordion("Yeni belge ekle — PDF / HTML / TXT", open=True):
            gr.Markdown(
                "Dosya kendi bilgisayarınızda işlenir; ücretli bulut API'si "
                "gerekmez. **Taranmış PDF'lerde Türkçe OCR**, kurulu yerel "
                "Tesseract ile çalışır. OCR sonucu belgeye bakarak kontrol "
                "edilebilir ve kaynak sayfa olduğu gibi saklanır."
            )
            with gr.Row():
                upload_file = gr.File(
                    label="İncelenecek belge",
                    file_types=[".pdf", ".html", ".htm", ".txt"],
                    type="filepath",
                    scale=6,
                )
                upload_ocr = gr.Checkbox(
                    label="Taranmış PDF sayfalarını OCR ile oku",
                    value=True,
                    scale=3,
                )
            upload_button = gr.Button("Belgeyi kütüphaneye ekle ve indeksle")
            upload_feedback = gr.Markdown(
                "Henüz yeni belge eklenmedi. Resmî kaynak arşivindeki mevcut "
                "belgeler de ayrıca aranabilir."
            )

            def upload_and_index(
                file_path: str | None, with_ocr: bool,
            ) -> tuple[str, str, gr.Dropdown]:
                if not file_path:
                    return (
                        "Önce bir dosya seçin.", _corpus_status(),
                        gr.update(choices=_document_choices(), value=""),
                    )
                outcome = ApiClient().import_document(
                    str(file_path), run_ocr=with_ocr,
                )
                if outcome.get("import_status") != "INDEXED":
                    return (
                        "Belge eklenemedi: "
                        + str(outcome.get("message") or "Bilinmeyen hata"),
                        _corpus_status(),
                        gr.update(choices=_document_choices(), value=""),
                    )
                item = outcome.get("document") or {}
                return (
                    f"**Kütüphaneye eklendi:** {item.get('filename', 'Belge')} · "
                    f"Kaynak kimliği: `{item.get('id', '')}` · "
                    "Dosya türü: kullanıcı yüklemesi. "
                    "Bu, belgedeki her ifadenin doğru olduğunu onaylamaz.",
                    _corpus_status(),
                    gr.update(
                        choices=_document_choices(),
                        value=str(item.get("id") or ""),
                    ),
                )

            upload_button.click(
                upload_and_index,
                inputs=[upload_file, upload_ocr],
                outputs=[upload_feedback, status_display, document_selector],
            )

        chatbot = gr.Chatbot(height=500, label="Belgelerimden Soru-Cevap")
        with gr.Row():
            chat_input = gr.Textbox(
                placeholder="Örn: 'Bu belgede ÇKS şartı nerede anlatılmış?'",
                label="Belgeye sor",
                scale=8,
            )
            chat_submit = gr.Button("Belgede ara", scale=2, variant="primary")
            chat_clear = gr.Button("Temizle", scale=1, variant="secondary")
        for sender in (chat_submit, chat_input):
            callback = sender.click if sender is chat_submit else sender.submit
            callback(
                ask_assistant_filtered,
                inputs=[chat_input, chatbot, document_selector],
                outputs=[chat_input, chatbot],
            )
        chat_clear.click(lambda: ("", []), outputs=[chat_input, chatbot])

        with gr.Row():
            q1 = gr.Button("2024/39 Madde 4'ü bul", size="sm")
            q2 = gr.Button("2025/42 hangi hükümleri değiştirmiş?", size="sm")
            q3 = gr.Button("EK-20 tablosunu hangi belge içeriyor?", size="sm")
        samples = (
            (q1, "2024/39 belgesinde MADDE 4 ne diyor?"),
            (q2, "2025/42 tebliğinde 2024/39 için hangi değişikliklerden söz ediliyor?"),
            (q3, "2025/42 EK-20 tablosu hangi kaynakta ve hangi sayfada geçiyor?"),
        )
        for button, question in samples:
            button.click(
                lambda history, src, prompt=question: ask_assistant_filtered(
                    prompt, history, src,
                ),
                inputs=[chatbot, document_selector],
                outputs=[chat_input, chatbot],
            )

        with gr.Accordion("SSS kataloğu (belge kanıtı değildir)", open=False):
            gr.Markdown(
                "Sık sorulan sorular arama önerisidir; kesin kaynak alıntısı "
                "değildir. Bir satıra tıkladığınızda belge RAG motorunda arama yapılır."
            )
            faq_cat_dropdown = gr.Dropdown(
                choices=get_faq_categories(),
                value="Tümü",
                label="Kategori",
            )
            faq_search_input = gr.Textbox(label="SSS içinde ara")
            faq_df = gr.DataFrame(value=get_faq_table(), interactive=False)

            def filter_faq(cat: str, query: str) -> pd.DataFrame:
                return get_faq_table(cat, query)

            faq_cat_dropdown.change(
                filter_faq, inputs=[faq_cat_dropdown, faq_search_input],
                outputs=[faq_df],
            )
            faq_search_input.submit(
                filter_faq, inputs=[faq_cat_dropdown, faq_search_input],
                outputs=[faq_df],
            )

            def choose_faq(
                evt: gr.SelectData,
                df: pd.DataFrame,
                history: list[dict[str, str]],
            ) -> tuple[str, list[dict[str, str]]]:
                row = evt.index[0] if evt is not None and evt.index else -1
                if 0 <= row < len(df):
                    return ask_assistant(str(df.iloc[row]["Soru"]), history)
                return "", history

            faq_df.select(
                choose_faq,
                inputs=[faq_df, chatbot],
                outputs=[chat_input, chatbot],
            )

        # Keep the prior evaluation's optional claim inspector compatible
        # with frontend_pc.app; hide it from the focused RAG user journey.
        with gr.Accordion("İleri düzey kaynak kimliği", open=False, visible=False):
            faq_claim_selector = gr.Dropdown(choices=[], value=None)
            faq_claim_display = gr.HTML()

    return {
        "chatbot": chatbot,
        "chat_input": chat_input,
        "chat_submit": chat_submit,
        "chat_clear": chat_clear,
        "faq_df": faq_df,
        "faq_claim_selector": faq_claim_selector,
        "faq_claim_display": faq_claim_display,
    }
