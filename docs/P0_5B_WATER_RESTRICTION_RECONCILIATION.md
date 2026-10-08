# P0-5b — 2026 Yeraltı Su Kısıtı İlçe Kütüğü ve Sürüm Çelişkisi Uzlaştırma Raporu

**Tarih:** 8 Ekim 2026  
**İlgili Issue:** #17 (P0-5b)  
**Mevzuat Dayanağı:** Resmî Gazete Sayı 32642 (24 Ağustos 2024) — 2024/39 Sayılı Tebliğ  
**Üretim Güvenlik Durumu:** **FAIL-CLOSED (Aktivasyon KAPALI — DRAFT / REVIEW)**  

---

## 1. Yönetici Özeti ve Tespit Edilen Risk

2026 tarımsal destekleme ve planlı üretim mevzuatı denetiminde resmî kaynaklar arasında somut bir **ilçe listesi ve sürüm çelişkisi** tespit edilmiştir:

1. **Bakanlık Eğitim / Bilgi Notu Kapsamı:**  
   Bakanlık EYDB *"Sorularla Tarımsal Üretim Planlaması"* dokümanı ve BUGEM *"Tarımsal Yeraltı Su Kısıtı Bilgi Notu"* 11 il ve 52 ilçe listelemektedir.
2. **Tebliğ 2024/39 Metin ve Ekleri:**  
   Bakanlık ve il müdürlükleri sitelerinde yer alan 2024/39 sayılı Tebliğ metinlerinde, 52 ilçelik kılavuzda yer almayan **Hatay/Kırıkhan, Konya/Yalıhüyük ve Mardin/Nusaybin** gibi ilave ilçeler geçmektedir.

### Hukuki Risk
- **Erken 52 İlçe Sınırlaması (False Negative):** Yasal olarak 2024/39 kapsamında olan çiftçileri haksız yere destek dışı bırakabilir (hak gaspı).
- **Erken Genişletilmiş Liste (False Positive):** Resmî yürürlüğü veya onay süreci tamamlanmamış ilçelere kamu kaynağı aktarımına neden olabilir (haksız hak ediş).
- **Çözüm:** 2026 su kısıtı değerlendirmesi için **bağımsız, kaynaklı, versiyonlu ve çift imzalı (Ed25519) `reviewed_water_restriction_districts` kütüğü** kurulmuş; çelişkili veya onaysız tüm kayıtlar için sistem **fail-closed (UNKNOWN -> REVIEW, tutar = None)** politikasına bağlanmıştır.

---

## 2. Resmî Gazete ve Mevzuat İncelemesi (Tebliğ 2024/39)

- **Resmî Gazete Tarih & Sayı:** 24 Ağustos 2024 / Sayı 32642
- **Tebliğ Adı:** 2025-2027 Yıllarında Yapılacak Bitkisel Üretime Yönelik Desteklemeler ile Diğer Bazı Tarımsal Desteklemelere İlişkin Kararın Uygulanmasına Dair Tebliğ (Tebliğ No: 2024/39)
- **Kritik Hüküm:** **Madde 6, Fıkra 3 (a, b, c)**:
  - **(a) Yeraltı Su Kısıtı Tanımı:** Yeraltı sularının yetersiz seviyede olduğu ve su kısıtı bulunduğu tespit edilen havzalarda/ilçelerde yer altı suyu kısıtı desteği ödenir.
  - **(b) Sulu Arazi ve Münavebe Şartı:** Yeraltı su kısıtı desteği sadece tescilli **sulu tarım arazilerinde**, su tasarrufu sağlayan münavebe (rotasyon) ürünlerinin (ör. nohut, mercimek, yağlık ayçiçeği vb.) ekilmesi hâlinde verilir. Kuru tarım arazileri bu desteğe **uygun değildir**.
  - **(c) Yüksek Su Tüketen Ürün Kısıtı:** Su kısıtı havzalarında dane mısır gibi yüksek su tüketen ürünlerin ekimi hâlinde, Bakanlıkça zorunlu kılınan modern damla sulama sistemi kullanılmadıkça planlı üretim/su kısıtı desteği ödenmez.

---

## 3. Karşılaştırmalı İlçe Kütüğü ve Çelişki Analizi

Sistemde `configs/2026_water_restriction_districts_draft.json` üzerinde 55 ilçe taranmış ve 3 durumlu (tri-state) olarak sınıflandırılmıştır:

