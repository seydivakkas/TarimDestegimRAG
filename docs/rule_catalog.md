# TarımDestekRAG — Resmî Mevzuat Kural Kataloğu (Rule Catalog v1.0)

> **Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)**  
> **ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR**  
> Bu katalog, 2026 Türkiye Bitkisel Üretim Destekleme kurallarının deterministik karar mantığını, yasal dayanaklarını, girdi parametrelerini ve hesaplama formüllerini tanımlar.

---

## 1. Genel Kurallar ve Değişmez İlkeler

1. **Sıfır LLM Kararı (Zero-LLM):** Hiçbir uygunluk kararı veya para hesabı yapay zekâya bırakılmaz. Kararlar %100 Python ve SQL ile doğrulanır.
2. **Kuruş Hassasiyeti:** Tutarlar float ile değil, `decimal.Decimal` ile hesaplanır.
3. **Üç Seviyeli Karar Matrisi:**
   - `ELIGIBLE` (Uygun görünüyor): Tüm yasal şartlar sağlandı.
   - `REVIEW` (Ek kontrol gerekiyor): Eksik bilgi (ÇKS kaydı belirsiz, tohum sertifikası girilmemiş vb.).
   - `NOT_ELIGIBLE` (Uygun görünmüyor): Kesin ret (ÇKS yok, ürün havzada desteklenmiyor, su kısıtında yasaklı vb.).
4. **Kaynak İzlenebilirliği (Source Provenance):** Her kural doğrudan bir resmî mevzuat numarası ve `source_id` ile eşleştirilmiştir.

---

## 2. Destek Programları ve Kural Özellikleri

### 2.1 Temel Destek (`BASIC_SUPPORT_2026`)

- **Resmî Dayanak:** Resmî Gazete 29.08.2024 / Sayı: 32647 — Karar Sayısı: 8860 (Madde 3)
- **Kaynak ID:** `RG-2026-BITKISEL`
- **Girdi Gereksinimleri:**
  - `production_year`: 2026
  - `cks_status`: `True`
  - `crop`: Tanımlı bitkisel ürün
  - `area_da`: > 0 (dekar)
- **Kural Mantığı:**
  ```text
  EĞER production_year == 2026 VE cks_status == True VE crop != NULL:
      DURUM: ELIGIBLE
      HESAPLAMA: alan (da) * kategori_birim_tutari (TL/da)
  EĞER cks_status == NULL / Tanımsız:
      DURUM: REVIEW
      EKSIK_ALAN: ["cks_status"]
  EĞER cks_status == False:
      DURUM: NOT_ELIGIBLE
      GEREKÇE: "ÇKS kaydı bulunmayan üreticiler temel destekten yararlanamaz."
  ```
- **2026 Birim Destek Katsayıları:**
  | Ürün | Kategori | Birim Destek (TL/da) |
  |---|---|---|
  | BUĞDAY | TAHIL | 465,00 TL |
  | ARPA | TAHIL | 465,00 TL |
  | MISIR | TAHIL | 380,00 TL |
  | FINDIK | MEYVE | 170,00 TL |
  | AYÇİÇEĞİ | YAĞLI TOHUM | 410,00 TL |
  | PAMUK | ENDÜSTRİ | 550,00 TL |

---

### 2.2 Planlı Üretim Desteği (`PLANNED_PRODUCTION_2026`)

- **Resmî Dayanak:** Resmî Gazete Karar Sayısı: 8860 (Madde 4) + BUGEM Tarım Havzaları Kararı
- **Kaynak ID:** `RG-2026-BITKISEL`, `BUGEM-HAVZA-2026`
- **Girdi Gereksinimleri:**
  - `province`, `district`: Parselin bulunduğu il ve ilçe
  - `crop`: Ekilen ürün
  - `cks_status`: `True`
  - `area_da`: > 0
- **Kural Mantığı:**
  ```text
  EĞER cks_status == True:
      EĞER crop IN havza_desteklenen_urunler(province, district):
          DURUM: ELIGIBLE
          HESAPLAMA: alan (da) * planli_uretim_ilave_tutari (TL/da)
      DEĞİLSE:
          DURUM: NOT_ELIGIBLE
          GEREKÇE: "Ürün, parselin bulunduğu havzada desteklenen öncelikli stratejik ürünler arasında yer almamaktadır."
  EĞER cks_status == NULL:
      DURUM: REVIEW
      EKSIK_ALAN: ["cks_status"]
  ```
- **Örnek Havza Listesi (2026):**
  - **KONYA / KARATAY:** BUĞDAY, ARPA, AYÇİÇEĞİ, MISIR
  - **DİYARBAKIR / BİSMİL:** PAMUK, BUĞDAY, MISIR, AYÇİÇEĞİ
  - **SAMSUN / ÇARŞAMBA:** FINDIK, ÇELTİK, MISIR

