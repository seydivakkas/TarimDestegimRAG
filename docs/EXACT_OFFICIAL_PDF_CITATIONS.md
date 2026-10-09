# Neden? — özgün resmî PDF'de birebir cümle kanıtı

**Sorun:** Önceki `TemplateExplainer` metinleri, resmî PDF'de bulunmayabilen hesap özeti/yapay açıklama içeriyordu. Bunlar `snippet` ve tırnak işaretleri içinde görünüyordu. Ayrıca sabit `#page=1/2` bağlantısı tek başına cümlenin o sayfada olduğunu kanıtlamaz.

**Doğru resmî belge kimliği:** 8859 sayılı Cumhurbaşkanı Kararı, 29 Ağustos 2024 / RG 32647. 2025–2027 bitkisel üretim uygulama Tebliği **2024/39**, 31 Aralık 2024 / RG 32769 (5. mükerrer): https://resmigazete.gov.tr/eskiler/2024/12/20241231M5-8.htm. Kullanıcı arayüzünde **2024/33** ile karıştırılmamalıdır. Tebliğin orijinali HTML olarak yayımlanmıştır; bir HTML sayfasını doğrulanmış PDF gibi göstermiyoruz.

## Çalışan teknik sözleşme

1. GitHub CI P0-10.3'te doğrulanmış 8859 özgün PDF'sini `data/legal_update_archive/originals/<SHA256>.pdf` klasörüne aktarın. **Orijinali değiştirmeyin.** Beklenen SHA-256 `89df0b6222edb4eddf3d5f588a4007061458adec8d518e3fbdb86b46ae5ba85f`. P0-10.3 kanıt artefaktlarının indirilebilmesi çalışma ortamına bağlıdır; `git clone` tek başına özgün PDF'leri içermez.
2. Kaynağın bir PDF sayfasındaki *gerçek metnini* yerel belge görüntüleyicisinde bulun. Madde/fıkra, sayfa ve üretim yılına uygunluğunu ayrıca bir hukuk incelemesine tabi tutun.
3. Doğru cümleyi **birebir** aşağıdaki komutla indeksleyin. Buradaki `<BELGEDEKI_BIREBIR_CUMLE>` metnini PDF'den doğrulayarak yazın; örnek/parafraz girmeyin:

```powershell
python -m tarim_destek_rag.citations.exact_index --support-id BASIC_SUPPORT_2026 --source-id RG_DECISION_8859 --page 2 --section "MADDE 2" --quote "<BELGEDEKI_BIREBIR_CUMLE>" --title "8859 sayılı Cumhurbaşkanı Kararı"
```

4. Doğrulayıcı, orijinal PDF'nin bayt SHA-256'sını `configs/p0_10_3_original_source_manifest.json` ile eşleştirir; tam cümlenin **seçilen PDF sayfasında tek kez** geçtiğini ve koordinatlarının çıkarılabildiğini kontrol eder. Başarırsa `data/legal_update_archive/verified_citations.json` dosyasına kaynak, sayfa, alıntı ve SHA'yı kaydeder.
5. `/evaluate` çağrısında `TemplateExplainer` yalnız bu offline indeksi okuyarak tekrar doğrulanmış gerçek cümleyi gösterir. PC arayüzünde **PDF'de işaretli cümleyi aç** bağlantısı, mevcut `/evidence/highlight/{sha256}?page=...&quote=...` endpoint'inin sarı vurgulu kopyasını açar. Üretim ortamında Gradio tarafından açılabilir backend URL'si için `API_PUBLIC_BASE_URL` ayarlanmalıdır.
6. Eksik PDF, farklı hash, bulunamayan veya birden çok kez geçen alıntı, okunamayan/OCR gerektiren sayfa ya da yanlış sayfa: **kanıt görüntülenmez**. Yalnız `Ön değerlendirme açıklaması — resmî alıntı değildir` gösterilir. Hiçbir kaynak kendiliğinden hak edişe veya onaylı birim tutara dönüşmez.

