# Kanıt Sistemini Önce Tamamlama Planı — Özellik Öncelikli

> **Kapsam güncellemesi — 13 Ekim 2026:** Bu belge önceki hukukî kanıt/ödeme iş paketlerinin tarihsel envanteridir. Kullanıcının yeni kararıyla varsayılan ürün **gelişmiş PDF/HTML/TXT belge analiz RAG asistanıdır**. Eski kanıt ve ödeme onayı çalışmaları ana ürünün zorunlu özellikleri değildir. Güncel tek ürün kapsamı: [ADVANCED_DOCUMENT_RAG_SCOPE.md](ADVANCED_DOCUMENT_RAG_SCOPE.md). Gerçek kaynak sayfası gösterme ve metin uydurmama ilkeleri korunur.

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
| F04 | Tablolar ve hücreler | KISMİ: native find_tables, OCR sözcük kutuları, gerçek raster ızgara hücreleri, orijinal hücre kırpımı ve EK-20 için kontrollü manuel semantik–piksel kutusu eşleştirme önizlemesi | Born-digital ve raster tabloların satır/sütun/hücre konumları özgün piksel/point sistemine bağlı; hata/boş/dash belirsizlikleri korunur |
| F05 | Grafik/şekil/çizim | KISMİ: bölge kırpımı | Gerçek sayfa görselleri ve bölgeler bulunur; semantik iddialar yalnız kanıtlı inceleme ile |
| F06 | PDF/HTML ortak kanıt gezgini | KISMİ: PDF görüntüsü, SHA-doğrulanmış HTML pasajı | Her iki belge türü aynı kanıt kimliği ve kaynak bağlantı kontratıyla gezilebilir |
| F07 | Tekil gerekçe → kaynak | KISMİ: tekil claim_id ve SHA/doğrulanmış HTML kaynak-konum kanıt kimliği; tüm rule-binding kapsamı yok | Bütün sonuç metinleri kaynak paragrafı/ek hücresi/yıl ile ayrı ayrı eşlenir; bulunamayan HOLD |
| F08 | Yıllara göre değişiklik zinciri | KISMİ: 2025/42 bazı pasajlar, 2025 geçiş | 2024/39, 2025/13, 2025/42, 8859, 10394, 11781 ve diğer uygulanabilir revizyonların etkisi hüküm bazlı izlenir |
| F09 | EK-20 satır/hücre kanıtı | KISMİ: 2026 taslak 12x4, gerçek sayfa ROI, ölçülen ızgara kutusundan kullanıcı kontrollü ROI ön doldurma, 48 hücre envanteri, iki ayrı Ed25519 inceleme imzası; 48 gerçek hücrenin bağımsız onayı henüz yok | Her sayısal hücrenin tam ROI, iki bağımsız görsel okuma ve geçerli yıl kaydı olmadan hukukî/ödeme PASS olmaz |
| F10 | Neden / SSS / rapor / mobil birlikteliği | KISMİ: ortak v1 kanıt kontratı, Neden/rapor/SSS claim navigator, mobil API/DTO/provider ve mobil Neden ekranı; gerçek cihaz kabulü ve PDF hücre kanıtı eksik | Tüm açıklamalar tekil aynı claim_id, source_id, SHA, sayfa ve pasaj/ROI bağını kullanır |
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

## P1-D03 — Taranmış EK-20 hücresini özgün koordinatla eşleştirme (özellik geliştirme)

Bu dalda `ek20_raster_alignment.py` özelliği eklendi. Artık incelemeci, özgün EK-20 tek sayfalık PDF'yi açarak kaynak raster pikselinden tespit edilen **çizgili ızgara kutusunu**, ayrı seçtiği **2026 ürün/etmen + destek sütununa** ROI ön taslağı olarak atayabilir.

**İncelemecinin uygulamadaki sırası:**

