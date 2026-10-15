# G37 — 2026 Temel Destek Kayıt Şartı: Özgün Kaynak ve Değişiklik Zinciri

## Asıl bulgu

**2025/42 sayılı Tebliğin MADDE 3'ü, 2024/39 sayılı Tebliğin MADDE 5(1) hükmündeki “ÇKS’ye” ifadesini “ÇKS/ÖKS/KOBÜKS’e” olarak değiştirir. MADDE 16 değişikliğin 1 Ocak 2026'da yürürlüğe girdiğini düzenler.** Dolayısıyla 2026 Temel Destek değerlendirmesinde yalnız ÇKS kaydı yok diye kesin otomatik ret yapmak hatalı olabilir; parselin ilgili sistemde resmî kaydı ayrıca incelenmelidir.

Resmî kaynak bağlantıları:

- [2024/39 asıl Tebliğ — 31 Aralık 2024, Resmî Gazete, MADDE 4(1), MADDE 5(1)](https://resmigazete.gov.tr/eskiler/2024/12/20241231M5-8.htm)
- [2025/42 değişikliği — 30 Aralık 2025, Resmî Gazete, MADDE 3 ve MADDE 16](https://resmigazete.gov.tr/eskiler/2025/12/20251230-9.htm)
- [2025/42 değişikliği — Tarım ve Orman Bakanlığı Şanlıurfa duyurusunun metin yayını](https://sanliurfa.tarimorman.gov.tr/Duyuru/615/2025-2027-Yillarinda-Yapilacak-Bitkisel-Uretime-Yonelik-Desteklemeler-Ile-Diger-Bazi-Tarimsal-Desteklemelere-Odeme-Yapilmasina-Dair-Teblig-_teblig-No-2024_39_de-Degisiklik-Yapilmasina-Dair-Teblig-_teblig-No-2025_42_)
- [2025/13 — Tarım ve Orman Bakanlığı Trabzon metin duyurusu; MADDE 1, 2024/39 MADDE 5(3)'e ikinci ürün soya hükmü ekler](https://trabzon.tarimorman.gov.tr/Sayfalar/Detay.aspx?TermId=edd3ebad-7b98-490d-a10a-55785a9924e2&TermSetId=79f2f663-7aec-4bc1-b40a-56e75866bfb3&TermStoreId=368e785b-af33-487d-a98d-c11d5495130b&UrlSuffix=996%2F2025-2027-Yillarinda-Yapilacak-Bitkisel-Uretime-Yonelik-Desteklemeler-Ile-Diger-Bazi-Tarimsal-Desteklemelere-Odeme-Yapilmasina-Dair-Teblig)
- [11781 sayılı 8 Eylül 2026 Karar değişikliği — Bakanlık haber kaydı](https://www.tarimorman.gov.tr/HHGM/Haber/262/); Bakanlığın işaret ettiği [özgün Resmî Gazete PDF](https://www.resmigazete.gov.tr/eskiler/2026/09/20260908-7.pdf)

**Kaynak notu:** Doğrudan resmî siteden indirme bu çalışma ortamında DNS yüzünden başarısızdı. Daha sonra 9 Ekim 2026 tarihli GitHub Actions özgün kaynak arşivi geri alınarak iki HTML'nin gerçek baytları SHA ve madde konumlarıyla 15 Ekim'de bağımsız yeniden denetlendi. 2025/13 ve 11781 özgün kaynak baytları hâlen ayrı HOLD. Gerçek kaynaktan benzersiz pasaj ve madde konumu doğrulanamazsa uygulama HOLD verir.

## Dört parçalı pilot kaynak haritası

| Sıra | Kaynak kimliği | Madde | Etki | Özgün dosya kabulü |
|---|---|---|---|---|
| 1 | `BASE_2024_39_ART4_P1` | 2024/39 4(1) | Bakanlık kayıt sistemine ilgili üretim yılında kayıtlı olma genel şartı | 9 Ekim arşiv baytları 15 Ekim'de SHA+doğru madde+tekil alıntı olarak doğrulandı; hukuki/üretim yılı HOLD |
| 2 | `BASE_2024_39_ART5_P1` | 2024/39 5(1) | Temel Destek'te kayıtlı arazi koşulunun eski metni | 9 Ekim arşiv baytları 15 Ekim'de SHA+doğru madde+tekil alıntı olarak doğrulandı; hukuki/üretim yılı HOLD |
| 3 | `AMEND_2025_42_ART3_BASE_ART5_P1` | 2025/42 3 | “ÇKS’ye” → “ÇKS/ÖKS/KOBÜKS’e” değişikliği | 9 Ekim arşiv baytları 15 Ekim'de SHA+doğru madde+tekil alıntı olarak doğrulandı; hukuki/üretim yılı HOLD |
| 4 | `AMEND_2025_42_ART16_EFFECTIVE_2026` | 2025/42 16 | 1 Ocak 2026 yürürlük ifadesi | 9 Ekim arşiv baytları 15 Ekim'de SHA+doğru madde+tekil alıntı olarak doğrulandı; hukuki/üretim yılı HOLD |

2025/13, 2024/39'un **MADDE 5(3)** hükmünü etkiler; MADDE 5(1) kayıt ifadesini doğrudan değiştirdiği bu incelemede belirlenmedi. 11781 ise temel 8859 sayılı Kararda farklı üretim yıllarına ve maddelere ilişkin değişiklikler içerir; ÇKS pilotunun tüm hukuki etkileri bununla ve sonraki mevzuatla birlikte nihai incelenmeden yıl geçerliliğine PASS verilmez.

## Bu turdaki somut kod işlemleri

1. `models/farmer_parcel.py`: `cks_status`, `oks_status`, `kobuks_status` bağımsız ve bilinmiyor = null.
2. `rules/rules_impl.py`: aynı `BASIC_CKS_REGISTRATION` check_id korunur; alternatif kayıt durumu bilinmezken ÇKS yokluğu nedeniyle otomatik ret kalkar. Herhangi bir kayıt beyanı olsa bile bu 2026 parselinin resmî kaydı bağımsız doğrulanmadığından `verified_2026_registered_parcel` eksik ve değerlendirme REVIEW.
3. `pages/farmer_parcels.py`, `services/evaluation_service.py`, `app.py`: kullanıcı formlarından üç kayıt durumu ayrı alınır ve hesaplama/rapor/altı örnek senaryoya aktarılır. ÇKS yok örneği artık doğrudan kesin ret iddiasında bulunmaz.
4. `configs/p0_10_7_claim_source_matrix.json`: tekil ÇKS pilotunun primary normatif bağlantısı doğru MADDE 5(1) hükmüne taşındı. Artık sekiz özgün span var; yeni MADDE 3 ve MADDE 16 ayrı.
5. `citations/claim_source_matrix.py`: kaynak doğrulayıcısı asıl Tebliğ'in MADDE 4(1) ile MADDE 5(1) kayıtlarını ayrı ayrı tanır; yanlış madde, yanlış SHA, belirsiz veya özgün olmayan metinde HOLD.
6. `citations/cks_2026_source_chain.py`: dört kaynağı her çağrıda manifest ve yerel özgün dosya SHA'sı ile yeniden kontrol eder. Eksik dosyada alıntıyı doğrulanmış saymaz ve sarı vurgu göstermez. 2025/13 ve 11781 ayrı dış doğrulama yükümlülükleri olarak saklanır.
7. `citations/central_evidence_engine.py`: merkezi pilotun `pilot_source_chain` alanı PC/SSS/rapor ve API'ye taşınır. Flutter ortak DTO ile Neden? ekranı da aynı dört kanıtın doğrulanma statüsünü gösterir.

## Kapanışta kalan gerçek dış girdiler (G37)

- Asıl 2024/39 HTML ve 2025/42 HTML'nin baytlarını resmî yayından indirip `data/legal_update_archive/originals/{sha}.html` olarak güvenli arşivde fiilen doğrulamak; ilgili tüm gerçek pasajların doğru tekil konuma açıldığını teyit etmek.
- 2025/13, 11781 ve başka yürürlük/değişiklik/istisna kaynaklarının 2026 Temel Destek kaydını etkileyen tüm hükümlerini tamamlayıp bağımsız hukukî imzalı onaya sunmak. Tek bir maddeyi saptamak tam yıllık mevzuat kapsamını kanıtlamaz.
- ÖKS/KOBÜKS/ÇKS durumunu **bu parsel ve ilgili üretim yılı** düzeyinde gerçek resmî kayıtlarla bağımsız doğrulamak; kullanıcı beyanından ödeme hakkı vermemek.
- PC/Flutter kaynak bağlantılarının gerçek cihaz kabulünü ve uçtan uca regresyonları en son F14'te yapmak.

Bu dış kaynak/hukukî girdiler gelmeden **G37 BLOCKED_EXTERNAL** ve bütün etkinlik/ödeme sonuçları **HOLD**. G36'nın tüm kurallara check_id genelleştirmesi, bu ilk pilot kabulünden sonra açılacak mühendislik genişleme hattıdır. PR #41 DRAFT/unmerged; main değiştirilmez.

## 15 Ekim 2026 — 2025/13 ve 11781'e ait hüküm-yıl araştırması

Kaynak analizinin sonucu **tek bir güncel yıl → bütün maddeler geçerli** yaklaşımının yanlış olduğu yönündedir:

| Kaynak ve hüküm | 2026 Temel Destek etkisi | Yürürlük dönemi | Kanıt seviyesi |
|---|---|---|---|
| 2025/13 MADDE 1 → 2024/39 MADDE 5(3) | İkinci ürün soya için ilave Temel Destek istisnası; kayıt ifadesini değiştirmez | 2025/13 MADDE 4 uyarınca 01.01.2025'ten geçerli | Resmî HTML/Bakanlık PDF'de metin incelendi; özgün SHA arşivi henüz yok, HOLD |
| 11781 MADDE 1(a) → 8859 MADDE 2(4)(a) | 2026 367 TL/da, 2027 442 TL/da **destek katsayı DEĞERİ**; doğrudan ödeme hakkı/dekar ödeme tutarı değildir | 11781 MADDE 6(a): 01.01.2026'dan geçerli, yayımında yürürlük | Resmî PDF orijinali/SHA bağımsız doğrulanmadı, HOLD |
| 11781 MADDE 1(ç) | Organik arıcılık baz katsayı değişikliği; ÇKS kaydının ana hükmü değil | MADDE 6(a): 01.01.2026'dan geçerli | HOLD |
| 11781 MADDE 4 → 8859 MADDE 6(4),(9) | Fındık ilçeleri ve yanlış ürün beyanı yaptırımı; Temel Destek uygunluğu açısından ayrıca önemlidir | MADDE 6(b): 01.01.2025'ten geçerli, yayımında yürürlük | HOLD, gerçek parsel incelemesi yok |
| 11781 MADDE 1'in diğer hükümleri, MADDE 2, MADDE 3, MADDE 5 | Çoğunlukla 2027 uygulamaları, finansman, ekler ve katsayılar | MADDE 6(c): 01.01.2027 | HOLD, 2026'ya otomatik uygulanmaz |

**Asıl resmî kanıtlar:**

- [2025/13 — 5 Ağustos 2025 Resmî Gazete, MADDE 1–5](https://www.resmigazete.gov.tr/eskiler/2025/08/20250805-4.htm)
- [BÜGEM tarafından yayımlanan 2025/13 orijinal RG sayfa görünümünün PDF kopyası](https://www.tarimorman.gov.tr/BUGEM/Belgeler/Tar%C4%B1m%20Havzalar%C4%B1/2025-2027%20Destekleme%20Tebli%C4%9Fi%20De%C4%9Fi%C5%9Fikli%C4%9Fi.pdf) — sayfa görüntüsü manuel karşılaştırıldı, özgün HTML'nin byte SHA'sı olarak kullanılmaz.
- [11781 — 8 Eylül 2026, 33364, resmî PDF](https://www.resmigazete.gov.tr/eskiler/2026/09/20260908-7.pdf) — PDF baytları bu oturumda açılıp SHA doğrulanamadı; madde etkileri bağımsız transkripsiyonlardan araştırma adayıdır.

Bu maddeler için makinece okunabilir araştırma kayıtları: [g37_2026_legal_impact_register.json](../configs/g37_2026_legal_impact_register.json). Yeni kayıtların tümü `OFFICIAL_WEB_TEXT_RESEARCHED_ORIGINAL_SHA_PENDING_HOLD`, bağımsız hukukî/onay FALSE. Kural/ödeme motorunda tutar veya PASS aktivasyonu yapılmaz.

### Windows / yerel özgün bayt edinimi (hazır, bu oturumda çalıştırılamadı)

Proje kökünde (Python standart kütüphanesi, ücretli API gerektirmez):

```powershell
python scripts/acquire_g37_official_sources.py --sources 2024_39 2025_42 2025_13 11781
```

- `2024_39`, `2025_42`: kaynak manifestindeki **tam özgün SHA-256 + byte length + URL** eşleşirse `data/legal_update_archive/originals/<sha>.html` dosyasına yazılır. Uymazsa `DOWNLOAD_OR_SHA_HOLD`, kaynak değiştirilemez.
- `2025_13`, `11781`: manifestte daha önceden bağımsız onaylı SHA bulunmadığı için indirilmiş gerçek baytlar **yalnız `data/legal_update_archive/quarantine/`** içinde ayrı sha adında saklanır; `UNPINNED_OFFICIAL_URL_BYTES_QUARANTINED_HOLD`. Bu dosyalar otomatik mevzuat kuralı veya onaylı kaynak sayılmaz.
- Orijinal HTML iki farklı dosyadır; kullanıcıya gösterilen dört ayrı hukuki pasaj bunlardan kaynaklanır. Aynı kaynaktaki birden fazla madde ayrı `span_id` taşır.
- Orijinaller indirildikten sonra ÇKS pilotunda her dört paragraf gerçek kaynaktan tekrar eşleştirilir. Herhangi biri yanlış/alınıp değişmiş/madde altında tekil değilse `HOLD`. Sarı imzasız görsel vurgu ve ödeme etkinleştirme YOK.

### Açık kabul engelleri

Doğrudan resmî HTTP bağlantısı bu oturumda DNS nedeniyle başarısızdı; fakat GitHub Actions'ın önceden topladığı özgün HTML baytları daha sonra aynı oturumda geri alınarak gerçek SHA ve madde konumu denetlendi. Bu doğrulama 2025/13 ve 11781 için geçerli değildir. Bağımsız parsel ve hukukî kabul hâlâ yoktur; G37 kapanmaz. Önce G37, sonra G36, en son F14.

## 15 Ekim 2026 — KAYNAK ARŞİVİ GERİ KAZANILDI: 2 SHA-doğrulanmış HTML, 4 gerçek pasaj

**Önceki 'bu oturumda özgün baytlar indirilemedi' notları, doğrudan resmigazete.gov.tr HTTP bağlantısının DNS sorununu anlatıyordu. Sonrasında önceki GitHub Actions arşivi keşfedilerek kaynaklar gerçekten geri alındı ve yeniden doğrulandı. Bu bölüm, önceki erişim engelinin son durumunu düzeltir.**

- GitHub Actions run `37906860240`, artifact `11604488899` / `p0-10-3-original-official-bytes` (9 Ekim 2026 kaynak toplama çalışması) geri alındı. İkinci çalışmada aynı artifact adıyla `37906865615` kaydı da mevcut.
- İçindeki `RG_COMMUNIQUE_2024_39` özgün HTML: **236810 bayt**, SHA-256 `efb1ebea650cf836155728b6bd3599b76a0fbee70d1a8e5c85f2af4792734530`; GitHub manifest ile tam eşleşti.
- İçindeki `RG_AMENDMENT_2025_42` özgün HTML: **45886 bayt**, SHA-256 `74a91122f52190cc4dd4322c1d7b6036466d5432f8f11577230151dba0119269`; GitHub manifest ile tam eşleşti.
- Gerçek özgün HTML düğümleri, alıntı içindeki satır sonlarına tolerans gösteren birebir regex ve belge içinde aktif MADDE takibiyle doğrulandı: `BASE_2024_39_ART4_P1`/MADDE 4, `BASE_2024_39_ART5_P1`/MADDE 5, `AMEND_2025_42_ART3_BASE_ART5_P1`/MADDE 3 ve `AMEND_2025_42_ART16_EFFECTIVE_2026`/MADDE 16. **Dördü de doğru madde altında tam tekil konumda bulundu.**
- Kanıt: `configs/g37_2026_original_sha_location_audit.json` (kriptografik bayt kimliği + tekil metin konumu incelemesi). Bu, bağımsız hukukî imza veya 2026 geçerlilik hükmü PASS değildir.
- Gerçek baytları kullanıcının Windows kopyasına taşımak için iki HTML + inceleme raporu içeren `g37_pinned_original_html_evidence.zip` paketi oluşturuldu; proje kökünde `python scripts/import_g37_verified_archive.py C:\PATH\g37_pinned_original_html_evidence.zip` çağrısı yerel `data/legal_update_archive/originals` arşivini, URL/manifest SHA/uzunluk kontrolünden geçirerek doldurur. Kullanıcının bilgisayarında komut henüz çalıştırılmadı.
- **Açık kalan G37:** 2025/13 özgün HTML ve 11781 PDF'nin SHA bağımsız arşiv kabulü, 11781'in tam tarihsel etkileri, gerçek çiftçi/parsel resmî kayıt kanıtı ve bağımsız hukukî inceleme. G37 `BLOCKED_EXTERNAL`; F14 kapsamlı kabul son aşamada.
