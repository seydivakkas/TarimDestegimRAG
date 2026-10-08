# TarımDestekRAG — Sistem Mimarisi

> **Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)**  
> **ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR**

---

## 1. Mimari Genel Bakış

TarımDestekRAG, Türkiye'deki 2026 bitkisel üretim desteklerine ilişkin mevzuat hükümlerini ve çiftçi verilerini deterministik olarak işleyen, hibrit RAG destekli bir karar destek sistemidir.

```text
Resmî Kaynaklar (Resmî Gazete, BÜGEM)
           │
           ▼
[Web Scraper & Change Detector (SHA-256)]
           │
           ▼
[ETL & Normalizasyon Motoru]
           │
           ▼
┌───────────────────────────────┬───────────────────────────────┐
│  Deterministik Yapılandırılmış │  Semantik & Sözcüksel İndeks  │
│          Veritabanı           │          (FAISS + BM25)       │
│           (SQLite)            │                               │
└──────────────┬────────────────┴───────────────┬───────────────┘
               │                                │
               ▼                                ▼
       [Rule Engine (Sıfır LLM)]        [Hibrit Arama (RRF)]
               │                                │
               ▼                                │
       [Support Calculator (Decimal)]           │
               │                                │
               └───────────────┬────────────────┘
                               │
                               ▼
                   [Template RAG Explainer]
                               │
                               ▼
                 [Citation Verifier Guard]
                               │
               ┌───────────────┴───────────────┐
               ▼                               ▼
       [FastAPI Backend]               [PC Web Arayüzü (Gradio)]
               │
               ▼
     [Flutter Mobil Uygulaması]
```

---

## 2. Değiştirilemez İlke: Zero-LLM Karar Motoru

Sistemde uygunluk kararları ve tutar hesaplamaları için **asla yapay zeka/LLM tahmini kullanılmaz**:

```text
LLM != Eligibility Decision
```

1. **Karar Determinizmi:** Uygunluk kuralları (`BasicSupportRule`, `PlannedProductionRule`, `CertifiedSeedRule`, `CertifiedSaplingRule`, `WaterRestrictionRule`) saf Python mantığıyla çalışır.
2. **Kuruş Hassasiyeti:** Tüm parasal büyüklükler Python `decimal.Decimal` ile hesaplanır. Kayan noktalı (`float`) yuvarlama hatası imkansızdır.
3. **Atıf ve Kanıt Koruması:** `CitationVerifier`, her açıklamanın geçerli ve mülga olmayan 2026 Resmî Gazete maddesine dayandığını denetler; desteksiz iddiaları (%0 halüsinasyon) engeller.

---

## 3. Hibrit Arama ve Bilgi Getirme (Hybrid Retrieval)

Bilgi getirme motoru, sözcüksel ve yoğun anlamsal aramayı **Reciprocal Rank Fusion (RRF)** ile birleştirir:

- **BM25Plus:** Türkçe özel karakter ve tokenizasyon desteğiyle tam sözcük eşleştirmesi.
- **Dense Vector:** `paraphrase-multilingual-MiniLM-L12-v2` embedding modeli ve `faiss-cpu` indeksi.
- **RRF Formülü:**

$$RRF\_Score(d) = \frac{w_{\text{dense}}}{60 + \text{rank}_{\text{dense}}(d)} + \frac{w_{\text{bm25}}}{60 + \text{rank}_{\text{bm25}}(d)}$$

---

## 4. Kullanıcı Arayüzleri

1. **PC Web Arayüzü (Gradio):** 9 sekmeli masaüstü yönetim paneli:
   - Tekil Parsel Değerlendirme
   - Destek Karşılaştırma
   - Mevzuat Soru-Cevap
   - Çoklu Parsel Simülasyonu
   - Benchmark v1 Koşucusu
   - Canlı Veritabanı İzleyici
   - Resmî Kaynak Kütüğü
   - Sistem Durumu & Metrikler
   - Master Plan & Lisans
2. **Flutter Mobil İstemcisi (`mobile/`):** Temiz mimari (Clean Architecture) ile geliştirilmiş, Android ve iOS uyumlu, erişilebilir mobil arayüz.
