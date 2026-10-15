# Yıldan Bağımsız Resmî Gazete Güncelleme ve PDF Kanıt Navigasyonu

## Hedef

TarımDestekRAG hiçbir üretim yılına sabitlenmez. Yönetici Mevzuatı Güncelle komutunu çalıştırdığında tarım destekleri ile ilgili resmî yayınları keşfeder, özgün HTML/PDF dosyalarını arşivler, SHA-256 ile korur, her PDF sayfasını native/OCR metin taslağı olarak indeksler ve araştırmada özgün belgenin gerçek sayfasına yönlendirir.

Üretim yılı ile Resmî Gazete yayım yılı birbirinden bağımsızdır. Örneğin 2025 sonunda yayımlanan bir değişiklik 2026 hükümlerini etkileyebilir; kapsam ve yürürlük OCR metninden otomatik belirlenmez.

## Bu dalda uygulanan işlevler

1. Eski portal tarayıcısında resmigazete URL'sindeki resm kelimesi yüzünden ilgisiz bütün belgeleri aday sayma hatası düzeltildi. Yalnız tarım mevzuatıyla ilişkili görünen resmî belge başlıkları keşfe girer.
2. Resmî Gazete tarih sayfalarında, biçimi DD.MM.YYYY olan resmî arşiv bağlantıları desteklenir. Yönetici yayın başlangıcı ve bitişini YYYY-MM-DD olarak seçebilir; tek işlem 1–14 günle sınırlıdır. Tarih boşsa son yedi gün seçilir. Eski yıl arşivleri aralık aralık araştırılabilir.
3. Ekin adresi tahmin edilmez: HTML ana belgedeki gerçekten bulunan ve aynı belge köküne ait ek PDF bağlantıları ayrıca çekilir.
4. İndirilen resmî PDF, izinli HTTPS hostu, MIME/PDF imzası, URL–SHA envanteri ve gerçek orijinal dosya içeriği eşleşirse sayfa indeksine alınır.
5. Bir işlemde en fazla 160 sayfa, belge başına 120 sayfa işlenir. Tamamlanmayan sayfalar HOLD kalır; büyük belgelere kaldığı yerden devam mekanizması henüz eklenmedi.
6. PDF metin katmanı varsa aslına dayalı metin taslağı çıkarılır; tarama sayfalarda yerel Tesseract tur+eng TSV ile 180 DPI gerçek sözcük koordinatları alınır. Baidu Unlimited-OCR ayrı isteğe bağlı motor olarak mevcuttur, bu toplu otomatik hatta henüz bağlanmadı.
7. Yönetim ve Doğrulama sekmesinde yıllık güncelleme, tarih aralığı, ilgili PDF içinde metin araması, gerçek kaynak URL ve SHA ile sayfa önizlemesi eklendi.
8. Arama sonucu, sayfayı özgün resmî PDF baytlarından yeniden render eder. Metin eşleşmesi turuncu adaydır; kaynağın ilgili yıl için geçerli olduğu veya ödemenin hak edildiği anlamına gelmez.
9. Backend yolları: POST /admin/legal-updates/refresh-evidence, GET /admin/legal-updates/research-pdf, GET /admin/legal-updates/research-pdf/{sha256}/page/{page}. Mevcut yönetici anahtarı gerekir.

## Açık mühendislik sınırları

