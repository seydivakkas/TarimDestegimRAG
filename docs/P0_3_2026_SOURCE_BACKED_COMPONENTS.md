# P0-3 — 2026 Mevzuat Bileşenleri: Kaynak, Katsayı, Güven Kapısı

**Tarih:** 2026-10-08  
**Durum:** Kaynaklı tutar kataloğu + kontrollü `DRAFT` aktarım hazır; üretim ödeme hesabına açılmadı.  
**Önkoşul:** P0-2 PR #12 (onaysız hesaplamayı engelleyen altyapı) başarıyla birleştirilmelidir.

## 1. Kaynak kronolojisi

1. **8859 sayılı Karar (29.08.2024)**: 2025–2027 destekleme modeli, MADDE 2, Tablo 1/2/3/4/6. [Resmî Gazete PDF](https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf)
2. **10394 sayılı değişiklik Kararı (14.09.2025)**: 2026 yılı ürün kategorileri, özellikle dane mısırın kategori 2 (1,3) olması; 2026 sertifikalı hububat tohumu 0,56 katsayısı. [Resmî Gazete PDF](https://www.resmigazete.gov.tr/eskiler/2025/09/20250914-6.pdf); [Bakanlık duyurusu](https://www.tarimorman.gov.tr/HHGM/Haber/175/).
3. **11781 sayılı değişiklik Kararı (08.09.2026)**: MADDE 1(a), 2026 üretim yılına **01.01.2026'dan itibaren geçerli** katsayı düzeltmesi `310 -> 367 TL/da`; 2027 katsayısı 442 TL'dir. MADDE 6(a)/(c) hangi hükmün hangi yılda yürürlükte olduğunu ayırır. [Resmî Gazete PDF](https://www.resmigazete.gov.tr/eskiler/2026/09/20260908-7.pdf), [Bakanlık duyurusu](https://www.tarimorman.gov.tr/HHGM/Haber/262/).
4. **BÜGEM resmî 2026 birim fiyat PDF'i** kategori katsayılarını doğrular ama bu PDF, **310 TL eski katsayı ile hesaplanmış tutarları** içerir. Burada açıklanan eski 403 TL buğday temel desteği, 08.09.2026 sonrası 2026 güncel katsayısını yansıtmaz. [BÜGEM PDF](https://www.tarimorman.gov.tr/BUGEM/Belgeler/Tar%C4%B1m%20Havzalar%C4%B1/2026%20Y%C4%B1l%C4%B1%20Destekleme%20Birim%20Fiyatlar%C4%B1.pdf).
5. **Bakanlığın 08.09.2026 açıklaması**, birleşik destekleri güncelleme sonrasında 2026 için ayrı yayımlar. [Resmî haber](https://www.tarimorman.gov.tr/Haber/7258/Bitkisel-Ve-Hayvansal-Uretimde-Destek-Tutarlari-Artirildi).

### Doğru aritmetik

```
2026 destek katsayısı: K = 367.00 TL/da
Ürün bazlı program bileşeni = K * destek katsayısı (Decimal)
Buğday temel = 367.00 * 1.30 = 477.10 TL/da
Buğday planlı = 367.00 * 1.30 = 477.10 TL/da
Hesap bileşenleri toplamı = 954.20 TL/da
Bakanlık kamu haberindeki tam TL'ye yuvarlatılmış referans = 954 TL/da
```

| Ürün tipi | Temel TL/da | Planlı TL/da | İki ondalıklı toplam | Bakanlık haberindeki tam TL |
|---|---:|---:|---:|---:|
| Buğday, arpa, dane mısır | 477.10 | 477.10 | 954.20 | 954 |
| Yağlık ayçiçeği, kuru fasulye, soya, kanola | 550.50 | 550.50 | 1101.00 | 1101 |
| Kütlü pamuk | 825.75 | 825.75 | 1651.50 | 1652 |
| Patates, kuru soğan, aspir | 367.00 | 367.00 | 734.00 | 734 |
| Mercimek, nohut | 367.00 | 367.00 | 734.00 | 734 |

*Bu tablolar bireysel çiftçi hak edişi değildir. Havza, ÇKS, su kısıtı, sertifika, fındık bölgesi ve ilgili diğer şartlar bağımsız olarak incelenmelidir.*

**2027 için olan hükümler 2026'ya uygulanmaz:** 11781 m.1(b)'nin mercimek/nohut ek planlı üretimi ve m.1(c)'nin 2027 sertifikalı tohum Tablo 4/5 katsayıları 01.01.2027 yürürlüktedir.

## 2. Makine tarafından okunabilir sözleşme

`configs/2026_documented_component_rates_draft.json`:

- 56 program–ürün bileşeni, 2026 katsayısı `367.00` ve ayrı kategori çarpanı.
- `BASIC_SUPPORT_2026`, `PLANNED_PRODUCTION_2026`, `CERTIFIED_SEED_2026`, `CERTIFIED_SAPLING_2026`, `WATER_RESTRICTION_2026`.
- Hukuki madde/tablo atfı ve tarımsal koşul açıklaması.
- Yıl/başlangıç tarihi, `TRY/da`, ulusal *katsayı tarifesi* için `*/*` (bu alan çiftçinin havza hak edişini onaylamaz).
- Ayrıştırılması gereken ürünler: `MISIR_DANE`, `AYÇİÇEĞİ_YAĞLIK`, `PAMUK_KÜTLÜ`, `FASULYE_KURU`, `SOĞAN_KURU`. Genel `MISIR`, `PAMUK` veya `AYÇİÇEĞİ` girdileri yanlışlıkla alt türe eşitlenmez.
- Kaynak URL'leri, hash ve inceleme durumları, 2027 hükümlerini hariç tutma.

`normalization/legal_components_2026.py`:
- `load_component_catalog()` ile bütün tutarlar katsayı × 367 Decimal hesabına karşı yeniden doğrulanır.
- Bakanlığın yayımladığı 13 temel + planlı birleşik referans ile **tam TL'ye yuvarlanmış** kontrolü yapılır.
- Sahte `VERIFIED`, 2027 satırı, yanlış kaynak kararı, geçersiz yıl, tutar oynama ve mükerrer satır reddedilir.
- `stage_component_rates(session, apply=False)`: varsayılan yalnız analiz, veritabanına yazmaz.
- `apply=True`: `verified_support_rates` tablosuna **sadece DRAFT**, `source_versions.content_hash=UNVERIFIED_PRIMARY_PDF_BYTES`, `approved_by=NULL` kayıtları ekler. Gerçek SHA-256 olduğu iddia edilmez.
- Tekrarlı aktarım veri çoğaltmaz ve var olan veriyi sessizce güncellemez.
- Eski `support_amounts` verisi yerinde ve hesaplama motorundan ayrıdır.

### Uygulama komutları

```powershell
# Varsayılan: yalnız doğrula / say, veritabanını değiştirme.
python -m tarim_destek_rag.normalization.import_2026_components

# Önkoşul: Veritabanı tabloları ve 2026 destek programları oluşturulmuş olmalı.
# Önce veritabanı yedeği alın; açık izinle yalnız taslak kayıtları aktarın.
python -m tarim_destek_rag.normalization.import_2026_components --apply-draft

# Kaynak+hesaplama güvenlik sınırı
python -m pytest backend/tests/unit/test_legal_components_2026.py backend/tests/unit/test_p0_2_verified_rates.py -q
```

Kullanıcının canlı veritabanına bu PR nedeniyle otomatik migration/seed uygulanmaz. CLI elle kullanılır.

## 3. Kalan üretim engelleri

- 8859, 10394 ve 11781 özgün Resmî Gazete PDF baytları GitHub Actions üzerinden indirilip pypdf ile açıldı ve **gerçek SHA-256** hesaplandı. [Kanıt iş akışı](https://github.com/seydivakkas/TarimDestegimRAG/actions/runs/37805521090) altında indirilmiş PDF'ler ve JSON manifest bulunmaktadır. **Yasal metnin ilgili maddelerinin bağımsız insan incelemesi ve onay imzası hâlâ eksiktir.**
- Yetkili insan/iki aşamalı imza ve audit log. `VERIFIED` yalnız gerçek belge kanıtı ve onaydan sonra mümkündür. Onay dizgelerinin doldurulması tek başına yetki doğrulaması değildir.
- Bakanlığın **tüm havza-ürün/ilçe 2026 uygunluk listesi** ve sulama/ÇKS kontrollerinin sürümlendirilmesi. Yalnız `*/*` tutar tablosu bu koşulları yerine getirmez.
- Sertifikalı tohum ve fidan seçenekleri/sertifika ispatı, su kısıtı istisnaları ve diğer düzenleyici kuralların testi.
- Tarihsel 465 ve 170 gibi seed rakamları ve önceki 100 golden case'in bağımsız uzman referanslarıyla yenilenmesi.
- Tüm entegrasyon ve UI testleri; bu paket özellikle yeni hukuk/deterministik güvenlik testlerine odaklanır.

**Karar:** Güncel mevzuatın bileşenleri taslak katalogda belgelenmiştir. Ancak onay iş akışı ve havza doğrulaması bitmeden herhangi bir `estimated_amount` güvenilir hak ediş olarak sunulmamalıdır.

## 4. Özgün karar PDF'leri — byte-level kanıt (GitHub Actions)

| Karar | İndirilen PDF SHA-256 |
|---|---|
| 8859 | `89df0b6222edb4eddf3d5f588a4007061458adec8d518e3fbdb86b46ae5ba85f` |
| 10394 | `cc2598be4128db1d84cef20232b107f19fcd86ae430fda07933ab47b711940d9` |
| 11781 | `732048cbed664faabc15ad20a6a86427af7881acde24a88adf81007b79479e80` |

Doğrulama akışı `.github/workflows/legal-primary-evidence.yml`, toplama kodu `scripts/collect_2026_legal_evidence.py`. PDF baytlarının kimliği ölçülmüştür; bu durum **otomatik `VERIFIED` tutar onayı DEĞİLDİR**. Katalog gerçek orijinal SHA-256 değerlerini taşısa da veritabanına yapılan `DRAFT` aktarımın kaynak sürümü `UNVERIFIED_PRIMARY_PDF_BYTES` bekçi değeri kullanır. Bunun amacı belge indirmenin tek başına hukuki onay sayılmasını ve basit bir `approved_by` metin değişikliğinin ödeme yolunu açmasını önlemektir.

## 5. Test bağımlılığı notu

Eski `AssistantEngine` başlatıcısı modül import sırasında embedding modeli indirdiği için çevrimdışı CI testlerinin keşfi engelleniyordu. Bu PR'da import sırasında yalnız sözcüksel **BM25** indeksinin hazırlanması sağlandı; dense index API lifespan aşamasında isteğe bağlı hazırlanır. Bu değişiklik otomatik RAG doğrulaması anlamına gelmez.
