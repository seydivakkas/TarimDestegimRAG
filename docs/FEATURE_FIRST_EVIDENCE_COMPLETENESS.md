# Kanıt Sistemini Önce Tamamlama Planı — Özellik Öncelikli

**Karar:** Önce bütün kullanıcı işlevleri ve belge türleri tamamlanır. Kapsam bütünlüğü netleşmeden yeni "tamam", "üretime hazır", "mevzuat kesin doğrulandı" iddiası verilmez. Kapsam bittiğinde son aşama Windows gerçek kullanım, sentetik negatif testler, kaynak bütünlüğü ve hukukî onaydır.

## Nihai kullanım senaryosu

Çiftçi bilgisi → 2025/2026/2027 üretim yılı → destek ailesi → tekil kural sonucu → **birebir** kaynak sürümü ve resmî URL → özgün SHA → PDF sayfa PNG veya özgün HTML hükmü → sarı gerçek pasaj/gerçek tablo hücresi konumu → kanıt değerlendirme durumu → uygulama/rapor/mobil kaynak ortak kimliği.

"Kaynak bulundu", "pasaj birebir görüldü", "üretim yılı bakımından yürürlükte", "çiftçi koşulu sağladı" ve "ödeme onaylı" birbirinden ayrı durumlardır.

## Özellik kapsamı ve iş bitiş tanımları

| ID | Özellik | Kod inceleme durumu | İşlevsel tamamlanma tanımı |
|---|---|---|---|
| F01 | Orijinal kaynak deposu | KISMİ: beş SHA-pinli belge | Birincil mevzuat ve tüm sürüm/değişiklik/ekler doğrulanmış orijinli; sentetik/türetilmiş belge dışlanmış |
| F02 | Gerçek PDF ekran görüntüsü | VAR, PR40 | Sayfa numarası, original SHA ve tam kaynak URL sayfaya bağlanır |
| F03 | PDF metin/OCR indeksleme | KISMİ: native metin, toplu OCR taslağı, gerçek sayfa üzerinde turuncu OCR satır kutusu önizlemesi | Bütün sayfalara tarama durumu, OCR geometrisi, indeks sürümü, görsel inceleme akışı ekli |
| F04 | Tablolar ve hücreler | KISMİ: native find_tables, OCR sözcük kutuları, görüntü piksellerinden ölçülen çizgili-ızgara hücre adayları ve kaynak SHA'lı orijinal hücre kırpımı | Born-digital ve raster tabloların satır/sütun/hücre konumları özgün piksel/point sistemine bağlı; hata/boş/dash belirsizlikleri korunur |
| F05 | Grafik/şekil/çizim | KISMİ: bölge kırpımı | Gerçek sayfa görselleri ve bölgeler bulunur; semantik iddialar yalnız kanıtlı inceleme ile |
| F06 | PDF/HTML ortak kanıt gezgini | KISMİ: PDF görüntüsü, SHA-doğrulanmış HTML pasajı | Her iki belge türü aynı kanıt kimliği ve kaynak bağlantı kontratıyla gezilebilir |
| F07 | Tekil gerekçe → kaynak | KISMİ: her gerekçe seçimi, sadece mevcut curated claim_bindings | Bütün sonuç metinleri kaynak paragrafı/ek hücresi/yıl ile ayrı ayrı eşlenir; bulunamayan HOLD |
| F08 | Yıllara göre değişiklik zinciri | KISMİ: 2025/42 bazı pasajlar, 2025 geçiş | 2024/39, 2025/13, 2025/42, 8859, 10394, 11781 ve diğer uygulanabilir revizyonların etkisi hüküm bazlı izlenir |
| F09 | EK-20 satır/hücre kanıtı | KISMİ: 2026 taslak 12x4, gerçek sayfa ROI önizleme, 48 hücre durumu, iki ayrı Ed25519 inceleme imzası ve imza sonrası görsel sarı alan; gerçek 48 ROI için onay henüz yok | Her sayısal hücrenin tam ROI, iki bağımsız görsel okuma ve geçerli yıl kaydı olmadan hukukî/ödeme PASS olmaz |
| F10 | Neden / SSS / rapor / mobil birlikteliği | KISMİ: Neden + raporda tekil claim_id; SSS/mobil henüz değil | Tüm açıklamalar tekil aynı claim_id, source_id, SHA, sayfa ve pasaj/ROI bağını kullanır |
| F11 | Offline Windows kullanım paketi | KISMİ: özgün kaynak yükleme, opsiyonel Tesseract | İlk kurulumdan indeks yenilemeye kadar ücretli API/bulut gerektirmeden Türkçe OCR ve resmî dosya yönetimi |
| F12 | Kaynak değişikliği ve doğrulama yönetimi | KISMİ: manifest, draft hukukî eşleşmeler | Yeni resmî belgeden eski kuralı iptal/değiştirme, fark inceleme, insan onayına sunma ve geri alma |
| F13 | Güvenli hak ediş/ödeme ayrımı | KISMİ: fail-closed ayrı PR37 | Ürün arayüzündeki görünür tahmini tutarlar da güvenilmeyen mevzuat aktivasyonundan ayrılır; ücret/ödeme kaynak onayı olmadan aktive olmaz |
| F14 | Son test ve kontrollü kabul | SON AŞAMA: **bilerek ertelendi** | F01–F13 için özellik kapanışından sonra regresyon, gerçek resmî kaynak, Windows kullanıcı kabulü, hukukî/kurumsal imzalar |

