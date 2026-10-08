"""Sayfa 5: Yönetim & Doğrulama (Rol Tabanlı Yönetici Araçları, 100 Benchmark Vakası ve Lisans)."""

from __future__ import annotations

import gradio as gr
import pandas as pd

from frontend_pc.api_client import ApiClient
from frontend_pc.services.benchmark_service import (
    get_benchmark_kpi_html,
    get_benchmark_summary,
    load_benchmark_data,
)


def render_admin_validation_tab(api_client: ApiClient) -> dict[str, gr.components.Component]:
    """Yönetim & Doğrulama sekmesini inşa eder ve bileşen sözlüğünü döner."""
    with gr.TabItem("⚙️ Yönetim & Doğrulama", id="tab_admin_validation"):
        gr.Markdown("### 🌾 Tarımsal Soru-Cevap Bilgi Tabanı Web Harvester & Doğrulama Paneli")
        gr.Markdown("""
        Tarım ve Orman Bakanlığı, BÜGEM, TAGEM Zirai Mücadele, TARSİM Sigortası, TKDK IPARD ve Ziraat Odaları gibi resmî kurumsal
        portallardan soru-cevap veri setini çeker, SQLite veritabanına işler ve arama vektör indeksine (Hybrid BM25 + FAISS) canlı entegre eder.
        """)
        with gr.Row():
            btn_harvest_faqs = gr.Button("Yerleşik SSS Verisini Yenile (Yönetici)", variant="secondary", interactive=False)
        harvest_status_box = gr.Markdown(
            "**Bilgi:** Web üzerinden canlı SSS taraması moderasyon hattı ile korunmaktadır. "
            "Yerleşik örnek veriyi yeniden yükleyen yönetici API'si yetkilendirme anahtarı gerektirir."
        )

        def on_harvest_click() -> str:
            res = api_client.harvest_faqs()
            if res.get("status") == "SUCCESS":
                cnt = res.get("harvested_count", 0)
                tot = res.get("total_faqs_in_db", 0)
                return f"✅ **Senkronizasyon Başarılı:** {cnt} yeni soru-cevap veritabanına işlendi ve RAG indeksine eklendi! (Toplam Veritabanı: **{tot} SSS**)."
            return f"⚠️ **Bilgi:** {res.get('message', 'İşlem tamamlandı.')}"

        btn_harvest_faqs.click(on_harvest_click, outputs=[harvest_status_box])

        gr.Markdown("---")
        gr.Markdown("""
        ### 🧪 Deterministik Kural Motoru Benchmark Test Seti (100 Vaka)
        100 farklı çiftçi/parsel senaryosunda (ÇKS eksikliği, havza uyumsuzluğu, sertifikasız tohum vb.)
        bu bölüm kaydedilmiş test çıktılarını gösterir. Mevzuatla bağımsız uyum doğrulaması için benchmark koşucusu çalıştırılmalıdır.
        """)
        bench_df = gr.DataFrame(value=load_benchmark_data(), interactive=False)
        bench_kpi = gr.HTML(value=get_benchmark_kpi_html())
        bench_summary = gr.Markdown(get_benchmark_summary())

        gr.Markdown("""
        ---
        ### 🏛️ TarımDestekRAG Sistem Mimarisi & Güvenlik Prensipleri
        - **Sıfır LLM (Zero-LLM Güvencesi):** Hak ediş ve karar aşamalarında üretici model kullanılmaz; kararlar `%100` deterministik Python kural motoru (`rules_impl.py`) tarafından yürütülür. Deterministik çıktının mevzuatla doğruluğu bağımsız testlerle düzenli denetlenir.
        - **Hassas Finansal Matematik:** Tüm parasal destek hesaplamaları Python `decimal.Decimal` ile kuruş hassasiyetinde yapılır. Kayan nokta yuvarlama hatası bulunmaz.
        - **Kaynak Provenansı ve Denetim:** Resmî Gazete, BÜGEM ve DSİ yasal metinleri baz alınır. Her kaynak URL'si ve doküman hash kontrolüyle izlenir.
        - **Belge İçi Renkli İşaretleme Sistemi:** Hak kazanma hükümleri 🟢 yeşil, ret ve yasak hükümleri 🔴 kırmızı, birim tutarlar 🟡 kehribar ve yasal merciler 🔵 mavi ile işaretlenerek mutlak şeffaflık sağlanır.
        - **Hibrit Arama Motoru:** `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2` + `FAISS` ve `BM25Plus` ile Reciprocal Rank Fusion birleşimi (MRR=1.0000).
        - **Çok Platformlu Mimari:** Arka uç FastAPI bağımsız REST API olarak çalışır; PC Paneli ve Flutter mobil istemcisi aynı çekirdeği paylaşır.

        ---
        ### 📜 Telif Hakkı ve Lisans Bildirimi
        ```
        ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
        Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)

        Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
        amaçlı olarak paylaşılmıştır.

        YASAKLAR:
          1. Kopyalanamaz, çoğaltılamaz, dağıtılamaz veya yeniden yayınlanamaz.
          2. Ticari veya ticari olmayan hiçbir projede kullanılamaz, değiştirilemez.
          3. Alt lisanslanamaz, satılamaz veya devredilemez.
          4. Tersine mühendislik yapılamaz.

        İZİN VERİLEN KULLANIM:
          - GitHub üzerinde görüntüleme ve okuma.
          - Kişisel öğrenim amacıyla kodu inceleme (kopyalamadan).

        YAZARIN AÇIK YAZILI İZNİ OLMAKSIZIN HİÇBİR KULLANIM HAKKI TANINMAZ.
        İzin talepleri için: GitHub @seydivakkas
        ```
        """)

    return {
        "bench_df": bench_df,
        "bench_kpi": bench_kpi,
        "bench_summary": bench_summary,
        "btn_harvest_faqs": btn_harvest_faqs,
        "harvest_status_box": harvest_status_box,
    }
