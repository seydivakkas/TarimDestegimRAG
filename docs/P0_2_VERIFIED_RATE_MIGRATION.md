# P0-2 — Mevzuat verisinin hesaplama motoruna güvenli aktarılması

**8 Ekim 2026 | Geliştirme aşaması | Production: BLOKELİ**

## Risk ve veri kaynağı

`support_amounts` tablosu eski/demo veriyi saklar. Bu tablo, 2026/11781 değişikliğinden önce örnek olarak girilmiş rakamlar içerir. Sistem açılışındaki seed artık mevcut destek tutarlarını ve kaynak kimliğinin URL/durumunu **yeniden yazmaz**. Böylece eski veri arşivde kalır. Ancak eski tutarların saklanması onların hâlâ doğru olduğu anlamına gelmez.

Mevzuat kaynağı:
- 8 Eylül 2026 Bakanlık duyurusu: https://www.tarimorman.gov.tr/Haber/7258/Bitkisel-Ve-Hayvansal-Uretimde-Destek-Tutarlari-Artirildi
- 11781 sayılı karar: https://www.tarimorman.gov.tr/HHGM/Haber/262/

**Kritik yürürlük notu:** 11781 sayılı Kararın 2026 katsayısını değiştiren hükümleri 1 Ocak 2026'dan itibaren uygulanır; aynı kararın bazı diğer hükümleri 1 Ocak 2027 tarihinde yürürlüğe girer. Bir metindeki 2027 tohum/fidan tablosu 2026 üretim yılına uygulanmamalıdır.

## Yeni tablo: `verified_support_rates`

`database/models.py` içinde eklenen yeni tablo, eski `support_amounts` tablosuna dokunmadan oluşturulur:

| Alan | Açıklama |
|---|---|
| `program_id`, `crop_name`, `production_year` | Bileşen, ürün ve üretim yılı |
| `province`, `district` | Ülke geneli için `*`/`*` veya tam konum |
| `unit_amount`, `unit` | Ondalık birim tutar, `TRY/da` |
| `effective_from`, `effective_to` | Bileşenin değerlendirme zamanındaki geçerliliği |
| `source_version_id`, `legal_clause` | Belge sürümü ve dayanak hüküm |
| `review_status` | `DRAFT`, `VERIFIED`, `REVOKED` |
| `approved_by`, `approved_at`, `review_reference` | Onay sorumlusu, zamanı ve denetim referansı |

`SourceVersionModel` için gerçek SHA-256, tespit zamanı, yürürlük tarihi ve `superseded=False` kontrolü uygulanır. **64 haneli bir hash biçiminin doğrulanması, PDF içeriğinin bağımsız olarak doğrulandığı anlamına gelmez.** Şimdilik bu metadata, yayımlamadan önce yetkili insan doğrulamasına ve onay prosedürüne ihtiyaç duyar. Gerçek PDF byte hash'i bir sonraki kaynak işleme görevinde oluşturulmalıdır.

## Güvenli okuma sözleşmesi

`SupportRepository.get_amount(program_id, crop_name, *, production_year, province, district, as_of)`:

1. Yalnız `VERIFIED` bileşen kayıtlarını alır; `get_legacy_amount` üzerinden **geri dönüş yapmaz**.
2. Kaynağın ve programın aktif olmasını, üretim yılı/geçerlilik tarihlerini zorunlu kılar.
3. Doğrulanmış sürümün süresinin dolmamış ve mülga olmamasını kontrol eder.
4. Gözden geçiren kimliği, onay zamanı, denetim referansı ve mevzuat maddesi olmayan kaydı reddeder.
5. Girdi konumunu ulusal veya eşleşen il/ilçe kapsamıyla karşılaştırır.
6. Sıfır/geçersiz veya birden fazla çakışan bileşen varsa **tutar döndürmez**.
7. Onaylı eşleşme yoksa `None` döner: kural `REVIEW`, hesaplanan tutar `null`.