**Belgeye özgü önemli sınır (8859):** Bakanlığın yayımladığı özgün 8859 PDF'si 89 sayfalık Resmî Gazete taraması niteliğindedir; 2. PDF sayfasında MADDE 1 "Amaç ve kapsam", MADDE 2 "Bitkisel üretimin desteklenmesi" bulunur. PDF sayfa görüntüsü okunabilse de kaynakta her sözcüğün aranabilir metin/koordinat katmanı olmayabilir. **OCR metni + görüntüde satır koordinatı + bağımsız insan kontrolü** sağlanmadan taranmış pasajları bu ilk motor `EXACT_PDF_MATCH` yapamaz. Sayfa görüntüsünü tahminî metinle eşleştirip sahte başarı üretmek yasaktır. Yukarıdaki CLI örneği yalnız belgede tam arama yapılabilen metin katmanı mevcutsa çalışır.

**Durum:** Motor ve arayüz entegrasyonu oluşturuldu; proje klonunda orijinal PDF otomatik mevcut olmadığından `BASIC_SUPPORT_2026` için gerçek hukukî eşleştirme, gerçek PDF'den doğru cümle seçilip yukarıdaki adım uygulanana kadar `HOLD`. Diğer destek türleri de tek tek aynı doğrulamayı gerektirir. Gerçek PDF'yi yerel arşive edinmeden hiçbir sentetik pasaj `VERIFIED` yapılmaz.

**Sınırlar:** `2024/39` resmî HTML ve taranmış/görüntü PDF'ler için ayrıca belge türüne özel orijinal metin/render/OCR koordinat indeksi gerekir. Mevcut işaretleme ilk aşamada yalnız metin katmanı bulunan **orijinal PDF** dosyalarını kapsar. `EXACT_PDF_MATCH_PENDING_LEGAL_REVIEW` metnin kaynaktaki yerini kanıtlar; hükmün yürürlük/geçerlilik/uygunluk onayını değil.

**Yanıltıcı eski kontrol linkleri:** Arayüzde kural durum satırları artık sırf "ÇKS", "havza" veya "tohum" kelimesi geçtiği için 8859 PDF'deki MADDE 1/2/3'e otomatik bağlanmaz. Bunlar kanıt indeksindeki gerçek madde ve alıntı eşleşmesine bağlanana kadar **Madde/pasaj henüz doğrulanmadı** olarak gösterilir.

## İlk gerçek örnek: 8859, MADDE 2(1), resim taraması

**Gerçek kaynağın kendisi**: https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf, **89 sayfa**, dosya SHA-256 `89df0b6222edb4eddf3d5f588a4007061458adec8d518e3fbdb86b46ae5ba85f`. Kararın **PDF sayfa 2**'si metin katmanı olmayan taranmış sayfadır.

Gözle işaretlenen resmî hüküm MADDE 2(1)'in Tarım ve Orman Bakanlığının belirlediği kayıt sistemlerine kayıt şartı ile ilgili pasajıdır. Kaynak görüntü üzerinde **3 gerçek satırın** sarı koordinatları `configs/p0_10_5_8859_visual_clause_index.json` içinde sürümlenmiştir. Bu, otomatik OCR cümlesi değildir; özgün PDF görüntüsüne dayanan **manuel konum tespitidir** ve `VISUAL_SOURCE_LOCATED_PENDING_SECOND_REVIEW` durumundadır. Hukukî uygunluk veya belirli destek tutarı onaylanmış değildir.

**Kullanım:**

```powershell
# Projenin kök dizininde, gerekli Python bağımlılıkları kurulduktan sonra
python -m tarim_destek_rag.citations.visual_pdf --install-8859

# Ardından mevcut PC arayüzünü normal şekilde başlatın.
# BASIC_SUPPORT_2026 destek gerekçesinde "PDF'de işaretli cümleyi aç" belirir.
```

İndirme yalnızca sabit resmî HTTPS URL'den gerçekleştirilir, yönlendirme kabul edilmez, indirilen baytların SHA-256 değeri değişirse kurulum **reddedilir**. Önceden doğrulanmış dosya varsa tekrar indirilmez. Çiftçi değerlendirmesi sırasında kontrolsüz ağ isteği yapılmaz.

