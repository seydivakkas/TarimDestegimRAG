# TarımDesteğimRAG — Kod İnceleme, Hata Listesi ve İyileştirme Planı

**İnceleme tarihi:** 8 Ekim 2026  
**Repository:** https://github.com/seydivakkas/TarimDestegimRAG  
**Referans commit:** `2e60121d29c9d37d24d0f00cdb81436d4e7b9dc6` (`main`)  
**İnceleme kapsamı:** GitHub kaynak dosyalarının uzaktan statik incelenmesi, README/master plan, PC Gradio arayüzü, FastAPI, veri seed'leri, kurallar, atıf kontrolü, RAG, benchmark, Flutter dosya ağacı ve seçili testler. **Kaynak kodu yerel makinede klonlanıp çalıştırılmadı; bütün testler yeniden çalıştırılmış gibi raporlanmıyor.**

## 1. Ürün vizyonu ve temel ilke

Sistem çiftçiye şu soruları cevaplamalıdır: **(1)** Hangi destekleri değerlendirebilirim? **(2)** Hangi belge veya koşul eksik? **(3)** Yaklaşık tutar ne ve hangi sürüm mevzuata göre? **(4)** Başvuru nereye, ne zaman yapılır? **(5)** Dayanağını nerede kontrol edebilirim? **(6)** Birden fazla parselim için toplam sonuç nedir?

Temel mimari kararı korunmalı: **LLM/RAG, hukuki uygunluk kararını ve tutarı belirlemez; kaynaklı açıklama katmanıdır.** Ancak bugünkü deterministik motorda kullanılan veri eksik/hatalı ise deterministik hesap **otomatik olarak doğru hesap** değildir.

## 2. Öncelikli bulgular ve kanıt dosyaları

### P0 — Güvenilirlik ve finansal doğruluk

**P0-01: 2026 birim fiyat kayıtları resmî güncel değişikliği yansıtmıyor.**  
`backend/src/tarim_destek_rag/normalization/seed_data.py:73-183` dosyasında buğday temel ve planlı üretim birim fiyatları ayrı ayrı 465 TL/da tanımlı. Tarım ve Orman Bakanlığı, 8 Eylül 2026 değişikliğinde destek katsayısını 310'dan 367 TL'ye çıkardığını; buğday/arpa/mısır temel+planlı toplamının 806 TL/da'dan yaklaşık 954 TL/da'ya yükseldiğini açıklıyor. Bu örnek, mevcut seed'lerin mevzuat sürümünün güncel olmadığını gösterir. Kaynak: https://www.tarimorman.gov.tr/Haber/7258/Bitkisel-Ve-Hayvansal-Uretimde-Destek-Tutarlari-Artirildi ; düzenleme bildirimi: https://www.tarimorman.gov.tr/HHGM/Haber/262/ . Eski yayımlanmış tablo: https://www.tarimorman.gov.tr/BUGEM/Belgeler/Tar%C4%B1m%20Havzalar%C4%B1/2026%20Y%C4%B1l%C4%B1%20Destekleme%20Birim%20Fiyatlar%C4%B1.pdf (güncel değişikliği tek başına yansıtmayabilir).  
**Öneri:** Karar/tebliğ, hüküm geçerliliği, ürün/kategori/katsayı ve başlangıç-bitiş tarihlerini ayrı, sürümlü kaydet; elle girilmiş eski değerleri doğrulanmış tabloyla değiştir. Yetkili kaynaksız tutar için sayısal tahmin üretme.

**P0-02: Coğrafi/ürün kapsamı sunum ile veri arasında uyuşmuyor.**  
`frontend_pc/geo_data.py` tüm il/ilçeleri sunarken `seed_data.py:198-227` sadece üç havza-ürün örneği ve `:246-264` yalnız iki su kısıtı bölgesi kaydı tohumluyor. 16 ürün menüsü olmasına rağmen tutar kapsamı sınırlı. Bulunmayan bilgi `UYGUN DEĞİL` şeklinde değerlendirilmemeli; `VERİ YETERSİZ/DOĞRULAMA GEREKLİ` durumuna ayrılmalı.