- G31: Her takvim yılı ve Resmî Gazete sayısı için eksiksiz kurumsal indeks taraması, mükerrer sayılar, eklerin tamlığı ve gün bazında başarı kaydı. Bugünkü sınırlı aralık taraması tam yıllık kapsama eşdeğer değildir.
- G32: Büyük PDF'lerde resume, OCR arızalarında devam, Baidu GPU otomatik OCR fallback ve Windows cihaz kabulü.
- G33 ve G10: Destek Analizi, Neden, SSS, mobil ve raporda HER gerekçenin PDF sayfa + gerçek paragraf/hücre koordinatına tek tıkla otomatik bağlanması. Yıllık araştırma sonucu gerçek PDF SAYFASINA gidebilir, ancak her gerekçe için tam ROI henüz eşlenmedi.
- G34 ve G14/G15: Kaynağın bir üretim yılı için gerçekten geçerli/ilga edilmiş hükmünü ve değişiklik zincirini uzman denetimiyle bağlama.
- G05/G17: EK-20'nin 48 gerçek kaynak hücresini belirleme ve iki farklı gerçek incelemeciden 96 bağımsız okuma imzası toplama.
- Bazı resmî hükümler aslen HTML, ekleri PDF'dir. Gerçekten bulunmayan PDF sayfasını üretmek yasaktır; özgün HTML normatif pasajı ile PDF ek kanıtı kaynak formatına göre ayrı sunulur.

## Çevrimdışılık ve hukukî durum

Yeni resmî belge indirmek için güncelleme anında internet gerekir. Daha önce SHA ile arşivlenmiş PDF ve OCR indeksleri daha sonra offline araştırılabilir. Yerel Tesseract dil modeli yoksa tarama sayfası OCR_ENGINE_MISSING olur. Baidu model kurulumu otomatik yapılmaz.

Yeni OCR metni veya yayın yılı otomatik ödeme katsayısı, yürürlük onayı, kesin destek hakkı veya sarı onaylı alıntı yaratamaz. Tüm hukukî yıl ve ödeme kararları HOLD kalır.

İş kalemleri ve çözümler: [OPEN_FEATURE_GAPS.md](OPEN_FEATURE_GAPS.md). Önce F01–F13; son F14 kapsamlı test, Windows/GPU kabulü ve hukukî incelemedir.

## Belge Analizi & RAG bağlantısı

Yıllık güncellemenin tamamlanmasının ardından backend mevcut kaynak-öncelikli Belge Analizi & RAG indeksini de yeniler. Yıllık araştırma kataloğundaki yeni PDF'ler yalnız gerçek özgün SHA'ları, sayfa numaraları ve arşivlenmiş OCR/native metin taslakları doğrulanabildiği ölçüde soru-cevap aramasına katılır. İlgili yanıtın kaynak bağlantısı orijinal resmî PDF'nin gerçek #page=N konumuna çıkar.

RAG yenilemesi başarısız olursa güncelleme cevabında LOCAL_RAG_REFRESH_HOLD görünür; yeni tarama dosyaları kendiliğinden eski/verili hukukî kuralları veya ödeme onaylarını değiştirmez. OCR taslağı orijinal metin veya üretim yılı için kesin kanıt değildir.

Tam kaynak doğrulaması gerçekleşmeden bütün ilgili PDF parçalarının araştırılabildiği, her hüküm için gerçek alt-paragraf/hücre koordinatının bulunduğu veya bütün tarihsel yıl mevzuatının kapsandığı iddia edilemez.

## RAG yanıtından gerçek sayfaya ulaşma

Belge Analizi & RAG motorundaki yeni keşfedilmiş yıllık PDF alıntısının kaynak kimliği RG_DISCOVERED_ ile başlar. Kaynak doğrulaması geçmişse ekranda özgün Resmî Gazete PDF bağlantısı gerçek #page=N numarasıyla gösterilir. Aynı alıntı için Gerçek sayfa ekran görüntüsü bağlantısı artık yerel /documents/annual-original-page/{sha}/page/{page} adresini kullanır; bu görüntü arşivdeki orijinal PDF piksellerinden anlık oluşturulur ve yalnız yerel uygulama oturumunda erişilir.

Kaynakta OCR ile bulunan ifade tekil madde/fıkra/tutar/hücreyi hukukî açıdan doğrulamış sayılmaz; tam koordinat ve bağımsız değerlendirme hâlâ eksiktir. Tarihsel kapsam eksik ve büyük PDF'ler için devam edebilme işi açık kalır.
