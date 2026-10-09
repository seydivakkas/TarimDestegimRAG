# Neden? — özgün resmî PDF'de birebir cümle kanıtı

**Sorun:** Önceki `TemplateExplainer` metinleri, resmî PDF'de bulunmayabilen hesap özeti/yapay açıklama içeriyordu. Bunlar `snippet` ve tırnak işaretleri içinde görünüyordu. Ayrıca sabit `#page=1/2` bağlantısı tek başına cümlenin o sayfada olduğunu kanıtlamaz.

**Doğru resmî belge kimliği:** 8859 sayılı Cumhurbaşkanı Kararı, 29 Ağustos 2024 / RG 32647. 2025–2027 bitkisel üretim uygulama Tebliği **2024/39**, 31 Aralık 2024 / RG 32769 (5. mükerrer): https://resmigazete.gov.tr/eskiler/2024/12/20241231M5-8.htm. Kullanıcı arayüzünde **2024/33** ile karıştırılmamalıdır. Tebliğin orijinali HTML olarak yayımlanmıştır; bir HTML sayfasını doğrulanmış PDF gibi göstermiyoruz.

## Çalışan teknik sözleşme

1. GitHub CI P0-10.3'te doğrulanmış 8859 özgün PDF'sini `data/legal_update_archive/originals/<SHA256>.pdf` klasörüne aktarın. **Orijinali değiştirmeyin.** Beklenen SHA-256 `89df0b6222edb4eddf3d5f588a4007061458adec8d518e3fbdb86b46ae5ba85f`. P0-10.3 kanıt artefaktlarının indirilebilmesi çalışma ortamına bağlıdır; `git clone` tek başına özgün PDF'leri içermez.
2. Kaynağın bir PDF sayfasındaki *gerçek metnini* yerel belge görüntüleyicisinde bulun. Madde/fıkra, sayfa ve üretim yılına uygunluğunu ayrıca bir hukuk incelemesine tabi tutun.
3. Doğru cümleyi **birebir** aşağıdaki komutla indeksleyin. Buradaki `<BELGEDEKI_BIREBIR_CUMLE>` metnini PDF'den doğrulayarak yazın; örnek/parafraz girmeyin:

```powershell
python -m tarim_destek_rag.citations.exact_index --support-id BASIC_SUPPORT_2026 --source-id RG_DECISION_8859 --page 1 --section "MADDE 2" --quote "<BELGEDEKI_BIREBIR_CUMLE>" --title "8859 sayılı Cumhurbaşkanı Kararı"
```

4. Doğrulayıcı, orijinal PDF'nin bayt SHA-256'sını `configs/p0_10_3_original_source_manifest.json` ile eşleştirir; tam cümlenin **seçilen PDF sayfasında tek kez** geçtiğini ve koordinatlarının çıkarılabildiğini kontrol eder. Başarırsa `data/legal_update_archive/verified_citations.json` dosyasına kaynak, sayfa, alıntı ve SHA'yı kaydeder.
5. `/evaluate` çağrısında `TemplateExplainer` yalnız bu offline indeksi okuyarak tekrar doğrulanmış gerçek cümleyi gösterir. PC arayüzünde **PDF'de işaretli cümleyi aç** bağlantısı, mevcut `/evidence/highlight/{sha256}?page=...&quote=...` endpoint'inin sarı vurgulu kopyasını açar. Üretim ortamında Gradio tarafından açılabilir backend URL'si için `API_PUBLIC_BASE_URL` ayarlanmalıdır.
6. Eksik PDF, farklı hash, bulunamayan veya birden çok kez geçen alıntı, okunamayan/OCR gerektiren sayfa ya da yanlış sayfa: **kanıt görüntülenmez**. Yalnız `Ön değerlendirme açıklaması — resmî alıntı değildir` gösterilir. Hiçbir kaynak kendiliğinden hak edişe veya onaylı birim tutara dönüşmez.

**Durum:** Motor ve arayüz entegrasyonu oluşturuldu; proje klonunda orijinal PDF otomatik mevcut olmadığından `BASIC_SUPPORT_2026` için gerçek hukukî eşleştirme, gerçek PDF'den doğru cümle seçilip yukarıdaki adım uygulanana kadar `HOLD`. Diğer destek türleri de tek tek aynı doğrulamayı gerektirir. Gerçek PDF'yi yerel arşive edinmeden hiçbir sentetik pasaj `VERIFIED` yapılmaz.

**Sınırlar:** `2024/39` resmî HTML ve taranmış/görüntü PDF'ler için ayrıca belge türüne özel orijinal metin/render/OCR koordinat indeksi gerekir. Mevcut işaretleme ilk aşamada yalnız metin katmanı bulunan **orijinal PDF** dosyalarını kapsar. `EXACT_PDF_MATCH_PENDING_LEGAL_REVIEW` metnin kaynaktaki yerini kanıtlar; hükmün yürürlük/geçerlilik/uygunluk onayını değil.