**P0-03: Sulama verisi istemciden doğru API alanına aktarılmıyor.**  
`frontend_pc/app.py:177-187` `parcel_data` içine `is_irrigated` gönderiyor; `backend/.../models/farmer_parcel.py` ise `irrigation: IrrigationStatusEnum` bekliyor ve varsayılan olarak `DRY` atıyor. İstemci ve Pydantic alan adı uyuşmazlığı nedeniyle kullanıcıdaki sulu/kuru/bilinmiyor ayrımı kaybolabilir. `backend/.../rules/rules_impl.py` içindeki `WaterRestrictionRule` ise sulama şartını kontrol etmiyor. Bakanlık 2026 tablosu su kısıtı desteği için belirlenen **sulu tarım arazileri** koşulunu içeriyor.  
**Öneri:** API sözleşmesinde `irrigation` gönder; üç durumu koru; su kısıtı kurallarında şartı işlet; regresyon testleri ekle.

**P0-04: Karar statülerinde başarısızlık/eksik bilgi önceliği belirsiz.**  
`rules_impl.py` içindeki kural örnekleri önce `if missing: REVIEW`, sonra `elif failed: NOT_ELIGIBLE` kullanıyor. Hem kesin olumsuz şart hem bilinmeyen şart varsa sonucu REVIEW seçiyor. **Karar politikası** program bazında, gerekçesiyle belirlenmeli. Kesin ret mevcutsa REVIEW ile gizlenmemeli; ayrı `failed` ve `unknown` etiketleri birlikte korunmalı.

**P0-05: Kaynak doğrulayıcı iddiaları gerçekte doğrulamıyor.**  
`backend/src/tarim_destek_rag/citations/verifier.py`: kayıtlı kaynak, `active` bayrağı ve `year == 2026` denetimi yapıyor. Belgenin erişilebilirliği, kaynak bölümünün doğruluğu, alıntının belgede bulunması, yürürlük ve değişiklik/supersession zinciri, SHA eşleşmesi incelenmiyor. Bu kontrole `doğrulanmış resmi madde` adı verilmemeli.  
**Öneri:** Kaynak kimliği + sürüm + madde kimliği + belge SHA256 + metinsel alıntı aralığı + yürürlük kontrolü; doğrulanamayan atıflar kullanıcıya açıkça gösterilmeli.

**P0-06: Benchmark metrikleri güvenilir değil.**  
`backend/src/tarim_destek_rag/evaluation/benchmark_runner_v1.py:129-136`: hiç atıf yoksa `citation_valid=True` kalıyor, yalnız ilk atıf sınanıyor. `:171`: eligibility ve calculation accuracy aynı `passed_cases` üzerinden hesaplanıyor. `:175`: `freshness_acc = 100.0` sabit. `:183-187`: eksik retrieval metrikleri mükemmel sonuç olan 1.0'a varsayılanlanıyor. `frontend_pc/app.py:93-130` her vakaya `✅ %100 Uyum` yazıyor, `:1100-1108` panel metrikleri sabit.  
**Öneri:** Durum doğruluğu/tutar exact-match ayrı pay/payda, citation için tüm atıflar, boş liste başarısız/coverage dışı etiketi, gerçek fresh/stale vakaları ve eksik metrik durumunda fail-closed; arayüz yalnız o commit+veri sürümünde yeniden üretilmiş `benchmark/report.json` göstersin.

**P0-07: Hak sahipliği raporu yanlış resmîlik izlenimi verebilir.**  
`frontend_pc/app.py:497-503` çıktı başında doğrudan `# T.C. TARIM VE ORMAN BAKANLIĞI` ve `RESMÎ ÖN DEĞERLENDİRME RAPORU` kullanıyor. Bu, özel geliştirilen aracı kamu kurumu raporuymuş gibi gösterebilir.  
**Öneri:** `TarımDesteğimRAG — Bağımsız Bilgilendirme ve Tahmini Ön Değerlendirme Raporu` başlığı; `resmî başvuru, onay veya ödeme belgesi değildir` uyarısı; üretim zamanı, veri revizyonu, kaynaklar, hata/eksik alanlar.

