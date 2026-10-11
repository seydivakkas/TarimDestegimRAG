# P0-39 — Özgün Sayfa Ekran Görüntüsü Kanıtı (taslak kabul)

**Sınır:** Resmî metni, tabloyu ve grafik öğelerini eksiksiz OCR ile doğruladığımızı iddia etmiyoruz. Kaynak yoksa HOLD.

1. Belgeler yalnız `configs/p0_10_3_original_source_manifest.json` içindeki `id`, `url`, `format=pdf`, `original_sha256` ve bayt uzunluğuyla eşleşen dosyalardan indekslenir. Dosya adı: `$TARIM_RAG_UPDATE_ARCHIVE/originals/<sha>.pdf`.
2. `get_global_pdf_indexer` eski `gazette_page_index.json` veya `data/documents/RG_*.pdf` varlıklarını **yüklemez**; `seed_default_gazette_documents` hiçbir PDF üretmez.
3. Kanıt sekmesi resmî URL'de tahmini #page kullanmaz. Yalnız gerçek PDF sayfa sayısı doğrulanmış seçimleri listeler; sayfayı **SHA sabitli gerçek dosyanın baytlarından** açıp PNG oluşturur. Metin katmanındaki *tam* arama vurgulanabilir; OCR veya resim için doğrulanmamış sarı işaretleme yapılmaz.
4. **Gerçek OCR:** Tesseract yüklü ise `OfficialPdfIndexer.ocr_page(record)` seçilen özgün sayfa PNG'sini yerel olarak Tesseract `tur+eng` ile işler. Çıktı `OCR_UNREVIEWED` kalır. Tesseract veya Türkçe model dosyası yoksa `OCR_NOT_INSTALLED` / `OCR_FAILED`. Otomatik yüzde yüz doğruluk, tam tablo semantiği veya hukukî onay yoktur.
5. Gerçek OCR sonucunu kaynağa satır-hücre koordinatlı bağlayıp ikinci incelemeyle doğrulayan iş akışı ileride ayrıca kurulmalıdır. İşlenmemiş image-only PDF'de metin araması sonuç üretmez, kaynak sayfası seçilerek incelenir.
6. Eski sentetik 8859/11781/2024-39 PDF'leri git ağacından kaldırıldı. 2024/39 asıl yayın HTML'dir; PDF diye taklit edilmez. İlgili sentetik testler hakikat kanıtına dayanan fail-closed testlerle değiştirildi.
7. Hukukî hüküm–üretim yılı, EK-20 hücre semantiği, çiftçi olguları, bağımsız hukukî imzalar, gerçek WORM/HSM ve ödeme aktivasyonu **HOLD**.

**Kabul için:** Özgün 8859 tarama PDF'si/2024/39 HTML ve 2025/42 ekteki EK-20, SHA kontrollü arşivde doğru yerlerde bulunmalı; Windows'ta Gradio gerçek sayfayı göstermeli; yanlış SHA/sayfa/kaynak testleri PASS olmalı; uygulamanın bütün yanlış resmî alıntı yolu kapalı kalmalı.

## Windows kurulumu — gerçekten özgün PDF gösterme

Windows PowerShell veya terminali proje kökünde açın:

```powershell
python -m scripts.install_pinned_gazette_sources --source-id RG_DECISION_8859
```

Komut yalnız Resmî Gazete HTTPS kaynağındaki **orijinal PDF** baytlarını indirir; kaynak manifestindeki SHA/uzunluk tutmazsa **HOLD** ve hata üretir. İnternet erişimi yoksa SHA isimleriyle düzenlenmiş, önceden bağımsız doğrulanmış arşiv kopyalarını şu yolla içe alın:

```powershell
python -m scripts.install_pinned_gazette_sources --source-id RG_DECISION_8859 --import-dir "C:\\ResmiGazeteOrijinallerim"
```

Ardından Gradio'yu yeniden başlatın. Destek Analizi / Kanıt bölümündeki açılır listede yalnız SHA-destekli PDF sayfaları listelenir. İlgili sayfayı seçip büyük sayfa görselini inceleyin; Tesseract varsa OCR düğmesini ayrıca çalıştırabilirsiniz. Özgün dosya kurulu değilse görünüm **HOLD** kalır. `2024/39` özgün HTML'dir; bu PDF kurucusu onu PDF'ye dönüştürmez.

**Not:** Windows/kurum ortamında gerçek kullanıcı kabul testi ve tüm belgelerin OCR'si burada çalıştırılmadı.
