"""Sayfa 2: Destek Analizi (Kartlar, Formül, Mevzuat Gerekçesi, Eksik Belgeler ve Raporlama)."""

from __future__ import annotations

import gradio as gr
import pandas as pd

from tarim_destek_rag.citations.document_links import render_document_viewer_html


def render_support_analysis_tab() -> dict[str, gr.components.Component]:
    """Destek Analizi sekmesini inşa eder ve bileşen sözlüğünü döner."""
    with gr.TabItem("📊 Destek Analizi", id="tab_support_analysis"):
        out_kpi = gr.HTML(
            "<div class='kpi-container'><div class='kpi-card'><div class='kpi-title'>Tahmini Destek</div><div class='kpi-value'>Hesaplama Bekleniyor</div></div></div>"
        )
        out_cards = gr.HTML(
            "<p style='color: #64748b;'>Lütfen 'Çiftçi & Parsellerim' sekmesinden bilgilerinizi girip 'Destekleri ve Hak Edişi Hesapla' butonuna tıklayınız.</p>"
        )

        with gr.Accordion("📊 Destek Kalemleri Detay Tablosu (Birim Fiyatlar & Formüller)", open=True):
            out_table = gr.DataFrame(
                headers=[
                    "Destek Programı",
                    "Durum",
                    "Birim Fiyat (TL/da)",
                    "Alan (da)",
                    "Tahmini Tutar",
                    "Hesaplama Formülü",
                    "Başvuru Dönemi",
                    "Dayanak",
                ],
                datatype=["str", "str", "str", "str", "str", "str", "str", "str"],
                interactive=False,
            )

        with gr.Accordion("⚖️ Kanıt Zinciri & Renkli Resmî Gazete Madde Önizleme (Neden?)", open=True):
            gr.Markdown(
                "**Özgün sayfa görüntüsü:** Belge dosyası SHA-256 ile doğrulanmadan "
                "hiçbir sayfa gösterilmez. Metin katmanı/OCR sonucunun doğruluğu "
                "ayrı inceleme gerektirir; otomatik hak ediş onayı yoktur."
            )
            out_reasons = gr.Markdown(
                "Buradaki hesaplama açıklamaları resmî alıntı değildir; "
                "hukukî kaynak bağlantıları bağımsız olarak doğrulanmalıdır."
            )
            gr.Markdown(
                "**Gerekçeden birebir kaynağa:** Hesaplamadan sonra tek bir "
                "şartı seçin. Sistem kural kimliği + şartın kelimesi kelimesine "
                "metni + üretim yılı eşleşmeden alıntı göstermeyecek. "
                "Eşleşse bile hukukî ve olgusal kabul HOLD kalır."
            )
            claim_selector = gr.Dropdown(
                choices=[],
                value=None,
                label="Tekil kural gerekçesini seç — Neden?",
                interactive=True,
            )
            btn_claim_show = gr.Button("Bu gerekçenin özgün hükmünü göster")
            claim_display = gr.HTML(
                value="<p>Hesaplama sonucundaki tekil gerekçeler "
                "burada seçilebilir. Kaynağı olmayanlar HOLD kalır.</p>"
            )
            with gr.Accordion(
                "Seçilen gerekçeyi özgün PDF/HTML arşivinde araştır — aday/HOLD",
                open=True,
            ):
                gr.Markdown(
                    "Her gerekçe, metni ve mevcut indekslenmiş gerçek belge "
                    "pasajları üzerinden ayrıca araştırılabilir. "
                    "**ÖNEMLİ:** Bu arama sonucu bir kanunun o şartı "
                    "düzenlediğini veya seçilen yılda yürürlükte olduğunu "
                    "ispatlamaz. Kesin birebir madde bağları yalnız üstteki "
                    "doğrulanmış kanıt panelinde gösterilir. "
                    "Kaynak adayı için orijinal PDF sayfası veya HTML "
                    "paragrafı turuncu renkle incelenir; sarı onay verilmez."
                )
                btn_claim_source_search = gr.Button(
                    "Bu tekil gerekçe için özgün belgelerde kaynak araştır",
                    variant="secondary",
                )
                claim_candidate_status = gr.Markdown(
                    "Kaynak adayı araması yapılmadı. "
                    "Önce gerekçeyi seçin, sonra aramayı başlatın."
                )
                claim_candidate_selector = gr.Dropdown(
                    choices=[], value=None, interactive=True,
                    label="Gerçek PDF/HTML kaynak adayları — onaysız",
                )
                claim_candidate_state = gr.State({
                    "claim_id": None, "candidates": [],
                })
                claim_candidate_display = gr.HTML(
                    "<p>Kaynak adayı seçilmedi. Özgün PDF bulunamıyorsa "
                    "yanlış sayfa veya hücre üretilmez: HOLD.</p>"
                )

            with gr.Accordion("Tüm gerekçeler için kanıt-konum kapsamı (HOLD)", open=False):
                gr.Markdown(
                    "Bu liste yalnız bu değerlendirmede hangi şartın özgün "
                    "madde konumuna bağlandığını sayar. Hukukî yıl veya ödeme "
                    "PASS oranı değildir."
                )
                btn_claim_coverage = gr.Button(
                    "Bu değerlendirmedeki eşleşmeyen kanıtları listele",
                    variant="secondary",
                )
                claim_coverage_display = gr.HTML(
                    "<p>Önce değerlendirme yapın; ardından kaynak kapsamını inceleyin.</p>"
                )


            from tarim_destek_rag.citations.pdf_page_indexer import (
                get_page_dropdown_choices,
                render_evidence_by_key,
                render_ocr_page_by_key,
            )

            gr.Markdown(
                "Yalnız **gerçek arşiv dosyasından çıkarılmış sayfalar** listelenir. "
                "Metin araması, doğrulanmamış OCR üzerinden tahmini sayfa üretmez."
            )
            with gr.Row():
                article_selector = gr.Dropdown(
                    choices=get_page_dropdown_choices(),
                    value=None,
                    label="Özgün PDF / gerçek sayfa",
                    scale=7,
                )
                page_search_input = gr.Textbox(
                    placeholder="Kaynak metin katmanında ara; bulunamazsa HOLD",
                    label="Kaynak içinde ara",
                    scale=4,
                )
                btn_page_search = gr.Button("Gerçek sayfayı göster", scale=2)

            article_display = gr.HTML(
                value="<p>Henüz kaynak kanıtı seçilmedi. "
                "Belge arşivi yoksa sayfa gösterilmez.</p>"
            )
            from tarim_destek_rag.citations.source_region_viewer import (
                page_region_choices,
                render_source_region,
            )

            gr.Markdown(
                "**Sayfa içi yakınlaştırma:** Gerçek PDF'den tespit edilen tablo, "
                "görsel veya çizim bölgelerini özgün koordinatlarıyla büyütün. "
                "Bölgenin hukukî ve sayısal anlamı ayrıca incelenmelidir."
            )
            region_selector = gr.Dropdown(
                choices=[],
                value=None,
                label="Gerçek sayfadaki tablo / görsel / çizim bölgesi",
                interactive=True,
            )
            region_display = gr.HTML(
                value="<p>Bir sayfa ve sayfa içi görsel bölge seçin.</p>"
            )
            from tarim_destek_rag.citations.raster_table_review import (
                raster_cell_choices,
                render_raster_cell,
            )

            gr.Markdown(
                "**Taranmış PDF'nin gerçek piksel hücreleri:** Sayfa seçip "
                "görüntü tablosunu isteğe bağlı tarayın. Yalnız sürekliliği "
                "ölçülen gerçek ızgara çizgileri arasındaki hücre adayları "
                "listelenir. Kenarlıksız veya belirsiz tabloda tahmini "
                "hücre oluşturulmaz. Turuncu çerçeve hukukî sarı vurgu değildir."
            )
            btn_raster_scan = gr.Button(
                "Seçili gerçek PDF sayfasında tablo hücresi adaylarını bul",
                variant="secondary",
            )
            raster_cell_selector = gr.Dropdown(
                choices=[],
                value=None,
                interactive=True,
                label="Gerçek görüntüden ölçülen hücre (OCR ve mevzuat HOLD)",
            )
            raster_cell_display = gr.HTML(
                "<p>Önce gerçek sayfayı seçip hücre adaylarını tarayın. "
                "Yoksa koordinat tahmin edilmeyecek.</p>"
            )

            from tarim_destek_rag.citations.ek20_review_workbench import (
                ek20_cell_choices,
                render_ek20_candidate,
            )

            gr.Markdown(
                "**2026 EK-20 tablo satır/hücre incelemesi:** Sol tarafta "
                "satır/sütun taslak aktarımı, altında özgün tek sayfalık "
                "resmî PDF görüntüsü. Değerler ödeme için kullanılmaz."
            )
            ek20_selector = gr.Dropdown(
                choices=ek20_cell_choices(),
                value=None,
                label="EK-20 ürün/etmen ve destek hücresi (taslak, HOLD)",
                interactive=True,
            )
            ek20_display = gr.HTML(
                value="<p>EK-20 hücresi seçildiğinde özgün tablo "
                "görüntüsüyle karşılaştırılabilir.</p>"
            )

            from tarim_destek_rag.citations.ek20_cell_provenance import (
                render_ek20_review_coverage,
                render_candidate_roi,
            )


            with gr.Accordion(
                "EK-20 piksel koordinatı öner ve gerçek sayfada önizle (HOLD)",
                open=False,
            ):
                gr.Markdown(
                    "180 DPI özgün PDF sayfasındaki x0, y0, x1, y1 tam piksel "
                    "koordinatlarını girin. Bu işlem bir ROI adayı gösterir; "
                    "bağımsız iki incelemeci imzası veya hukukî onay vermez."
                )
                from tarim_destek_rag.citations.ek20_raster_alignment import (
                    measured_ek20_cell_choices,
                )

                gr.Markdown(
                    "**Özgün PDF'den ölçülen kutuyu seç:** EK-20 sayfasında "
                    "gerçek ve tam çizgili ızgara bulunursa hücre adaylarını "
                    "listeleyebilirsiniz. Ürün-sütun kaydını ve fiziksel "
                    "kutuyu ayrı ayrı, kendiniz seçmelisiniz. Bağlantı "
                    "sadece ROI ön taslağıdır. Tam ızgara yoksa manuel "
                    "koordinat girişi kullanılabilir; tahmin yapılmaz."
                )
                btn_ek20_grid_scan = gr.Button(
                    "EK-20 özgün sayfasındaki ölçülmüş ızgara hücrelerini getir",
                    variant="secondary",
                )
                ek20_grid_selector = gr.Dropdown(
                    choices=[],
                    value=None,
                    label="Ölçülen gerçek PDF hücresi (semantik eşleşme onaysız)",
                    interactive=True,
                )
                btn_ek20_align = gr.Button(
                    "Seçtiğim gerçek hücreyi seçtiğim EK-20 alanına ROI adayı yap",
                    variant="secondary",
                )

                with gr.Row():
                    roi_x0 = gr.Number(value=0, precision=0, label="x0")
                    roi_y0 = gr.Number(value=0, precision=0, label="y0")
                    roi_x1 = gr.Number(value=0, precision=0, label="x1")
                    roi_y1 = gr.Number(value=0, precision=0, label="y1")
                btn_roi_preview = gr.Button(
                    "Seçili hücre için orijinal piksel ROI önizle",
                    variant="secondary",
                )
                roi_preview_display = gr.HTML(
                    "<p>Özgün görüntü koordinatları girilmedi. HOLD.</p>"
                )
                btn_unlimited_ek20 = gr.Button(
                    "Baidu Unlimited-OCR ile seçili gerçek EK-20 hücre ROI'sini oku",
                    variant="secondary",
                )
                unlimited_ek20_display = gr.HTML(
                    "<p>Baidu Unlimited-OCR yalnız SHA-doğrulanmış 180 DPI "
                    "hücre görüntüsünde, özel onaylı yerel GPU modeli "
                    "kurulmuşsa isteğe bağlı çalışır. Sonuç HOLD.</p>"
                )


            gr.Markdown(
                "**48 hücre kanıt envanteri:** Her EK-20 tutar alanının özgün "
                "PDF piksel konumu ve iki bağımsız görsel incelemeci imzası "
                "ayrıca denetlenir. Kaynak eksikse bütün hücreler HOLD kalır."
            )
            btn_ek20_coverage = gr.Button(
                "EK-20 12×4 hücrenin kanıt durumlarını göster",
                variant="secondary",
            )
            ek20_coverage_display = gr.HTML(
                "<p>48 hücre kapsamını görmek için denetimi açın.</p>"
            )

            from tarim_destek_rag.citations.ocr_spatial_layout import (
                render_ocr_spatial_review,
            )

            btn_ocr_spatial = gr.Button(
                "Gerçek PDF üzerinde OCR satır kutularını göster (HOLD)",
                variant="secondary",
            )
            ocr_spatial_display = gr.HTML(
                "<p>OCR satır kutularını görmek için doğrulanmış sayfayı seçin. "
                "Bu kutular kesin mevzuat alıntısı değildir.</p>"
            )
            btn_page_ocr = gr.Button(
                "Seçili gerçek sayfayı yerel OCR ile oku (inceleme taslağı)",
                variant="secondary",
            )
            ocr_display = gr.HTML(
                value="<p>OCR yalnızca isteğiniz üzerine çalışır; "
                "OCR sonucu resmî alıntı veya onay değildir.</p>"
            )
            from tarim_destek_rag.citations.unlimited_ocr_review import (
                render_unlimited_ocr_page,
            )
            with gr.Accordion("Baidu Unlimited-OCR — isteğe bağlı yerel OCR", open=False):
                gr.Markdown(
                    "Bu motor **Baidu/Unlimited-OCR**'dır; PaddleOCR değildir. "
                    "Önceden kurulmuş yerel NVIDIA GPU modeli, onaylı özel "
                    "model kodu ve özgün SHA-doğrulanmış kaynak PDF gerektirir. "
                    "OCR sonucu yalnız karşılaştırmalı metin taslağıdır; "
                    "imzalı hücre, kanıt vurgusu veya ödeme PASS değildir."
                )
                btn_unlimited_page = gr.Button(
                    "Seçili özgün PDF sayfasını Baidu Unlimited-OCR ile oku",
                    variant="secondary",
                )
                unlimited_page_display = gr.HTML(
                    "<p>Kaynak seçilmedi veya yerel model kurulmadı: HOLD.</p>"
                )


            def update_article_view(choice: str | None, query: str = "") -> str:
                return render_evidence_by_key(choice or "", query or "")

            article_selector.change(
                update_article_view,
                inputs=[article_selector, page_search_input],
                outputs=[article_display],
            )
            article_selector.change(
                lambda key: gr.update(
                    choices=page_region_choices(key), value=None,
                ),
                inputs=[article_selector],
                outputs=[region_selector],
            )
            # The grid scan is explicit and runs only for the current original.
            # A page switch clears stale selections from a different SHA/page.
            article_selector.change(
                lambda: gr.update(choices=[], value=None),
                inputs=None,
                outputs=[raster_cell_selector],
            )
            btn_raster_scan.click(
                lambda key: gr.update(
                    choices=raster_cell_choices(key), value=None,
                ),
                inputs=[article_selector],
                outputs=[raster_cell_selector],
            )
            raster_cell_selector.change(
                render_raster_cell,
                inputs=[raster_cell_selector],
                outputs=[raster_cell_display],
            )
            region_selector.change(
                render_source_region,
                inputs=[region_selector],
                outputs=[region_display],
            )
            # This listener accepts evaluation state wired by frontend_pc.app.
            # No evidence or source is inferred from a user-selected label.

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
            btn_ocr_spatial.click(
                render_ocr_spatial_review,
                inputs=[article_selector],
                outputs=[ocr_spatial_display],
            )
            btn_ek20_grid_scan.click(
                lambda: gr.update(
                    choices=measured_ek20_cell_choices(), value=None,
                ),
                inputs=[],
                outputs=[ek20_grid_selector],
            )
            ek20_selector.change(
                lambda: (
                    gr.update(value=None),
                    None, None, None, None,
                    "<p>HOLD — Yeni EK-20 alanı için hücre ROI'sini yeniden seçin.</p>",
                ),
                inputs=[],
                outputs=[
                    ek20_grid_selector,
                    roi_x0, roi_y0, roi_x1, roi_y1,
                    roi_preview_display,
                ],
            )
            btn_roi_preview.click(
                render_candidate_roi,
                inputs=[ek20_selector, roi_x0, roi_y0, roi_x1, roi_y1],
                outputs=[roi_preview_display],
            )
            btn_ek20_coverage.click(
                render_ek20_review_coverage,
                inputs=[],
                outputs=[ek20_coverage_display],
            )
            btn_page_ocr.click(
                render_ocr_page_by_key,
                inputs=[article_selector],
                outputs=[ocr_display],
            )
            btn_unlimited_page.click(
                render_unlimited_ocr_page,
                inputs=[article_selector],
                outputs=[unlimited_page_display],
            )
            # Switching source pages invalidates any prior local OCR preview.
            article_selector.change(
                lambda: "<p>Sayfa değişti: Baidu OCR yeniden istenmeli. HOLD.</p>",
                inputs=[],
                outputs=[unlimited_page_display],
            )
            ek20_selector.change(
                lambda: "<p>EK-20 hücre seçimi değişti: OCR sonucu temizlendi. HOLD.</p>",
                inputs=[],
                outputs=[unlimited_ek20_display],
            )


        with gr.Accordion("📁 Başvuru İçin Gerekli Belgeler & Ön Değerlendirme Raporu", open=True):
            gr.Markdown("""
            #### 📁 Başvuru İçin Gerekli Belgeler Kontrol Listesi
            - ✅ **Çiftçi Kayıt Sistemi (ÇKS) Belgesi:** Güncel 2026 üretim yılı için İlçe Tarım Müdürlüğünden veya e-Devlet kapısından onaylı.
            - ✅ **Sertifikalı Tohum / Fidan Faturası:** Bakanlık yetkili tohum/fidan bayisinden alınmış kaşeli orijinal fatura ve etiket kopyası.
            - ✅ **Tapu / Kira / Muvafakatname:** Parselin mülkiyet veya intifa hakkını tevsik eden belge.
            - ✅ **Başvuru Dilekçesi & Taahhütname:** İlgili destekleme programı için standart form.

            #### 📌 Eksik Evrak / İnceleme Durumunda Yapılması Gerekenler
            1. ÇKS kaydınız henüz aktifleşmediyse İlçe Tarım ve Orman Müdürlüğüne 2026 başvuru formunuzu teslim ediniz.
            2. Sertifikalı tohum veya fidan desteği için faturanızın üretim yılı (2026) ile uyumlu olduğunu kontrol ediniz.
            3. Askı icmalleri yayımlandığında 5 günlük yasal itiraz süresini kaçırmamak için köy muhtarlığı panosunu takip ediniz.
            """)

            with gr.Row():
                btn_report = gr.Button(
                    "📄 Bağımsız Ön Değerlendirme Raporunu İndir (.md)",
                    variant="primary",
                    size="lg",
                )
            file_report = gr.File(label="İndirilebilir Rapor Dosyası", visible=False)

        out_disclaimer = gr.HTML("")

    return {
        "out_kpi": out_kpi,
        "out_cards": out_cards,
        "out_table": out_table,
        "out_reasons": out_reasons,
        "claim_selector": claim_selector,
        "btn_claim_show": btn_claim_show,
        "claim_display": claim_display,
        "btn_claim_source_search": btn_claim_source_search,
        "claim_candidate_status": claim_candidate_status,
        "claim_candidate_selector": claim_candidate_selector,
        "claim_candidate_state": claim_candidate_state,
        "claim_candidate_display": claim_candidate_display,
        "btn_claim_coverage": btn_claim_coverage,
        "claim_coverage_display": claim_coverage_display,
        "article_selector": article_selector,
        "article_display": article_display,
        "ocr_display": ocr_display,
        "ocr_spatial_display": ocr_spatial_display,
        "region_selector": region_selector,
        "region_display": region_display,
        "raster_cell_selector": raster_cell_selector,
        "raster_cell_display": raster_cell_display,
        "ek20_selector": ek20_selector,
        "ek20_grid_selector": ek20_grid_selector,
        "btn_ek20_align": btn_ek20_align,
        "roi_x0": roi_x0,
        "roi_y0": roi_y0,
        "roi_x1": roi_x1,
        "roi_y1": roi_y1,
        "roi_preview_display": roi_preview_display,
        "ek20_display": ek20_display,
        "ek20_coverage_display": ek20_coverage_display,
        "roi_preview_display": roi_preview_display,
        "btn_unlimited_ek20": btn_unlimited_ek20,
        "unlimited_ek20_display": unlimited_ek20_display,
        "btn_report": btn_report,
        "file_report": file_report,
        "out_disclaimer": out_disclaimer,
    }