**P0-08: Gerçek web hasadı iddiası ile uygulama farklı.**  
`backend/src/tarim_destek_rag/api/main.py:306-320` `/faqs/harvest` çağrısı yalnız `seed_initial_knowledge()` çalıştırıyor; gerçek `harvest_from_web()` çağrılmıyor. `faq_harvester.py:515-519` dış veriler verilmediğinde `0` döndürüyor. `:544` dış kayıtlar için varsayılan `verified=True`; doğrulama kanıtı zorunlu değil.  
**Öneri:** Sabit veri aktarımı ve gerçek taramayı ayrı işlevlere böl, tarama sırasında URL/HTTP durumu/snapshot/değişiklik farkı/inceleme onayı/indeks yenileme zincirini gerçek zamanlı göster. İnsanca/onaylı kontrol olmadan dış soruları `verified` işaretleme.

**P0-09: Açık yönetim uçları.**  
`api/main.py:94-100` CORS kaynakları `*`; `:306-320` veri yazan `/faqs/harvest` için yetkilendirme kontrolü görünmüyor. Yerel bilgisayarda yalnız `127.0.0.1` ile sınırlı çalışma ayrı; ağ erişimine açıldığında erişim kontrolü şart.  
**Öneri:** Yetkilendirilmiş admin rolü, audit log, CSRF/Origin stratejisi, rate limiting, CORS allowlist, production hata mesajlarında ayrıntı saklama.

### P1 — Eksik işlevler ve davranış hataları

**P1-01: Flutter çalıştırılabilir uygulama eksik.**  
Repo `mobile/` altında `pubspec.yaml` ve iki `test/*.dart` barındırıyor; ancak `lib/main.dart`, servisler, modeller ve ekranlar yok. Testlerde içe aktarılan `data/models` ve `data/services` paketleri kaynak ağacında bulunmuyor. Bu commit için README'deki tamamlanmış mobil istemci iddiası karşılanmıyor. Temel scaffold, typed API, durum yönetimi, ekranlar ve testlerle tamamlanmalı.

**P1-02: Birbirini izleyen ve aynı veri gösteren ekranlar.**  
`frontend_pc/app.py:207-284` profilde destek kalemleri+toplam, ardından `:286-348` Desteklerim kartları+aynı toplam hazırlanıyor, sonra ayrı detay tablosu var. Tek hesap response'u `gr.State` ile korunmalı ve aşağı akışlarda yeniden kullanılmalı. Detay/gerekçe ayrı modüler bileşenler olmalı.

**P1-03: Başvuru takvimi yanlış 'açık' gösterilebilir.**  
`frontend_pc/app.py:650-664` API'de tarih bulunamazsa 01.09–31.12.2026 varsayımı yapıyor; `active=True` ise `BAŞVURUYA AÇIK` diyor, bugünün tarihi ve programın başlangıç/bitişi değerlendirilmiyor. `:343` destek tablosunda da aynı genel tarih sabit. **Öneri:** bilinmeyen tarih `Doğrulanmadı`, durum `UPCOMING/OPEN/CLOSED/UNKNOWN` yalnız kaynaklı tarih + yerel Türkiye tarihiyle hesaplanmalı.

**P1-04: Kurallar arayüzdeki tüm alanları işletmiyor.**  
`age_group`, `gender`, `is_closed_orchard` alınmasına karşın incelenen 5 kuralda genç/kadın ilave desteği hesaplaması ve kapama bahçe koşulu kontrolü yok. Bu alanlar süs niteliğinde kalmamalı. İlgili mevzuatın kapsamı yeniden yorumlanmalı; tek bir `age_group/gender` bayrağı her üreticinin ilave hak kazanması anlamına gelmez.

