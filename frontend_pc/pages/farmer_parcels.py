"""Sayfa 1: Çiftçi & Parsellerim (Girdi ve Profil Yönetimi)."""

from __future__ import annotations

import gradio as gr

from frontend_pc.geo_data import TURKEY_DISTRICTS, TURKEY_PROVINCES

PROVINCES = TURKEY_PROVINCES
DISTRICTS = TURKEY_DISTRICTS

CROPS = [
    "BUĞDAY", "ARPA", "MISIR", "AYÇİÇEĞİ", "PAMUK", "FINDIK",
    "MERCİMEK", "NOHUT", "SOYA", "ÇELTİK", "KANOLA", "ASPİR",
    "KURU FASULYE", "PATATES", "ZEYTİN", "YEM BİTKİLERİ"
]


def render_farmer_parcels_tab() -> dict[str, gr.components.Component]:
    """Çiftçi & Parsellerim sekmesini inşa eder ve bileşen sözlüğünü döner."""
    with gr.TabItem("🌱 Çiftçi & Parsellerim", id="tab_farmer_parcels"):
        with gr.Row():
            # Çiftçi Profili
            with gr.Column(scale=1):
                gr.Markdown("### 👤 1. Çiftçi Profili")
                in_province = gr.Dropdown(
                    label="İl",
                    choices=PROVINCES,
                    value="KONYA",
                    allow_custom_value=True,
                )
                in_district = gr.Dropdown(
                    label="İlçe",
                    choices=DISTRICTS["KONYA"],
                    value="KARATAY",
                    allow_custom_value=True,
                )

                def update_districts(prov: str):
                    choices = DISTRICTS.get(prov, ["MERKEZ"])
                    return gr.Dropdown(choices=choices, value=choices[0])

                in_province.change(
                    update_districts, inputs=[in_province], outputs=[in_district]
                )

                in_cks = gr.Radio(
                    label="Çiftçi Kayıt Sistemi (ÇKS) Durumu",
                    choices=[
                        "✅ Evet (ÇKS Kaydım Aktif)",
                        "❌ Hayır (ÇKS Kaydım Yok)",
                        "❓ Bilmiyorum / Emin Değilim",
                    ],
                    value="✅ Evet (ÇKS Kaydım Aktif)",
                )
                in_age = gr.Radio(
                    label="Yaş Durumu",
                    choices=["Genç Çiftçi (< 41 Yaş)", "Standart (41+ Yaş)"],
                    value="Genç Çiftçi (< 41 Yaş)",
                )
                in_gender = gr.Radio(
                    label="Cinsiyet",
                    choices=["Erkek", "Kadın Çiftçi"],
                    value="Erkek",
                )

            # Parsel & Ürün Bilgileri
            with gr.Column(scale=1):
                gr.Markdown("### 🚜 2. Parsel & Ürün Bilgisi")
                in_crop = gr.Dropdown(
                    label="Ekilmiş / Planlanan Ürün",
                    choices=CROPS,
                    value="BUĞDAY",
                    allow_custom_value=True,
                    filterable=True,
                )
                in_area = gr.Number(
                    label="Parsel Alanı (Dekar / da)",
                    value=25.0,
                    minimum=0.1,
                    maximum=10000.0,
                    step=1.0,
                )
                in_irrigation = gr.Radio(
                    label="Sulama Türü",
                    choices=["Kuru Tarım", "Sulu Tarım", "❓ Bilmiyorum / Emin Değilim"],
                    value="Kuru Tarım",
                )
                in_seed_cert = gr.Radio(
                    label="Sertifikalı Tohum Faturası / Beyanı",
                    choices=[
                        "✅ Evet (Faturalı / Sertifikalı)",
                        "❌ Hayır (Sertifikasız Tohum)",
                        "❓ Bilmiyorum / Emin Değilim",
                    ],
                    value="✅ Evet (Faturalı / Sertifikalı)",
                )
                in_sapling_cert = gr.Radio(
                    label="Sertifikalı Fidan Faturası / Beyanı",
                    choices=[
                        "✅ Evet (Faturalı / Sertifikalı)",
                        "❌ Hayır (Standart / Sertifikasız)",
                        "❓ Bilmiyorum / Emin Değilim",
                    ],
                    value="❌ Hayır (Standart / Sertifikasız)",
                )
                in_orchard = gr.Radio(
                    label="Kapama Meyve Bahçesi Tesisi",
                    choices=[
                        "Evet (Kapama Bahçe)",
                        "Hayır (Münferit / Tarla)",
                        "❓ Bilmiyorum / Emin Değilim",
                    ],
                    value="Hayır (Münferit / Tarla)",
                )

        gr.Markdown("#### ⚡ Hızlı Örnek Test Senaryoları (Tek Tıkla Otomatik Doldur & Hesapla)")
        with gr.Row():
            preset_1 = gr.Button("🌾 1. Konya Buğday (Genç, Tohum)", size="sm", variant="secondary")
            preset_2 = gr.Button("🌰 2. Samsun Fındık (Fidan, Bahçe)", size="sm", variant="secondary")
            preset_3 = gr.Button("🌾 3. Konya Arpa (Standart)", size="sm", variant="secondary")
            preset_4 = gr.Button("💧 4. Konya Mercimek (Su Kısıtı)", size="sm", variant="secondary")
            preset_5 = gr.Button("❌ 5. ÇKS Kaydı Yok (Ret)", size="sm", variant="secondary")
            preset_6 = gr.Button("❓ 6. Bilmiyorum / Eksik Bilgi", size="sm", variant="secondary")

        btn_calculate = gr.Button(
            "🎯 Destekleri ve Hak Edişi Hesapla",
            variant="primary",
            size="lg",
        )

        out_inline = gr.HTML(
            "<div style='margin-top: 16px; padding: 14px; background: #f8fafc; border: 1px dashed #cbd5e1; border-radius: 10px; color: #64748b; text-align: center;'>"
            "Bilgilerinizi girip yukarıdaki <b>'Destekleri ve Hak Edişi Hesapla'</b> butonuna basarak hak edişinizi hemen görebilirsiniz.</div>"
        )

    return {
        "in_province": in_province,
        "in_district": in_district,
        "in_cks": in_cks,
        "in_age": in_age,
        "in_gender": in_gender,
        "in_crop": in_crop,
        "in_area": in_area,
        "in_irrigation": in_irrigation,
        "in_seed_cert": in_seed_cert,
        "in_sapling_cert": in_sapling_cert,
        "in_orchard": in_orchard,
        "preset_1": preset_1,
        "preset_2": preset_2,
        "preset_3": preset_3,
        "preset_4": preset_4,
        "preset_5": preset_5,
        "preset_6": preset_6,
        "btn_calculate": btn_calculate,
        "out_inline": out_inline,
    }