## Bu özellik dalında şimdiden yapılan işler

- PR #40 üzerinde özgün PDF sayfa ekran görüntüsü ve SHA bağlı yerel OCR.
- PR #38'den taşınan **P0-10.7 kaynak–kural–yıl matrisi** ve birebir SHA+madde+pasaj denetimi.
- Destek Analizi > Neden: bütün hesaplama şartları ayrı ayrı seçilebilir; yalnız belirlenmiş `rule_id/support_id/production_year/field/exact_claim_text` eşleşmesinden normatif pasaj açılır.
- Gerçek PDF tablosu, resim ve vektör bölgeleri koordinatla kırpılır; görsel **hükmün doğru yorumlandığının belgesi değildir**.
- 2026 EK-20'nin 12 satır/4 hücre sınıfı kullanıcı tarafından seçilebilir; kaynak orijinal sayfa ve taslak aktarım yan yana gösterilir; onay/ödeme HOLD.
- Tesseract TSV ile her sözcüğün `pixel_bbox` koordinatı ve satır adayları arşivlenebilir; gerçek tablo hücresi doğrulaması ayrı kalır.
- Ön değerlendirme raporunun bütün hesaplanmış gerekçeleri aynı `claim_id`, `source_id`, kaynak SHA ve kesin hüküm/durum ayrımıyla izlenir. Tahmini madde/sayfa URL'leri ve sabit "yasal dayanak" etiketleri kaldırılmıştır.


## Geliştirme bitmeden "hazır" denmeyecek

* Özellikle F04, F07, F08, F09, F10 ve F11 eksiktir. İlk aşama kullanıcı deneyimi güçlendirilmiş olsa da tüm mevzuat gerekçeleri kanıtlanmış **değildir**.
* Ürün koduna SHA'sı doğru fakat ilgili madde/fıkra/hücre doğrulanmamış bağlantı eklenemez.
* Her kurumun elindeki belge ve 2026/2027 ödeme mevzuatı bağımsız incelemede kabul edilmeden ödeme yetkisi **HOLD** kalır.
* `main`, güvenlik PR #37, mevzuat entegrasyonu PR #38, kaynak görüntüsü PR #40 ve bu özellik PR'ının ilişkisi birleştirme aşamasında **ayrı** ele alınır. Doğrudan `main`e sürpriz merge yapılmaz.

## Son aşama (özelliklerden sonra)

1. Kod ve arayüz kapsam denetimi, tüm kullanıcı akışları; kaynaklar arası yıl-sürüm-tablo kontrolü.
2. İstenilen tüm gerçek PDF/HTML orijinallerinde sayfa, OCR, bölge, satır/hücre ve link doğrulaması.
3. Windows yerel Tesseract `tur+eng`, internet kapalı, kaynak yok, OCR hatalı, hash değiştirilmiş ve yanlış yıl senaryoları.
4. Bütün backend, Gradio, API, rapor, mobil ve GitHub CI; ardından bağımsız hukukî kabul.

CI sistemin otomatik tetiklenmesi kod tamamlanmasına eşit sayılmayacak; bu belgenin temel kapsam hedefi **önce işlevleri tamamlamak**.


## PR #41 — Raster tablo/OCR inceleme ek paketi (özellik geliştirme)

