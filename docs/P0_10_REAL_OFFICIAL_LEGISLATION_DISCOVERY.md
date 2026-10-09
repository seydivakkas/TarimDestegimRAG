# P0-10: Gerçek Resmî Mevzuat Keşfi ve Yapısal Sınıflandırma

> **Özel Lisans:** Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas). Tüm Hakları Saklıdır.  
> Bu yazılım yalnızca görüntüleme ve eğitim amaçlıdır; izinsiz ticari veya ticari olmayan kullanımı, çoğaltılması veya dağıtılması yasaktır.

---

## 1. Amaç ve Kapsam

P0-10 geliştirme paketi, TarımDesteğimRAG sisteminin Resmî Gazete ve Tarım ve Orman Bakanlığı portallarından çekilen ham mevzuat metinlerini (PDF veya HTML) otomatik olarak ayrıştırmasını, hukuki türlerine göre sınıflandırmasını, ek tablolarını ve yürürlük tarihlerini tespit etmesini sağlar.

Bu paket sayesinde sistem, 2026 yılı ve gelecekteki yıllarda (2027–2030+) yayımlanacak mevzuat belgelerini yalnızca birer ikili dosya (blob) olarak değil, **anlamsal ve yapısal olarak zenginleştirilmiş mevzuat varlıkları** olarak keşfeder ve kataloglar.

---

## 2. Temel Mimari Bileşenleri

### 2.1 Mevzuat Veri Modelleri (`legislation_models.py`)
- **`LegislationType`**:
  - `CUMHURBASKANI_KARARI` (Örn: 2024/8859 sayılı Karar)
  - `BAKANLIK_TEBLIGI` (Örn: 2024/39 sayılı Bitkisel Üretim Tebliği)
  - `DEGISIKLIK_TEBLIGI` (Örn: 2025/42 sayılı Değişiklik Tebliği)
  - `YONETMELIK` (Örn: Çiftçi Kayıt Sistemi Yönetmeliği)
  - `EK_TABLO` (Müstakil yayımlanan ek tablolar)
  - `GENELGE` (Uygulama talimatları)
  - `BILINMEYEN` (Tanınamayan formatlar)
- **`TableKind`**:
  - `SUPPORT_RATES`: Temel/Planlı destek birim tutarları ve katsayılar
  - `WATER_RESTRICTION`: Su kısıtı olan havzalar/ilçeler ve istisnalar
  - `PLANNED_PRODUCTION`: Planlı üretim kapsamındaki ürün listeleri
  - `SEED_SAPLING`: Sertifikalı tohum ve fidan destekleri
  - `GENERAL`: Diğer idari ve teknik tablolar
- **`LegislationIdentity`**: Belge türü, başlığı, tebliğ/karar sayısı, Resmî Gazete tarihi, sayısı ve düzenleyen otorite.
- **`EffectiveDateInfo`**: Yürürlük tarihi (ISO), yürürlük maddesi metni, geçerli üretim yılları listesi, yayımı tarihinde yürürlüğe girme ve geriye yürüme bayrakları.
- **`AmendmentTarget`**: Değişiklik tebliğleri için ana mevzuat referansı (başlık, no, RG tarihi/sayısı) ve değiştirilen maddeler listesi.
- **`AnnexTableInfo`**: Ek tablo kodu (EK-1, EK-2, EK-3), başlığı, türü, sayfa numarası ve sayfa içerik SHA-256 hash'i.
- **`DiscoveredLegislation`**: Uçtan uca çözümlenmiş mevzuat nesnesi, `review_status="DRAFT_DISCOVERED"`.

### 2.2 Yapısal Çözümleme Motoru (`legislation_analyzer.py`)
- **Türkçe Harf Duyarlı Normalizasyon (`_turkish_lower`)**:
  - Python'ın standart `.casefold()` metodunun `"İ"` karakterini `"i\u0307"` (birleştirici noktalı) yapması sonucu `"DEĞİŞİKLİK"` aramasının başarısız olmasını engeller.
  - Türkçe ünsüz yumuşamasını (`yönetmelik` -> `yönetmeliği`) tolere eder.
- **Tarih ve Sayı Çıkarımı**:
  - Hem Türkçe yazılı ayları (`24 Ağustos 2024`) hem de eğik çizgili tarihleri (`24/8/2024`) standart ISO `YYYY-MM-DD` biçimine normalize eder.
