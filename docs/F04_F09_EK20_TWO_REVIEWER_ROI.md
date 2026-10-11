# F04 + F09 — EK-20 gerçek hücre ROI ve iki bağımsız görsel inceleme

**Durum: Özellik altyapısı geliştirme dalında. 48 gerçek ROI için imzalanmış inceleme tamamlanmadı.**
Bu belge resmî mevzuat tasdiki ya da ödeme yetkisi değildir.

## Kanıt katmanları

1. **Özgün kaynak:** Yalnız manifestte tanımlı, SHA-256 bütünlüğü tekrar kontrol edilmiş
   RG_AMENDMENT_2025_42_ANNEX PDF. Sayfa 1; 2026 taslak aktarım.
2. **Görüntü:** PDF orijinal bytes -> PyMuPDF 180 DPI -> RGB görüntüsü. Görüntü
   boyutu, tüm sayfanın RGB hash'i, piksel kutusu ve kesilmiş hücrenin RGB hash'i
   birlikte kaydedilir; ekran ölçeğinden / HTML boyutundan koordinat üretilmez.
3. **Hücre önermesi:** Tam olarak bir (row_id, field) ile bağlanan x0,y0,x1,y1
   koordinatları. Mevcut raster ızgara bulucu aday üretebilir fakat otomatik
   görsel-aktarım eşlemesi ve OCR çıktısı onay sayılamaz. Çizgisiz veya karmaşık
   tabloya sahte ızgara eklenmez. Yönetici / incelemeci gerçek özgün sayfaya
   bakarak **elle** koordinat önerir. Turuncu işaret = onaysız konum önerisi.
4. **Birinci/ikinci inceleme:** İki ayrı kayıtlı **gerçek kişi**, birbirinden
   bağımsız iki farklı Ed25519 anahtarı ve farklı primary / independent rolleri
   ile **aynı** kaynak SHA + sayfa RGB SHA + ROI RGB SHA + konum + ürün/satır
   + alan + taslak değeri ve birimini ayrı ayrı imzalar. Anahtarın kriptografik
   farklılığı gerçek kişilerin bağımsızlığının tek başına kanıtı DEĞİLDİR;
   kurum yöneticisi kimlik, yetki ve farklı kişileri ayrıca doğrulamalıdır.
5. **Görsel sonuç:** İki geçerli ve aynı ROI'ye bağlı APPROVE imzası bulunursa
   yalnız **görsel hücre / metin aktarımı teyidi** için sarı işaretli,
   özgün PDF'den yeniden oluşturulan ekran görüntüsü. Eksik imza, farklı
   kaynak hash'i, farklı ROI, eski kaynak, REJECT, imza bozulması, anahtar
   iptali, yinelenen kimlik veya kaynak yoksa HOLD; sarı işaret YOK.
6. **Hukukî sonuç:** Üretim yılına göre yürürlük, diğer değişikliklerin
   uygulanabilirliği, çiftçi olguları, ödeme ve tarife aktivasyonu daima ayrı
   ve HOLD. Görsel doğrulamanın başarıya ulaşması ödeme aktivasyonu değildir.

### 12 × 4 envanter

İncelenecek 12 satır x 4 alan toplam **48 ayrı hücre kaydıdır**:
biological_tl_da, biotechnical_tl_da, feromone_trap_tl_da ve
feromone_only_tl_da. Orijinalde tutar bulunmayan değer **JSON null**
olarak korunur; 0 TL'ye çevrilmez, sahte sayı OCR'la tamamlanmaz.
Satırın ürün/zararlı başlığını da iki kişi gerçek görsel üzerinde kontrol
etmelidir; sadece sayısal kutuyu imzalamak diğer koşulları doğrulamaz.

UI: Destek Analizi > Neden > EK-20 incelemesi.
- Bir ürün/alan seçin. Doğrulanmış tek sayfalık gerçek PDF görüntüsünü izleyin.
- 180 DPI **gerçek piksel** ROI koordinatlarını girip turuncu önizlemeyi açın.
  Önizleme henüz kanıt veya inceleme kaydı değildir.
- 48 alan durumunu gösteren envanteri açın. Hiçbir başvuru / hak ediş
  hesabına bu taslak değerleri otomatik bağlamayın.

## Windows — yerel reviewer anahtarları ve registry

Her gerçek incelemeci, kendi korumalı alanında (proje klasörü **dışında**)
ayrı bir özel anahtar oluşturur. Örnek PowerShell komutları:

~~~powershell
python scripts/generate_ek20_reviewer_key.py --reviewer-id incelemeci_a --output-dir "C:\EK20-Guvenli-Inceleme-A"
python scripts/generate_ek20_reviewer_key.py --reviewer-id incelemeci_b --output-dir "C:\EK20-Guvenli-Inceleme-B"
~~~

**Özel anahtarları GitHub'a, ZIP'e, issue/PR içeriğine veya kullanıcı raporuna
eklemeyin.** Windows dosya izinleri, ayrı insan kimlikleri ve kurum rol
onayı BT/yetkili yönetici sorumluluğundadır. Public key registry uygulamanın
çalıştığı sistemde, yönetici kontrolünde ayrı bir JSON dosyasıdır:

