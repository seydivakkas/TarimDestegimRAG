# G33 — Destek Analizi: Her Gerekçeden Özgün PDF/HTML Kaynağına

## İşlevsel hedef ve mevcut kısıt

**İstenen:** Destek Analizi → Neden? ekranındaki her tekil destek şartına
tıklanınca o şartın ilgili yıldaki gerçek mevzuat dayanağına, özgün PDF
sayfasına ve madde/paragraf/tablo hücresine götürülmesi; kanıt gerçekten
yoksa yanlış bağlantı oluşturmadan HOLD gösterilmesi.

Bu turda **her gerekçe için araştırma ve kaynak-adayı önizlemesi** eklendi,
ancak bütün gerekçelerin kesin hukukî kaynak bağlantıları oluşturulmadı.
Çünkü mevcut curated kaynak matrisinde 5 özgün HTML pasajı, bunlara
ait yalnızca **2 tekil 2026 şartı eşleştirmesi** var.
Yeni native PDF kural eşleştirme kayıt defterinde **0** gerçek kayıt var.
Kullanıcının kuralları ve yeni yıllarındaki şart sayısı çalışma sırasında
hesaplanır; bu sayılar tüm kuralların ne kadarının doğrulandığını göstermez.

## Masaüstü kullanımı

1. Çiftçi/parsel için **Destek Analizi** yap.
2. **Neden? → Tekil kural gerekçesini seç** menüsünde sağlanan,
   sağlanamayan veya eksik bilgi şartlarından birini seç.
