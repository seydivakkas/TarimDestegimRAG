# TarımDestekRAG — REST API Sözleşmesi (API Contract v1.0)

> **Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)**  
> **ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR**  
> Bu belge, FastAPI arka ucu ile Flutter mobil istemci ve üçüncü taraf entegrasyonları arasındaki HTTP REST veri değişim sözleşmesini tanımlar.

---

## 1. Genel Prensipler

- **Temel URL (Lokal/PC):** `http://127.0.0.1:8000`
- **Temel URL (Android Emülatör):** `http://10.0.2.2:8000`
- **İçerik Tipi:** `application/json; charset=utf-8`
- **Swagger / OpenAPI:** `http://127.0.0.1:8000/docs`
- **Hata Formatı:** RFC-7807 uyumlu deterministik `ApiErrorResponse`

---

## 2. API Endpoint Kataloğu

| Metot | Uç Nokta | Etiket | Açıklama |
|---|---|---|---|
| `GET` | `/health` | Sistem | Servis sağlık durumu |
| `POST` | `/eligibility` | Karar Motoru | 5 program için uygunluk durumları |
| `POST` | `/calculate` | Hesaplayıcı | Destek tutarı hesaplamaları |
| `POST` | `/evaluate` | Birleşik | Karar + Tutar + Türkçe Açıklama |
| `POST` | `/ask` | Soru-Cevap | Doğal dil mevzuat semantik arama (Hybrid) |
| `GET` | `/supports` | Destekler | 2026 destek programları ve başvuru tarihleri |
| `GET` | `/sources` | Kaynaklar | Resmî mevzuat kütüğü ve öncelikleri |

---

## 3. Veri Modelleri ve Şemalar

### 3.1 Çiftçi ve Parsel Girdi Modelleri (`FullEvaluationRequest`)

```json
{
  "farmer": {
    "farmer_id": "TR-42-001",
    "province": "KONYA",
    "district": "KARATAY",
    "cks_status": true,
    "age_group": "30-40",
    "gender": "E"
  },
  "parcel": {
    "parcel_id": "P-101",
    "crop": "BUĞDAY",
    "area_da": "12.40",
    "irrigation": false,
    "production_year": 2026,
    "certified_seed": true,
    "certified_sapling": false
  }
}
```

### 3.2 Uçtan Uca Değerlendirme Yanıtı (`FullEvaluationResponse` - `POST /evaluate`)

```json
{
  "farmer": { ... },
  "parcel": { ... },
  "rules": [
    {
      "rule_id": "RULE_BASIC_SUPPORT_2026",
      "support_id": "BASIC_SUPPORT_2026",
      "support_name": "Temel Destek",
      "status": "ELIGIBLE",
      "passed_checks": [
        "Üretim yılı 2026",
        "ÇKS kaydı mevcut",
        "Ürün tanımlı: BUĞDAY"
      ],
      "failed_checks": [],
      "missing_fields": [],
      "source_ids": ["RG-2026-BITKISEL"],
      "trace": "ÇKS ve ürün koşulları sağlandı."
    }
  ],
  "calculations": [
    {
      "support_id": "BASIC_SUPPORT_2026",
      "status": "ELIGIBLE",
      "area_da": "12.40",
      "unit_amount": "465.00",
      "estimated_amount": "5766.00",
      "unit": "TRY/da",
      "formula": "12.40 da * 465.00 TL/da = 5766.00 TL",
      "source_id": "RG-2026-BITKISEL"
    }
  ],
  "explanations": [
    {
      "support_id": "BASIC_SUPPORT_2026",
      "support_name": "Temel Destek",
      "status": "ELIGIBLE",
      "summary_tr": "Temel Destek programına uygun görünüyorsunuz.",
      "reason_tr": "Çiftçi Kayıt Sistemi (ÇKS) kaydınız aktif ve BUĞDAY üretimi destek kapsamındadır.",
      "calculation_summary_tr": "12.40 da parseliniz için toplam tahmini 5.766,00 TL destek öngörülmektedir.",
      "missing_fields_tr": [],
      "next_steps_tr": "İlçe Tarım Müdürlüğüne ÇKS belgeniz ile başvurabilirsiniz.",
      "citations": [
        {
          "source_id": "RG-2026-BITKISEL",
          "title": "2024-2026 Bitkisel Üretime Yönelik Desteklemeler Kararı",
          "section": "Madde 3 (Temel Destek)",
          "publication_date": "2024-08-29",
          "effective_year": 2026
        }
      ]
    }
  ],
  "total_estimated_amount": "5766.00"
}
```

---

### 3.3 Mevzuat Soru-Cevap İsteği (`POST /ask`)

**İstek:**
```json
{
  "question": "2026 yılında buğday için temel destek dekar başına kaç TL?",
  "top_k": 3
}
```

**Yanıt:**
```json
{
  "question": "2026 yılında buğday için temel destek dekar başına kaç TL?",
  "summary_answer_tr": "Sorunuza ilişkin mevzuatta bulunan madde (Madde 3):\n\n\"2026 yılı bitkisel üretim desteklerinde buğday ve arpa için dekar başına 465 TL temel destek ödemesi yapılır.\"\n\nResmî Kaynak: 2024-2026 Bitkisel Üretime Yönelik Desteklemeler Kararı (2026)",
  "matched_chunks": [
    {
      "chunk_id": "chunk_001",
      "source_id": "RG-2026-BITKISEL",
      "title": "2024-2026 Bitkisel Üretime Yönelik Desteklemeler Kararı",
      "section": "Madde 3",
      "page": 1,
      "text": "2026 yılı bitkisel üretim desteklerinde buğday ve arpa için dekar başına 465 TL temel destek ödemesi yapılır.",
      "effective_year": 2026,
      "support_type": "BASIC_SUPPORT"
    }
  ],
  "source_titles": [
    "2024-2026 Bitkisel Üretime Yönelik Desteklemeler Kararı"
  ]
}
```

---

## 4. Hata Yönetimi (`ApiErrorResponse`)

Tüm hata durumlarında tutarlı JSON gövdesi döner:

```json
{
  "code": "HTTP_422",
  "message": "Validation Error",
  "details": {
    "field": "area_da",
    "issue": "Alan değeri pozitif bir sayı olmalıdır"
  }
}
```
