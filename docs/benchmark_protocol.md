# TarımDestekRAG — Değerlendirme ve Kıyaslama Protokolü (Benchmark Protocol v1.0)

> **Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)**  
> **ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR**  
> Bu doküman, TarımDestekRAG sisteminin doğruluğunu, bilgi getirme (retrieval) kalitesini, atıf güvenilirliğini ve gecikme sürelerini ölçen bilimsel benchmark protokolünü ve metrik formüllerini açıklar.

---

## 1. Kapsam ve Örneklem Dağılımı (100 Resmî Test Vakası)

Sistem, 2026 Resmî Gazete destekleme kararı ve havza listelerinden derlenmiş **100 adet doğrulanmış yer gerçeği (ground truth)** vakası üzerinde test edilir (`benchmark/cases.jsonl`):

| Kategori | Vaka Sayısı | İçerik ve Senaryolar |
|---|---|---|
| **Temel Destek (`BASIC`)** | 30 vaka | Buğday, Arpa, Mısır, Fındık, Ayçiçeği, Pamuk; ÇKS'li, ÇKS'siz, eksik ÇKS |
| **Planlı Üretim (`PLANNED`)** | 25 vaka | Konya, Diyarbakır, Samsun, Şanlıurfa, Adana havza içi ve dışı ekimler |
| **Sertifikalı Tohum (`SEED`)** | 15 vaka | Sertifikalı/sertifikasız kullanım, eksik belge incelemesi |
| **Sertifikalı Fidan (`SAPLING`)** | 15 vaka | Kapama meyve bahçesi, >=5 dekar asgari alan sınır testleri |
| **Yeraltı Su Kısıtı (`WATER`)** | 15 vaka | Karatay, Çumra su kısıtı havzaları, mercimek/nohut vs mısır |
| **TOPLAM** | **100 vaka** | **Tüm sınır koşulları ve eksik veri durumları kapsanmıştır** |

---

## 2. Metrik Tanımları ve Matematiksel Formülleri

### 2.1 Uygunluk Karar Doğruluğu (Eligibility Accuracy)
Modelin ürettiği uygunluk durumunun (`ELIGIBLE`, `REVIEW`, `NOT_ELIGIBLE`) yer gerçeği ile uyuşma oranı:

$$\text{Eligibility Accuracy} = \frac{\sum_{i=1}^{N} \mathbb{I}(\hat{y}_i = y_i)}{N} \times 100\%$$

*Burada $N=100$, $\hat{y}_i$ sistemin kararı, $y_i$ yer gerçeği etiketidir.*

### 2.2 Tutar Hesaplama Doğruluğu (Calculation Accuracy)
Uygun görülen vakalarda kuruş hassasiyetinde hesaplanan destek tutarının hatasızlığı:

$$\text{Calculation Accuracy} = \frac{\sum_{i \in \text{Eligible}} \mathbb{I}(\hat{A}_i = A_i)}{|\text{Eligible}|} \times 100\%$$

*Burada $\hat{A}_i$ `decimal.Decimal` hesaplanan tutar, $A_i$ yer gerçeği tutarıdır.*

### 2.3 Bilgi Getirme Başarısı (Retrieval Metrics: Hit@K & MRR)
Mevzuat maddesi aramasında doğru belgenin ilk $K$ sırada gelme oranı ve ortalama ters sıra başarısı:

$$\text{Hit@K} = \frac{1}{|Q|} \sum_{q=1}^{|Q|} \mathbb{I}(\text{rank}_q \le K)$$

$$\text{MRR (Mean Reciprocal Rank)} = \frac{1}{|Q|} \sum_{q=1}^{|Q|} \frac{1}{\text{rank}_q}$$

### 2.4 Atıf Doğruluğu ve Desteksiz İddia Oranı (Citation Verification)
Üretilen açıklamada geçen resmî mevzuat atıflarının geçerliliği ve uydurma iddia içermeme durumu:

$$\text{Citation Accuracy} = \frac{N_{\text{doğrulanmış atıf}}}{N_{\text{toplam atıf}}} \times 100\%$$

$$\text{Unsupported Claim Rate} = \frac{N_{\text{kaynaksız iddia}}}{N_{\text{toplam iddia}}} \times 100\% \quad (\text{Hedef: } 0.00\%)$$

### 2.5 Güncellik Doğruluğu (Freshness Accuracy)
Yürürlükten kalkan mülga kararlar (2024 kararnamesi) ile güncel 2026 kararı arasında güncel olanın seçilme başarısı:

$$\text{Freshness Accuracy} = \frac{N_{\text{güncel kaynak seçimi}}}{N_{\text{test edilen mülga vakalar}}} \times 100\% \quad (\text{Hedef: } 100.00\%)$$

---

## 3. Çalıştırma Protokolü ve Yeniden Üretilebilirlik

Benchmark testi tek komutla çalıştırılır ve sonuçlar diskte kalıcı olarak saklanır:

```bash
# Sanal ortam aktifken:
python backend/src/tarim_destek_rag/evaluation/benchmark_runner_v1.py
```

**Üretilen Dosyalar:**
- `benchmark/results.csv`: 100 vakanın her biri için girdi, beklenen/alınan karar, beklenen/alınan tutar, eşleşme durumu ve milisaniye bazında işlem gecikmesi.
- `benchmark/report.md`: Konsolide özet tablosu, başarı oranları ve sistem donanım bilgisi.

---

## 4. Gerçek Ölçüm Sonuçları (Resmî Koşu)

| Metrik | Hedef | Ölçülen Değer | Durum |
|---|---|---|---|
| Karar Doğruluğu (Eligibility) | >= 95.0% | **%100.00** (100/100) | ✅ PASS |
| Tutar Doğruluğu (Calculation) | >= 99.0% | **%100.00** (61/61) | ✅ PASS |
| Kaynak Atıf Doğruluğu | >= 95.0% | **%100.00** (100/100) | ✅ PASS |
| Desteksiz İddia Oranı | == 0.0% | **%0.00** (Sıfır Halüsinasyon) | ✅ PASS |
| Retrieval MRR (Hybrid) | >= 0.85 | **1.0000** | ✅ PASS |
| Ortalama Uçtan Uca Gecikme | < 50 ms | **4.68 ms** | ✅ PASS |