1. Destek Analizi / Neden sekmesinde değerlendirme üretim yılı 2026 olmalı; EK-20 ürün ve tutar türü seçilmeli.
2. "EK-20 özgün sayfasındaki ölçülmüş ızgara hücrelerini getir" ile yalnız gerçek PDF piksellerinden çıkarılmış kutular açılır. Izgara eksik/kenarlıksız ise liste **boş** kalır; metin veya satır sırasından uydurma koordinat üretmeyiz.
3. İncelemeci gördüğü gerçek raster kutusunu kendisi seçer. **Tablodaki semantik 12 satırlık sıra, fiziksel raster satır numarasına otomatik bağlanmaz.**
4. "Seçtiğim gerçek hücreyi ... ROI adayı yap" dört piksel koordinatını form alanına taşır. Kaynak URL + SHA + sayfa + DPI + gerçek resim boyutu, `prepare_roi` ile yeniden bağlanır. Gerçek görüntü üzerinde turuncu aday kutusu ve varsa aynı piksellerdeki onaysız OCR kelimeleri gösterilir.
5. Farklı EK-20 sütunu/ürünü ya da yeni çiftçi değerlendirmesi seçildiğinde önceki koordinatlar temizlenir. Kullanıcı kendi girdiği manuel ROI ile de önizleme yapabilir.
6. Hiçbir adım proposal dosyası yazmaz, otomatik inceleme imzası oluşturmaz, sarı hukukî işaret veya hak ediş tutarı onayı vermez. Mevcut iki kişilik Ed25519 görsel inceleme zinciri ayrı ve kurumsal kontrollüdür.

**Kalan F04/F09 özelliği:** Öncelikle tam 48 EK-20 hücresinin gerçek PDF piksel ROI haritalaması ve görsel gözden geçirme; sonra kenarlıksız, birleşik başlıklı ve çizgisi kesilmiş tarama tabloları için güvenli yerleşim analizinde karşılaştırmalı insan incelemesi. Bu eksikler kapatılmadan F04/F09 `TAMAM` değildir.

**Test ve nihai doğrulama sırası değişmedi:** Kullanıcı kararı gereği geniş regresyon/gerçek Windows kabul turu bütün özellikler bittikten sonra F14 sırasında yapılır. CI'nin push ile otomatik çalışması bir işlevi tamamlanmış saymaz.


## P1 — F07–F10 ortak kanıt kimliği, kanallar arası sözleşme (özellik geliştirme)

Yeni `canonical_evidence_contract.py`, `claim_evidence_workbench.claim_evidence_record` tarafından
zaten özgün SHA + madde + birebir HTML düğümüyle konumlandırılmış olan **aynı**
gerekçeyi tekrar yorumlamadan tekil JSON sözleşmesine dönüştürür:

- `claim_id`: mevcut kural/değerlendirme gerekçesinin değişmeyen kimliği.
- `evidence_id`: yalnız birebir özgün kaynak konumu gösterilebilirse, belirli
  kaynak belgesi + SHA + span_id + claim_id birleşiminden türetilmiş sabit
  `TRAG-EV1-...` kimliği. Kanıt yoksa **null**.
- `source`: yalnız gerçek kaynak pasajı yeniden doğrulandıysa açıklanan özgün
  HTML URL, madde, hedef fıkra, SHA ve birebir pasaj. Destek ailesinin genel
  linki bireysel şartın kanıtı sayılmaz.
- `amendment_chain.status = NOT_PROVEN_COMPLETE`: revizyonların eksiksizliği
  ispatlanmadı. `review_required` yalnız kayıtta bulunan açık inceleme
  yükümlülüklerini içerir; gelecekteki değişiklikleri keşfetmiş gibi sunmaz.
- `temporal_legal_status = HOLD`, `farmer_fact_status =
  NOT_INDEPENDENTLY_VERIFIED`, `payment_status = HOLD`: kaynak konumu bulunsa
  bile hukukî, olgusal ve ödeme kabulünü yükseltmez.
- Aynı v1 kontratı: Neden sekmesi, indirilebilir rapor, SSS'de kullanıcı
  tarafından **açıkça** seçilen değerlendirme şartı ve
  `POST /api/v1/evidence/evaluation` endpoint'inden döner.
