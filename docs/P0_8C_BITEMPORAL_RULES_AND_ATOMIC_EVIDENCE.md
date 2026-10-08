# P0-8C / P0-8D / P0-8E: Bitemporal Kural Motoru, Atomik Yayın Doğrulayıcı ve Program Bazlı PDF Kanıt Arayüzü

## 1. Giriş ve Amaç

Bu doküman, Issue #22 kapsamındaki temel ürün kabul kriterlerini karşılamak üzere geliştirilen mimari bileşenleri belgeler:

1. **P0-8C (Kod Değiştirmeden Yeni Yıl Kural Motoru)**:
   - Kural ID'leri ve program anahtarları yıl son eklerinden arındırılmış, değişmez (invariant) ID'ler olarak tanımlanmıştır (`BASIC_SUPPORT`, `PLANNED_PRODUCTION`, `WATER_RESTRICTION`, `CERTIFIED_SEED`, `CERTIFIED_SAPLING`).
   - Bitemporal veri modeli: Sistemin keşif anı (`discovered_at`), resmî kararın yayımlanma anı (`published_at`), yasal yürürlük dönemi (`effective_from` .. `effective_to`) ve tarımsal üretim yılı (`production_year`) birbirinden bağımsız olarak saklanır.
   - Tam izolasyon güvencesi: 2029 yılı sorgusu asla 2030 kurallarından etkilenmez. 2030 yılı sorgusu henüz kural yayımlanmamışsa fail-closed olarak `UNKNOWN`/`None` döner; asla 2026 tohum verisine sessizce geri düşmez (zero silent fallback).

2. **P0-8D (Atomik Yayın ve Çakışma Engelleyici - Publish Blocker)**:
   - Çok yıllı kural adayları yayınlanmadan önce `AtomicSnapshotPublisher` tarafından atomik olarak denetlenir.
   - Aynı üretim yılı, aynı ürün ve aynı coğrafya için çakışan yürürlük pencerelerinde farklı tutarlar bulunursa yayın derhal engellenir (`PUBLISH BLOCKED`).
   - Her yayın paketi için deterministik kanonik JSON SHA-256 manifest özeti üretilir.
   - Her kuralın veritabanında doğrulanmış bir `source_sentence_id` (PDF cümle koordinat kanıtı) referansına sahip olması zorunludur.

3. **P0-8E (Program Bazlı PDF Kanıt API'si ve Gradio Arayüzü)**:
   - `GET /api/v1/grounding/program/{program_key}?year=2030&crop_code=BUĞDAY` uç noktası ile herhangi bir destek programı ve ürün için doğrudan orijinal PDF sayfası ve fosforlu sarı işaretli koordinatlar getirilir.
   - Gradio PC paneline eklenen "Kural/Program Seçimi" modu sayesinde kullanıcılar karmaşık ID'ler girmek zorunda kalmadan tek tıkla ilgili desteğin Resmî Gazete dayanağını ve sarı işaretli sayfasını görüntüleyebilir.

---

## 2. Bitemporal Veri Şeması

```python
@dataclass(frozen=True)
class BitemporalRule:
    rule_id: str                      # Örn: RULE_2030_BASIC_WHEAT
    program_key: str                  # Değişmez: BASIC_SUPPORT
    crop_code: str                    # Değişmez: BUĞDAY
    production_year: int              # Tarımsal Üretim Yılı: 2030
    province: str                     # "*" veya İl adı
    district: str                     # "*" veya İlçe adı
    base_coefficient: Decimal         # 540.00
    category_multiplier: Decimal      # 1.0000
    official_unit_amount: Decimal     # 540.00 TL/da
    unit: str                         # TRY/da
    effective_from: date              # 2030-01-01
    effective_to: date | None         # 2030-12-31
    published_at: datetime            # 2029-12-25T10:00:00Z
    discovered_at: datetime           # 2029-12-26T08:00:00Z
    source_document_sha256: str       # Orijinal Resmî PDF SHA-256
    source_sentence_id: int           # sentence_bounding_boxes.id
    conditions: dict[str, Any]        # Deklaratif DSL şartları (all_of)
    review_status: str                # DRAFT / VERIFIED
```

---

## 3. Doğrulama ve Test Sonuçları

Tüm sistem testleri pytest ile koşturulmuş ve tam başarı sağlamıştır:

```bash
& .venv\Scripts\pytest.exe backend/tests/ -q
# 256 passed, 1 warning in 57.16s (100% Başarı)
```

- **P0-8C Bitemporal Engine Birim Testleri**: 6/6 Başarılı ([`test_p0_8c_bitemporal_engine.py`](file:///c:/Users/seydieryilmaz/Tar%C4%B1mRAGProje/backend/tests/unit/test_p0_8c_bitemporal_engine.py))
- **P0-8D Atomic Publisher Birim Testleri**: 4/4 Başarılı ([`test_p0_8d_atomic_publisher.py`](file:///c:/Users/seydieryilmaz/Tar%C4%B1mRAGProje/backend/tests/unit/test_p0_8d_atomic_publisher.py))
- **P0-8C Program Bazlı Grounding API Entegrasyon Testleri**: 2/2 Başarılı ([`test_p0_8c_grounding_by_program_api.py`](file:///c:/Users/seydieryilmaz/Tar%C4%B1mRAGProje/backend/tests/integration/test_p0_8c_grounding_by_program_api.py))
- **Tüm Önceki Regresyon Testleri**: 244/244 Başarılı.

---

## 4. Güvenlik ve Hukuki Sorumluluk Notu

Otomatik olarak taranan, ayrıştırılan ve çıkarılan yeni yıl (2029/2030) kural ve tutar adayları veritabanında `DRAFT` statüsünde saklanır. Bağımsız iki yetkili kamu görevlisinin Ed25519 kriptografik imzası ve S3 WORM kanıtı tamamlanmadan hiçbir aday canlı hesaplamada ödeme tutarına (`payable_amount`) dönüştürülmez.
