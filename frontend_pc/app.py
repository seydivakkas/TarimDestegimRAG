"""TarımDestekRAG PC Gradio Arayüzü (5 Ana Kullanıcı Görevi & Ortak Değerlendirme Durumu).

Türkiye 2026 Bitkisel Üretim Destekleri Deterministik Karar ve Açıklama Asistanı.
UX Görev Mimarisi (Issue #6):
1. 🌱 Çiftçi & Parsellerim (Girdi, Profil ve Anlık Özet)
2. 📊 Destek Analizi (Kartlar + Formül + Kanıt Zinciri + Eksik Belge & Raporlama)
3. 💬 Mevzuat Asistanı (Sıfır LLM Doğrulanmış Soru-Cevap & SSS Rehberi)
4. 📅 Kaynaklar & Takvim (Başvuru Pencereleri, Resmî Kaynaklar ve Sürümleme)
5. ⚙️ Yönetim & Doğrulama (Rol Tabanlı Yönetici Araçları, 100 Benchmark Vakası ve Lisans)
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path
from typing import Any

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

import gradio as gr
import pandas as pd

# Proje kök dizinini ve backend/src dizinini sys.path'e ekle
_ROOT = Path(__file__).resolve().parent.parent
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))
_BACKEND_SRC = _ROOT / "backend" / "src"
if str(_BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(_BACKEND_SRC))

try:
    from frontend_pc.api_client import ApiClient
    from frontend_pc.formatters import (
        calculate_window_status,
        format_currency,
        parse_irrigation_status,
        parse_tri_state,
    )
    from frontend_pc.geo_data import TURKEY_DISTRICTS, TURKEY_PROVINCES
    from frontend_pc.pages.admin_validation import render_admin_validation_tab
    from frontend_pc.pages.farmer_parcels import (
        CROPS,
        DISTRICTS,
        PROVINCES,
        render_farmer_parcels_tab,
    )
    from frontend_pc.pages.legal_assistant import render_legal_assistant_tab
    from frontend_pc.pages.sources_calendar import render_sources_calendar_tab
    from frontend_pc.pages.support_analysis import render_support_analysis_tab
    from frontend_pc.services.benchmark_service import (
        get_benchmark_kpi_html,
        get_benchmark_summary,
        load_benchmark_data,
    )
    from frontend_pc.services.calendar_service import get_application_windows_table
    from frontend_pc.services.evaluation_service import (
        evaluate_farmer_parcel,
        evaluate_for_ui,
        generate_evaluation_report,
    )
    from frontend_pc.services.faq_service import (
        ask_assistant,
        get_faq_banner_text,
        get_faq_categories,
        get_faq_table,
    )
    from frontend_pc.services.sources_service import get_sources_table
    from frontend_pc.state import global_eval_state
    from frontend_pc.theme import CUSTOM_CSS, get_tarim_theme
except ModuleNotFoundError:
    from api_client import ApiClient  # type: ignore[no-redef]
    from formatters import (  # type: ignore[no-redef]
        calculate_window_status,
        format_currency,
        parse_irrigation_status,
        parse_tri_state,
    )
    from geo_data import TURKEY_DISTRICTS, TURKEY_PROVINCES  # type: ignore[no-redef]
    from pages.admin_validation import render_admin_validation_tab  # type: ignore[no-redef]
    from pages.farmer_parcels import (  # type: ignore[no-redef]
        CROPS,
        DISTRICTS,
        PROVINCES,
        render_farmer_parcels_tab,
    )
    from pages.legal_assistant import render_legal_assistant_tab  # type: ignore[no-redef]
    from pages.sources_calendar import render_sources_calendar_tab  # type: ignore[no-redef]
    from pages.support_analysis import render_support_analysis_tab  # type: ignore[no-redef]
    from services.benchmark_service import (  # type: ignore[no-redef]
        get_benchmark_kpi_html,
        get_benchmark_summary,
        load_benchmark_data,
    )
    from services.calendar_service import get_application_windows_table  # type: ignore[no-redef]
    from services.evaluation_service import (  # type: ignore[no-redef]
        evaluate_farmer_parcel,
        evaluate_for_ui,
        generate_evaluation_report,
    )
    from services.faq_service import (  # type: ignore[no-redef]
        ask_assistant,
        get_faq_banner_text,
        get_faq_categories,
        get_faq_table,
    )
    from services.sources_service import get_sources_table  # type: ignore[no-redef]
    from state import global_eval_state  # type: ignore[no-redef]
    from theme import CUSTOM_CSS, get_tarim_theme  # type: ignore[no-redef]

logger = logging.getLogger("frontend_pc")

# Global API İstemcisi
api_client = ApiClient()


def build_ui() -> gr.Blocks:
    """5 Kullanıcı Görevine İndirgenmiş Modern Gradio Arayüzünü İnşa Eder."""
    with gr.Blocks(title="TarımDestekRAG 2026") as app:
        # Üst Hero Header
        gr.HTML("""
        <div class="hero-header">
            <div style="display: flex; justify-content: space-between; align-items: center;">
                <div>
                    <h1>🌾 TarımDestekRAG — 2026 Bitkisel Üretim Destekleri</h1>
                    <p>Deterministik Kural Motoru, Doğrudan Resmî Atıflar ve Çiftçi Destek Karar Asistanı</p>
                    <span class="badge-tag">Kural Tabanlı Ön Değerlendirme &middot; Mevzuat Doğrulaması Devam Ediyor</span>
                </div>
                <div style="text-align: right; font-size: 0.9rem; opacity: 0.9;">
                    <div><b>Sürüm:</b> v1.0.0 (PC Sürümü)</div>
                    <div><b>Telif:</b> (c) 2026 Seydi Eryılmaz</div>
                </div>
            </div>
        </div>
        """)

        # Ortak Değerlendirme Durumu (Tüm sekmeler bu state'i paylaşır)
        eval_state = gr.State(value=None)

        with gr.Tabs():
            # 1. Görev: Çiftçi & Parsellerim
            p1 = render_farmer_parcels_tab()

            # 2. Görev: Destek Analizi (Kartlar + Formül + Mevzuat + Eksik Belge / Raporlama)
            p2 = render_support_analysis_tab()

            # 3. Görev: Mevzuat Asistanı
            p3 = render_legal_assistant_tab()

            # 4. Görev: Kaynaklar & Takvim
            p4 = render_sources_calendar_tab()

            # 5. Görev: Yönetim & Doğrulama (Rol Tabanlı)
            p5 = render_admin_validation_tab(api_client)

        # Girdi ve Çıktı Bağlantıları
        inputs_list = [
            p1["in_province"],
            p1["in_district"],
            p1["in_cks"],
            p1["in_age"],
            p1["in_gender"],
            p1["in_crop"],
            p1["in_area"],
            p1["in_irrigation"],
            p1["in_seed_cert"],
            p1["in_sapling_cert"],
            p1["in_orchard"],
        ]

        calc_outputs = [
            eval_state,
            p1["out_inline"],
            p2["out_kpi"],
            p2["out_cards"],
            p2["out_table"],
            p2["out_reasons"],
            p2["out_disclaimer"],
        ]

        def on_calculate_click(*args):
            return evaluate_for_ui(
                province=args[0],
                district=args[1],
                cks_status=args[2],
                age_group=args[3],
                gender=args[4],
                crop=args[5],
                area_da=args[6],
                irrigation_type=args[7],
                seed_cert=args[8],
                sapling_cert=args[9],
                closed_orchard=args[10],
                client=api_client,
            )

        # Değerlendirme Butonu Bağlantısı
        p1["btn_calculate"].click(
            on_calculate_click,
            inputs=inputs_list,
            outputs=calc_outputs,
        )

        # Hızlı Örnek Test Senaryoları
        p1["preset_1"].click(
            lambda: (
                "KONYA", "KARATAY", "✅ Evet (ÇKS Kaydım Aktif)", "Genç Çiftçi (< 41 Yaş)", "Erkek",
                "BUĞDAY", 25.0, "Kuru Tarım", "✅ Evet (Faturalı / Sertifikalı)", "❌ Hayır (Standart / Sertifikasız)", "Hayır (Münferit / Tarla)",
            ),
            outputs=inputs_list,
        ).then(on_calculate_click, inputs=inputs_list, outputs=calc_outputs)

        p1["preset_2"].click(
            lambda: (
                "SAMSUN", "ÇARŞAMBA", "✅ Evet (ÇKS Kaydım Aktif)", "Standart (41+ Yaş)", "Kadın Çiftçi",
                "FINDIK", 15.0, "Kuru Tarım", "❌ Hayır (Sertifikasız Tohum)", "✅ Evet (Faturalı / Sertifikalı)", "Evet (Kapama Bahçe)",
            ),
            outputs=inputs_list,
        ).then(on_calculate_click, inputs=inputs_list, outputs=calc_outputs)

        p1["preset_3"].click(
            lambda: (
                "KONYA", "KARATAY", "✅ Evet (ÇKS Kaydım Aktif)", "Standart (41+ Yaş)", "Erkek",
                "ARPA", 30.0, "Kuru Tarım", "✅ Evet (Faturalı / Sertifikalı)", "❌ Hayır (Standart / Sertifikasız)", "Hayır (Münferit / Tarla)",
            ),
            outputs=inputs_list,
        ).then(on_calculate_click, inputs=inputs_list, outputs=calc_outputs)

        p1["preset_4"].click(
            lambda: (
                "KONYA", "KARATAY", "✅ Evet (ÇKS Kaydım Aktif)", "Genç Çiftçi (< 41 Yaş)", "Erkek",
                "MERCİMEK", 20.0, "Kuru Tarım", "❌ Hayır (Sertifikasız Tohum)", "❌ Hayır (Standart / Sertifikasız)", "Hayır (Münferit / Tarla)",
            ),
            outputs=inputs_list,
        ).then(on_calculate_click, inputs=inputs_list, outputs=calc_outputs)

        p1["preset_5"].click(
            lambda: (
                "KONYA", "KARATAY", "❌ Hayır (ÇKS Kaydım Yok)", "Standart (41+ Yaş)", "Erkek",
                "BUĞDAY", 10.0, "Kuru Tarım", "❌ Hayır (Sertifikasız Tohum)", "❌ Hayır (Standart / Sertifikasız)", "Hayır (Münferit / Tarla)",
            ),
            outputs=inputs_list,
        ).then(on_calculate_click, inputs=inputs_list, outputs=calc_outputs)

        p1["preset_6"].click(
            lambda: (
                "KONYA", "KARATAY", "❓ Bilmiyorum / Emin Değilim", "Standart (41+ Yaş)", "Erkek",
                "BUĞDAY", 20.0, "Kuru Tarım", "❓ Bilmiyorum / Emin Değilim", "❌ Hayır (Standart / Sertifikasız)", "Hayır (Münferit / Tarla)",
            ),
            outputs=inputs_list,
        ).then(on_calculate_click, inputs=inputs_list, outputs=calc_outputs)

        # Resmî Ön Değerlendirme Raporu Oluşturma (Tekil State'ten beslenir, fazladan evaluate çağırmaz)
        def on_report_click(state_val, *args):
            return generate_evaluation_report(
                province=args[0],
                district=args[1],
                cks_status=args[2],
                age_group=args[3],
                gender=args[4],
                crop=args[5],
                area_da=args[6],
                irrigation_type=args[7],
                seed_cert=args[8],
                sapling_cert=args[9],
                closed_orchard=args[10],
                client=api_client,
                cached_resp=state_val,
            )

        p2["btn_report"].click(
            on_report_click,
            inputs=[eval_state] + inputs_list,
            outputs=[p2["file_report"]],
        )

    return app


if __name__ == "__main__":
    app_instance = build_ui()
    server_port = int(os.getenv("GRADIO_SERVER_PORT", "7860"))
    theme = get_tarim_theme()
    try:
        app_instance.launch(
            server_name="127.0.0.1",
            server_port=server_port,
            theme=theme,
            css=CUSTOM_CSS,
            share=False,
        )
    except OSError:
        logger.info("Port %s meşgul, otomatik olarak boş bir port seçiliyor...", server_port)
        app_instance.launch(
            server_name="127.0.0.1",
            theme=theme,
            css=CUSTOM_CSS,
            share=False,
        )