- Flutter `CanonicalClaimEvidence/CanonicalEvidenceIndex` modeli ve istemci
  metodu eklendi; mobil istemci ancak şema, SHA, kanıt kimliği ve resmî HTTPS
  hostu doğruysa özgün kaynak linkini gösterebilir. API değerlendirme çıktısı
  içindeki çiftçi kimliği yerine yalnız kanıt metaverisini döndürür.
- Genel SSS/RAG metin benzerliği, alıntı kırpıntısı veya sadece kaynak başlığı
  **bir gerekçeye veya ödeme maddesine otomatik bağlanamaz**. SSS'de yalnız
  kullanıcının tam `claim_id` seçimi aynı doğrulanmış pasajı açar.


**Mobil arayüz ek adımı:** `DestekProvider` aynı çiftçi/parsel
değerlendirmesi için `/evaluate` ile kanıt endpoint'inin döndürdüğü
`production_year`, tüm `rule_id + support_id + field + exact_claim_text`
kümesini eşitlik kontrolünden geçirir. Farklı, eksik, yinelenen veya
ulaşılamayan kanıt seti `HOLD` kalır. Mobil **Neden?** penceresi
`claim_id`, doğrulanmış kaynak varsa aynı `TRAG-EV1` kanıt kimliği,
özgün SHA, sarı birebir HTML pasajı ve kullanıcı isteğiyle açılan
resmî HTTPS URL'yi gösterir. Doğrulanmamış RAG atıfları yalnız
`HOLD` genel kaynak adayı olarak listelenir, tıklanabilir delil
bağlantısı üretmez. Flutter `url_launcher` bağımlılığı eklendi.
Kaynak arşivi olmayan cihaz, yürürlük/geçerlilik veya ödeme için
bağımsız imza doğrulayan kurum rolüne dönüşmez.

**Tamamlanmadı:** tüm destek kural şartlarının birebir kaynak bağları (F07),
2025/2026/2027 değişikliklerin madde/fıkra seviyesinde uygulanabilirlik ve
iptal zinciri (F08), gerçek 48 EK-20 hücresinin bağımsız görsel onayları
(F04/F09), Flutter ekranında tam akış/rapor/SSS birlikte son kabul (F10),
resmî HTML sayfa içi derin gezinti, PDF/HTML ortak tıklama görüntüleyicisinin
tam kapsamı. Yeni API/Flutter yolu güvenlik entegrasyonunun son testine tabi
olmalıdır; bu kod yazımı bir Windows veya hukukî kabul sonucu değildir.

Sıra F01–F13 özellik tamamlanması → arayüz ve modül bütünleşmesi → en son
F14 kapsamlı regresyon, gerçek Windows kabulü, bağımsız mevzuat incelemesi
ve gerekirse kurumsal güvenlik/onay sistemi. PR #41 DRAFT, main değişmez.


## F04 — Baidu Unlimited-OCR ek OCR motoru (isteğe bağlı, yerel)

- SHA-pinned özgün Resmî Gazete PDF sayfasını 180 DPI yeniden render eden,
  seçilen EK-20 hücre ROI'sini üretim yılı 2026 + gerçek görüntü ve
  ROI RGB SHA'sına bağlayan arayüz/adaptör eklendi.
- Resmî Baidu/Unlimited-OCR Transformers GPU örneğini çalıştıran **ayrı
  yerel Python işçisi** eklendi. Modelin önceden indirilmesi, denetlenmiş
  yerel kod, belirgin yönetici onayı, NVIDIA CUDA ve ayrı Python ortamı
  gerekir. Varsayılan sistem otomatik kurulum veya bulut isteği yapmaz.
- Genel kaynak PDF sayfası ve EK-20 piksel hücresi için ayrı Baidu OCR
  arayüz düğmeleri, Tesseract karşılaştırması, kaynak SHA / işlenen görüntü
  kimliği ve açık **OCR_UNREVIEWED / HOLD** sınırı tanımlandı.
- Çıktılar hiçbir zaman imzalı hücre önerisi, sarı kanıt doğrulaması,
  production-year legal PASS veya ödeme motoruna otomatik aktarılmaz.