İşaretli kanıt API'si: `GET /evidence/highlight/visual/{sha256}?support_id=BASIC_SUPPORT_2026#page=2`. Kaynağın tamamının bir **kopyası** döner; renkli işaretleme yalnız sayfa 2'deki gerçek üç satırı çevreler. Orijinal dosya üzerinde tek bayt değiştirilmez. Orijinal Resmî Gazete linki ayrıca görünür.

Diğer destekler için bu kayıt **genelleştirilmez**. 2024/39 aslı HTML olduğundan ayrı özgün HTML kanıt mekanizması gerekir. Metnin gerçek tarihsel yürürlük/güncellik denetimi, cümle konumu kontrolünden ayrıdır. Aynı belge üzerinde yanlış MADDE veya başka sayfaya bağlantı tahmin edilmez.

## Seçilen il / ilçe / ürün için aynı belgeden kaynaklı işaretleme

Mevcut proje kaynaklarından yararlanır: `configs/2026_2027_basin_crop_draft.json` içinde 945 ilçe / 81 il / özgün PDF sayfası; `backend/src/tarim_destek_rag/normalization/basin_2026.py` sabit resmî kaynak URL ve SHA-256'sını taşır.

**Özgün Bakanlık PDF'si:** https://www.tarimorman.gov.tr/BUGEM/Belgeler/Tar%C4%B1m%20Havzalar%C4%B1/2026%20Y%C4%B1l%C4%B1%20Planlamaya%20Konu%20Havza%20%C3%9Cr%C3%BCn%20Deseni%20Listesi.pdf  
**SHA-256:** `60263e83a953659ecc4f581bcd1ef1a921cf397bc5b4469869852470473f0b21` · **81 sayfa**.

**Kullanım:**

```powershell
# Arka uçla aynı yerel arşive özgün Bakanlık PDF'sini indir ve hash doğrula:
python -m tarim_destek_rag.citations.basin_visual --install

# Ardından FastAPI ve Gradio'yu normal başlatıp
# Çiftçi & Parsellerim → İl / İlçe / Ürün → Hesapla adımını kullanın.
```

- Örnek: **KONYA / KARATAY / BUĞDAY → PDF sayfa 53**. `Konya/Karatay` mavi, **yalnız aynı satırdaki** `Buğday` sarı işaretlenir. Orijinal PDF tüm sayfalarıyla ayrı ve değiştirilmeden korunur.
- Diğer örnekler: **ADANA / CEYHAN / ARPA → sayfa 1**; **SAMSUN / ATAKUM / BUĞDAY → sayfa 67**; **TRABZON / AKÇAABAT / PATATES → sayfa 75**.
- Şehir adını, başka ilçenin ürün listesini veya belirsiz ürün alt türünü eşleyerek sahte PDF kanıtı oluşturmaz. `MISIR` genel ifadesi otomatik `MISIR_DANE` yapılmaz; `FINDIK` havza planlama listesindeki 14 tanımlı gruba zorla eşlenmez.
- Kullanıcı yıl olarak **2025** seçerse 2026–2027 PDF'si **kanıt olarak sunulmaz**.
- **Önemli:** Bu katalog `DRAFT_REQUIRES_HUMAN_ROW_AND_FOOTNOTE_REVIEW` durumundadır. Kaynak satırının gerçek PDF'de bulunması, çiftçinin başvuru hakkı, münavebe/ÇKS, sulama şartı ya da ödeme tutarı için tek başına onay değildir. `ELIGIBLE` ya da `NOT_ELIGIBLE` üretmez.
- Görünüm için `GET /evidence/highlight/basin/{sha256}?province=KONYA&district=KARATAY&crop=BUĞDAY&production_year=2026#page=53`. URI yalnız kaynak hash, tam ilçe adı, tam ürün adı ve yılla yeniden doğrulanır.
- PDF sunucusu ile PC arayüzü farklı makinelerdeyse `API_PUBLIC_BASE_URL` tarayıcının erişebildiği gerçek API adresi olmalı. İstemciye kaynak koordinatları serbestçe yazdırılmaz.