**P1-05: İndeksleme aynı parçaları iki kez ekliyor.**  
`api/main.py:50-58` hem doğrudan `vector_store.add_chunks(OFFICIAL_REGULATION_CHUNKS)` hem `hybrid_retriever.add_chunks(...)` çağırıyor; `hybrid.py` ikinci çağrıda aynı `vector_store.add_chunks()` çalışıyor. Aynı kaynakların dense indeksinde iki kez bulunmasına neden olur. Ayrıca senkronizasyon tekrarlandıkça aynı FAQ chunk'ları yeniden indekslenebilir. **Öneri:** tek indeksleme giriş noktası ve `chunk_id/source_version` esaslı idempotent upsert veya tam rebuild.

**P1-06: Kaydetme ve çoklu parsel yok.**  
Mevcut PC formunda tek `PARCEL-DEMO-001` ile bir defalık değerlendirme var. Kullanıcının birden fazla tarlasını toplama, profili kalıcı saklama, değerlendirmeyi yeniden açma, başvuru/dosya durumunu izleme akışı geliştirilmelidir. Kimlik/kişisel verilerin KVKK kapsamı ayrıca değerlendirilmelidir.

**P1-07: Raporlar güvenli/tekil ve tekrar üretilebilir değil.**  
`app.py:584-593` rapor adı Unix saniyesinden oluşuyor, eşzamanlı üretimler aynı dosyaya yazabilir. Her kullanıcı için kimliksiz kayıt da değil; çok kullanıcılı kullanımda rapor erişimi düşünülmeli. **Öneri:** benzersiz UUID, kullanıcının oturumuna ait depolama, indirme yaşam döngüsü, kaynak ve karar sürümleri.

**P1-08: `0 TL` ile bilinmeyen/uygun değil karışabiliyor.**  
Eksik miktar `0` ile doldurulduğunda gerçek hak ediş hesabı yapan kullanıcı yanlış yorumlayabilir. `estimated_amount=null`, `amount_status=NOT_CALCULATED/UNKNOWN` ve iş nedeni ayrı taşınmalı.

### P2 — Bakım, API ve UX

**P2-01:** README '9 sekme' diyor; `frontend_pc/app.py:735,852,869,898,942,1058,1093,1111` konumlarında **8 adet** `gr.TabItem` bulunuyor. Ek bir sekme üretmek yerine bilgi mimarisini gerçek tasarımla uyumlu hale getir.  
**P2-02:** `MASTER_PLAN.md` ve `TarimDestekRAG_Cursor_MASTER_PLAN_v1.0.md` Git blob SHA'sı aynı (`89553a86...`); tek kanonik plan + isteğe bağlı yönlendirici dosya.  
**P2-03:** `benchmark/cases.jsonl` ve `data/benchmark/cases.jsonl` aynı içerik; tek veri konumu.  
**P2-04:** Birden fazla FAQ / sohbet / SSS / mevzuat görünümü parçalı akış yaratıyor; ortak arama ve tek kanıt kartı.  
**P2-05:** HTML içine kullanıcı/servis metinlerinin doğrudan biçimlendirilmesi (`app.py:189-192,226-233,316-327`) XSS/sunum bozulması riski doğurabilir; `html.escape` ve güvenilir komponent render tercih edilmeli.  
**P2-06:** SSS senkronizasyonu sonucunda arayüzün beklediği `total_faqs_in_db` API cevabında yok (`main.py` sadece `total_faqs` döndürüyor). Dolayısıyla başarılmış hasatta üst panel yanlış `0 SSS` gösterebilir.  
**P2-07:** Kullanıcı arayüzü ile yönetim/benchmark menülerini ayır; iç kalite metriklerini ürün değerleriyle karıştırma.  
**P2-08:** SQL seed işlemleri uygulama açılışında her defasında upsert yapıyor; idempotency ve kontrollü migration/release veri yönetimi tanımlanmalı.

## 3. Yinelenen sayfalar için yeni bilgi mimarisi

**Kullanıcı menüsü (önerilen 5 bölüm):**