- Kaynak projesi ve lisans: https://github.com/baidu/Unlimited-OCR
  (kod MIT; model kartı MIT); bağımlılık/CUDA ve model dağıtımı müşteri
  lisans incelemesine tabidir.
- Windows adım adım hazırlık ve kısıtlar:
  [F04_UNLIMITED_OCR_OFFLINE_INTEGRATION.md](F04_UNLIMITED_OCR_OFFLINE_INTEGRATION.md).

**Dürüst durum:** OCR adaptörünün kodu ve arayüz bağlantıları vardır;
gerçek NVIDIA/Windows cihazında model çalıştırılmadı, 48 hücreye ait
kaynak geometrisi ölçülmedi, iki gerçek insan imzası alınmadı.
Bu nedenle F04/F09 henüz tamamlanmadı. F14 en son.


## PR #41 — G09/G13/G26 özellik geliştirme ve canlı açık iş panosu (12 Ekim 2026)

**Yeni takip altyapısı:** configs/feature_gap_register.json bütün F01–F14
özellik başlıklarını ve tek tek gap_id/P0–P3/durum/çözüm/kapanış ölçütlerini
tutar. Şu an 30 açık mühendislik iş kalemi vardır; 48 EK-20 hücresi ve 2
insan incelemecisi tek tek "tamam" işaretlenmemiştir. Okunabilir
docs/OPEN_FEATURE_GAPS.md dosyası bu kayıt dosyasından
scripts/render_feature_gap_register.py ile yeniden üretilebilir.
Masaüstü Yönetim & Doğrulama sekmesindeki salt-okunur "Geliştirme
Eksikleri ve Çözüm Takibi" paneli, uygulamanın paketindeki yerel kaydı
yeniden okuyabilir; GitHub'daki güncel commit'leri kendi kendine çekmez.

**G09 (F06) özgün HTML düğümü:** Neden? ve SSS'de açık seçilen exact
claim_id kaynak denetiminden geçerse original_html_navigator.py,
yerel arşivdeki resmî HTML baytlarını SHA-256 ve manifest ile yeniden
karşılaştırıp doğru MADDE/GECICI MADDE altında **tek** birebir metin
düğümünü bulur. Özgün düğümün escape edilmiş komşu metnini, sarı
birebir parçasını ve Chrome/Edge gibi destekleyen tarayıcılar için
Text Fragment yönlendirmesini gösterir. Tarayıcı scroll garantisi
verilmez; güvenli yerel düğüm önizlemesi kesin fallback'tir.
Özgün HTML belgesi değiştirilmez. Bu yalnız kaynak **konumu**:
üretim yılı, çiftçi koşulu ve ödeme her zaman ayrı HOLD.
G10 gerçek PDF sayfası/hücre auto-navigasyonu açık kalır.

**G13 (F07) kaynak kapsam listesi:** Neden? bölümünde hesaplanmış
parseldeki bütün tekil şartların sayısı, özgün HTML'de
konumlandırılabilenlerin sayısı ve karşılığı bulunmayan/arşivi eksik
olanların exact claim_id + rule_id + şart metni listelenebilir. Yıllık
hukukî doğrulama veya ödeme onay yüzdesi değildir. Bütün kural
şartlarının curated source mapping'i (G12) hâlâ açık kalır.

**G26 (F13) yanlış sıfır tutar düzeltmesi:** Desktop detay birim
tutarında, raporda ve Flutter toplam/kalem kartlarında null/eksik
tutar **0,00 TL değil Hesaplanmadı** gösterilir. "Resmî rapor"
şeklindeki yanıltıcı arayüz düğmesi bağımsız ön değerlendirme
olarak değiştirildi. Temel simülasyon ve kesin ödeme ayrımı ile
legacy endpoint aktivasyon kapısı (G26/G27) bitmedi.

**Durum:** Feature-first kodlama/arayüz entegrasyonu işlendi.
Gerçek kaynak/satır geometrisi, 48×2 insan onayı, bütün
mevzuat yıl/değişiklik zincirinin kanıtlanması ve Windows/Flutter
çalışma kabulü tamamlanmadı. PR #41 DRAFT, main değişmeden;
F14 son kabul en sona bırakılmıştır.