- **Değişiklik Hedefi ve Madde Tespiti**:
  - `... tarihli ve ... sayılı Resmî Gazete'de yayımlanan ... Tebliği (Tebliğ No: ...)'in ... maddesi` desenlerini bütünüyle yakalar.
- **Ek Tablo Sınıflandırması**:
  - Belge sayfalarındaki `EK-1`, `EK-2`, `EK-3` başlıklarını içeriklerine göre `SUPPORT_RATES`, `WATER_RESTRICTION`, `PLANNED_PRODUCTION` vb. kategorilere ayırır.

### 2.3 İçerik Adresli Mevzuat Kataloğu (`legislation_repository.py`)
- `data/legal_update_archive/legislation_catalog/{sha256}.json` altında atomik olarak saklanır.
- Yıl ve mevzuat türüne göre hızlı filtreleme, listeleme ve tekil SHA-256 ile tam analiz yükleme yetenekleri sunar.

### 2.4 Resmî Tarama Entegrasyonu (`discovery.py`)
- `scan_official_sources` fonksiyonu indirilen her ham veriyi otomatik olarak `LegislationAnalyzer` motorundan geçirir.
- Oluşan `DiscoveredLegislation` kataloğa yazılır ve tarama özetine `legislation_analysis` sözlüğü olarak eklenir.

---

## 3. Güvenlik ve Hukuki Bütünlük (Fail-Closed)

1. **Taslak İzolasyonu**: Keşfedilen tüm mevzuat kayıtları `DRAFT_DISCOVERED` statüsünde saklanır.
2. **Sıfır Otomatik Hak Ediş**: Tarama motoru hiçbir koşulda doğrudan hesaplama katsayılarını veya ödeme tutarlarını güncellemez (`payable_amount = None`).
3. **İki Yetkili İmzası Şartı**: Keşfedilen mevzuat ve tablolar, P0-5 / P0-7 HSM ve WORM tabanlı iki bağımsız yetkili onayı tamamlanmadan kural motoruna bağlanamaz.

---

## 4. REST API ve Gradio Admin Entegrasyonu

### 4.1 REST API Uç Noktaları
- `GET /admin/legal-updates/legislation?year=2026&legislation_type=BAKANLIK_TEBLIGI`: Yapısal mevzuat listesi.
- `GET /admin/legal-updates/legislation/{document_sha256}`: Maddeler, ek tablolar ve yürürlük detayları.
- `POST /admin/legal-updates/analyze-raw`: Metin veya base64 PDF içeriğini anında yapısal analizden geçirme uç noktası.

### 4.2 Gradio Admin UI
- Admin doğrulama sekmesinde (`frontend_pc/pages/admin_validation.py`) resmî tarama çalıştırıldığında keşfedilen mevzuatın:
  - Mevzuat Türü ve Numarası
  - Resmî Gazete Tarihi ve Sayısı
  - Yürürlük Tarihi
  - Değişiklik Hedefi ve Değiştirilen Maddeler
  - Tespit Edilen Ek Tablolar (EK-1, EK-2, EK-3)
  kullanıcıya zengin Markdown biçiminde raporlanır.

---

## 5. Doğrulama ve Testler

- **Test Paketi**: `backend/tests/unit/test_p0_10_legislation_discovery.py`
  - `test_classify_legislation_types`: Karar, Tebliğ, Değişiklik Tebliği, Yönetmelik doğrulaması.
  - `test_extract_identity_from_presidential_decision`: 8859 sayılı Karar alanları.
  - `test_extract_identity_from_communique`: 2024/39 sayılı Tebliğ alanları.
  - `test_extract_effective_dates_and_production_years`: 2025–2027 üretim yılları ve 1/1/2025 yürürlük tarihi.
  - `test_extract_amendment_targets`: 2025/42 Değişiklik tebliğinin 2024/39'a atıfları ve MADDE 6, 16, EK-3 tespitleri.
  - `test_extract_annex_tables`: EK-1, EK-2, EK-3 tablo türleri.
  - `test_legislation_catalog_repository`: Kayıt, yükleme, filtreleme.
  - `test_scan_official_sources_with_legislation_analysis`: Tarama boru hattı entegrasyonu.
  - `test_api_legislation_endpoints`: Yetkili/yetkisiz API ve anında metin analizi.
- **Regresyon Güvencesi**: 345 testin tamamı hatasız geçmiş, Ruff lint kontrolü 0 hata vermiştir.
