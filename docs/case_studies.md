# TarımDestekRAG — Detaylı Vaka İncelemeleri (Case Studies v1.0)

> **Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)**  
> **ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR**  
> Bu belge, TarımDestekRAG sisteminin deterministik karar motoru, RAG açıklama üretimi, eksik bilgi tespiti ve mülga mevzuat korumasını gösteren 4 kritik kullanım vakasını inceler.

---

## 1. Vaka 1: Temel Destek ve Doğrulanmış Hesaplama (Konya Buğday Üreticisi)

### Senaryo
Konya ili Karatay ilçesinde Çiftçi Kayıt Sistemi'ne (ÇKS) kayıtlı bir üretici, 12,4 dekar arazisine buğday ekimi yapmıştır.

### Girdi Verisi
```json
{
  "farmer": {
    "farmer_id": "TR-42-001",
    "province": "KONYA",
    "district": "KARATAY",
    "cks_status": true
  },
  "parcel": {
    "parcel_id": "P-KNY-124",
    "crop": "BUĞDAY",
    "area_da": "12.40",
    "production_year": 2026
  }
}
```

### Sistem Değerlendirmesi
- **Kural:** `RULE_BASIC_SUPPORT_2026`
- **Karar:** `ELIGIBLE` (Uygun görünüyor)
- **Kategori:** TAHIL (Kategori 1)
- **Birim Destek:** 465,00 TL / dekar
- **Matematiksel Formül:** $12{,}40 \times 465{,}00 = 5.766{,}00\text{ TL}$

### Üretilen Resmî Açıklama ve Kaynak
> *"ÇKS kaydınız aktif ve 2026 yılı bitkisel üretim destekleme takviminde BUĞDAY üretimi Kategori 1 kapsamında yer almaktadır. 12,40 dekar parseliniz için tahmini 5.766,00 TL temel destek öngörülmektedir."*
> **Kaynak:** Resmî Gazete 29.08.2024 / Sayı: 32647, Karar No: 8860, Madde 3.

---

## 2. Vaka 2: Planlı Üretim İlave Desteği (Diyarbakır Pamuk Havzası)

### Senaryo
Diyarbakır Bismil'de ÇKS'li bir çiftçi, 40 dekar arazisine pamuk ekmiştir. Diyarbakır/Bismil havzasında pamuk stratejik öncelikli ürün olarak ilan edilmiştir.

### Girdi Verisi
```json
{
  "farmer": {
    "province": "DİYARBAKIR",
    "district": "BİSMİL",
    "cks_status": true
  },
  "parcel": {
    "crop": "PAMUK",
    "area_da": "40.00",
    "production_year": 2026
  }
}
```

### Sistem Değerlendirmesi
1. **Temel Destek:** `ELIGIBLE` — $40 \times 550{,}00 = 22.000{,}00\text{ TL}$
2. **Planlı Üretim Desteği:** `ELIGIBLE` — $40 \times 550{,}00 = 22.000{,}00\text{ TL}$
- **Toplam Destek:** **44.000,00 TL**

### Sistem Açıklaması
> *"Pamuk, Bismil tarım havzasında desteklenen öncelikli stratejik ürünler arasındadır. Temel desteğe ek olarak 1.0 katı oranında ilave Planlı Üretim Desteğine hak kazanmaktasınız."*
> **Kaynak:** BÜGEM Tarım Havzaları Kararı & Karar No: 8860, Madde 4.

---

## 3. Vaka 3: Eksik Bilgi Yönetimi ("Ne Eksik?" Durumu)

### Senaryo
Bir üretici ÇKS durumunu belirtmemiş (`null`), ayrıca sertifikalı tohum kullandığını beyan etmiş ancak tohum sertifika numarasını veya sertifika teyidini sisteme girmemiştir.

### Girdi Verisi
```json
{
  "farmer": {
    "province": "ANKARA",
    "district": "POLATLI",
    "cks_status": null
  },
  "parcel": {
    "crop": "BUĞDAY",
    "area_da": "50.00",
    "certified_seed": null
  }
}
```

### Sistem Değerlendirmesi (Halüsinasyonsuz)
- **Temel Destek Durumu:** `REVIEW` (Ek kontrol gerekiyor)
- **Eksik Alanlar:** `["cks_status"]`
- **Sertifikalı Tohum Durumu:** `REVIEW` (Ek kontrol gerekiyor)
- **Eksik Alanlar:** `["certified_seed"]`
- **Hesaplanan Tutar:** Belirsiz / 0,00 TL (Tahmin yapılmaz).

### Çiftçiye Gösterilen Mesaj
> *"Başvurunuzun değerlendirilebilmesi için ÇKS kayıt durumunuz ve Tohum Sertifika bilginiz eksiktir. Sistemimiz tahmin yapmaz; lütfen eksik belgelerinizi tamamlayınız."*

---

## 4. Vaka 4: Mülga Mevzuat ve Güncellik Filtresi (Superseded Source Guard)

### Senaryo
Sistemde geçmiş yıllara ait 2024 yılı mazot-gübre destek kararnamesi (eski mevzuat) ile 2026 yeni destek modeli yan yana bulunduğunda sorgulama yapılır.

### Mevzuat Durumu
- `RG-2024-ESKI-KARAR`: `effective_to = 2025-12-31`, `superseded = True`
- `RG-2026-BITKISEL`: `effective_from = 2026-01-01`, `superseded = False`, `active = True`

### Sistem Değerlendirmesi
- Karar motoru `superseded=True` olan eski kaynağı doğrudan filtreler.
- Eski mevzuat üzerinden hak talep eden bir soru yöneltildiğinde RAG katmanı şu koruma uyarısını verir:
> *"2024 yılı kararı yürürlükten kalkmış (mülga) olup 2026 yılı üretimleri için Cumhurbaşkanlığı 8860 sayılı yeni Kararı yürürlüktedir."*
- **Atıf Denetçisi (Citation Guard):** Mülga kaynaktan gelen iddialara `UNSUPPORTED_CLAIM` bayrağı çeker ve kullanıcıyı yanıltmaz.
