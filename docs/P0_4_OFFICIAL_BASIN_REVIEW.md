# P0-4 — 2026–2027 Resmî Havza–Ürün Deseni ve Denetlenebilir Karar Geçidi

**Durum (8 Ekim 2026):** 81 sayfalık resmî PDF'den **945 havza/ilçe, 81 il** çıkarıldı. JSON dosyası ve test altyapısı PR #14 içindedir. **Veri henüz bağımsız uzman onaylı değildir.** PR #12 (sürüm/hesaplama koruması), PR #13 (kaynaklı bileşen katsayıları) önkoşuludur.

## Tek kanonik kaynak

- [Tarım ve Orman Bakanlığı — 2026 yılı planlamaya konu havza ürün deseni PDF'i](https://www.tarimorman.gov.tr/BUGEM/Belgeler/Tar%C4%B1m%20Havzalar%C4%B1/2026%20Y%C4%B1l%C4%B1%20Planlamaya%20Konu%20Havza%20%C3%9Cr%C3%BCn%20Deseni%20Listesi.pdf)
- [Bakanlık Tarım Havzaları sayfası](https://www.tarimorman.gov.tr/Konular/Bitkisel-Uretim/Tarim-Havzalari)
- PDF byte SHA-256: `60263e83a953659ecc4f581bcd1ef1a921cf397bc5b4469869852470473f0b21`.
- İlk indirme ve ayrıştırma CI: [P0-4 kaynak kanıtı](https://github.com/seydivakkas/TarimDestegimRAG/actions/runs/37814505139).
- Kalıcı taslak dosya: `configs/2026_2027_basin_crop_draft.json`.
- İçerik: 945 adet benzersiz il/ilçe, ürünler, PDF sayfa numarası, yıldızlı dane mısır/damla sulama koşulu, `DRAFT` etiketi. Bu dosyada `complete_row_verified_by_human = false` zorunludur.

**Önemli:** Resmî ürün deseni iki üretim yılı (2026 ve 2027) için başlık taşır. Bu, 2027 para tutarı katsayılarının 2026'ya aktarılabileceği anlamına gelmez. İlçe deseninde listelenmeyen başka bir ürünün hangi destek programında temel desteğe uygun olduğu bu belgeyle tek başına karara bağlanamaz.

## Sürüm geçidi

`reviewed_basin_snapshots` adlı eklemeli yeni tablo, demo `basin_crop_rules` satırlarından bağımsızdır. İkisi karıştırılmamalı. Yeni ilçe kaydında tam ürün kümesi, `source_version_id`, `document_page`, `production_year`, damla sulama bayrağı ve denetçi bilgileri saklanır.

`BasinRepository.evaluate_official_crop()` yalnız şu sonuçları döndürür:

| Sonuç | Şart | Karar motoruna etkisi |
|---|---|---|
| `UNKNOWN` | İlçe yok; kayıt `DRAFT`; PDF sürümü/denetim alanları eksik; belirsiz ürün adı; mükerrer onaylı sürümler | `REVIEW` ve `verified_basin_provenance` |
| `LISTED` | Tek bir `VERIFIED`, `coverage_complete` ilçe kaydında ürün açıkça bulunuyor | Liste kapsamına uygun; ancak fiyat/ÇKS/özel koşullar ayrıca denetlenmeli |
| `NOT_LISTED` | Aynı onaylı **tam ilçe listesi**, tanımlı alt ürün kodunu içermiyor | Yalnız planlı üretim ürün deseni için ret kanıtı |

`MISIR` ifadesi otomatik `MISIR_DANE` yapılmaz. `PAMUK` otomatik `PAMUK_KÜTLÜ` değildir. `YEM_BITKILERI_GROUP`, tek bir yem bitkisi çeşidini otomatik kapsadığı anlamına gelmez; ürün alt türü ve özel koşulları ayrıca doğrulanmalıdır.

### Yıldızlı ilçeler: özel damla sulama şartı

Bakanlığın dipnotu: **Su kısıtı kapsamında belirlenen yıldızlı ilçelerde dane mısır üretiminde damla sulama şartı aranır.**

Konya/Karatay, PDF **53. sayfa**, listede `MISIR_DANE` ve yıldız işaretiyle kayıtlıdır. Veri onaylı olsa bile:

- `Parcel.drip_irrigation = None`: **REVIEW**.
- `Parcel.drip_irrigation = False`: bu koşul bakımından **NOT_ELIGIBLE**.
- `Parcel.drip_irrigation = True`: damla sulama koşulu geçebilir ama diğer koşullar eksikse **REVIEW**.

Bu alandaki `True` şimdilik **çiftçi beyanıdır**, resmi sulama belgesinin bağımsız kanıtı değildir.

## Kaynak çekme ve idempotent taslak aktarım

```powershell
# Resmî PDF ve JSON taslağı çıkar (veritabanına yazmaz).
python -m pip install pdfplumber
python scripts/extract_2026_basin_pdf.py --out-dir data/2026_basin_review

# Depoda saklı JSON'u şema/il/ilçe kapsamı yönünden denetle.
python -m tarim_destek_rag.normalization.import_2026_basin --catalog configs/2026_2027_basin_crop_draft.json

# Önce mevcut SQLite veritabanını yedekleyin.
# Yalnız DRAFT satırlarını yükler: 945 ilçe x 2 yıl = 1890 satır.
python -m tarim_destek_rag.normalization.import_2026_basin --catalog configs/2026_2027_basin_crop_draft.json --pdf data/2026_basin_review/source_2026_basin.pdf --apply-draft
```

Aktarım komutu aynı PDF'nin baytlarını ve JSON'daki SHA-256 değerini karşılaştırır; eşleşme olmadan veri yazılmaz. `--apply-draft` bile `VERIFIED` veya `coverage_complete` üretmez. Değişen kaynakla karşılaşılırsa mevcut kayıtlar üzerine yazılmaz, yeni belge sürümü/inceleme gerekir.

CI `.github/workflows/p0-4-basin-2026.yml` her değişiklikte resmi PDF'yi yeniden indirir; yeniden çıkarılan JSON ile depoda taahhüt edilen katalogun içerik eşitliğini zorunlu tutar ve resmi PDF'yi artefakt olarak saklar. 945 havza sayısı [Bakanlığın Tarım Havzaları sayfası](https://www.tarimorman.gov.tr/Konular/Bitkisel-Uretim/Tarim-Havzalari) ile de uyumludur.

## Onaylama gereksinimleri (henüz uygulanmış bir yetkilendirme sistemi değil)

1. PDF'nin gerçek SHA-256 ve yasal yürürlük kontrolü.
2. İlçe ürün satırları, satır sayısı, başlıklar ve dipnotların uzman incelemesi. PDF tablosunun makinece ayrıştırılması tek başına insan onayı değildir.
3. Ürün alt türlerinin, yem bitkileri alt gruplarının, 2026-2027 farklılıklarının ve su kısıtı şartının teyidi.
4. Değişiklik ve onay işlemleri için kimlik doğrulamalı, tercihen iki onaycı gerektiren imzalı denetim izi.
5. Ancak tamamlanmış ilçe satırları `VERIFIED` ve `coverage_complete=True` olabilir. Sistem için böyle bir otomatik yükseltme API'si eklenmemiştir.
6. `SupportRepository.get_amount` da ayrıca onaylı ücret kaydını gerektirir; havza deseninin onayı ödeme yetkisi değildir.

**Üretim durumu:** Kapalı. Havza verisi coğrafi kanıt temelini geliştiriyor ancak yetkili hukuk/doğrulama onayı ve ödeme bileşenleri yayımlanana kadar `REVIEW` ilkesi korunmalıdır.