---

### 2.3 Sertifikalı Tohum Kullanım Desteği (`CERTIFIED_SEED_2026`)

- **Resmî Dayanak:** Resmî Gazete Karar Sayısı: 8860 (Madde 6)
- **Kaynak ID:** `RG-2026-BITKISEL`
- **Girdi Gereksinimleri:**
  - `crop`: Sertifikalı tohum destekleme kapsamındaki ürün
  - `certified_seed`: `True` / `False` / `None`
  - `cks_status`: `True`
  - `area_da`: > 0
- **Kural Mantığı:**
  ```text
  EĞER cks_status == True:
      EĞER certified_seed == True:
          DURUM: ELIGIBLE
          HESAPLAMA: alan (da) * tohum_birim_tutari (TL/da)
      EĞER certified_seed == NULL:
          DURUM: REVIEW
          EKSIK_ALAN: ["certified_seed"]
          AÇIKLAMA: "Tohum sertifika belgesi girilmediğinden değerlendirilemedi."
      EĞER certified_seed == False:
          DURUM: NOT_ELIGIBLE
          GEREKÇE: "Sertifikasız tohum kullanımı desteklenmez."
  ```
- **Birim Destek Tutarları:**
  - BUĞDAY: 75,00 TL/da
  - ARPA: 75,00 TL/da
  - AYÇİÇEĞİ: 90,00 TL/da
  - PAMUK: 120,00 TL/da
  - MISIR: 60,00 TL/da

---

### 2.4 Sertifikalı Fidan Kullanım Desteği (`CERTIFIED_SAPLING_2026`)

- **Resmî Dayanak:** Resmî Gazete Karar Sayısı: 8860 (Madde 7)
- **Kaynak ID:** `RG-2026-BITKISEL`
- **Girdi Gereksinimleri:**
  - `crop`: Meyve türü (Örn: FINDIK, CEVİZ, BADEM)
  - `certified_sapling`: `True` / `False` / `None`
  - `cks_status`: `True`
  - `area_da`: Kapama bahçe asgari büyüklük şartı (>= 5 da)
- **Kural Mantığı:**
  ```text
  EĞER cks_status == True:
      EĞER certified_sapling == True VE area_da >= 5.0:
          DURUM: ELIGIBLE
          HESAPLAMA: alan (da) * fidan_birim_tutari (500,00 TL/da)
      EĞER certified_sapling == NULL:
          DURUM: REVIEW
          EKSIK_ALAN: ["certified_sapling"]
      EĞER area_da < 5.0:
          DURUM: NOT_ELIGIBLE
          GEREKÇE: "Kapama bahçe tesisinde asgari 5 dekar büyüklük şartı sağlanmalıdır."
  ```

---

### 2.5 Yeraltı Su Kısıtı Desteği (`WATER_RESTRICTION_2026`)

- **Resmî Dayanak:** Resmî Gazete Karar Sayısı: 8860 (Madde 5) + TRGM Su Kısıtı Kararları
- **Kaynak ID:** `RG-2026-BITKISEL`, `TRGM-SU-KISITI-2026`
- **Girdi Gereksinimleri:**
  - `province`, `district`: Parsel konumu
  - `crop`: Münavebe veya az su tüketen ürün
  - `cks_status`: `True`
  - `area_da`: > 0
- **Kural Mantığı:**
  ```text
  EĞER parsel_konumu IN su_kisiti_havzalari (KONYA/KARATAY, KONYA/ÇUMRA, KARAMAN/MERKEZ vb.):
      EĞER crop IN ["NOHUT", "MERCİMEK", "YEM_BEZELYESİ"]:
          DURUM: ELIGIBLE
          HESAPLAMA: alan (da) * 250,00 TL/da
      EĞER crop IN ["MISIR", "ŞEKER_PANCARI"]:
          DURUM: NOT_ELIGIBLE
          GEREKÇE: "Yeraltı su kısıtı bölgesinde yüksek su tüketen ürünler bu ilave destekten yararlanamaz."
  DEĞİLSE:
      DURUM: NOT_ELIGIBLE
      GEREKÇE: "Parsel yeraltı su kısıtı ilan edilen havzalarda yer almamaktadır."
  ```

---

## 3. Karar Denetim ve Çelişki Yönetimi (Conflict Resolution)

1. Bir parsel için birden fazla kural aynı anda değerlendirilebilir (Örn: Hem Temel Destek, hem Planlı Üretim, hem Sertifikalı Tohum bir arada alınabilir).
2. İlave desteklerin geçerli olabilmesi için temel şart **ÇKS kaydının aktif ve doğrulanabilir olmasıdır**.
3. Geçerlilik süresi dolmuş veya yürürlükten kalkmış (`superseded=True`) kaynaklar karar motoru tarafından işleme alınmaz.
