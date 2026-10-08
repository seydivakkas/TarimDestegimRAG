# TarımDestekRAG — Veri Kaynakları ve Menşe Kütüğü (Data Provenance)

> **Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)**  
> **ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR**

---

## 1. Resmî Kaynaklar Politikası

Sistem yalnızca resmî devlet kurumlarının yayımladığı birincil kaynakları kabul eder. Sosyal medya, blog yazıları veya resmî olmayan haber siteleri veri kaynağı olarak kesinlikle kabul edilmez.

| Kaynak ID | Makam | Başlık | Format | URL / Kayıt |
|---|---|---|---|---|
| `RG-2026-BITKISEL` | Resmî Gazete | 2024-2026 Bitkisel Üretime Yönelik Desteklemeler Kararı (Karar Sayısı: 8860) | PDF | [resmigazete.gov.tr/.../20240829-1.pdf](https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf) |
| `BUGEM-HAVZA-2026` | Tarım ve Orman Bakanlığı | Bitkisel Üretim Genel Müdürlüğü Tarım Havzaları Ürün Listesi | HTML / Tablo | [tarimorman.gov.tr/BUGEM](https://www.tarimorman.gov.tr/BUGEM) |
| `TRGM-SU-KISITI-2026` | TRGM / DSI | Yeraltı Sularının Yetersiz Seviyede Bulunduğu Havzalar Listesi | PDF / Karar | [tarimorman.gov.tr/TRGM](https://www.tarimorman.gov.tr/TRGM) |

---

## 2. Değişiklik Tespiti ve SHA-256 Sürümleme

Tüm kaynaklar indirilip metinleri kanonik hale getirildikten sonra SHA-256 özetleri çıkarılır:
- Herhangi bir kaynak içeriği değiştiğinde sistem `UPDATED` olayı üretir.
- Eski sürüm mevzuat (`superseded`) otomatik olarak tespit edilir ve aktif karar motorundan mülga olarak işaretlenir.