| Yeni bölüm | Eski ekranlardan taşınacak içerik | Yeni yetenek |
|---|---|---|
| **Çiftçi & Parsellerim** | Profil + Parsel formu | Çoklu parsel, doğrulama, kaydet/düzenle/sil |
| **Desteklerim** | Profil inline özet + Desteklerim + Destek Detay + Neden? | Özet KPI, filtrelenebilir destek kartı, açılır detay, kural gerekçesi, resmî atıf, başvuru durumu |
| **Başvuru & Belgelerim** | Dağınık belge listesi, statik takvim | Program bazlı kaynaklı takvim, kontrol listesi, durum takibi, hatırlatıcı |
| **Mevzuat Asistanı** | Chat + hızlı sorular + SSS tablosu | Tek arama kutusu, soru koleksiyonu, kaynak/kaynak tarihi, cevap güven düzeyi |
| **Hesaplamalarım & Raporlar** | Markdown rapor ve değerlendirme | Kaydedilen sürümlü hesaplamalar, yeniden karşılaştırma, yazdırma, CSV/PDF export |

**Yönetici/araştırmacı menüsü (kullanıcıdan ayrı, yetki kontrollü):** `Kaynaklar & Sürüm Farkları`, `Doğrulama & Benchmark`, `Parametre Yönetimi & Sistem Sağlığı`.

**Önemli UX kararı:** 'Destek Detay' ve 'Neden?' tüm destekleri baştan tekrar eden ayrı sayfa olmayacak; seçilen **tek bir destek kartının altındaki** `Hesaplama`, `Uygunluk Şartları`, `Eksikler`, `Başvuru`, `Kaynaklar` sekmeleri/akordeonları olarak gösterilecek. Desteklerim sayfasında ayrı ayrı veri tekrar edilmeyecek.

**Veri akışı:** `Form -> POST /evaluate -> EvaluationResponse(gr.State) -> Özet KPI + destek kartları -> Seçilen destek için detay -> Kaynak kanıtı -> Rapor`. Aynı yanıttan farklı görünüm üretilir; gereksiz tekrar API çağrısı yoktur.

## 4. Önerilen uygulama mimarisi

```text
frontend_pc/
  app.py                    # Uygulama, navigasyon
  components/
    profile_form.py
    summary_cards.py
    support_detail.py
    source_card.py
    application_steps.py
  pages/
    parcels.py
    supports.py
    applications.py
    assistant.py
    reports.py
  state.py                  # Evaluation UI state
  api_client.py

backend/src/tarim_destek_rag/
  api/
    main.py
    routes/
      evaluations.py
      supports.py
      assistant.py
      admin.py
  rules/
    rules_impl.py
    policy.py              # ELIGIBLE / NOT_ELIGIBLE / REVIEW / DATA_UNAVAILABLE
  legal/
    version_catalog.py
    effective_dates.py
    evidence_verifier.py
  normalization/
    seed_data.py            # Gerçek doğrulanmış sürümlü veri
  ingestion/
    fetch.py
    snapshot.py
    parse.py
    diff.py
    review.py
    publish.py
  retrieval/
    hybrid.py
    vector_store.py       # Tekil, idempotent indeks
  evaluation/
    benchmark_runner_v2.py

mobile/
  lib/
    main.dart
    data/models/
    data/services/
    features/profile/
    features/parcels/
    features/supports/
    features/assistant/
    features/applications/
```

Yeni klasörler öneridir; mevcut dosyaları doğrudan silmeden, testler yeşil kalacak şekilde aşamalı taşınmalıdır.

## 5. Önerilen sözleşme düzenlemeleri