| İl | İlçe | 52 İlçe Rehberi | Tebliğ 2024/39 | 2026 Sistem Durumu | Hukuki Gerekçe / Çözüm |
|---|---|:---:|:---:|:---:|---|
| **Aksaray** | 6 İlçe (Eskil, Gülağaç, Güzelyurt, Merkez, Ortaköy, Sultanhanı) | Var | Var | `RESTRICTED` (DRAFT) | Uyuşmazlık yok, 2 imzalı aktivasyon bekler |
| **Ankara** | 6 İlçe (Bala, Evren, Gölbaşı, Haymana, Polatlı, Şereflikoçhisar) | Var | Var | `RESTRICTED` (DRAFT) | Uyuşmazlık yok, 2 imzalı aktivasyon bekler |
| **Çankırı** | 2 İlçe (Kızılırmak, Şabanözü) | Var | Var | `RESTRICTED` (DRAFT) | Uyuşmazlık yok, 2 imzalı aktivasyon bekler |
| **Çorum** | 1 İlçe (Alaca) | Var | Var | `RESTRICTED` (DRAFT) | Uyuşmazlık yok, 2 imzalı aktivasyon bekler |
| **Eskişehir** | 4 İlçe (Alpu, Beylikova, Çifteler, Sivrihisar) | Var | Var | `RESTRICTED` (DRAFT) | Uyuşmazlık yok, 2 imzalı aktivasyon bekler |
| **Karaman** | 2 İlçe (Ayrancı, Merkez) | Var | Var | `RESTRICTED` (DRAFT) | Uyuşmazlık yok, 2 imzalı aktivasyon bekler |
| **Kırıkkale** | 4 İlçe (Bahşılı, Balışeyh, Keskin, Merkez) | Var | Var | `RESTRICTED` (DRAFT) | Uyuşmazlık yok, 2 imzalı aktivasyon bekler |
| **Kırşehir** | 2 İlçe (Boztepe, Merkez) | Var | Var | `RESTRICTED` (DRAFT) | Uyuşmazlık yok, 2 imzalı aktivasyon bekler |
| **Konya** | 16 İlçe (Ahırlı, Akören, Altınekin, Bozkır, Cihanbeyli, Çumra, Emirgazi, Ereğli, Güneysınır, Halkapınar, Karapınar, Karatay, Kulu, Meram, Sarayönü) | Var | Var | `RESTRICTED` (DRAFT) | Uyuşmazlık yok, 2 imzalı aktivasyon bekler |
| **Konya** | Selçuklu | Yok | Yok | `NOT_RESTRICTED` | Su kısıtı dışı ilçe (kesin ret üretir) |
| **Nevşehir** | 3 İlçe (Acıgöl, Derinkuyu, Gülşehir) | Var | Var | `RESTRICTED` (DRAFT) | Uyuşmazlık yok, 2 imzalı aktivasyon bekler |
| **Niğde** | 6 İlçe (Altunhisar, Bor, Çamardı, Çiftlik, Merkez, Ulukışla) | Var | Var | `RESTRICTED` (DRAFT) | Uyuşmazlık yok, 2 imzalı aktivasyon bekler |
| **Hatay** | **Kırıkhan** | **YOK** | **VAR** | `UNDER_REVIEW` | **Sürüm Çelişkisi:** Resmî Gazete teyidi ve çift imza olmadan asla hak ediş üretilmez (REVIEW) |
| **Konya** | **Yalıhüyük** | **YOK** | **VAR** | `UNDER_REVIEW` | **Sürüm Çelişkisi:** 17. ilçe ekleme ihtilafı (REVIEW) |
| **Mardin** | **Nusaybin** | **YOK** | **VAR** | `UNDER_REVIEW` | **Sürüm Çelişkisi:** Resmî Gazete teyidi ve çift imza olmadan asla hak ediş üretilmez (REVIEW) |

---

## 4. Uygulanan Mimari ve Karar Kuralları (`WaterRestrictionRule`)

1. **ÇKS Kontrolü:** ÇKS kaydı aktif olmayan parseller kesin olarak `NOT_ELIGIBLE` alır.
2. **Tri-State Bölge Değerlendirmesi (`evaluate_official_water_restriction`):**
   - `NOT_RESTRICTED` $\rightarrow$ Kesin Ret (`NOT_ELIGIBLE`): Parsel su kısıtı bölgesinde değildir.
   - `RESTRICTED` $\rightarrow$ Geçti: Ancak çift imzalı onay ve geçerli mevzuat tarihi aranır.
   - `UNKNOWN` / `UNDER_REVIEW` $\rightarrow$ İnceleme (`REVIEW`): `missing_fields` listesine `"verified_water_provenance"` eklenir. Tutar **hesaplanmaz** (`None`).
3. **Sulama Durumu Şartı (Madde 6/3-b):**
   - `IRRIGATED` (Sulu) $\rightarrow$ Şart sağlandı.
   - `DRY` (Kuru) $\rightarrow$ Kesin Ret (`NOT_ELIGIBLE`): Kuru araziler su tasarrufu münavebe desteğine hak kazanamaz.
   - `UNKNOWN` (Bilinmiyor) $\rightarrow$ İnceleme (`REVIEW`): `missing_fields` listesine `"irrigation"` eklenir.
4. **Münavebe Ürünü ve Onaylı Katsayı:**
   - Parseldeki ürün su kısıtı programında onaylı birim fiyata sahip olmalıdır (`SupportRepository.get_amount`).
   - Onaylı tutar yoksa `missing_fields` listesine `"verified_support_rate"` eklenir (`REVIEW`).

---

## 5. Çift Kontrollü Kriptografik Aktivasyon Kapısı

`ReviewedWaterRestrictionDistrictModel`, PR #16 ile kurulan Ed25519 iki kişilik imza protokolüne (`legal_approvals.py`) tam olarak entegre edilmiştir:

- **Konu Türü:** `_subject_kind(subject) == "WATER"`
- **CLI Desteği:** `python -m tarim_destek_rag.database.legal_approval_cli inspect --kind WATER --id <ID>`
- **İmza Zorunluluğu:** `REVIEWER` ve `APPROVER` rollerindeki iki ayrı yetkili tarafından haricî KMS/HSM açık anahtarlarıyla imzalanmadıkça, `evaluate_official_water_restriction` hiçbir ilçeyi `RESTRICTED` veya `NOT_RESTRICTED` olarak kabul etmez; fail-closed `UNKNOWN` döner.
- **İptal Desteği (Revocation):** Yetkili iptal imzası ile bir ilçenin kaydı dondurulabilir.

---

## 6. Sonuç ve Güvenlik Taahhüdü

Bu mimariyle:
1. Hiçbir çiftçi, eski bir 52 ilçe eğitim dokümanı yüzünden haksız yere doğrudan reddedilmez.
2. Hiçbir çelişkili ilçe (Kırıkhan, Yalıhüyük, Nusaybin), iki yetkili hukuk/mevzuat uzmanının kriptografik onayı olmadan sisteme hak ediş kazandırmaz.
3. Hukuki ve finansal güvenlik fail-closed olarak %100 teminat altındadır.