## 2026-10-13 — Yıllardan bağımsız resmî mevzuat güncelleme/kanıt araştırma hattı

- Kullanıcı gereksinimi artık sabit: tek bir yıla bağlı destek hesaplayıcı değil; seçilen üretim yılı ve bağımsız yayın tarihi aralığındaki ilgili yeni Resmî Gazete karar/tebliğ/PDF eklerini güncelleyip her araştırmayı **asıl PDF sayfası veya orijinal HTML pasajına** götüren yazılım.
- Yeni backend modülleri: updates/gazette_date_pages.py (1–14 günlük resmî DD.MM.YYYY tarih arşivi gezintisi); updates/annual_pdf_pipeline.py (keşfedilmiş özgün PDF SHA, her gerçek sayfanın native/Tesseract OCR inceleme taslağı ve orijinal PNG sayfa render'ı).
- Eski link keşfi sırf URL'de resmigazete/resm geçtiği için her kararı bitkisel destek sanıyordu: artık kaynak başlığı odaklı aday seçimi ve **gerçek HTML anchor bağlantısı bulunduğunda** aynı mevzuatın ek PDF'sini keşfetme var.
- Yeni API uçları yönetici anahtarı altında: POST /admin/legal-updates/refresh-evidence, GET /admin/legal-updates/research-pdf ve GET /admin/legal-updates/research-pdf/{sha256}/page/{page}. İlk uç yalnız kaynak keşfi, SHA arşivi, teknik OCR indeksi; kural/ödeme aktivasyonu değildir.
- Yönetim sekmesine yıl, bağımsız yayın tarihi başlangıç/bitiş, Mevzuatı Güncelle + PDF OCR, belge metninde araştır, gerçek PDF sayfası (180 DPI) ve özgün sayfa URL'si bağlandı. OCR/native metin eşleşmesi turuncu **aday**; sarı onay ve hukukî geçerlilik değil.
- Taranmış PDF sayfasında yerel Tesseract tur+eng TSV sözcük koordinatı kullanılır. Baidu Unlimited-OCR **henüz bu toplu indeksleme hattına otomatik bağlanmadı**; isteğe bağlı ayrı sayfa/hücre aracı olarak mevcuttur.
- Şimdilik tek seferde 14 günlük resmî arşiv aralığı ve belge başına 120/toplam 160 sayfa sınırı vardır. Bu, eksiksiz yıllık Resmî Gazete taraması değildir; eksik sayfalar/HOLD ve hatalar görünür.
- Her somut Neden/SSS/rapor/mobil iddiasının **PDF'deki gerçek madde-paragraf/ROI konumuna tek tıklama** desteği henüz F06/F07/G10/G33 açığıdır. Yıllık PDF araştırma panelinde ilgili gerçek sayfa açılabilir; bütün iddiaların otomatik kanıt bağı henüz yok.
- Güncel gap/çözüm kayıt defteri **34 iş**: docs/OPEN_FEATURE_GAPS.md ve configs/feature_gap_register.json. Yeni kayıtlar: G31 tarihsel tüm RG kapsamı; G32 toplu PDF OCR/resume/Baidu; G33 her iddiadan tam PDF konumuna geçiş; G34 değişiklik/yıl uygulama kapısı.
- Ayrıntılı yürütme kaydı: [ANNUAL_OFFICIAL_GAZETTE_UPDATE_AND_PDF_EVIDENCE.md](ANNUAL_OFFICIAL_GAZETTE_UPDATE_AND_PDF_EVIDENCE.md).

**Değişmeyen sınır:** Gerçek orijinal arşiv, 48 EK-20 hücresi, iki bağımsız insan onayı ve mevzuat değişikliklerinin yıldan yıla hukukî etkisi bitmedi. F14 geniş regression, gerçek Windows/GPU ve bağımsız hukukî onay en sonda. PR #41 DRAFT, main değiştirilmez.