3. Üstteki kanıt paneli **yalnız birebir rule_id, support_id, production_year,
   field ve exact_claim_text** bağları doğrulanmışsa gerçek mevzuat metnine
   gider: özgün SHA, madde/fıkra ve (HTML'de) gerçek metin düğümünü; native
   PDF'de gerçek sayfa ve 180 DPI metin kutularını gösterir.
4. Kesin bağ bulunmuyorsa **HOLD** görünür. Alt bölümde
   **"Bu tekil gerekçe için özgün belgelerde kaynak araştır"** düğmesi
   mevcut indekslenmiş resmî PDF/HTML kaynaklarını arar.
5. Bir arama adayı seçilince kaynak dosyası SHA ile yeniden doğrulanır.
   PDF'nin gerçek sayfası ve *benzersiz kelime dizisi varsa* gerçek turuncu
   kutular; HTML'nin özgün pasajı gösterilir.
   **Arama benzerliği, "bu mevzuat bu kuralın dayanağıdır" sonucu değildir.**
6. Seçilen gerekçe veya parsel/değerlendirme değişirse eski kaynak-adayı
   seçimi temizlenir; önceki yıldan kanıt taşınmaz.
7. Rapor ve mobil, doğrulanmış HTML/native PDF bağları varsa aynı
   claim_id ve evidence_id üzerinden gerçek kaynak türünü, sayfayı ve
   kaynak URL'sini gösterir. Arama adayları resmî normatif kaynak gibi
   rapora veya mobil hukukî sonuca aktarılmaz.

## Kayıtlar ve doğrulama seviyeleri

### A) Daha önce curator bağları olan özgün HTML

- Dosya: configs/p0_10_7_claim_source_matrix.json
- Kural metni, şart türü, yıl, kaynak kimliği, URL, gerçek SHA,
  madde/fıkra ve birebir quote birlikte eşleşir.
- Yerel özgün HTML arşivi mevcutsa gerçek metin düğümü yeniden
  doğrulanır. Kaynak konumu bulunduğu için metin önizlemesi gösterilir;
  **geçerlilik ve ödeme HOLD**.

### B) Native PDF ile yeni EXACT bağ

- Dosya: configs/claim_pdf_exact_bindings.json
- Şimdilik bindings=[]; **sahte sayfa, alıntı veya ROI eklenmedi**.
- Gerçek bir incelemede aşağıdaki alanlar gerekir:

~~~json
{
  "rule_id": "<GERÇEK_RULE_ID>",
  "support_id": "<GERÇEK_SUPPORT_ID>",
  "production_year": 2026,
  "field": "passed_checks",
  "exact_claim_text": "<DEĞERLENDİRMEDE_KELİMESİ_KELİMESİNE_ŞART>",
  "source_id": "<MANIFEST_VEYA_DOĞRULANMIŞ_ARŞİV_KAYNAK_ID>",
  "source_sha256": "<ÖZGÜN_PDF_SHA256>",
  "source_url": "<DOĞRULANMIŞ_RESMÎ_HTTPS_PDF_URL>",
  "pdf_page": 1,
  "target_provision": "<GERÇEK_MADDE_FIKRA>",
  "exact_quote": "<ÖZGÜN_NATIVE_PDF_METNİNDE_BİREBİR_GEÇEN_ALINTI>"
}
~~~

Bu **yalnız şema örneğidir**, gerçek bağ değildir. Aynı beşli kural
anahtarından iki PDF kayıt önerisi varsa fail-closed. PDF özgün SHA'sı
manifest veya daha önce indirilmiş doğrulanmış yıllık arşivden tekrar
denetlenir. Kaynak sayfadaki native metinde alıntı bir kez bulunmalı,
gerçek PyMuPDF search_for konumları 180 DPI sayfa piksellerine sığmalı.
OCR ile taranmış bir PDF bu kapıdan otomatik kesin kaynak olamaz:
onun için gerçek piksel inceleme, gereken görsel insan onayı ve ayrı
mevzuat bağlamı sözleşmesi gerekir.

### C) Arama benzerliğiyle bulunan RAG/PDF adayları

- Dosya: citations/claim_source_discovery.py.
- Sonuçlar strict selected claim_id'ye bağlı geçici listede tutulur.
- Sadece resmî source_id ve kaynak SHA + chunk ID taşıyan gerçek
  arşiv pasajları seçilebilir. Kullanıcı yüklediği özel belgeler
  resmî kaynak adayı olarak gösterilmez.
- Önizleme citations/rag_exact_location.py üzerinden kaynak baytları
  ve sayfa pikselleri yeniden doğrulanarak üretilir.
- Asla curated mapping JSON'una, kural motoruna veya ödeme katsayısına
  otomatik eklenmez. Kutu **turuncu**, delil/yürürlük/ödeme HOLD.

## Güncel durum / kapanış koşulu

- **Kodlandı:** PC seçili her gerekçe için araştırma, gerçek kaynak adayının
  özgün PDF/HTML konumu; exact curated HTML + native PDF bağının
  ortak kanıt sözleşmesi; rapor/native PDF linki ve mobil kaynak formatı;
  değerlendirme değişince geçici kaynak seçimlerinin sıfırlanması.
- **Bekliyor:** 2025, 2026, 2027 ve sonraki bütün destek kural şartları
  için özgün hüküm/üretim yılı/ilgili PDF/HTML kaynaklarını
  **fiilen** doğrulayıp curated claim binding kayıtlarını doldurma;
  taranmış PDF'lerde onaylı ROI'yi bağlama; 48 EK-20 gerçek hücre
  ve iki gerçek kişi imzası; bütün modüllerde nihai tıklama
  bütünlüğü ve F14 kabul.
- **Kapanış:** Geçerli uygulama envanterindeki her tekil gerekçe,
  doğrudan tekil gerçek kaynak (HTML pasajı, orijinal PDF madde/pasajı,
  incelemecilerle doğrulanmış tablo hücresi) veya açıkça *kanıt henüz yok*
  durumuna atanır; bütün kaynağı bilinenler tıklanıp gerçek konumu
  gösterebilir. İlgili üretim yılı kanıtı ayrı onaylanır.

G33 ve G10 geliştirme aşamasında tutulur. PR #41 **DRAFT** kalır;
özellikler → arayüz bütünleşmesi → en son F14 regresyon, Windows ve
bağımsız hukukî doğrulama.
