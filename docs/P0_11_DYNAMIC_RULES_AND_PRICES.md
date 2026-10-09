# P0-11: Dinamik Kural ve Fiyat Motoru

> **Özel Lisans:** Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas). Tüm Hakları Saklıdır.  
> Bu yazılım yalnızca görüntüleme ve eğitim amaçlıdır; izinsiz ticari veya ticari olmayan kullanımı, çoğaltılması veya dağıtılması yasaktır.

---

## 1. Amaç ve Kapsam

P0-11 geliştirme paketi, P0-10 kapsamında keşfedilen ve yapısal olarak çözümlenen resmî mevzuat belgelerinden (`DiscoveredLegislation`), ek tablolardan (EK-1 Katsayı Tablosu, EK-2 Planlı Üretim Destek Listesi, EK-3 Su Kısıtı Olan Havza/İlçeler Listesi ve sertifikalı girdi cetvelleri) **otomatik olarak deklaratif bitemporal kurallar ve fiyat matrisleri sentezleyen** dinamik kural ve fiyat motorudur.

Bu paket sayesinde sistem:
1. Resmî Gazete'de yayımlanan katsayı ve ek tabloları makinece okunabilir matrislere (`ParsedAnnexMatrix`) dönüştürür.
2. `schema_version=1` biçiminde doğrulanabilir, deklaratif kural sözlükleri (`RuleSynthesizer`) üretir.
3. Çiftçi parselinin tüm destek kalemlerini (`BASIC_SUPPORT`, `PLANNED_PRODUCTION`, `WATER_RESTRICTION`, `CERTIFIED_SEED`, `CERTIFIED_SAPLING`) eşzamanlı ve kuruş hassasiyetinde (`DynamicSupportEvaluator`) değerlendirir.
4. **Fail-Closed Güvenlik İlkesi:** Sentezlenen tüm kuralları `DRAFT` statüsünde başlatır; yetkili çift onaylı WORM imzası olmaksızın `payable_amount` değerinin oluşmasını kesin olarak engeller (`total_payable_amount = None`).

---

## 2. Temel Mimari Bileşenleri

### 2.1 Ek Tablo ve Fiyat Ayrıştırıcı (`table_parser.py`)
- **`normalize_crop_code`**:
  - Türkçe harf ve Unicode birleştirici aksan (`\u0307`) uyumsuzluklarını gidererek 20'den fazla tarımsal ürünü (Buğday, Arpa, Dane Mısır, Yağlık Ayçiçeği, Pamuk, Mercimek, Nohut, Kuru Fasulye, Fındık, Zeytin vb.) kanonik ürün kodlarına eşler.
- **`TableParser` Metotları**:
  - `extract_base_coefficient`: Metin veya tablodaki temel gösterge katsayısını (Örn: `244,00 TL/da`) ayıklar.
  - `parse_support_rates_table` (`parse_rate_table`): EK-1 Temel Destek katsayı satırlarını, ürün kategorilerini ve birim tutarlarını (`official_unit_amount = base_coefficient * category_multiplier`) tam Decimal aritmetiğiyle hesaplar.
  - `parse_planned_production_table` (`parse_planned_crops`): EK-2 Planlı üretim kapsamındaki ürün listelerini ayrıştırır.
  - `parse_water_restriction_table` (`parse_water_restriction`): EK-3 Su kısıtı kapsamındaki 11 il ve 52 ilçeyi (Konya, Aksaray, Karaman, Ankara, Eskişehir vb.) ve teşvik edilen baklagil/yağlı tohum ürünlerini yapılandırır.
  - `parse_annex_matrices`: Tüm ek tabloları tek bir `ParsedAnnexMatrix` nesnesinde birleştirir.

### 2.2 Deklaratif Kural Sentezleyici (`rule_synthesizer.py`)
- **Şema Uyumluluğu (`schema_version=1`)**:
  - `BitemporalRuleCatalog.validate_candidate` tarafından denetlenen 19 zorunlu alanın (rule_id, program_key, crop_code, production_year, base_coefficient, category_multiplier, official_unit_amount, unit, effective_from/to, published_at, discovered_at, source_document_sha256, source_sentence_id, conditions, review_status) tamamını eksiksiz üretir.
- **`_ascii_slug` Regex Güvencesi**:
  - Kural ID'lerinin (`rule_id`) `^[A-Z0-9_]{2,96}$` kalıbına uygun olmasını sağlamak için Türkçe karakterleri ASCII eşdeğerlerine translitere eder (Örn: `BUĞDAY` -> `RULE_2026_BASIC_BUGDAY`).
- **Beş İnvaryant Destek Programı**:
  1. `BASIC_SUPPORT`: Temel ÇKS ve ürün uygunluğu kuralı.
  2. `PLANNED_PRODUCTION`: Planlı üretim ilave destek kuralı.
  3. `WATER_RESTRICTION`: Su kısıtı havzalarında sulamasız (kuru) mercimek, nohut vb. üretim kuralı.
  4. `CERTIFIED_SEED`: Sertifikalı tohum kullanım kuralı.
  5. `CERTIFIED_SAPLING`: Sertifikalı fidan kullanım kuralı.
