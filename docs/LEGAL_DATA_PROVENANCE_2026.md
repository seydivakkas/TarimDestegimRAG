# Mevzuat Kaynaklarının Yönetimi — 2026/11781 (P0-1)

**Durum:** İlk kaynaklı referans kataloğu hazır, bireysel destek tutarı hesaplamasına bağlanmadı.  
**Kayda alma tarihi:** 2026-10-08.  
**İlgili problem:** [Issue #2](https://github.com/seydivakkas/TarimDestegimRAG/issues/2).

## 1. Resmî kaynaklar ve doğrulama seviyesi

| Kimlik | Kaynak | Tarih | Kapsam |
|---|---|---|---|
| TOB-NEWS-7258-2026-09-08 | https://www.tarimorman.gov.tr/Haber/7258/Bitkisel-Ve-Hayvansal-Uretimde-Destek-Tutarlari-Artirildi | 08.09.2026 | 2026 katsayısı (367 TL/da), ürün grubu bazında **temel+planlı toplamları** |
| RG-2026-11781 | https://www.resmigazete.gov.tr/eskiler/2026/09/20260908-7.pdf | 08.09.2026 | 11781 sayılı karar, Resmî Gazete 33364; **PDF içerik çözümleme ve hash henüz tamamlanmadı** |

Bakanlığın haberindeki veriler resmî kurumsal açıklama olarak doğrulanmıştır; Resmî Gazete PDF bağlantısının içeriği bu değişiklik paketinde bağımsız olarak ayrıştırılmamıştır. Bu nedenle katalog **program-bileşen bazında onaylı fiyat listesi değildir**.

## 2. Makine tarafından okunabilir kaynak

- `configs/official_support_reference_2026.json` — *tek kanonik kaynak*.
- `backend/src/tarim_destek_rag/normalization/official_rates.py` — veri biçimini ve veri kullanım sınırını denetler.
- `GET /legal/2026-reference-rates` — API tarafından yalnızca yayınlanmış **birleşik referans tutarlar** sunulur.
- `backend/tests/unit/test_official_rate_reference_2026.py` — kaynak metadata, Decimal, çakışma ve yetkisiz kullanım bayrağı testleri.

Veri yapısında her tutar için birden fazla ürün kodu yer alabilir. Ürün alt türleri özellikle ayrılmıştır: `MISIR_DANE` ile jenerik `MISIR`, `AYÇİÇEĞİ_YAĞLIK` ile diğer ayçiçeği çeşitleri aynıymış gibi hesaplanamaz.

## 3. Bakanlık 2026 verileri

| Ürünler / grup | Temel + planlı destek toplamı (TL/da) |
|---|---:|
| Buğday, arpa, dane mısır | 954 |
| Yağlık ayçiçeği, fasulye, soya, kanola | 1101 |
| Pamuk | 1652 |
| Patates, soğan, aspir | 734 |
| Mercimek, nohut | 734 |

Destek katsayısı: **2026 için 367 TL/da**. 2027 katsayısı farklıdır ve bu katalogda 2026'ya uygulanmaz.

**Kesinlikle yapılmaması gerekenler:**

- Birleşik toplamı ikiye bölüp `BASIC_SUPPORT_2026` ve `PLANNED_PRODUCTION_2026` tutarları gibi kaydetmek.
- `GET /legal/2026-reference-rates` verisini `POST /evaluate` yerine kullanmak.
- Bakanlığın genel duyurusunu, tek çiftçinin ÇKS/havza/başvuru koşullarını karşıladığının kanıtı kabul etmek.
- Tutar kaydı olmayan ürün veya ilçeye `0 TL` veya `NOT_ELIGIBLE` vermek.
- Gerçek PDF içeriğini indirmeden veya kayıt altında hash oluşturulmadan `content_sha256` alanını doldurmak.

## 4. Eski seed tutarlarının uyumsuzluğu

`seed_data.py` içinde buğdayın mevcut iki bileşeni 465+465 = **930 TL/da**, Bakanlığın aynı desteklerin birleşik 2026 tutarı **954 TL/da**. Dolayısıyla fark **24 TL/da**. Bu durum `find_legacy_rate_discrepancies(...)` ile kayda alınabilir; farkın nasıl bileşenlere paylaştırılacağını tek başına belirlemez.

**Bu ilk alt paket, eski destek tutarlarını henüz değiştirmedi veya otomatik olarak güvenilir saymadı.** Eski seed yazmaya ve iş mantığı kullanmaya devam eder. Bu nedenle `POST /evaluate` uç noktasının destek tutarları mevzuat açısından nihai olarak doğrulanmış değildir. Bu risk takip eden P0 veri migration/karar motoru işinin kabul kriteridir; production release için engeldir.

## 5. Bir sonraki P0 kod gereksinimi

1. `SupportAmountModel` ve `SourceVersionModel` ile ilişkili sürümlü **program bileşeni** modeli.
2. Özel üretim yılı/geçerlilik aralığı, kaynak belge madde/fıkra ve gözden geçiren onayı.
3. Bileşenlerin tablo/katsayı üzerinden doğrulanması ve birleşik Bakanlık referanslarıyla tutarlılık testi.
4. SQLite ve diğer hedef veritabanları için idempotent migration; eski rakamlar geçmiş sürüm olarak kalmalı fakat varsayılan güncel hesapta kullanılmamalı.
5. `SupportRepository.get_amount` yalnızca geçerli ve doğrulanmış yeni sürümü döndürmeli; eksikse değerlendirme `REVIEW`.
6. Ülke çapında kapsama ayrı ele alınmalı. `BasinRepository.is_crop_supported_in_basin()` içinde `False` dönen eksik kayıtlar kayıtlı ret değildir.

## 6. Kullanım ve yerel doğrulama

```powershell
uv sync --extra dev
uv run pytest backend/tests/unit/test_official_rate_reference_2026.py -q
uv run uvicorn tarim_destek_rag.api.main:app --app-dir backend/src --reload
```

Tarayıcıdan `http://localhost:8000/legal/2026-reference-rates` endpoint'ini inceleyin.

**Test sonucu notu:** Bu oturumda GitHub erişimi bağlı uygulama üzerinden sağlanmış; ortamdan repo klonlama mümkün olmadığından `pytest` çalıştırma sonucu yoktur. Kod gözden geçirilip yerel/CI testleri geçmeden PR birleştirilmemelidir.
