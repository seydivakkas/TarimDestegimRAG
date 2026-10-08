"""Sayfa 5: Yönetim & Doğrulama (Rol Tabanlı Yönetici Araçları, 100 Benchmark Vakası ve Lisans)."""

from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO

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

        gr.Markdown("### Gelecek Yıl Mevzuat Kontrolü (DRAFT)")
        gr.Markdown(
            "Resmî kaynaklardan yeni/değişen belgeleri arşivler; **onaysız "
            "katsayıları, ilçe listelerini ve hak edişleri etkinleştirmez**. "
            "Bilinen portal bağlantıları taranır; eksiksiz mevzuat kapsamı iddia edilmez."
        )
        local_admin = (
            os.getenv("TARIM_RAG_LOCAL_UPDATES_ENABLED") == "true"
            and bool(os.getenv("TARIM_RAG_ADMIN_API_KEY"))
            and api_client.base_url.startswith(("http://127.0.0.1:", "http://localhost:"))
        )
        with gr.Row():
            legal_year = gr.Number(
                label="Hedef üretim yılı", value=datetime.now().year,
                precision=0, minimum=2020, maximum=2100,
            )
            btn_scan_year = gr.Button(
                "Resmî Mevzuatı Kontrol Et",
                variant="secondary",
                interactive=local_admin,
            )
        scan_status = gr.Markdown(
            "Yönetici taraması varsayılan kapalıdır. Yalnız yerel oturumda "
            "TARIM_RAG_LOCAL_UPDATES_ENABLED=true ve yönetici API anahtarıyla açılır."
        )

        def on_scan_year(year: float) -> str:
            if not local_admin:
                return "**Erişim reddedildi:** Güncelleme taraması bu oturumda kapalı."
            result = api_client.scan_legal_updates(int(year))
            if result.get("status") in ("ERROR", "ADMIN_NOT_CONFIGURED"):
                return "**Tarama çalışmadı:** " + str(result.get("message", ""))
            return (
                f"**DRAFT tarama:** {result.get('new_or_changed', 0)} yeni/değişen belge; "
                f"{len(result.get('documents', []))} kontrol; "
                f"{len(result.get('errors', []))} hata. "
                "Destek fiyatları ve koşulları **güncellenmedi**."
            )
        btn_scan_year.click(on_scan_year, inputs=[legal_year], outputs=[scan_status])

        gr.Markdown("#### PDF Cümlesinin Gerçek Sayfasını Göster (Onaysız Kanıt)")
        with gr.Row():
            evidence_id = gr.Number(label="Kaydedilmiş cümle ID", value=1, precision=0, minimum=1)
            btn_evidence = gr.Button("Sarı İşaretli Sayfayı Göster", variant="secondary")
        evidence_status = gr.Markdown(
            "Yalnız SHA-256 doğrulanmış belge/cümle eşleşmesi gösterilir; "
            "hukukî yürürlük veya çiftçi hak edişi onayı değildir."
        )
        evidence_image = gr.Image(
            label="Orijinal PDF sayfası — birebir cümle sarı işaretli",
            type="pil", interactive=False,
        )

        def view_evidence(record_id: float, year: float):
            from PIL import Image

            data = api_client.get_grounding_evidence(int(record_id), int(year))
            if data.get("status") != "DRAFT_NEEDS_HUMAN_LEGAL_REVIEW":
                return "**Kanıt bulunamadı veya henüz doğrulanmadı.**", None
            raw = api_client.get_grounding_page_bytes(
                int(record_id), int(data["page_number"]), int(year)
            )
            if not raw:
                return "**Orijinal PDF sayfası doğrulanamadı.**", None
            with Image.open(BytesIO(raw)) as rendered:
                rendered.load()
                picture = rendered.copy()
            # Render as plain text (not unescaped HTML) to avoid injecting
            # source document content into the local admin view.
            return (
                f"**DRAFT — Hukukî onay bekliyor** | Sayfa {data['page_number']} "
                f"| SHA-256 `{data['original_pdf_sha256']}`"
                f"\n\n**Birebir cümle:** {data['exact_quote']}",
                picture,
            )
        btn_evidence.click(
            view_evidence, inputs=[evidence_id, legal_year],
            outputs=[evidence_status, evidence_image],
        )

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
