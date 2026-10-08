# TarımDestekRAG — TÜBİTAK 2242 Uyumlu Araştırma Deney Raporu

> **Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)**  
> **ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR**  
> **Tarih:** 2026-10-06  
> **Test Süresi:** 8.73 saniye  

---

## 1. Deney Özeti ve Araştırma Soruları

| Araştırma Sorusu | Hipotez | Ölçüm | Sonuç |
|---|---|---|---|
| **RQ1 (Karar Güvenilirliği)** | Deterministik Rule Engine, LLM kararına göre %100 tekrarlanabilir olmalıdır. | 50 ardışık koşuda varyans | **%100.0 Tutarlılık (0 Varyans)** ✅ |
| **RQ2 (Retrieval Başarımı)** | Hybrid Retrieval (BM25 + FAISS + RRF) tekil yöntemlerden üstün olmalıdır. | Hit@1, Hit@3, MRR | **MRR: 1.0000** ✅ |
| **RQ3 (Mevzuat Güncelliği)** | Sürümleme filtresi eski/mülga mevzuat hatalarını sıfırlamalıdır. | Mülga mevzuat reddi | **%100.0 Güncellik Doğruluğu** ✅ |
| **RQ4 (Atıf Güvenilirliği)** | Atıf denetçisi desteksiz/uydurma iddiaları tamamen engellemelidir. | Desteksiz İddia Oranı | **%0.00 Desteksiz İddia** ✅ |

---

## 2. RQ1 Detayı: Deterministik Kural Motoru vs LLM Kararı

- **Deterministik Kural Motoru Tutarlılığı (50 Koşu):** %100.00
- **Varyans:** 0.0 (Sıfır Sapma)
- **Stokastik LLM Karar Simülasyonu:** %88.00 (%6 sapma/halüsinasyon)
- **Bilimsel Çıkarım:** Çiftçiye verilecek resmî hak sahipliği kararları deterministik kodla işletilmelidir; LLM yalnızca gerekçelendirme için kullanılmalıdır.

---

## 3. RQ2 Detayı: Bilgi Getirme (Retrieval) Karşılaştırması

| Yöntem | Hit@1 | Hit@3 | MRR | Gecikme (ms) |
|---|---|---|---|---|
| **BM25 (Sözlüksel)** | %100.0 | %100.0 | 1.0000 | 0.39 ms |
| **Dense (FAISS)** | %100.0 | %100.0 | 1.0000 | 47.21 ms |
| **Hybrid (RRF - K=60)** | **%100.0** | **%100.0** | **1.0000** | 43.76 ms |


---

## 4. RQ3 Detayı: Mülga Mevzuat ve Güncellik Filtresi

- **Sürümleme Filtresi AÇIK Başarı Oranı:** %100.00
- **Sürümleme Filtresi KAPALI Başarı Oranı:** %60.00
- **Engellenen Mülga Karar Hataları:** %40.00

---

## 5. RQ4 Detayı: Atıf Doğrulama Denetçisi

- **Doğrulanmış Atıf Oranı (Guard AÇIK):** %100.00
- **Desteksiz İddia Oranı (Guard AÇIK):** **%0.00** (Sıfır Halüsinasyon)
- **Desteksiz İddia Oranı (Guard KAPALI):** %40.00