~~~json
{
  "schema_version": 1,
  "reviewers": [
    {
      "reviewer_id": "incelemeci_a",
      "role": "primary",
      "active": true,
      "public_key_pem": "<PEM genel anahtar satır sonları JSON \\n ile>"
    },
    {
      "reviewer_id": "incelemeci_b",
      "role": "independent",
      "active": true,
      "public_key_pem": "<ikinci kişinin GERÇEK PEM genel anahtarı>"
    }
  ]
}
~~~

Yukarıdaki PEM yer tutucuları **geçerli anahtar değildir**. Dosyaya gerçek
genel anahtar metnini güvenli ve JSON-geçerli biçimde yerleştirin. Aynı
anahtarın iki kimliğe verilmesi sistem tarafından reddedilir.

~~~powershell
$env:TARIM_RAG_EK20_REVIEWER_REGISTRY = "C:\EK20-Yonetim\reviewer_registry.json"
~~~

**Registry yoksa veya yetkili anahtarlar geçersizse hiçbir sarı işaret
üretilmez.** Anahtar iptalinde ilgili registry satırını inactive yapın:
eski imzalar da görüntüleme zamanında reddedilir. Kurumsal donanım anahtarı,
WORM ve hukukî onay burada sağlanmış kabul edilmez.

## Gerçek ROI öner ve inceleme kaydı oluştur

**Örnek bir satır/alan kimliği** (rakam koordinatları örneklenmez, asla uydurulmaz).
Orijinal PDF üzerinde elle incelenmiş gerçek 180 DPI koordinatlarını girin:

~~~powershell
python -m tarim_destek_rag.citations.ek20_cell_provenance propose --row-id citrus --field biological_tl_da --bbox <x0> <y0> <x1> <y1>
~~~

Bu komut yalnız doğru orijinal kaynak yerel arşivde mevcutsa
data/ek20_review_proposals/<source_sha>/citrus__biological_tl_da.json
oluşturur; dosyada kaynak URL'si, kaynak digest, sayfa, görüntü hash'i,
kesilmiş ROI hash'i, tam konum, satır, alan, 2026 ve taslak değer bulunur.
Aynı dosya üzerine sessiz yazma yoktur. Yanlış ROI'nin imzalanmasından
önce düzeltme için dosya ayrıca yönetici kontrolünde kaldırılır;
imzalı kararların silinmesi/iptali denetim kaydında ayrıca tutulmalıdır.

İncelemeci A **kendi** özel anahtarıyla, gerçek sayfa ve ROI'yi görsel
olarak kontrol ettikten sonra imzalar:

~~~powershell
python -m tarim_destek_rag.citations.ek20_cell_provenance sign --proposal "data/ek20_review_proposals/<source_sha>/citrus__biological_tl_da.json" --reviewer-id incelemeci_a --private-key "C:\EK20-Guvenli-Inceleme-A\incelemeci_a.private.pem" --decision APPROVE --visual-confirmation
~~~

İncelemeci B de **farklı insan + farklı yetkili özel anahtar** ile aynı
orijinal görüntüyü, satır başlığını, alanı ve ROI metnini bağımsız inceler;
kendi reviewer_id ve özel anahtar yoluyla ayrıca APPROVE veya REJECT
imzalar. Rejected hücrede sarı renk yoktur. Bu CLI'nin
--visual-confirmation parametresi sadece kişinin açık beyanını kaydeder;
insanın gerçekten doğru inceleme yaptığını yazılım bağımsız ispatlayamaz.

Kayıtlar:
data/ek20_signed_reviews/<source_sha>/<row_id>__<field>/<reviewer_id>.json

**Önemli:** Bu klasörler müşteri makinesinde erişim kontrollü, yedekli
ve gerekirse değiştirilemez kayıt sistemi altında işletilmelidir. Proje
git deposuna hiçbir özel anahtar, gerçek onay veya kişisel veri konulmaz.
Yayımlanacak ekran yalnız kanıt statülerini gösterir.

## F04 / F09 kapanış ölçütü

- 48 ayrı alanın *tamamında* orijinal hücre bölgesi gerçek PDF
  piksellerinden belirlenir; yanlış koordinat, birleştirilmiş başlık hücresi
  veya belirsiz değer için AUTO-APPROVE YOK.
- Her alanın taslak sayı/null gösterimi ve satır/kolon anlamı iki gerçek
  kişice görsel olarak doğrulanır; eksiklerin durumu HOLD.
- İki imza aynı cell/source/page/pixel-hash/bbox/metne bağlı değilse
  sarı vurgulu sayfa üretilemez.
- **Ayrı bağımsız hukukî/kurumsal kabul** son F14'te yapılır.
- F07–F10 aşamasında tekil claim_id, uygulanabilir mevzuat ve üretim
  yılı, ortak kanıt kimliği, SSS/rapor/mobil bağlantıları aynı
  fail-closed kurala bağlanır.

Bu yeni işlevler PR #41 DRAFT dalındadır; main ve ödeme hesaplaması
değiştirilmemiştir. Gerçek 48 hücre imzalanmadan F09 tamamlanmış sayılmaz.
