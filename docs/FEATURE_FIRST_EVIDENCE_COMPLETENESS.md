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
| F03 | PDF metin/OCR indeksleme | KISMİ: native metin, seçili Tesseract ve toplu taslak | Bütün sayfalara tarama durumu, OCR geometrisi, indeks sürümü, görsel inceleme akışı ekli |
| F04 | Tablolar ve hücreler | KISMİ: native find_tables ve OCR sözcük kutuları | Born-digital ve raster tabloların satır/sütun/hücre konumları özgün piksel/point sistemine bağlı; hata/boş/dash belirsizlikleri korunur |
| F05 | Grafik/şekil/çizim | KISMİ: bölge kırpımı | Gerçek sayfa görselleri ve bölgeler bulunur; semantik iddialar yalnız kanıtlı inceleme ile |
| F06 | PDF/HTML ortak kanıt gezgini | KISMİ: PDF görüntüsü, SHA-doğrulanmış HTML pasajı | Her iki belge türü aynı kanıt kimliği ve kaynak bağlantı kontratıyla gezilebilir |
| F07 | Tekil gerekçe → kaynak | KISMİ: her gerekçe seçimi, sadece mevcut curated claim_bindings | Bütün sonuç metinleri kaynak paragrafı/ek hücresi/yıl ile ayrı ayrı eşlenir; bulunamayan HOLD |
| F08 | Yıllara göre değişiklik zinciri | KISMİ: 2025/42 bazı pasajlar, 2025 geçiş | 2024/39, 2025/13, 2025/42, 8859, 10394, 11781 ve diğer uygulanabilir revizyonların etkisi hüküm bazlı izlenir |
| F09 | EK-20 satır/hücre kanıtı | KISMİ: 2026 taslak 12x4, gerçek PDF görüntüsü | Her sayısal hücrenin tam ROI, iki bağımsız görsel okuma ve geçerli yıl kaydı olmadan hukukî/ödeme PASS olmaz |
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
