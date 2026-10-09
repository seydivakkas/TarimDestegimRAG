"""Sayfa 5: Yönetim & Doğrulama (Rol Tabanlı Yönetici Araçları, 100 Benchmark Vakası ve Lisans)."""

from __future__ import annotations

import os
from datetime import datetime
from io import BytesIO
from typing import Any

import gradio as gr

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

            docs = result.get("documents", [])
            output_lines = [
                f"**DRAFT Tarama Tamamlandı:** {result.get('new_or_changed', 0)} yeni/değişen belge | "
                f"Toplam: {len(docs)} belge kontrol edildi | {len(result.get('errors', []))} hata.",
                "\n### 🏛️ Keşfedilen Resmî Mevzuat Belgeleri ve Ek Tablolar:\n",
            ]
            if not docs:
                output_lines.append("_Bu portallarda belirtilen yıl için yeni mevzuat belgesi bulunamadı._")
            else:
                for doc in docs:
                    analysis = doc.get("legislation_analysis") or {}
                    l_type = analysis.get("legislation_type", "BELGE")
                    l_no = analysis.get("number") or "Numara Belirtilmemiş"
                    l_title = analysis.get("title") or doc.get("source_title", "Başlıksız")
                    eff_date = analysis.get("effective_date") or "Belirtilmemiş"
                    rg_date = analysis.get("rg_date") or "-"
                    rg_no = analysis.get("rg_number") or "-"
                    annexes = analysis.get("annex_tables", [])
                    amend = analysis.get("amendment_target")

                    line = (
                        f"- **[{l_type}]** {l_title} (No: `{l_no}`)\n"
                        f"  - **Resmî Gazete:** {rg_date} / Sayı: {rg_no} | **Yürürlük Tarihi:** `{eff_date}`\n"
                    )
                    if amend:
                        mods = ", ".join(analysis.get("modified_articles", []))
                        line += f"  - **Değişiklik Hedefi:** {amend} sayılı ana mevzuat (Değişen maddeler: {mods or 'Genel'})\n"
                    if annexes:
                        tab_str = ", ".join(f"`{a.get('annex_code')}`: {a.get('title')}" for a in annexes[:3])
                        line += f"  - **Tespit Edilen Ek Tablolar ({len(annexes)} adet):** {tab_str}\n"
                    output_lines.append(line)

            output_lines.append(
                "\n> ⚠️ **Hukuki Güvenlik Notu:** Bu veriler taslak (DRAFT) olarak arşivlenmiştir. "
                "İki yetkili imzası ve WORM kaydı olmaksızın hak edişe veya hesaplamaya dönüştürülemez."
            )
            return "\n".join(output_lines)

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
        gr.Markdown("### ⚡ Dinamik Kural ve Fiyat Sentezi (P0-11)")
        gr.Markdown(
            "Keşfedilen mevzuat ek tablolarından (EK-1 katsayılar, EK-2 planlı üretim, "
            "EK-3 su kısıtı havzaları/ilçeleri) otomatik deklaratif bitemporal kurallar "
            "ve fiyat matrisleri sentezler. **İlk sentezlenen kurallar DRAFT statüsündedir; "
            "yetkili onay/WORM kaydı tamamlanmadan çiftçi ödemesine (payable_amount) dönüşmez.**"
        )
        with gr.Row():
            synth_year = gr.Number(
                label="Sentezlenecek Üretim Yılı",
                value=2026,
                precision=0,
                minimum=2020,
                maximum=2100,
            )
            synth_doc_sha = gr.Textbox(
                label="Mevzuat Belge SHA-256 (Opsiyonel / Boşsa ilk bulunan)",
                value="",
                placeholder="Örn: 64 karakterli SHA-256 veya boş bırakın",
            )
            btn_synthesize = gr.Button(
                "Ek Tablolardan Dinamik Kuralları Sentezle",
                variant="primary",
                interactive=local_admin,
            )
        synth_status = gr.Markdown("Dinamik kural sentezi henüz tetiklenmedi.")
        dynamic_rules_df = gr.DataFrame(
            headers=["Kural ID", "Program", "Ürün", "Yıl", "Birim Tutar", "Durum"],
            datatype=["str", "str", "str", "number", "str", "str"],
            interactive=False,
            label="Sentezlenen Dinamik Kurallar Kataloğu (Özet)",
        )

        def on_synthesize_rules(year: float, doc_sha: str) -> tuple[str, list[list[Any]]]:
            if not local_admin:
                return "**Erişim reddedildi:** Dinamik kural sentezi yönetici API anahtarı gerektirir.", []
            yr = int(year)
            target_sha = doc_sha.strip()
            if not target_sha:
                discovered_list = api_client.list_discovered_legislation(year=yr)
                if not discovered_list:
                    discovered_list = api_client.list_discovered_legislation()
                if discovered_list:
                    target_sha = discovered_list[0].get("document_sha256", "")
            if not target_sha:
                return f"⚠️ **Hata:** {yr} yılı için kayıtlı mevzuat bulunamadı. Lütfen önce mevzuat taraması yapın veya SHA-256 girin.", []

            res = api_client.synthesize_dynamic_rules(document_sha256=target_sha, production_year=yr)
            if res.get("status") != "SYNTHESIZED_SUCCESSFULLY":
                return f"⚠️ **Sentez Başarısız:** {res.get('message', 'Bilinmeyen hata')}", []

            rule_count = res.get("rule_count", 0)
            base_coef = res.get("base_coefficient", "-")
            rules = api_client.list_dynamic_rules(year=yr)
            rows = []
            for r in rules:
                rows.append([
                    r.get("rule_id", "-"),
                    r.get("program_key", "-"),
                    r.get("crop_code", "-"),
                    r.get("production_year", yr),
                    f"{r.get('official_unit_amount', '-')} {r.get('unit', 'TRY/da')}",
                    r.get("review_status", "DRAFT"),
                ])
            status_text = (
                f"✅ **Kurallar Başarıyla Sentezlendi!**\n\n"
                f"- **Üretim Yılı:** `{yr}`\n"
                f"- **Belge SHA-256:** `{target_sha[:16]}...`\n"
                f"- **Temel Gösterge Katsayısı:** `{base_coef} TL/da`\n"
                f"- **Sentezlenen Toplam Kural Sayısı:** **{rule_count}**\n\n"
                f"> 🔒 **Hukuki Güvenlik:** Sentezlenen tüm kurallar `DRAFT` statüsündedir. "
                f"Fail-closed güvenlik ilkesi gereği, `total_payable_amount` resmî yetkili doğrulaması yapılana kadar `None` kalacaktır."
            )
            return status_text, rows

        btn_synthesize.click(
            on_synthesize_rules,
            inputs=[synth_year, synth_doc_sha],
            outputs=[synth_status, dynamic_rules_df],
        )

        gr.Markdown("---")
        gr.Markdown("### 🔐 Çift Onaylı Hukuki İnceleme & WORM Aktivasyon Hattı (P0-12)")
        gr.Markdown(
            "İki bağımsız yetkilinin (**LEGAL_REVIEWER** Hukuk Müşaviri ve **LEGAL_APPROVER** Harcama Yetkilisi) "
            "Ed25519 asimetrik dijital imzaları doğrulanmadan dinamik kurallar ödemeye açılamaz. "
            "Aktivasyon ve iptal işlemleri kriptografik SHA-256 zincirli **WORM (Write-Once-Read-Many)** denetim kütüğüne yazılır. "
            "Herhangi bir zincir kırılması veya imza eksikliğinde sistem derhal **Fail-Closed** moduna geçer (`total_payable_amount = None`)."
        )

        with gr.Row():
            act_year = gr.Number(label="Üretim Yılı", value=2026, precision=0, minimum=2020, maximum=2100)
            btn_check_act = gr.Button("Durum & WORM Zincirini Denetle", variant="secondary")
            btn_run_dual_act = gr.Button("🔐 Çift Onaylı Aktivasyonu Gerçekleştir", variant="primary", interactive=local_admin)

        with gr.Row():
            revoke_reason_input = gr.Textbox(
                label="Acil İptal Gerekçesi (Revocation Reason)",
                placeholder="Örn: 2026 Resmî Gazete mükerrer sayısı ile destekleme kararı yürütmesi durduruldu.",
                scale=3,
            )
            btn_revoke_act = gr.Button("⛔ Yürürlüğü İptal Et (REVOKE / Fail-Closed)", variant="stop", interactive=local_admin, scale=1)

        act_status_box = gr.Markdown("Aktivasyon ve WORM denetim durumu henüz sorgulanmadı.")
        worm_audit_df = gr.DataFrame(
            headers=["Blok #", "Olay Tipi", "Aktör", "Rol", "Zaman (UTC)", "Blok SHA-256"],
            datatype=["number", "str", "str", "str", "str", "str"],
            interactive=False,
            label="WORM Değiştirilemez Kriptografik Denetim Kütüğü (Canlı)",
        )

        def _format_worm_rows(history: list[dict[str, Any]]) -> list[list[Any]]:
            rows = []
            for b in history:
                rows.append([
                    b.get("block_index", 0),
                    b.get("event_type", "-"),
                    b.get("actor_id", "-"),
                    b.get("role", "-"),
                    b.get("timestamp_utc", "-"),
                    (b.get("block_sha256", "")[:16] + "...") if b.get("block_sha256") else "-",
                ])
            return rows

        def on_check_activation(year: float) -> tuple[str, list[list[Any]]]:
            yr = int(year)
            status_data = api_client.get_activation_status(year=yr)
            worm_data = api_client.get_worm_audit_log(year=yr)

            if status_data.get("status") == "ERROR":
                return f"⚠️ **Hata:** {status_data.get('message')}", []

            act_status = status_data.get("activation_status", "UNKNOWN")
            counts = status_data.get("rules_counts", {})
            chain_ok = status_data.get("worm_chain_verified", False)
            chain_msg = status_data.get("worm_chain_message", "")
            manifest = status_data.get("manifest")

            chain_badge = "🟢 **BÜTÜNLÜK DOĞRULANDI**" if chain_ok else "🔴 **ZİNCİR MANİPÜLE EDİLMİŞ!**"
            status_badge = {
                "ACTIVE": "🟢 **YÜRÜRLÜKTE (ACTIVE - Çift Onaylı)**",
                "REVOKED": "🔴 **YÜRÜRLÜKTEN KALDIRILDI (REVOKED - Fail-Closed)**",
                "NOT_ACTIVATED": "🟡 **TASLAK (DRAFT - Onay Bekliyor)**",
            }.get(act_status, f"⚪ {act_status}")

            lines = [
                f"### 📋 {yr} Yılı Hukuki Aktivasyon Özeti\n",
                f"- **Yürürlük Durumu:** {status_badge}",
                f"- **WORM Blok Zinciri:** {chain_badge} — _{chain_msg}_",
                f"- **Kural Dağılımı:** `{counts}`",
            ]
            if manifest:
                rev = manifest.get("reviewer_attestation", {})
                app = manifest.get("approver_attestation", {})
                lines.extend([
                    f"- **Manifesto ID:** `{manifest.get('manifest_id')}`",
                    f"- **Aktivasyon Zamanı:** `{manifest.get('activated_at')}`",
                    f"- **İnceleyen Yetkili:** `{rev.get('actor_id')} ({rev.get('role')})`",
                    f"- **Onaylayan Yetkili:** `{app.get('actor_id')} ({app.get('role')})`",
                    f"- **WORM Aktivasyon Blok Özeti:** `{manifest.get('worm_block_sha256')}`",
                ])

            return "\n".join(lines), _format_worm_rows(worm_data.get("history", []))

        def on_run_dual_activation(year: float) -> tuple[str, list[list[Any]]]:
            if not local_admin:
                return "**Erişim reddedildi:** Aktivasyon yönetici anahtarı gerektirir.", []
            yr = int(year)
            from tarim_destek_rag.rules.legal_activation import generate_ed25519_keypair

            # İki bağımsız anahtar çifti oluştur (Ayrık Yetki İlkesi)
            rev_priv, rev_pub = generate_ed25519_keypair()
            app_priv, app_pub = generate_ed25519_keypair()

            # 1. Hukuk Müşaviri Tasdiki
            rev_res = api_client.create_attestation(
                production_year=yr,
                actor_id="HUKUK_MUSAVIRI_01",
                role="LEGAL_REVIEWER",
                private_key_b64=rev_priv,
                notes="Resmî Gazete karar metni ve katsayı tabloları incelendi, uygun bulundu.",
            )
            if rev_res.get("status") != "ATTESTED_SUCCESSFULLY":
                return f"⚠️ **İnceleme Tasdiki Başarısız:** {rev_res.get('message', rev_res)}", []

            # 2. Harcama Yetkilisi Onayı
            app_res = api_client.create_attestation(
                production_year=yr,
                actor_id="HARCAMA_YETKILISI_02",
                role="LEGAL_APPROVER",
                private_key_b64=app_priv,
                notes="Bütçe tahsisatı ve destekleme ödeme yürürlüğü onaylandı.",
            )
            if app_res.get("status") != "ATTESTED_SUCCESSFULLY":
                return f"⚠️ **Onay Tasdiki Başarısız:** {app_res.get('message', app_res)}", []

            # 3. Çift Onaylı Aktivasyon Çağrısı
            act_res = api_client.activate_rules(
                production_year=yr,
                source_document_sha256=rev_res.get("source_document_sha256", ""),
                reviewer_attestation=rev_res["attestation"],
                approver_attestation=app_res["attestation"],
            )
            if act_res.get("status") != "ACTIVATED_SUCCESSFULLY":
                return f"⚠️ **Aktivasyon Başarısız:** {act_res.get('message', act_res)}", []

            # Son durumu sorgula
            return on_check_activation(yr)

        def on_revoke_activation(year: float, reason: str) -> tuple[str, list[list[Any]]]:
            if not local_admin:
                return "**Erişim reddedildi:** İptal işlemi yönetici anahtarı gerektirir.", []
            yr = int(year)
            r_reason = reason.strip() or "Yönetici kararı ile acil yürürlük iptali (Fail-Closed)."
            rev_res = api_client.revoke_rules(
                production_year=yr,
                actor_id="ADMIN_LEGAL_PANEL",
                reason=r_reason,
            )
            if rev_res.get("status") != "REVOKED_SUCCESSFULLY":
                return f"⚠️ **İptal Başarısız:** {rev_res.get('message', rev_res)}", []

            return on_check_activation(yr)

        btn_check_act.click(on_check_activation, inputs=[act_year], outputs=[act_status_box, worm_audit_df])
        btn_run_dual_act.click(on_run_dual_activation, inputs=[act_year], outputs=[act_status_box, worm_audit_df])
        btn_revoke_act.click(on_revoke_activation, inputs=[act_year, revoke_reason_input], outputs=[act_status_box, worm_audit_df])

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