Bu paketteki **uygulanan** işlevler:
- Raster hücre inceleme: özgün PDF SHA'sı her çağrıda yeniden doğrulandıktan sonra 180 DPI gerçek sayfa PNG pikselleri incelenir. Yatay/dikey ızgara çizgilerinin sürekliliği ve kesişimi ölçülür; yalnız fiziksel çizgiler arasından gerçek piksel kutusu *adayları* çıkarılır. Eksik/bölünmüş veya çizgisiz tablo için koordinat icat edilmez; HOLD.
- Destek Analizi > Neden: kullanıcı seçtiği gerçek PDF sayfasında isteğe bağlı ızgara taraması yapar; hücre adayını seçince aynı kaynaktan yeniden kırpılmış bölge ve turuncu inceleme çerçevesi görünür. Tam SHA-256 + sayfa + DPI + piksel kutusu gösterilir. İndeks varsa aynı SHA/sayfa/DPI bağlı OCR sözcükleri gösterilir.
- Toplu indeks: her özgün sayfanın indeks kaydına raster_table_geometry (SHA, sayfa, DPI, gerçek piksel kutuları veya açıkça HOLD) eklendi.
- OCR incelemesi: seçilen gerçek sayfada Tesseract TSV satır koordinatları turuncu kutularla orijinal sayfanın geçici görüntü kopyası üzerinde gösterilir. Kaynak PDF değiştirilmez.

**Doğrulama sınırı:** RASTER_GRID_CANDIDATES_UNREVIEWED ve OCR_LAYOUT_UNREVIEWED yalnız taslak konum/metin adaylarıdır. EK-20 aktarım satırı bu aşamada görüntü hücresine otomatik bağlanmaz. Bağımsız ikinci görsel inceleme, üretim yılına göre hukukî yürürlük, çiftçi koşulları ve ödeme kararları HOLD kalır. Turuncu kutu resmî sarı kanıt vurgusu değildir.

**Kalan işler:** çizgisiz/raster tablo bölütlemesi; birden fazla alt tablo; EK-20'nin 48 alanının gerçek kaynak ROI'si üzerinde iki gerçek insan tarafından fiilen incelenip imzalanması; bağımsız insan kimliği/yetki kontrolü ve onayların kurumsal arşivlenmesi; bütün değişiklik/yıl/kural bağlantıları; ortak PDF/HTML kanıt kontratı; SSS ve mobil senkronizasyonu; Windows paketleme. F04 ve F09 henüz TAMAM değil.

**Sıra:** F01–F13 özellikler ve bütünleşme → en son F14 kapsamlı test, gerçek Windows kabul, hukukî ve güvenlik onayı. PR #41 taslak kalır, main değişmez.


## PR #41 — F04/F09 gerçek ROI + iki imzalı hücre onayı altyapısı

- EK-20 `12×4=48` hücre ayrı kanıt birimi; **null tireyi 0 TL olarak yorumlama yok**.
- Tam SHA-doğrulanmış gerçek PDF sayfasının 180 DPI piksel koordinatları
  ile manuel ROI öneri/önizleme ekranı eklendi; kullanıcı girişi tek başına
  doğru tablo hücresi konumu veya sarı kanıt VURGUSU DEĞİL.
- Her ROI önerisi: kaynağın SHA-256 ve URL'si, sayfa kimliği, görüntünün RGB
  hash'i, hücre RGB hash'i, tam piksel kutusu, satır/sütun ve 2026 taslak
  alan değeriyle bağlanıyor; kaynak değişirse eski onay kullanılamaz.
- Yerel yönetici tarafından tanınan iki farklı Ed25519 genel anahtarı, iki ayrı
  `primary/independent` kişi rolü ve aynı payload üzerine iki ayrı imzalı
  inceleme kaydı gereklidir. Eksik/bozuk/REJECT/kaynak uyuşmazlığı HOLD.
- Sadece iki imza doğrulanırsa gerçek orijinal sayfanın **görüntü kopyası**
  üzerindeki gerçek ROI sarı işaretli açılır. Bu sarı görsel **hukukî yürürlük
  veya ödeme izni değildir**; kanıt durumu `CELL_VISUAL_DUAL_VERIFIED`
  katmanıyla sınırlandırılmıştır.
- 48 hücre envanteri oluşturuldu; özel reviewer key'ler repository dışında
  tutulur; herhangi bir varsayılan reviewer onayı veya uydurma bbox eklenmedi.
- Bağımsız iki gerçek kişinin imzalarının fiilen toplanması, 48 ayrı hücrenin
  birebir kaynak ROI'sinin belirlenmesi ve kurumsal onay henüz yapılmadı.
  Mevcut özellik `F04 KISMİ / F09 KISMİ` statüsündedir.
- İşletim prosedürü: [F04_F09_EK20_TWO_REVIEWER_ROI.md](F04_F09_EK20_TWO_REVIEWER_ROI.md).

**Sonraki özellik:** 48 kaynak hücrenin fiilî koordinat ve bağımsız incelemesi,
ardından F07/F08 mevzuat sürüm–yıl–kural zinciri ve F10 ortak SSS/rapor/mobil
kanıt kontratı. Son F14 kapsamlı regression, gerçek Windows ve hukukî kabul.
