# P0-8B — Çok Yıllı PDF Bounding-Box ve Dinamik Katsayı Adayları

**Gereksinim kaynağı:** Kullanıcının paylaştığı Çok Yıllı Dinamik Mevzuat Güncelleme ve Görsel PDF Cümle Kanıtlama Master Promptu. Bu paket bunun ilk 3 adımı için kontrollü bir uygulama başlangıcıdır.

**Asıl hedef:** 2029/2030 ve sonraki yıllarda resmî PDF/HTML kaynaklarından, eski sürümleri koruyarak yeni kararları önerebilmek; her kural ve tutarı gerçek belgedeki tam sayfa/cümle ile gösterebilmek. Bu PR bu nihai hedefin tamamı değildir; yeni yıl verisi otomatik yayımlanmaz.

## 1. PDF sayfasında gerçek cümleyi işaretlemek

Dosya: backend/src/tarim_destek_rag/auto_updater/pdf_grounding.py

PDFGroundingEngine.ground() önce gerçek PDF'nin SHA-256 değerini, 1-tabanlı sayfayı, birebir alıntıyı ve sayfadaki tekil metin eşleşmesini doğrular. Eşleşen PDF text quad/rect koordinatlarını döndürür. Sahte cümle, yanlış sayfa, değişmiş belge veya OCR'siz taranmış PDF kanıt sayılmaz.

PDFGroundingEngine.render_highlighted_page() aynı orijinal baytları tekrar doğrular; cümleyi sarı renkle vurgulayıp PNG ya da WebP sayfa görseli üretir. WebP için PyMuPDF anotasyonlu PNG, Pillow ile dönüştürülür. PDF arşivindeki ham baytlar değişmez.

Yeni API:
- GET /api/v1/grounding/evidence/{sentence_id}?year=2030 — resmî kaynak adresi, hash, sayfa numarası, birebir metin, article/paragraph/clause, bbox ve quad.
- GET /api/v1/grounding/image/{sentence_id}/page/{page_num}?year=2030&fmt=webp — sarı işaretli gerçek sayfa görseli.

Bu servisler yalnız önceden kaydedilmiş, özgün kaynağa bağlı id üzerinden çalışır. Çıktıda hukukî onay durumu açıkça **false**, hak ediş tutarı **null** kalır. Bir cümlenin PDF'de bulunması, o hükmün 2030'da yürürlükte olduğunu tek başına kanıtlamaz.

## 2. Veritabanı sözleşmeleri

- source_documents: resmî kaynak kimliği, URL, ham PDF SHA-256, ilgili üretim yılı, arşiv yolu, kaydedilme ve inceleme durumu. Aynı kaynak dosyası birden fazla üretim yılına ait olabilir.
- sentence_bounding_boxes: ilgili PDF'den çıkarılmış birebir metin, metnin hash'i, madde/fıkra/bent, 1-tabanlı sayfa, PDF dikdörtgenleri ve normalized quads.
- dynamic_rate_candidates: yıl bağımsız program_kimliği, ürün, üretim yılı, coğrafya, temel katsayı, kategori çarpanı, belge cümlesi ve önerilen fiyat.

Üç tablo da bağımsız DRAFT araştırma verisi içerir. dynamic_rate_candidates tablosuna VERIFIED veya ELIGIBLE statüsü atanamaz. Üretim şema değişikliği ayrıca yetkili DBA tarafından deployment/sql/p0_8b_create_grounding_and_dynamic_drafts.sql ile incelenerek yapılır. Canlı veritabanında migration uygulanmadı.

## 3. Dinamik katsayı ve kural sözleşmesi

Dosya: backend/src/tarim_destek_rag/rules/dynamic_engine.py

DynamicRateCatalog: üretim yılını kodla 2026'ya sabitlemez; exact Decimal formülüyle temel katsayı × kategori çarpanı hesaplar, sonuç resmî diye girilmiş kaynak tutarla uyuşmazsa hata verir. Kaynak PDF cümlesi staging FK'sı zorunludur. Program kimliğinde zorunlu yıl eki yoktur.

DynamicRuleEngine: yalnız allowlist alanlar ve eq/in koşullarına izin verir. Keyfî Python kodu, eval veya kaynağı bilinmeyen operatör çalıştırılmaz. Eksik ÇKS/ürün/coğrafya bilgisi REVIEW üretir. **DRAFT bileşenin ön izlemesi koşulları sağlasa bile ödeme_amount None**; hiçbir şekilde hak kazanılmış gerçek tutar olarak sunulamaz.

Kullanıcı örneğinde geçen 2029'a ait varsayımsal katsayı, gerçek mevzuat doğrulaması yapılmadan buraya eklenmedi.

## 4. Tek komut ve otomasyon

Önce P0-8A tarayıcısı resmî belgeyi orijinal hash ile arşivler. Ardından geliştirici, kaydedilmiş kaynak id'si ve gerçek PDF sayfa/alinti bilgisi ile scripts/stage_pdf_evidence.py komutunu --apply-draft seçeneğiyle kullanabilir. Bu işlem yalnız yerel, üretim dışı DRAFT staging içindir.

Birim testler 2029/2030 sentetik PDF'sinin doğru sayfasını, gerçek PNG ve WebP baytlarını, dosya tahrifinde güvenli ret, idempotent staging, çok yıllı kayıt tutarlılığı ve hatalı fiyat/rule JSON reddini kapsar. Ayrı FastAPI entegrasyon testleri gerçek endpoint sözleşmesini kontrol eder.

## 5. Hâlâ zorunlu kabul kapıları

1. Resmî Gazete, Bakanlık BÜGEM ve Mevzuat Bilgi Sistemi için tam yıl kapsamı yakalayabilen resmî keşif adaptörleri. Bilinen ana sayfada bağlantı bulmak eksiksiz hukuk taraması değildir.
2. Yeni ve mülga fıkraların gerçek metin diff'i, eski-yeni fiyat/başvuru/havza tablo karşılaştırması ve kaynak sürümünün hukukî yürürlük başlangıcı.
3. OCR, tablo koordinatları ve çok satırlı Türkçe fıkralarda gerçek belgelerle bağımsız doğrulama.
4. Onaylı çok yıllı kural sürümlerinin gerçek DecisionOrchestrator'a güvenli bağlanması, iki gerçek görevli imzası ve dış KMS/HSM/WORM denetimi, geçiş/iptal/geri alma.
5. Hesaplanan her destek kartından onaylı bir sentence_id'ye birincil anahtar bağı; otomatik sayfa/vurgu modalı ve Flutter ekranı.
6. PyMuPDF için AGPL/ticari lisans yükümlülüklerinin hakları saklı tutulan ürün lisansına uygunluğu. Kodun kaynak projesi özel lisans olarak korunuyor.

Takip: [P0-8 master hedef Issue #22](https://github.com/seydivakkas/TarimDestegimRAG/issues/22), [kurumsal kimlik/onay Issue #20](https://github.com/seydivakkas/TarimDestegimRAG/issues/20).

**Önemli:** Bu aşama gerçek bir 2030 mevzuatı keşfettiğini, hukukî onay verdiğini veya otomatik ödeme sistemi oluşturduğunu iddia etmez.