* `Parcel.irrigation: "IRRIGATED" | "DRY" | "UNKNOWN"` zorunlu açık alan veya güvenli explicit bilinmeyen; istemci `is_irrigated` göndermemeli.
* `Eligibility.status: "ELIGIBLE" | "NOT_ELIGIBLE" | "REVIEW" | "DATA_UNAVAILABLE"`; ayrıca `failed_checks`, `unknown_fields`, `evidence_refs`.
* `Calculation.amount_status: "CALCULATED" | "NOT_APPLICABLE" | "NOT_CALCULATED"`; JSON tutarlar kesin ondalık **string** taşınmalı; sunumda `Decimal` kullanılmalı.
* `Evidence` için `source_url`, `document_sha256`, `source_version_id`, `article`, `effective_from`, `effective_to`, `verified_at`, `quote`, `verification_status`.
* `ApplicationWindow` için `start_date`, `end_date`, `source_version_id`, `verified_at`; değer eksikse hiç tarih uydurulmamalı.
* `EvaluationResponse` için `calculation_id`, `ruleset_version`, `dataset_version`, `evaluated_at`, `coverage_warnings`, `confidence_disclaimer`.

## 6. Aşamalı düzeltme sırası ve kabul kriterleri

### Sprint 0 — Finansal ve hukuki güvenlik (ilk ve zorunlu)

- [ ] Mevzuat ve fiyat tablolarının 8.09.2026 değişiklikleri dahil sürümlü doğrulanması.
- [ ] Yanlış/eksik kaynakta 'doğrulama gerekli' statüsü ve tutar bastırma.
- [ ] `irrigation` alanı ile su kısıtı koşulunu uçtan uca düzeltme.
- [ ] Sabit başvuru tarihleri ve açık/kapalı bayraklarını kaldırma.
- [ ] Bağımsız rapor kimliğini doğru gösterme.
- [ ] Güvenilmeyen SSS'yi varsayılan `verified=True` yapmama.
- [ ] Sağlık/benchmark göstergelerini gerçeğe uygunlaştırma.

**Bitiş kapısı:** Mevzuat referansları, ürün başına tutar ve negatif/bilinmeyen koşul testleri doğrulanmadan “resmî olarak doğrulanmış” ibaresi kullanılmıyor.

### Sprint 1 — Tekilleştirme ve ekran sadeleştirme

- [ ] 8 tabı sadeleştir; 5 kullanıcı alanı + yetkili yönetim alanı.
- [ ] Profilde yalnızca küçük hesaplama özetini tut; tüm kartlar tek Desteklerim ekranında.
- [ ] Detay, gerekçe, belge ve atıf aynı destek nesnesine bağlanmalı.
- [ ] `gr.State` ile form/result durumu tek merkezde yönetilmeli.
- [ ] FAQ ve sohbet ortak arama/kaynak kartını kullanmalı.

**Bitiş kapısı:** Her işlevin tek ana giriş noktası var, bir değerlendirme bir kez hesaplanıyor; görünümler tutarlı.

### Sprint 2 — RAG + kaynak senkronizasyonu

- [ ] `seed_initial_knowledge` ve `harvest_from_web` uçları ayrıldı.
- [ ] Kaynak değişikliği için fetch → parse → diff → review → publish işlem hattı.
- [ ] Atıf doğrulama gerçek belge, metin, sürüm ve yürürlük kontrolü.
- [ ] Yeniden indeksleme idempotent; tekrar senkronize edildiğinde chunk sayısı artmıyor.
- [ ] SSS için taslak/onaylı/eskimiş statüleri.

**Bitiş kapısı:** Aynı kaynak iki kez işlendiğinde indeks cardinality sabit; doğrulanmamış madde doğru etiketleniyor.

### Sprint 3 — Eksik ürün işlevleri

- [ ] Çoklu parsel/profil kayıtları, hesaplama geçmişi, çıktı raporu.
- [ ] Belgelerim/başvurularım ekranı, takvim ve yol haritası.
- [ ] Flutter `lib/` uygulamasını model+servis+ekran+test olarak tamamla.
- [ ] Yetkili yönetici girişi ve rol bazlı erişim.

**Bitiş kapısı:** Mobil bir end-to-end happy path çalışıyor; PC ve mobil aynı API sözleşmesini kullanıyor.

### Sprint 4 — Bilimsel değerlendirme ve sürüm yayımlama