Birden fazla programın tahmini toplamı ancak **hiçbir bileşen `REVIEW` değilse** sayısal olarak raporlanır. Bütün bileşenler belirsizse total = `null`, asla güvenilir `0 TL` değildir.

## Migration stratejisi

- Eklemeli şema: `Base.metadata.create_all()` eksik `verified_support_rates` tablosunu oluşturur; `support_amounts` için destructive migration yoktur.
- Eski fiyat ve kaynak kayıtlarını güncelleyen startup işlemi engellenmiştir.
- Tekrarlı çalıştırma, onaylı bileşen kaydı oluşturmaz veya mevcut eski fiyatı değiştirmez.
- **Bu PR otomatik `VERIFIED` fiyat satırı eklemez.** Onay olmadan tutar girilmesi özellikle yasaktır.
- İleride gerçek kaynak PDF, madde/fıkra ve katsayı tablosu doğrulanınca `DRAFT` kayıtlar hazırlanacak; ayrı insan incelemesi sonrası yeni sürüm `VERIFIED` yapılacak.
- Önceki sürümler üzerinde geriye dönük değişiklik yapmak yerine `REVOKED`/`superseded` durumu ve yeni sürüm oluşturulmalıdır.
- Migration öncesi SQLite yedeği alınmalıdır. `create_all` şema dönüşümü veya data migration yerine geçmez; bu PR yalnızca eklemeli tablo oluşturmaktadır.

## Güvenlik sınırları ve eksik işler

- Yeni tabloda kayıtların `VERIFIED` olarak işaretlenmesini sağlayan **herkese açık bir API bulunmaz**. Yetkili veritabanı operasyonu kontrollü yapılmalıdır.
- Kod, `approved_by` gibi denetim alanlarının dolu olduğunu denetler; onaycının gerçekten yetkili olduğunu veya belgenin içeriğinin gerçek SHA-256'sını henüz bağımsız doğrulamaz. Bu nedenle üretimde veri onayı kapalı tutulmalıdır.
- Havza seed verisi henüz resmî kapsam doğrulaması değildir. Planlı üretim ve su kısıtı kuralları için ilave `verified_basin_rule_provenance` / `verified_water_restriction_provenance` gereklidir.
- Başvuru pencereleri ve ÇKS belgelerinin resmî doğrulaması ayrı çalışmadır.
- RAG metinsel iddia-kanıt doğrulaması P1 kapsamındadır.

## Kabul testleri

- Eski 465 TL/da değerinin varlığında bile `get_amount` `None` döndürmeli.
- Eksik/güncelliği dolmuş/yetkisiz/onaysız/iptal edilmiş/çakışan oranlar hesaplanmamalı.
- Kaynak sürümü `superseded` olduğunda daha önce onaylı rakam da artık kullanılamamalı.
- Ürün, üretim yılı ve ilçe eşleşmesi zorunlu.
- Birim fiyat doğrulanmamışsa API `REVIEW`, tutar ve toplam `null`.
- Sadece **sentetik test fixture** ile onaylı belge/bileşen eşlemesi gösterilebilir; bu sentetik tutar resmî fiyat ilanı değildir.
- `python -m pytest backend/tests/unit/test_p0_2_verified_rates.py -q` GitHub Actions üzerinde geçmeli.

## Sonraki aşama (bloker)

1. Resmî Gazete PDF'leri için tam içerik indirme/hash ve kaynak sürümü onay sistemi.
2. 2026/11781 ve 8859 kararındaki **program ayrı bileşenleri** için madde/Tablo 2/ürün grubu katsayısı doğrulaması.
3. Katı veri migration ve `VERIFIED` kayıt yayınlama yetkilendirmesi.
4. Havza ürün kapsamı, ek koşullar ve sulama mantığı (P0 karar motoru).
5. Eski 100 benchmark vakasının yeni, uzman kaynaklı gold set ile yeniden oluşturulması.

**Sonuç:** Hesaplama erişim hattı fail-closed olarak kurulmuştur. Onaylı üretim verisi bulunmadığı için uygulamanın güncel destek tahminleri hâlâ yayımlanmamalıdır.