- **Doğrudan Katalog Derleme (`compile_bitemporal_catalog`)**:
  - Üretilen adayları anında `BitemporalRuleCatalog` motoruna yükler.

### 2.3 Kalıcı Kural Deposu (`dynamic_rule_repository.py`)
- `data/legal_update_archive/rules_catalog/rules_{year}.json` dosya yolunda atomik geçici dosya (`.tmp`) taktiğiyle diske yazar.
- Üretim yılı, program anahtarı, ürün kodu ve inceleme durumuna göre filtreleme sağlar.
- `get_catalog(years)` metoduyla kayıtlı kuralları tek hamlede bitemporal değerlendirme motoruna aktarır.

### 2.4 Çoklu Destek Değerlendirici (`dynamic_support_evaluator.py`)
- `DynamicSupportEvaluator.evaluate_parcel`:
  - Belirtilen parsel parametrelerini (ürün, alan, il, ilçe, ÇKS, sulama, sertifikalı tohum/fidan) 5 program üzerinden değerlendirir.
  - Her kalem için `unit_amount`, `proposed_amount` ve onaylı `payable_amount` değerlerini üretir.
  - **Fail-Closed Garantisi:** Eğer kurallar arasında `DRAFT` statüsünde olan varsa `overall_status = "REVIEW"` ve `total_payable_amount = None` olarak döner. Ödeme yetkisi ancak tüm kurallar `VERIFIED` olduğunda verilir.

---

## 3. REST API Uç Noktaları

| Uç Nokta | Metot | Erişim | Açıklama |
|---|---|---|---|
| `/admin/rules/synthesize` | `POST` | Yönetici (`X-Admin-Key`) | Keşfedilen mevzuattan dinamik kuralları sentezler ve diske kaydeder. |
| `/admin/rules/dynamic` | `GET` | Yönetici (`X-Admin-Key`) | Kayıtlı dinamik kuralları yıl, program ve ürün bazında listeler. |
| `/api/v1/rules/dynamic-evaluate` | `POST` | Genel / Çiftçi | Parsel parametrelerine göre çoklu destek değerlendirmesi yapar (Sıfır LLM, fail-closed). |

---

## 4. PC Ön Yüz (Gradio) Entegrasyonu

`frontend_pc/pages/admin_validation.py` sekmesine **Dinamik Kural ve Fiyat Sentezi** bölümü eklenmiştir:
- Yönetici hedef üretim yılını seçerek tek tıkla mevzuat ek tablolarından kuralları sentezleyebilir.
- Sentezlenen kural sayısı, temel gösterge katsayısı ve özet kural tablosu interaktif DataFrame üzerinde görüntülenir.
- Gradio arayüzünde "DRAFT statüsündeki kuralların onaylanmadan ödemeye dönüşemeyeceği" uyarısı belirgin şekilde vurgulanmıştır.

---

## 5. Test ve Doğrulama

P0-11 test paketi (`backend/tests/unit/test_p0_11_dynamic_rules_and_prices.py`) şu senaryoları kapsar:
1. `TestTableParser`:
   - Türkçe ürün normalizasyonu (`buğday`, `dane mısır`, `kırmızı mercimek` vb.)
   - Temel katsayı gösterge tutarı tespiti
   - EK-1, EK-2 ve EK-3 ayrıştırması
2. `TestRuleSynthesizer`:
   - Bitemporal kural sentezi ve şema doğrulaması (`BitemporalRuleCatalog.validate_candidate`)
   - Bitemporal katalog derleme ve DRAFT fail-closed koruması
3. `TestDynamicRuleRepository`:
   - Atomik kayıt, okuma, filtreleme ve katalog derleme
4. `TestDynamicSupportEvaluator`:
   - Buğday parseli çoklu kalem değerlendirmesi (Temel + Planlı + Tohum)
   - Karapınar mercimek parseli su kısıtı ilave desteği doğrulaması
   - ÇKS kaydı olmayan çiftçinin ret durumu
   - VERIFIED kurallarda tam ödenebilir tutar yetkilendirmesi
5. `TestApiEndpointsP011`:
   - Yetkisiz isteklerin reddi (503 / 403 / 401)
   - `/admin/rules/synthesize` ve `/admin/rules/dynamic` uç noktaları
   - `/api/v1/rules/dynamic-evaluate` uç noktası doğrulaması

**Test Sonuçları:**
- P0-11 testleri: **14/14 BAŞARILI**
- Tüm sistem testleri: **359/359 BAŞARILI (%100 geçiş oranı, sıfır regresyon)**
- Ruff linter: **Temiz (0 hata)**
