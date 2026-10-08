# Issue #17 / P0-6 — 2026 Yürürlükteki Su Kısıtı İlçeleri ve Destek İstisnaları

**Durum:** Belgelenmiş 52 ilçe + 2025/42 yürürlük farkı + testli karar geçidi. **Gerçek yetkili onayı ve üretim aktivasyonu tamamlanmadı.**  
**Kaynak dönem:** 2026 üretim yılı. 2025 yılı başlatılmış işlemleri ve 2027 ayrı tutulur.

## 1. Hukukî sürüm zinciri

| Öncelik | Kaynak | Değerlendirme |
|---|---|---|
| Esas düzenleme | **2024/39 Tebliğ**, RG 31.12.2024/32769 (5. mükerrer), **m.6/3(a)**, Bakanlıkta [PDF](https://www.tarimorman.gov.tr/BUGEM/Belgeler/Tar%C4%B1m%20Havzalar%C4%B1/2024-39%20Bitkisel%20%C3%9Cretime%20Y%C3%B6nelik%20Desteklemeler%20ile%20Di%C4%9Fer%20Baz%C4%B1%20Tar%C4%B1msal%20Desteklemelere%20%C3%96deme%20Yap%C4%B1lmas%C4%B1na%20Dair%20Tebli%C4%9F%20%28Tebli%C4%9F%20No%202024-39%29.pdf) sayfa 9 | **11 il, 52 ilçe** açıkça sayılır. m.6/3(b), listelenen su kısıtlı havzalardaki **sulu** tarım arazileri ve Karar Tablo 3 ürünleri için ilave destek hükmüdür. |
| Yürürlükteki 2026 değişikliği | **2025/42 Tebliğ**, RG **30.12.2025/33123**, [asıl metin](https://resmigazete.gov.tr/eskiler/2025/12/20251230-9.htm) ve [Bakanlık duyurusu](https://sanliurfa.tarimorman.gov.tr/Duyuru/615/2025-2027-Yillarinda-Yapilacak-Bitkisel-Uretime-Yonelik-Desteklemeler-Ile-Diger-Bazi-Tarimsal-Desteklemelere-Odeme-Yapilmasina-Dair-Teblig-_teblig-No-2024_39_de-Degisiklik-Yapilmasina-Dair-Teblig-_teblig-No-2025_42_) | **m.4**: 2024/39 **m.6/3(c) yürürlükten kalktı**. Böylece 2026'da önceki **damla sulama ile dane mısır ödeme istisnası artık kullanılamaz**. **m.12**: 2024/39 m.17/2(j) eklendi; ilanlı su kısıtı bölgelerinde **dane mısır ve patates ekilişi**, m.17/2'nin girişinde sayılan **m.5, m.6 ve m.7** desteklemeleri için dışlama kapsamında. **m.16** yürürlük **01.01.2026**; **Geçici m.2**, 2025 üretim yılı başlatılmış süreçler için önceki hükümleri korur. |
| Tarihsel açıklama | [Bakanlık Yeraltı Su Kısıtı Bilgi Notu](https://www.tarimorman.gov.tr/BUGEM/Belgeler/Tar%C4%B1m%20Havzalar%C4%B1/Tar%C4%B1msal%20Yeralt%C4%B1%20Su%20K%C4%B1s%C4%B1t%C4%B1%20Bilgi%20Notu.pdf) sayfa 1–2 | 2016 için **10 il/47 ilçe**, 2020–2021 çalışmaları sonrası **11 il/52 ilçe** açıklar. **Hassa, Kırıkhan, Payas, Nusaybin'in geçmişte kapsamdan çıkarıldığını** belirtir. Ancak bu notta yazan eski damla sulama örneği **2026 mevzuatı yerine geçmez**. |
| Ürün planlama listesi | P0-4'teki **945 havza/ilçe ürün deseni** | Farklı hukuki amaç. İlçe yıldızı veya ürünün desende bulunması, 2026 yeraltı su kısıtı ek desteğini veya kaldırılmış damla istisnasını kendiliğinden kanıtlamaz. |

**Sürüm çelişkisi düzeltmesi:** Önceki Issue #17'de yayımlanmış kopyalarda geçtiği ileri sürülen **Hatay/Kırıkhan, Konya/Yalıhüyük ve Mardin/Nusaybin** adlarını bağımsız 2026 kısıt listesi olarak kabul etmiyoruz. Görülen Bakanlık PDF'sinin **2024/39 m.6/3(a)** metni ve 52 ilçe bilgi notu bunları **2026'daki 52 ilçelik kapsamda saymıyor**. **Kırıkhan ve Nusaybin** hakkında tarihsel çıkarılma notu da var. Bu aşamada resmî 52 kümesi referansını çıkarabiliriz; ancak makine, *insan onayı ve ikinci mevzuat sürümü imzaları yokken* **olumsuz ya da olumlu karar üretmez**.

## 1.1. İki özgün belgenin gerçek SHA-256 kanıtı

GitHub Actions [2026 water source evidence](https://github.com/seydivakkas/TarimDestegimRAG/actions/runs/37824333841) çalışmasında resmî hostlardan içerikler indirildi, 2024/39 PDF 9. sayfa ve 2025/42'nin yürürlük/değişiklik hükümleri metin olarak doğrulandı, ham dosyalar artefakt olarak saklandı.

| Belge | İndirilen ham baytların SHA-256'sı |
|---|---|
| 2024/39, Bakanlıktaki PDF | `8b8b0785e2692268a60a0931f54aa36783ca32d80aea12800b66b25ea0d71612` |
| 2025/42, özgün Resmî Gazete HTML | `74a91122f52190cc4dd4322c1d7b6036466d5432f8f11577230151dba0119269` |

`water_2026.py` ve `WaterRestrictionRepository.assess_2026` **her iki hash'i sabit olarak doğrular**; herhangi bir 64 haneli hash yetmez. Esas mevzuat kaynağı değişirse yeni sürüm+uzman incelemesi gerekecektir. Bu kanıt **insan onayı değildir**.

## 2. Kontrol edilen veri kümesi

- `configs/2026_water_restriction_52_draft.json`: 2026, **11 il**, tam **52 ilçe**, kanuni kaynak/URL, madde ve değişiklik notları, ayrıca `DRAFT` ve `authoritative_membership_approved=false`.
- `normalization/water_2026.py`: JSON verisi **kaynak metinden ayrı tanımlanmış sabit 52 ilçe kümesine** karşı doğrulanır; kopya kayıt, fazla/eksik kayıt, 2027 yürürlük tarihi, hatalı istisna veya DRAFT etiketi değiştirilmiş kayıt reddedilir.
- `ReviewedWaterRestrictionScopeModel`: **tam ulusal küme** tek bir hukuki nesne olarak sürümlenir; **esas PDF** ve **2025/42 değişikliği** için *iki ayrı* `source_version_id` tutulur. Eski `water_restrictions` seed tablosu sadece tarihsel/demodur.
- `stage_water_scope` ve `import_water_2026.py`: varsayılan sadece **dry-run**. Açık `--apply-draft` için 2024/39 kaynak PDF baytları ve 2025/42 Resmî Gazete HTML baytları gerekir. PDF'nin 6/3(a) içeriği asgari yapısal kontrolden geçer, her iki kaynağın gerçek SHA-256 değeri hesaplanıp sürümlenir; **DRAFT** dışında statü atanmaz.
- `WaterRestrictionRepository.assess_2026` yalnızca **tam, aktif, benzersiz, iki imzalı, kaynak ve değişiklik sürümü doğrulanmış** ulusal listeyle karar verir:
  - `RESTRICTED`: listedeki 52 ilçeden biri;
  - `NOT_RESTRICTED`: ancak aynı **tam ve çift onaylı** listede bulunmayan ilçe;
  - `UNKNOWN`: herhangi bir kanıt/onay/yıl/sürüm/kimlik/bütünlük eksikliği.

## 3. 2026 karar motoru istisna zinciri

2025/42 m.12 ile eklenen 2024/39 m.17/2(j), m.17/2 girişindeki **5, 6 ve 7. maddelerde** belirtilen desteklemeler bakımından değerlendirilir. Bu projedeki beş kural bu kapsamdadır.

| Ürün / konum | 2026 sonucu |
|---|---|
| **Dane mısır veya patates**, **onaylı su kısıtı** ilçesi | `NOT_ELIGIBLE` — m.17/2(j) gerekçesi; damla sulama beyanı sonucu değiştirmez |
| Dane mısır veya patates, konumu onaysız/bilinmiyor | `REVIEW` / `verified_water_scope`; eski demo verisi kesin ret kanıtı değil |
| Dane mısır veya patates, **onaylı ulusal listede dışında** | Yalnız **su kısıtı dışlaması yok**; ÇKS, ürün deseni, sertifika ve fiyat gibi başka kurallar ayrıca gerekir |
| **Su kısıtı ek desteği** ve onaylı su kısıtı ilçesi | Bakanlık Tablo 3'teki uygun ürün + **sulu tarım** + onaylı bileşen fiyatı ile ayrıca değerlendirilir; otomatik ödeme yok |
| **Su kısıtı ek desteği**, ilçe onaysız veya liste eksik | `REVIEW`; demo `water_restrictions` kaydı kullanılamaz |
| 2025 yılı daha önce başlatılmış işlemler | 2025/42 Geçici m.2 uyarınca **önceki dönem**; 2026 istisnasını otomatik geriye yürütme yok |

**P0-4'e göre düzeltme:** Damla sulamalı dane mısırın yıldızlı ilçede planlı üretim ödemesini açtığı eski test senaryosu 2026'da artık geçerli değildir. `PlannedProductionRule` artık yıldızlı ilçe notunu tarihsel olarak açıklar ama bunu ödeme izni saymaz. 2026 su kısıtı pozitif kararı varsa **damla sulama True olsa bile** ret uygulanır.

## 4. İmzalı yetki mekanizmasına aktarım

PR #16 ile hazırlanan **Ed25519 REVIEWER+APPROVER** imza denetleyicisine `WATER` konusu eklendi. Bu konunun `subject_digest` değeri:
- 52 ilçelik **tam küme**,
- 2026 yılı ve `coverage_complete`,
- esas **2024/39 PDF** kaynak sürümü/id/URL/hash,
- değişiklik **2025/42** kaynak sürümü/id/URL/hash,
- inceleme alanları
üzerinden hesaplanır. Kaynak veya tek ilçe değiştirilirse imza geçersiz olur; iptal kaydı aynı konu sürümünü kalıcı olarak kapatır.

### Üretimde etkinleştirme: varsayılan KAPALI

`TARIM_RAG_LEGAL_ACTIVATION_ENABLED` varsayılan olarak ayarlı değildir. **Tam olarak `true` olmadığı sürece** iki geçerli imza bulunsa bile hiçbir mevzuat kaydı `two_person_approved` kontrolünden geçmez. Bu değişken bir özellik kilidi ve **asla yetki kanıtının yerine geçmez**. Ayrı `TARIM_RAG_LEGAL_TRUSTED_KEYS_JSON` anahtar sicili, gerçek iki bağımsız görevli ve imza işlemleri yine şarttır. Test yardımcıları anahtarı sadece geçici test oturumunda açar.

Kurumsal gerçek onay adımları: kimlik ve görev yetkisi doğrulaması → Bakanlık hukukî madde incelemesi → PDF ve HTML kaynak hash kontrolü → bağımsız REVIEWER ve APPROVER imzaları → ayrı üretim DB rolü ve değiştirilemez haricî audit → yetkilendirilmiş dağıtımda kill-switch kontrolü → üretim smoke test. Herhangi bir aşama eksikse kilit **açılmamalı**.

Sadece daha önce gerçekten yetkisi tanımlanmış, iki farklı gerçek kişinin KMS/HSM anahtarıyla imzaladığı kayıtlar çalışabilir. Mevcut repoda gerçek kimlik/anahtar **bulunmuyor**; yalnız geçici test anahtarları vardır. Gerçek yetkililerin ataması, kurum içi erişim kontrolü, veritabanı rol ayrımı, haricî WORM audit ve mevzuat inceleme tutanağı tamamlanmadan `VERIFIED` yapılmamalıdır.

### Çalıştırma

```powershell
# Kayıt ve 52 ilçe kontrolü: DB'ye hiçbir veri yazmaz.
python -m tarim_destek_rag.normalization.import_water_2026

# Özgün kaynak dosyalarının ayrıca indirilmiş, incelenmiş olması gerekir:
python -m tarim_destek_rag.normalization.import_water_2026 `
   --original-pdf data/legal/2024_39.pdf `
   --amendment-html data/legal/2025_42.htm `
   --apply-draft

# Yetkilendirme işlemleri (gerçek onay olmadan yürütmeyin):
python -m tarim_destek_rag.database.legal_approval_cli inspect --kind WATER --id 1
```

Kod, otomatik **VERIFIED** geçişi sağlamaz. API'de kamuya açık onaylama yolu yoktur.

## 5. Üretim kabul kapısı

- Resmî belgelerin bayt bazında SHA-256 doğrulaması, özgün Resmî Gazete sürümü ve yeni değişiklik olmadığının resmî kontrolü.
- Su kısıtı kapsamında *ilçe sınırı/ilgili parsel* gibi coğrafi istisnaların ve ürün bazlı sulama/ÇKS/münavebe kayıtlarının uzman doğrulaması.
- Gerçek iki yetkili onayı ve haricî, yetkili/audit edilmiş imza altyapısı.
- Ayrı şema migrasyonu, bütün entegrasyon/sistem testleri, UI ve benchmark altın etiket güncellemesi.
- **Hiçbiri olmadan güvenilir 2026 ödeme tahmini yayımlanamaz.**

**Durum:** 2026 hukukî liste ve değişiklik metni kaynaklara dayandırıldı; **canlı aktivasyon yapılmadı**.
