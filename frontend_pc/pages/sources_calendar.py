"""Sayfa 4: Kaynaklar & Takvim (Başvuru Pencereleri, Resmî Kaynaklar ve Sürümleme)."""

from __future__ import annotations

import gradio as gr
import pandas as pd

from frontend_pc.services.calendar_service import get_application_windows_table
from frontend_pc.services.sources_service import get_sources_table


def render_sources_calendar_tab() -> dict[str, gr.components.Component]:
    """Kaynaklar & Takvim sekmesini inşa eder ve bileşen sözlüğünü döner."""
    with gr.TabItem("📅 Kaynaklar & Takvim", id="tab_sources_calendar"):
        gr.Markdown("### 📅 2026 Resmî Başvuru Takvimi & Açık Destek Pencereleri")
        windows_df = gr.DataFrame(value=get_application_windows_table(), interactive=False)

        gr.Markdown("---")
        gr.Markdown("### 📡 Takip Edilen Resmî Mevzuat Kaynakları (Kazıyıcı / Scraper)")
        sources_df = gr.DataFrame(value=get_sources_table(), interactive=False)
        with gr.Row():
            btn_refresh_sources = gr.Button("🔄 Kaynakları Yenile", size="sm")
        btn_refresh_sources.click(get_sources_table, outputs=[sources_df])

        gr.Markdown("""
        #### 🔄 Otomatik Değişiklik Algılama & Hash Sistemi
        - Her resmî kaynak URL'si düzenli aralıklarla kontrol edilir.
        - İçerik SHA-256 kanonik hash'i alınarak sürüm tablosuna kaydedilir (`source_versions`).
        - Mevzuat değiştiğinde sistem uyarı üretir ve değişiklik logu tutar.
        - Tüm kaynak bağlantıları şeffaf, güvenli ve doğrudan resmî devlet portallarına (`resmigazete.gov.tr`, `tarimorman.gov.tr`) açılır.
        """)

    return {
        "windows_df": windows_df,
        "sources_df": sources_df,
        "btn_refresh_sources": btn_refresh_sources,
    }
