# TarımDestekRAG — Benchmark v1 Değerlendirme Raporu

**Rapor Tarihi:** 2026-10-08
**Test Edilen Vaka Sayısı:** 100
**Lisans:** Özel Lisans — Tüm Hakları Saklıdır (c) 2026 Seydi Eryılmaz (@seydivakkas)

---

## 1. Karar ve Hesaplama Metrikleri (Decision & Calculation)

| Metrik | Hedef | Ölçülen Sonuç | Durum |
|---|---|---|---|
| **Uygunluk Karar Doğruluğu (Eligibility Accuracy)** | %100 | **%100.00** | Vaka verisine göre |
| **Kural Kapsamı (Rule Coverage)** | %100 | **%100.00** | Vaka verisine göre |
| **Tutar Hesaplama Doğruluğu (Decimal Exact Match)** | %100 | **%100.00** | Vaka verisine göre |

> *Bu metrikler depo içindeki beklenen sonuçlara karşı ölçülür; güncel mevzuatla bağımsız karşılaştırma değildir.*

---

## 2. Arama ve Bilgi Getirme Metrikleri (Retrieval Engine)

| Yöntem | Hit@1 | Hit@3 | Hit@5 | MRR | Gecikme |
|---|---|---|---|---|---|
| **Hibrit (BM25 + FAISS + RRF)** | **%100.00** | **%100.00** | **%100.00** | **1.0000** | **44.23 ms** |

---

## 3. RAG Açıklama ve Atıf Doğrulama (Citation & Guardrails)

| Metrik | Hedef | Ölçülen Sonuç | Açıklama |
|---|---|---|---|
| **Atıf Kayıt Geçerliliği (Citation Registry Validity)** | >= %98 | **%100.00** | Tüm atıflarda kayıt, aktiflik ve yıl kontrolü; metinsel kanıt doğrulaması değil |
| **Atıfsız veya Geçersiz Atıflı Açıklama Oranı (Proxy)** | %0.00 | **%0.00** | Anlamsal desteksiz iddia oranı henüz ölçülmüyor |
| **Mevzuat Tazeliği (Freshness Accuracy)** | %100 | **Ölçülmedi** | Kaynak sürümü, yürürlük ve değişiklik kontrolü henüz yok |

---

## 4. Sistem Gecikme Profili (Latency Benchmark)

| Bileşen | Ortalama Süre (ms) |
|---|---|
| **Rule Engine Değerlendirmesi** | 4.42 ms |
| **Hibrit Arama (RRF Retrieval)** | 44.23 ms |
| **Deterministik Açıklama Üretimi** | 0.03 ms |
| **Uçtan Uca (End-to-End Latency)** | **5.06 ms** |

---

## 5. Sonuç

**Sınırlamalar:** Ölçümler depo içi test vakalarına göredir. Atıf kontrolü sadece kaynak kaydı/aktiflik/yıl denetimidir. Mevzuat tazeliği ve iddia-kanıt uyumu ölçülmediği için genel doğruluk veya sıfır halüsinasyon garantisi verilemez.
