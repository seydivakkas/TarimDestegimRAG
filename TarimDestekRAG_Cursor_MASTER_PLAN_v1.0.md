# TarımDestekRAG — Cursor Master Plan v1.0

> **Tek kaynaklı proje planı / Cursor çalışma sözleşmesi**
>
> Proje: **TarımDestekRAG — Türkiye Bitkisel Üretim Destekleri için Kaynaklı Uygunluk ve Başvuru Asistanı (2026 MVP)**
>
> Hedef platform: **Flutter mobil uygulama + Python/FastAPI backend**
>
> Bu dosya proje boyunca **ana teknik referans** kabul edilir. Cursor ile geliştirme yapılırken görevler bu dosyada tanımlanan sıraya, mimari sınırlara, test kapılarına ve kapsam kararlarına göre yürütülmelidir.
>
> 📌 **Tek Kaynak (Canonical Source):** Bu planın yetkili ana kopyası [`MASTER_PLAN.md`](file:///c:/Users/seydieryilmaz/TarımRAGProje/MASTER_PLAN.md) dosyasıdır. Değişiklikler ana dosyada tutulmalıdır.

---

# 0. Projenin Kısa Tanımı

TarımDestekRAG, Türkiye'deki 2026 bitkisel üretim desteklerine ilişkin resmî kaynakları otomatik olarak toplayıp sürümleyen; çiftçi ve parsel bilgilerini deterministik uygunluk kurallarıyla değerlendiren; tahmini destek miktarını hesaplayan ve kararlarını kaynak gösteren RAG tabanlı bir karar destek sistemidir.

Sistemin temel kullanıcı sorusu:

> **“Hangi tarımsal desteklerden yararlanabilirim, neden, yaklaşık ne kadar destek alabilirim ve başvuru için ne yapmam gerekiyor?”**

Teknik kanıt zinciri:

```text
Official Sources
    ↓
Web Scraping
    ↓
ETL / Normalization
    ↓
Versioning / Change Detection
    ↓
Structured Data
    ↓
Rule Engine
    ↓
Eligibility
    ↓
Calculator
    ↓
Information Retrieval
    ↓
RAG Explanation
    ↓
Citation Verification
    ↓
Flutter Mobile App
    ↓
Benchmark / Evaluation
```

---

# 1. Ana Mimari İlkesi

## 1.1 Değiştirilemez kural

```text
LLM != Eligibility Decision
```

LLM:

- destek uygunluğu kararı vermez,
- destek tutarını kendi başına hesaplamaz,
- mevzuat kuralı uydurmaz,
- eksik veriyi tahmin etmez,
- resmî olmayan kaynaktan hüküm çıkarmaz.

LLM yalnızca:

- rule engine çıktısını açıklar,
- ilgili resmî kaynağı retrieve eder,
- gerekçeyi insan dilinde ifade eder,
- eksik bilgi/belgeleri açıklar,
- kaynak/citation üretir.

Uygunluk kararı **deterministik Rule Engine** tarafından verilir.

---

# 2. Sistem Bileşenleri

| Bileşen | Teknoloji | Sorumluluk |
|---|---|---|
| Mobile Client | Flutter / Dart | Kullanıcı arayüzü, profil/parsel girişi, sonuç gösterimi |
| API | FastAPI | Mobil istemci ile backend arasındaki sözleşme |
| Scraper | Python | Resmî kaynakları toplama |
| Change Detector | Python | Kaynak değişikliklerini tespit etme |
| ETL | Python | Ham veriyi normalize etme |
| Structured DB | SQLite → PostgreSQL opsiyonel | Kurallar, tarihler, miktarlar, ürün/konum verileri |
| Retrieval Index | BM25 + Dense / FAISS | Mevzuat ve açıklama retrieval |
| Rule Engine | Python | Uygunluk kararı |
| Calculator | Python Decimal | Tahmini destek hesabı |
| RAG | Python | Kaynaklı açıklama |
| Evaluation | Pytest + benchmark scripts | Doğruluk, retrieval ve freshness ölçümü |

---

# 3. MVP Kapsamı — Freeze

## 3.1 V1'de desteklenecek programlar

1. **Temel Destek**
2. **Planlı Üretim Desteği**
3. **Sertifikalı Tohum Kullanım Desteği**
4. **Sertifikalı / Standart Fidan Kullanım Desteği**
5. **Yeraltı Su Kısıtı Desteği**

## 3.2 V1 dışında

- Hayvancılık
- Arıcılık
- IPARD
- KKYDP yatırım hibeleri
- Tarım kredileri
- TARSİM
- Organik Tarım
- İyi Tarım Uygulamaları
- Biyolojik / biyoteknik mücadele
- Genel tarımsal yetiştiricilik chatbotu
- Hastalık teşhisi
- Pestisit reçetesi
- Gübre doz önerisi

---

# 4. Kullanıcıya Verilecek Temel Fonksiyonlar

MVP şu 6 sorgu ailesini eksiksiz çözmelidir:

1. **Hangi desteklere uygun görünüyorum?**
2. **Bu desteğe neden uygun / uygun değilim?**
3. **Ne kadar destek alabilirim?**
4. **Başvurmak için hangi belgeler gerekiyor?**
5. **Uygunluk değerlendirmesi için hangi bilgilerim eksik?**
6. **Şu anda başvurabileceğim destekler hangileri?**

Ek kritik özellik:

```text
What am I missing?
```

Sistem karar için gerekli alan eksikse tahmin yapmak yerine eksik alanı istemelidir.

---

# 5. Uygunluk Durumları

Binary karar kullanılmayacak.

```text
ELIGIBLE
REVIEW
NOT_ELIGIBLE
```

Mobil UI karşılığı:

| Internal | UI |
|---|---|
| ELIGIBLE | Uygun görünüyor |
| REVIEW | Ek kontrol gerekiyor |
| NOT_ELIGIBLE | Uygun görünmüyor |

`REVIEW` şu durumlarda kullanılabilir:

- eksik bilgi,
- resmî kaynağın yorum gerektirmesi,
- kaynağın güncelliğinin doğrulanamaması,
- iki resmî kaynak arasında çelişki,
- kuralın deterministik olarak değerlendirilememesi.

---

# 6. Kaynak Politikası

## 6.1 Öncelik sırası

```text
P0 — Resmî Gazete
P1 — Tarım ve Orman Bakanlığı
P2 — Bakanlık Genel Müdürlükleri
P3 — İl / İlçe Tarım ve Orman Müdürlükleri
```

## 6.2 Yasak kaynaklar

Aşağıdaki kaynaklar uygunluk, tutar veya tarih için primary source olamaz:

- blog,
- forum,
- haber sitesi,
- sosyal medya,
- kişisel web sitesi.

## 6.3 Source model

```text
source_id
url
authority
title
content_type
publication_date
effective_from
effective_to
scraped_at
content_hash
version
superseded
priority
active
```

Her deterministic rule bir `source_id` ile izlenebilmelidir.

---

# 7. Structured DB vs Vector Retrieval

## 7.1 Structured DB'de tutulacaklar

```text
support_type
year
crop
province
district
basin
area_da
amount
unit
category
application_start
application_end
cks_required
irrigation_condition
eligibility_requirements
source_id
effective_from
effective_to
```

Örnek:

> “2026 fındık temel desteği kaç TL/da?”

Bu sorgu vector search kullanmamalıdır.

## 7.2 Retrieval / Vector tarafında tutulacaklar

```text
mevzuat açıklamaları
başvuru şartlarının doğal dil metni
belge gereksinimleri
gerekçe metinleri
tanımlar
istisnalar
SSS
rehber metinleri
```

Örnek:

> “Bu desteğin şartları nelerdir?”

Bu sorgu retrieval + RAG kullanabilir.

---

# 8. Temel Veri Modeli

## 8.1 Farmer

```text
farmer_id
province
district
cks_status
age_group
gender
```

Not: `age_group` ve `gender` yalnızca ilgili destek kuralında gerekiyorsa kullanılmalıdır.

V1'de:

- TC kimlik no yok
- banka bilgisi yok
- gereksiz kişisel veri yok

## 8.2 Parcel

```text
parcel_id
farmer_id
crop
area_da
irrigation
production_year
```

## 8.3 SupportProgram

```text
support_id
year
name
support_type
unit_amount
unit
application_start
application_end
source_id
```

## 8.4 EligibilityRule

```text
rule_id
support_id
field
operator
value
result_if_true
result_if_false
source_id
effective_from
effective_to
```

## 8.5 Source

```text
source_id
url
authority
title
publication_date
effective_from
effective_to
scraped_at
content_hash
version
superseded
```

---

# 9. Rule Engine Contract

Her rule aşağıdaki contract'a uymalıdır:

```text
rule_id
support_id
required_inputs
condition
passed
failed
missing_fields
source_ids
trace
```

Örnek:

```text
RULE BASIC_SUPPORT_2026

IF
    production_year == 2026
AND cks_status == true
AND crop != null
THEN
    evaluate category
    calculate amount
```

Planlı üretim örneği:

```text
IF
    production_year == 2026
AND cks_registered == true
AND crop IN strategic_crops
AND crop IN basin_supported_products
THEN
    ELIGIBLE
```

Rule engine:

```text
0 LLM call
```

ile çalışabilmelidir.

---

# 10. Calculator Contract

LLM matematik yapmayacak.

Örnek:

```text
estimated_support = eligible_area_da × unit_amount
```

Kullanılacak:

```text
Decimal
```

Çıktı:

```json
{
  "area_da": 12.4,
  "unit_amount": 465,
  "estimated_amount": 5766,
  "formula": "12.4 * 465",
  "unit": "TRY"
}
```

Her kullanıcıya şu uyarı gösterilmelidir:

> Tahmini ön değerlendirmedir; resmi ödeme veya hak sahipliği sonucu değildir.

---

# 11. RAG Contract

Input:

```text
EligibilityResult
+
Failed / Passed Rules
+
Retrieved Evidence
```

Output:

```text
status
reason
missing_requirements
next_action
sources
```

Prompt temel kuralı:

```text
Never change the eligibility decision.
Never invent a regulation.
Never invent a missing user field.
Use only supplied evidence.
If evidence is insufficient, return INSUFFICIENT_EVIDENCE.
```

---

# 12. Citation Contract

Her önemli mevzuat iddiası:

```text
Claim
 ↓
Source
 ↓
Document
 ↓
Page / Section
 ↓
Publication date
 ↓
Effective date
```

ile izlenebilmelidir.

Kontroller:

```text
source exists
document exists
chunk exists
source active
effective date valid
source not superseded
claim supported
```

Failure:

```text
INSUFFICIENT_EVIDENCE
```

---

# 13. Freshness / Versioning

Pipeline:

```text
URL
 ↓
Fetch
 ↓
Canonicalize
 ↓
Content Hash
 ↓
Compare previous
 ↓
NEW / UNCHANGED / UPDATED / REMOVED
 ↓
Version old data
 ↓
Normalize
 ↓
Update structured DB
 ↓
Re-index affected chunks
```

Eski veri silinmemelidir.

```text
effective_to
superseded = true
```

ile saklanmalıdır.

Amaç:

```text
2024 kuralı ≠ 2026 kuralı
```

---

# 14. Repository Yapısı

```text
tarim-destek-rag/
│
├── README.md
├── MASTER_PLAN.md
├── .gitignore
├── .env.example
│
├── backend/
│   ├── pyproject.toml
│   ├── src/
│   │   └── tarim_destek_rag/
│   │       ├── api/
│   │       ├── scraper/
│   │       ├── parser/
│   │       ├── normalization/
│   │       ├── database/
│   │       ├── models/
│   │       ├── rules/
│   │       ├── eligibility/
│   │       ├── calculator/
│   │       ├── retrieval/
│   │       ├── rag/
│   │       ├── citations/
│   │       ├── evaluation/
│   │       ├── config/
│   │       └── logging/
│   │
│   └── tests/
│       ├── unit/
│       ├── integration/
│       └── regression/
│
├── mobile/
│   ├── pubspec.yaml
│   ├── lib/
│   │   ├── app/
│   │   ├── core/
│   │   ├── data/
│   │   ├── domain/
│   │   ├── features/
│   │   └── shared/
│   └── test/
│
├── configs/
│   ├── sources.yaml
│   └── app.yaml
│
├── data/
│   ├── raw/
│   ├── normalized/
│   ├── snapshots/
│   ├── indexes/
│   └── benchmark/
│
├── benchmark/
│   ├── cases.jsonl
│   └── results.csv
│
└── docs/
    ├── architecture.md
    ├── data_sources.md
    ├── rule_catalog.md
    ├── api_contract.md
    └── benchmark_protocol.md
```

---

# 15. Cursor Çalışma Protokolü

Cursor'a hiçbir zaman:

> “P8'i komple yap.”

denmemelidir.

Doğru yöntem:

```text
P8.1
→ implement
→ test
→ review
→ PASS
→ P8.2
```

Her görev sonunda Cursor şunları raporlamalıdır:

```text
TASK:
FILES CREATED:
FILES MODIFIED:
TESTS:
TEST RESULT:
ACCEPTANCE CRITERIA:
KNOWN LIMITATIONS:
STATUS: PASS / FAIL
```

Kurallar:

1. Mevcut mimariyi izinsiz değiştirme.
2. Yeni dependency eklemeden önce nedenini açıkla.
3. Bir sonraki alt göreve otomatik geçme.
4. Test başarısızsa görevi PASS sayma.
5. Gerçek resmî veri yerine uydurma production verisi yazma.
6. Test fixture'larında sentetik veri kullanılabilir; açıkça `fixture` olarak işaretle.
7. LLM karar üretmemeli.
8. Rule source_id olmadan merge edilmemeli.
9. Değişiklikleri küçük tut.
10. Her görev bağımsız review edilebilir olmalı.

---

# 16. Definition of Done

Bir alt görev ancak:

```text
Implementation complete
AND tests written
AND tests passing
AND acceptance criteria satisfied
AND no unrelated changes
AND docs updated if required
```

ise `PASS` sayılır.

---

# 17. TD-P0 — Project Foundation

## TD-P0.1 Repository Structure

### Amaç

Monorepo dizin yapısını kurmak.

### Yapılacaklar

- root dizin yapısı
- backend/
- mobile/
- configs/
- data/
- benchmark/
- docs/
- root README
- root .gitignore

### Test

- required directories exist
- no accidental generated files committed

### PASS

Repo yapısı freeze ile birebir uyumlu.

---

## TD-P0.2 Python Package

### Amaç

Backend'i import edilebilir Python package yapmak.

### Yapılacaklar

```text
backend/src/tarim_destek_rag/
```

package oluştur.

Minimum:

```text
__init__.py
```

### Test

```python
import tarim_destek_rag
```

çalışmalı.

### PASS

Package clean import edilmeli.

---

## TD-P0.3 Dependency Management

### Amaç

Backend dependency yönetimini kurmak.

### Tercih

`pyproject.toml`

### Başlangıç dependency grupları

Runtime:

```text
fastapi
uvicorn
pydantic
pydantic-settings
httpx
beautifulsoup4
sqlalchemy
```

Test/dev:

```text
pytest
pytest-cov
ruff
mypy
```

RAG dependency'leri P11/P12'den önce eklenmemeli.

### PASS

Fresh environment kurulabilmeli.

---

## TD-P0.4 Configuration

### Amaç

Environment-specific değerleri koddan ayırmak.

### Hedef

```text
backend/src/tarim_destek_rag/config/
configs/app.yaml
.env.example
```

Config örnekleri:

```text
environment
database_url
raw_data_path
snapshot_path
log_level
```

Secret repo'ya girmez.

### Test

- defaults
- env override
- missing required config

---

## TD-P0.5 Logging

### Amaç

Scraper ve backend olaylarını izlenebilir yapmak.

Minimum alanlar:

```text
timestamp
level
component
event
message
```

Daha sonra:

```text
source_id
request_id
```

eklenebilir.

### Test

- log level
- structured message
- exception logging

---

## TD-P0.6 Testing

### Amaç

Pytest altyapısı.

Yapılacaklar:

```text
backend/tests/unit/
backend/tests/integration/
backend/tests/regression/
```

Minimum:

```python
def test_health():
    assert True
```

### PASS

`pytest` exit code 0.

---

## TD-P0.7 Formatting / Lint

### Araçlar

```text
ruff
mypy
```

Kurallar:

- lint clean
- import order
- obvious typing errors blocked

### PASS

```text
ruff check .
mypy ...
```

başarılı.

---

## TD-P0.8 Smoke Test

### Amaç

P0 tamamının birlikte çalışması.

Smoke test:

```text
config loads
package imports
logger works
pytest works
lint works
```

### Gate

```text
TD-P0 PASS
```

olmadan P1 yok.

---

# 18. TD-P1 — Official Source Registry

## P1.1 Source Contract

`SourceDefinition` modeli:

```text
id
url
authority
priority
content_type
active
```

Validation ekle.

## P1.2 Source Priority & Validity

Authority enum:

```text
OFFICIAL_GAZETTE
MINISTRY
GENERAL_DIRECTORATE
PROVINCIAL_DIRECTORATE
```

Priority deterministic olmalı.

## P1.3 Seed Registry

`configs/sources.yaml`

İlk kaynak aileleri:

- Tarım Havzaları
- 2026 destekleme birim fiyatları
- Tohumculuk desteklemeleri
- gerekli resmî mevzuat sayfaları

## P1.4 Source Validator

Kontroller:

```text
valid URL
known authority
content type supported
duplicate source_id absent
priority valid
```

## P1.5 Registry Service

Fonksiyonlar:

```text
get_source(id)
list_active_sources()
list_by_authority()
```

### P1 Tests

- schema validation
- duplicate id
- disabled source
- priority order

### P1 PASS

Tüm scraper kaynakları registry üzerinden tanımlanmalı.

---

# 19. TD-P2 — Ministry Scraper

## P2.1 HTTP Client

Özellikler:

```text
timeout
retry
user-agent
error mapping
```

## P2.2 HTML Acquisition

HTML body + response metadata al.

## P2.3 PDF Acquisition

PDF bytes indir.

MIME ve extension doğrula.

## P2.4 Rate Limit Discipline

Agresif scraping yapılmamalı.

- request spacing
- retry backoff
- timeout
- no crawling explosion

## P2.5 Raw Snapshot Writer

Path:

```text
data/raw/{source_id}/{timestamp}/
```

Kaydet:

```text
content
metadata.json
```

## P2.6 Scraper Orchestrator

Registry'deki active sources:

```text
registry
→ fetch
→ raw snapshot
→ status
```

### P2 Tests

- HTTP mocked success
- timeout
- retry
- invalid MIME
- HTML save
- PDF save
- snapshot metadata

### P2 PASS

En az 3 farklı resmî kaynak tipi reproducible şekilde indirilebilmeli.

---

# 20. TD-P3 — Change Detection

## P3.1 Canonicalization

Hash öncesi içerik normalizasyonu.

HTML için:

- irrelevant whitespace normalize
- dynamic noise mümkünse ayır

PDF için raw binary + extracted representation stratejisi belgeye yazılmalı.

## P3.2 Content Hash

SHA-256.

Aynı canonical content → aynı hash.

## P3.3 State Comparator

Durumlar:

```text
NEW
UNCHANGED
UPDATED
REMOVED
```

## P3.4 Version Event Store

Her change:

```text
source_id
old_hash
new_hash
detected_at
status
```

## P3.5 Supersession Candidate

Bir kaynak değiştiğinde:

- eski kayıt hemen silinmez,
- re-parse queue/candidate oluşturulur,
- valid_to ve superseded daha sonraki normalization aşamasıyla güncellenir.

### P3 Tests

- canonical equivalent
- deterministic hash
- NEW
- UNCHANGED
- UPDATED
- version linkage

### P3 PASS

Değişiklikler deterministic ve audit edilebilir.

---

# 21. TD-P4 — Normalization Schema / ETL Contract

## P4.1 Canonical Entities

Tanımla:

```text
Source
Document
SupportProgram
SupportAmount
ApplicationWindow
EligibilityRequirement
Crop
Location
BasinCrop
WaterRestriction
```

## P4.2 Enums + Units

Örnek:

```text
TRY_PER_DA
ELIGIBLE
REVIEW
NOT_ELIGIBLE
```

## P4.3 Date + Number Normalization

Türkiye tarih biçimleri normalize edilir.

Örnek:

```text
31 Temmuz 2026
→ 2026-07-31
```

Türk sayı formatları güvenli parse edilir.

## P4.4 Crop / Location Aliases

Örnek:

```text
fındık
findik
hazelnut
```

canonical crop ID'ye map edilebilir.

Ancak semantic guess ile yanlış eşleştirme yapılmamalı.

## P4.5 Provenance Contract

Her normalized record:

```text
source_id
source_version
source_fragment
effective dates
```

taşımalı.

## P4.6 Parser Interface

Parser:

```text
RawDocument
→ NormalizedRecords
```

contract'ı.

### P4 Tests

- date fixtures
- money fixtures
- alias fixtures
- provenance required
- invalid unit rejected

### P4 PASS

Parser'lar tek canonical şemaya yazabilmeli.

---

# 22. TD-P5 — Structured Database

## P5.1 Database Engine

MVP:

```text
SQLite
```

Abstraction PostgreSQL geçişine uygun olmalı.

## P5.2 Tables / ORM

Tablolar:

```text
sources
documents
source_versions
support_programs
support_amounts
crops
locations
basin_crop_rules
application_windows
eligibility_requirements
water_restrictions
```

## P5.3 Constraints

- unique source_id
- year validations
- nonnegative amounts
- valid date ranges
- FK source references

## P5.4 Repositories

Repository pattern.

Örnek:

```text
SupportRepository
SourceRepository
BasinRepository
```

## P5.5 Query Services

Destekle:

```text
get support amount
get application window
get basin crop relation
get active source
```

## P5.6 Migration Strategy

MVP'de lightweight migration yaklaşımı.

### P5 Tests

- CRUD
- constraints
- FK
- known query
- duplicate rejection

### P5 PASS

Rule Engine'in ihtiyaç duyacağı structured queries hazır.

---

# 23. TD-P6 — 2026 Support Dataset

## P6.1 Basic Support Parser

2026 temel destek miktarları normalize edilir.

## P6.2 Planned Production Dataset

Ürün/havza/konum ilişkileri.

## P6.3 Certified Seed Dataset

- eligible crops
- amount/formula
- conditions
- dates
- documents

## P6.4 Certified / Standard Sapling Dataset

- conditions
- dates
- material type
- documents

## P6.5 Water Restriction Dataset

- relevant basin/location
- crop rule
- conditions

## P6.6 Data Validation

Her record:

```text
source
year
effective date
support id
```

taşımalı.

## P6.7 Dataset Snapshot

Versioned output:

```text
data/normalized/2026/
```

### P6 PASS — M1

```text
M1 DATA FOUNDATION PASS
```

Şart:

5 destek programının rule-engine için gerekli verileri normalized DB'de bulunmalı.

---

# 24. TD-P7 — Farmer / Parcel Models

## P7.1 Farmer Model

Pydantic model.

## P7.2 Parcel Model

Pydantic model.

## P7.3 Enums

```text
Crop
IrrigationStatus
ProductionYear
```

## P7.4 Validation

Örnek:

```text
area_da > 0
production_year valid
province nonempty
```

## P7.5 Missing Field Detection

Rule-specific missing fields.

Örnek:

```text
certified_seed support
→ seed certificate status missing
```

## P7.6 Privacy Review

Gereksiz sensitive field kaldır.

### P7 PASS

Valid profile + parcel deterministic modele dönüşmeli.

---

# 25. TD-P8 — Rule Engine

## P8.1 Rule Protocol + Decision Trace

Interface:

```text
evaluate(context) -> RuleResult
```

RuleResult:

```text
rule_id
status
passed_checks
failed_checks
missing_fields
source_ids
trace
```

## P8.2 Basic Support Rule

Girdi:

```text
year
cks_status
crop
area
```

Çıktı:

```text
ELIGIBLE / REVIEW / NOT_ELIGIBLE
```

## P8.3 Planned Production Rule

Kontrol:

```text
cks
strategic crop
basin-supported crop
year
```

## P8.4 Certified Seed Rule

Program-specific conditions.

## P8.5 Certified / Standard Sapling Rule

Program-specific conditions.

## P8.6 Water Restriction Rule

Konum + ürün + irrigation koşulları.

## P8.7 Decision Orchestrator

Tek kullanıcı için tüm programları değerlendir.

Output:

```text
support_id
status
reason_codes
missing_fields
source_ids
```

## P8.8 Rule Catalog Audit

Her rule:

```text
source_id != null
effective year valid
test coverage exists
```

### P8 Tests

Her rule için:

```text
positive
negative
missing field
boundary
wrong year
```

### P8 PASS

LLM çağrısı olmadan bütün V1 programları değerlendirilebilir.

---

# 26. TD-P9 — Support Calculator

## P9.1 Calculation Contract

Input:

```text
eligible area
unit amount
rule result
```

## P9.2 Decimal Arithmetic

Float kullanma.

## P9.3 Basic Support Calculation

Unit x area.

## P9.4 Program-specific Formula

Gerekliyse ayrı strategy.

## P9.5 Calculation Trace

Output:

```text
formula
inputs
result
unit
source_id
```

## P9.6 Validation

NOT_ELIGIBLE durumda calculate etme.

### P9 PASS

Benchmark fixtures üzerinde hesaplar deterministik ve tam doğru.

---

# 27. TD-P10 — Benchmark v0 / Decision Engine Gate

## P10.1 Ground Truth Schema

```json
{
  "case_id": "TD-001",
  "year": 2026,
  "province": "...",
  "district": "...",
  "crop": "...",
  "area_da": 10,
  "cks": true,
  "expected_status": "ELIGIBLE",
  "expected_amount": null
}
```

## P10.2 Initial 50 Cases

Dağılım:

```text
15 Basic
15 Planned
7 Seed
7 Sapling
6 Water Restriction
```

## P10.3 Benchmark Runner

Tek komut:

```text
run decision benchmark
```

## P10.4 Metrics

```text
Eligibility Accuracy
Rule Coverage
Missing Field Accuracy
Calculation Accuracy
```

## P10.5 Failure Report

Her yanlış case:

```text
case id
expected
actual
failed rule
trace
```

## P10.6 Regression Gate

P8/P9 değişiklikleri benchmark'ı bozamaz.

### P10 PASS — M2

```text
DECISION ENGINE PASS
```

P10 geçmeden retrieval/RAG geliştirilmez.

---

# 28. TD-P11 — Document Chunking

## P11.1 Document Extraction

HTML/PDF parsed text.

## P11.2 Heading-aware Chunking

Önce heading/section boundaries.

## P11.3 Fixed Token Fallback

Heading yoksa token-based fallback.

## P11.4 Chunk Metadata

Her chunk:

```text
chunk_id
document_id
source_id
title
section
page
effective_date
support_type
year
text
```

## P11.5 Traceability

Chunk → source document geri izlenebilmeli.

## P11.6 Index-ready Dataset

`data/indexes/input/`

### P11 PASS

Her chunk citation-ready.

---

# 29. TD-P12 — Retrieval

## P12.1 Retriever Protocol

Interface:

```text
search(query, filters, k)
```

## P12.2 BM25 Baseline

Lexical retrieval.

## P12.3 Dense Retrieval

Embedding + FAISS.

Embedding modeli MVP'de multilingual/Turkish-capable seçilmeli.

Model seçimi benchmark ile gerekçelendirilmeli.

## P12.4 Metadata / Freshness Filter

Filter:

```text
year
support_type
effective date
active source
not superseded
```

## P12.5 Hybrid Retrieval

BM25 + dense.

Fusion:

```text
RRF
```

veya belgelenmiş basit weighted fusion.

## P12.6 Retrieval Benchmark

Ground truth questions.

Metrics:

```text
Hit@1
Hit@3
Hit@5
MRR
```

## P12.7 Strategy Freeze

BM25 / Dense / Hybrid sonuçlarına göre production retrieval seç.

### P12 PASS

Production retrieval yaklaşımı ölçümle seçilmiş olmalı.

---

# 30. TD-P13 — RAG Explanation

## P13.1 LLM Adapter

Provider/model abstraction.

## P13.2 Context Builder

Input:

```text
rule result
decision trace
retrieved chunks
```

## P13.3 Prompt Template

Kurallar:

```text
do not change decision
do not invent eligibility
do not invent documents
cite evidence
abstain if unsupported
```

## P13.4 Response Schema

```text
status
summary
reason
missing_information
next_steps
citations
```

## P13.5 Unsupported Evidence Behavior

```text
INSUFFICIENT_EVIDENCE
```

## P13.6 Consistency Test

Rule Engine result:

```text
NOT_ELIGIBLE
```

ise RAG answer bunu tersine çeviremez.

### P13 PASS

LLM deterministic kararı sadece açıklar.

---

# 31. TD-P14 — Citation Verification

## P14.1 Citation Resolver

Citation → chunk → document → source.

## P14.2 Source Validity

Kontrol:

```text
active
not superseded
correct effective year
```

## P14.3 Claim-support Check

Basit ilk sürüm:

- citation existence
- source text availability
- keyword/evidence consistency

Daha gelişmiş NLI evaluator opsiyonel.

## P14.4 Citation Formatter

Mobil için structured citation.

## P14.5 Unsupported Claim Guard

Desteksiz claim işaretlenir.

## P14.6 Metrics

```text
Citation Accuracy
Unsupported Claim Rate
```

### P14 PASS — M3

```text
RAG PASS
```

Karar + açıklama + kaynak zinciri doğrulanmış olmalı.

---

# 32. TD-P15 — FastAPI

## P15.1 App Bootstrap

FastAPI app + versioning.

## P15.2 Health

```text
GET /health
```

## P15.3 Eligibility

```text
POST /eligibility
```

## P15.4 Calculate

```text
POST /calculate
```

## P15.5 Ask

```text
POST /ask
```

## P15.6 Supports

```text
GET /supports
GET /supports/open
```

## P15.7 Sources

```text
GET /sources
```

## P15.8 Error Contract

Structured errors:

```text
code
message
details
```

### P15 PASS

Swagger üzerinden end-to-end backend flow çalışmalı.

---

# 33. TD-P16 — Flutter Mobile UI

Flutter MVP'dir. Backend logic Flutter'a taşınmaz.

## P16.1 API Client + Models

Dart models:

```text
Farmer
Parcel
EligibilityResult
SupportResult
Citation
```

HTTP client.

## P16.2 Farmer Profile Screen

Alanlar:

```text
province
district
cks status
```

Gerekirse diğer relevant fields.

## P16.3 Parcel Screen

```text
crop
area
irrigation
production year
```

## P16.4 My Supports

Card list:

```text
Temel Destek        Uygun görünüyor
Planlı Üretim       Uygun görünmüyor
Fidan               Ek kontrol gerekiyor
```

## P16.5 Support Detail

Göster:

```text
status
estimated amount
conditions
missing fields
deadline
```

## P16.6 Why? + Citations

Kullanıcı:

```text
"Neden?"
```

tıklayınca:

- RAG açıklaması,
- source title,
- publication/effective date,
- document section.

## P16.7 State / Error UX

State:

```text
loading
success
empty
validation error
network error
server error
insufficient evidence
```

## P16.8 Navigation + Accessibility

Minimum:

```text
Profile
Parcel
My Supports
Support Detail
```

Accessibility:

- readable typography
- touch targets
- semantic labels
- color-only status kullanma

### P16 PASS

Teknik olmayan kullanıcı onboarding → result → why/citation akışını tamamlayabilmeli.

---

# 34. TD-P17 — Benchmark v1

## P17.1 Final 100 Cases

Dağılım:

```text
30 Basic Support
25 Planned Production
15 Certified Seed
15 Certified / Standard Sapling
15 Water Restriction
```

## P17.2 Decision Metrics

```text
Eligibility Accuracy
Rule Coverage
```

## P17.3 Calculation Metric

```text
Amount Calculation Accuracy
```

## P17.4 Retrieval Metrics

```text
Hit@1
Hit@3
Hit@5
MRR
```

## P17.5 RAG / Citation Metrics

```text
Citation Accuracy
Unsupported Claim Rate
```

## P17.6 Freshness Metric

Eski/güncel kaynak scenarios.

```text
Freshness Accuracy
```

## P17.7 Latency

```text
rule latency
retrieval latency
generation latency
end-to-end latency
```

## P17.8 Results Export

```text
benchmark/results.csv
benchmark/report.md
```

Sahte sonuç yasak.

### P17 PASS

Tüm final metrikler reproducible runner ile üretilmiş olmalı.

---

# 35. TD-P18 — Final Portfolio Release

## P18.1 Problem & Scope

README ilk ekranında gerçek problem.

## P18.2 Architecture

Göster:

```text
Scraping
ETL
Versioning
Rules
Retrieval
RAG
Flutter
Evaluation
```

## P18.3 Reproduction

Kurulum adımları.

## P18.4 Data Sources / Provenance

Kaynak listesi ve neden resmî oldukları.

## P18.5 Benchmark Results

Gerçek tablolar:

```text
Decision metrics
Retrieval metrics
Citation metrics
Latency
```

## P18.6 Case Studies

En az:

```text
Basic support
Planned support
Missing information
Superseded source
```

case'leri.

## P18.7 Limitations / Safety

Açıkça belirt:

- official decision system değildir,
- tahmini ön değerlendirme,
- 2026 V1 scope,
- data freshness dependency,
- final eligibility official institution.

## P18.8 Release Hygiene

- clean git
- secrets absent
- tests green
- README links valid
- screenshots current
- tags/releases

### P18 PASS

Repo recruiter / jüri tarafından clone edilip anlaşılabilir ve yeniden üretilebilir.

---

# 36. Milestone Gates

```text
P0 → P1 → P2 → P3 → P4 → P5 → P6
==================================
M1 — DATA FOUNDATION PASS
==================================

P7 → P8 → P9 → P10
==================================
M2 — DECISION ENGINE PASS
==================================

P11 → P12 → P13 → P14
==================================
M3 — RAG PASS
==================================

P15 → P16
==================================
M4 — PRODUCT PASS
==================================

P17 → P18
==================================
M5 — FINAL PORTFOLIO RELEASE
==================================
```

---

# 37. Test Stratejisi

## Unit

Test et:

```text
models
normalizers
rules
calculator
hashing
repositories
retrieval helpers
citation helpers
```

## Integration

Test et:

```text
scraper → raw
raw → normalized
normalized → DB
profile → rule engine
rule → calculator
rule + retrieval → RAG
API → services
```

## Regression

Özellikle:

```text
known eligibility cases
known amounts
known source versions
known supersession behavior
```

## Mobile

Flutter:

```text
model parsing
API client
form validation
state transitions
widget tests
```

---

# 38. Benchmark İlkeleri

Ground truth manuel doğrulanmış olmalı.

Her case:

```text
case_id
input
expected status
expected amount
expected source
notes
```

Metric formülleri belgelenmeli.

Sahte başarı oranı yazılmamalı.

---

# 39. Security / Privacy

V1:

```text
no national identity
no bank account
no password storage
no unnecessary PII
```

API:

- input validation
- request size limits
- secrets env
- logs sensitive-data free

---

# 40. Failure Modes

## Source unavailable

```text
retry
→ fail safely
→ preserve previous active version
→ log
```

## Conflicting official sources

```text
priority
+
effective date
+
REVIEW if unresolved
```

## Missing user field

```text
REVIEW
+
missing_fields
```

## No RAG evidence

```text
INSUFFICIENT_EVIDENCE
```

## Outdated source

Do not use for active decision if superseded.

---

# 41. 2242 Uyumlu Araştırma Çerçevesi

Proje sadece uygulama değil, ölçülebilir araştırma/mühendislik çalışması olarak ele alınmalı.

## Araştırma Soruları

### RQ1
Deterministik Rule Engine, LLM-only uygunluk yaklaşımına göre daha güvenilir midir?

### RQ2
Hybrid retrieval, BM25 ve dense retrieval'a göre resmî mevzuat retrieval'ında daha yüksek başarı sağlıyor mu?

### RQ3
Kaynak sürümleme ve effective-date filtreleme eski mevzuat kaynaklı yanlış cevapları azaltıyor mu?

### RQ4
Citation verification unsupported claims oranını düşürüyor mu?

## Deneyler

```text
Rule Engine vs LLM-only
BM25 vs Dense vs Hybrid
Freshness ON vs OFF
Citation Guard ON vs OFF
```

## Çıktılar

```text
Eligibility Accuracy
MRR
Hit@K
Citation Accuracy
Unsupported Claim Rate
Freshness Accuracy
Latency
```

---

# 42. Özgün Değer

Bu proje:

```text
"Tarım desteklerini hesaplayan app"
```

olarak konumlandırılmamalıdır.

Özgün teknik bileşim:

```text
Official-source scraping
+
change detection
+
legal/administrative versioning
+
structured eligibility
+
decision trace
+
RAG explanation
+
citation verification
+
benchmark
+
mobile delivery
```

Ana değer:

> Güncel resmî bilgiyi sadece bulmak değil; geçerlilik tarihini ve kaynağını takip ederek deterministik uygunluk kararına dönüştürmek ve bu kararı kullanıcıya kanıtıyla açıklamak.

---

# 43. Cursor için Alt Görev Prompt Şablonu

Her görevde şu şablonu kullan:

```text
You are implementing TarımDestekRAG.

Current task:
TD-PX.Y — <task name>

Read MASTER_PLAN.md first.

Rules:
- Work only on this subtask.
- Do not implement later phases.
- Do not change frozen architecture.
- Do not add dependencies unless required and justified.
- Write tests for the task.
- Run relevant tests.
- Do not fabricate official production data.
- Preserve source provenance.
- Never move eligibility logic into an LLM.

Deliver:
1. Summary
2. Files created
3. Files modified
4. Tests added
5. Test results
6. Acceptance criteria check
7. Known limitations
8. STATUS: PASS or FAIL

Stop after this subtask.
```

---

# 44. İlk Cursor Görevi

Cursor'a ilk verilecek görev:

```text
TD-P0.1 — Repository Structure
```

Prompt:

```text
Read MASTER_PLAN.md completely.

Implement only TD-P0.1 Repository Structure.

Create the frozen monorepo directories and root placeholder files described in the master plan.

Do not:
- initialize backend application logic,
- add scraper logic,
- add Flutter screens,
- add RAG dependencies,
- implement P0.2 or later.

Add a minimal verification test/script if useful to check required paths.

Return:
- files created,
- tree,
- verification result,
- STATUS PASS/FAIL.

Stop after P0.1.
```

---

# 45. Proje Boyunca Kırmızı Çizgiler

Cursor aşağıdakileri yapmamalıdır:

```text
❌ LLM eligibility
❌ fake benchmark
❌ fake official data
❌ unsupported citations
❌ latest-source assumption without dates
❌ broad feature creep
❌ implementing Pn+1 before Pn PASS
❌ silently changing schema
❌ hiding failed tests
❌ putting business rules in Flutter
```

---

# 46. Son Ürün Akışı

Kullanıcı mobil uygulamayı açar:

```text
Profile
 ↓
Parcel
 ↓
Backend Eligibility
 ↓
Rule Engine
 ↓
Estimated Support
 ↓
My Supports
 ↓
Why?
 ↓
RAG Explanation
 ↓
Official Citation
```

Örnek ekran mantığı:

```text
TEMEL DESTEK
Uygun görünüyor

Tahmini:
5.766 TL

[Neden?]
[Kaynağı Gör]
```

---

# 47. Final Başarı Tanımı

Proje ancak şu zincir gerçek veri ve gerçek testlerle çalışıyorsa tamamlanmış sayılır:

```text
Official source
      ↓
Scrape
      ↓
Change detection
      ↓
Normalize
      ↓
Structured DB
      ↓
Farmer profile
      ↓
Rule evaluation
      ↓
Eligibility
      ↓
Calculation
      ↓
Evidence retrieval
      ↓
RAG explanation
      ↓
Citation verification
      ↓
FastAPI
      ↓
Flutter
      ↓
100-case benchmark
      ↓
README evidence
```

---

# 48. Freeze

Bu dosya **TarımDestekRAG Cursor Master Plan v1.0**'dır.

Kapsam değişikliği gerekiyorsa:

1. önce gerekçe yazılır,
2. etkilenen phase belirlenir,
3. benchmark etkisi değerlendirilir,
4. bu dosyanın versiyonu artırılır,
5. ardından implementasyon yapılır.

Aksi durumda mevcut plan değiştirilmeden uygulanır.

## Başlangıç noktası

```text
TD-P0.1 Repository Structure
```

## Nihai nokta

```text
TD-P18.8 Release Hygiene
```

## Çalışma prensibi

```text
ONE SUBTASK
→ IMPLEMENT
→ TEST
→ REVIEW
→ PASS
→ NEXT SUBTASK
```