- [ ] Benchmark metrikleri ayrık ve dürüst (eligibility, amount, retrieval, citation, freshness).
- [ ] Doğrudan resmî kaynaklardan oluşturulmuş *bağımsız* golden set / hakem kontrollü testler.
- [ ] İlgisiz sorular, çelişkili mevzuat, eksik kaynak, zaman aşımı, index boşluğu, yanlış ilçe, olumsuz senaryolar.
- [ ] Pipeline sürümleri, test ortamı, commit SHA, CPU/GPU, ölçüm yöntemi ve tarih raporlandı.
- [ ] `.github/workflows/ci.yml`: Python test/lint, Flutter analyze/test, güvenlik taraması, smoke test.

**Bitiş kapısı:** Sonuçlar tekrarlanabilir, testler CI'da doğrulanmış; yüzdelik metrikler sabit yazılmıyor.

## 7. Yeni test sözleşmeleri (ilk eklenmesi gerekenler)

1. `test_frontend_irrigation_enum_roundtrip`: Kullanıcının Sulu/Kuru/Bilinmiyor seçimi API `irrigation` alanından aynen geçiyor.
2. `test_water_restriction_requires_irrigated`: Kuru tarım parselinde su kısıtı desteği uygunluk kararı verilmez; bilinmiyor REVIEW olur.
3. `test_missing_basin_data_not_equivalent_to_ineligible`: Henüz kaynaklanmamış ilçe, açık destek dışı ilçe gibi muamele görmez.
4. `test_calculation_official_wheat_2026_updated_coefficient`: Resmî kaynağın geçerli sürümüne göre koşullu buğday senaryosu doğru hesaplanır.
5. `test_unknown_application_window_not_open`: Tarih yoksa UI OPEN demez.
6. `test_citation_missing_or_wrong_quote_fails`: Boş atıf veya kaynakta bulunmayan alıntı VERIFIED olmaz.
7. `test_benchmark_accuracy_metrics_independent`: Karar doğru, tutar yanlış vakası iki metrikte ayrı sayılır.
8. `test_freshness_requires_evidence`: Gerçek kaynak sürümü olmadan freshness `%100` olamaz.
9. `test_same_source_twice_does_not_duplicate_vectors`: İki seed/harvest sonrası indeks parça sayısı değişmez.
10. `test_harvest_does_not_verify_unknown_web_items`: Dış kayıt önce inceleme bekler.
11. `test_mobile_scaffold_present`: `mobile/lib/main.dart` ve test importlarının gerçek dosyaları var.
12. `test_report_is_not_misrepresented_as_government_document`: Sistem raporu resmî makam yazısı gibi isimlendirilmez.

## 8. İlk değişiklik PR'ının önerilen sınırı

**PR-001: `fix/accuracy-and-data-integrity`**

**Değiştirilecekler:** `normalization/seed_data.py`, `models/farmer_parcel.py` (gerekli sözleşme kontrolü), `frontend_pc/app.py`, `rules/rules_impl.py`, `citations/verifier.py`, `evaluation/benchmark_runner_v1.py`, uygun testler ve README.  
**Değişiklik sırası:** (1) kaynak/katsayı sürümü → (2) API alan eşleşmesi → (3) kural önceliği & bilinmeyen veri → (4) dinamik takvim → (5) dürüst benchmark → (6) rapor etiketi.  
**Geri alma:** Her değişiklik bağımsız commit; eski mevzuat sürümü geçmiş değerlendirmeler için arşivde tutulur.  
**Yayımlama engeli:** Resmî veri güncellenmeden rakamların prod'da “kesin” görünmesi kabul edilmez.

## 9. Erişim ve doğrulama durumu

Bu rapor **okunan kaynak koduna dayanır**, fakat depo bütün halinde yerel test ortamına indirilemedi ve GitHub'a yazma yetkisiyle bağlantı kurulamadı. Dolayısıyla hiçbir düzeltme uygulanmış veya testler çalıştırılmış gibi gösterilmemelidir. İleri adım: deponun GitHub entegrasyonunu bağlayıp ayrı bir branch üzerinde PR-001'i uygulamak ve testleri çalıştırmak; ya da kullanıcının ZIP dosyasını çalışma alanına yüklemesi.
