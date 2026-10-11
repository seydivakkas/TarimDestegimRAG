# PR #36 — Mevzuat gerekçesi → özgün kaynak → işaretli pasaj kabul planı

## Sözleşme

Üç ayrı iddia birbirine karıştırılmayacak:

1. **Konum kanıtı:** PDF/HTML'de ilgili cümle veya ilçe/ürün hücresi gerçekten var mı? Değişmeyen özgün belge SHA'sı, sayfa, madde/fıkra veya kaynak satırı ve birebir pasaj denetlenir.
2. **Hukukî geçerlilik:** Hüküm ilgili üretim yılında yürürlükte mi? 2024/39, 2025/42, 8859 ve eklerdeki değişiklik/yürürlük zinciri bağımsız denetlenmeden hukukî onay verilmez.
3. **Çiftçi koşulunun sağlanması:** Örn. 2024/39'un kayıt zorunluluğu cümlesi, herhangi bir üreticinin ÇKS kaydının **aktif** olduğunu tek başına ispatlamaz. ÇKS, sertifika, tapu, tarla, sulama ve icmalin olgusal doğrulaması ayrıdır.

## Ortak kanıt yolu

`citations/evidence_contract.py::verified_highlight_path` aynı doğrulama mantığını PC Neden? paneli ve indirilen rapor için kullanır. Her kanıt linki, ilgili API endpoint'i tarafından arşivdeki özgün SHA sabitli dosyaya göre **yeniden doğrulanır**. Sözleşme aşağıdaki türleri destekler:

| Belge | Doğrulanan kimlik ve konum | İşaretli endpoint | Kapsam |
|---|---|---|---|
| Metin katmanlı PDF | SHA + sayfa + birebir cümle + doğru madde konumu | `/evidence/highlight/{sha}?page=&quote=` | Yalnız özgün kaynakta indekslenen cümleler |
| Taranmış 8859 PDF | SHA + sayfa + gözden geçirilen fiziksel pasaj koordinatı | `/evidence/highlight/visual/{sha}?support_id=` | MADDE 2(1) konum işareti; transkripsiyon ve hukukî onay ayrı |
| 2024/39 özgün HTML | SHA + MADDE 4(1) + birebir tam pasaj + benzersiz hedef | `/evidence/highlight/html/{sha}?support_id=` | `BASIC_SUPPORT_2026` kaydı; diğer maddeler henüz indekslenmedi |
| Havza–ürün PDF | SHA + il + ilçe + kesin ürün alt türü + yıl + aynı tablo satırı ve hücre | `/evidence/highlight/basin/{sha}?province=&district=&crop=&production_year=` | Konum kanıtı; destek uygunluğu değil |

**Her türlü SHA, madde, sayfa, sorgu parametresi veya paragraf belirsizliği: NO LINK.** Yalnızca genel belgeyi açma, işaretli mevzuat kanıtı sayılmaz.

## 2026 destek programı ve gerekçe kapsama matrisi

Bu tablo doğrulanmamış maddeleri tahmin ederek doldurmaz. Kaynakta ilgili hüküm veya kural-madde eşlemesi bulunmadığında durum bilerek HOLD'dur.

| Kural ailesi | Gerekçenin alt konuları | Kaynak konumunun mevcut kapsamı | Açık iş |
|---|---|---|---|
| `BASIC_SUPPORT_2026` | Üretim yılı, ÇKS şartı, parsel alanı, destekli ürün, birim oran | 8859 MADDE 2(1) görsel; 2024/39 MADDE 4(1) özgün HTML konum ispatı | Diğer alt şartların birebir kaynak maddeleri, 2025/42 değişiklik etkisi, hukukî uygunluk |
| `PLANNED_PRODUCTION_2026` | ÇKS, havza–ürün eşlemesi, sulama alt türü, münavebe ve onaylı tutar | Kaynak varsa yalnız **seçilen** ilçe/ürün PDF satırı | Tüm diğer gerekçelerin madde/fıkra ve dönemsel yürürlük kanıtları |
| `CERTIFIED_SEED_2026` | ÇKS, destek kapsamı, sertifikalı tohum faturası ve onaylı birim oran | Birebir kaynak–gerekçe eşlemesi tamamlanmadı | Tebliğ hüküm/fıkra, ek cetvel, geçerli sürüm |
| `CERTIFIED_SAPLING_2026` | ÇKS, fidan faturası, kapama bahçe, asgari alan ve oran | Birebir kaynak–gerekçe eşlemesi tamamlanmadı | Tebliğ hüküm/fıkra, ek cetvel, geçerli sürüm |
| `WATER_RESTRICTION_2026` | ÇKS, ilçe/havza su kısıtı, sulama durumu, ürün kapsamı, oran | Birebir kaynak–gerekçe eşlemesi tamamlanmadı | Onaylı su kısıtı kaynağı, değişiklikler, yürürlük ve tutar |
| Mevzuat Asistanı / SSS | Serbest arama sonuçları ve mevzuat kaynak adayları | Semantik eşleşme bir hukukî kanıt değildir | Her iddiayı ayrı kaynak pasajına bağlama ve güncellik incelemesi |

## Kapsama denetimi

Gerçek `/evaluate` JSON yanıtını saklayıp çalıştır:

```powershell
python -m tarim_destek_rag.citations.claim_coverage --input evaluation.json --output evidence-claim-audit.json --strict
```

Bu sürüm her tekil passed/failed/missing kuralını sayar, kaynakta bulunmuş destek düzeyi pasajları ayrıca listeler ve claim-to-span bağımsız eşleşmeleri mevcut olmadığı için **HOLD** döner. Bilerek kısmi kanıtı tam başarıya dönüştürmez. Komuttaki `--strict`, herhangi bir eksik gerekçede başarısız çıkış (2) üretir.

## Kabul koşulları

- Her gerekçenin sabit **kural/check kimliği**, kaynak belgesi sürümü ve birebir ilgili hüküm aralığı ayrıca denetlenmiş olmalı; yalnız aynı destek programından bir pasaj bulunması yeterli değil.
- Özgün kaynak mevcut, SHA doğru, madde/fıkra/sayfa doğru ve işaret gerçek cümle/hücrede olmalı; tek bir yanlış pozitif dahi kabul edilmemeli.
- Her doğrulanmış atıf PC Neden?, indirilen rapor, mobil Neden? ve Mevzuat Asistanı arasında aynı kimliği korumalı; doğrulanmamış alıntı hiçbiri tarafından resmî pasaj olarak gösterilmemeli.
- Sentetik regresyon, arşivdeki gerçek kaynak entegrasyon testleri, CI ve ardından bağımsız hukukî/geçerli yıl kontrolü tamamlanmalı.
- **Gerçek kaynak indirme `ReadTimeout` ile başarısızsa yeşil kabul yazılmaz; test atlanarak veya sahte belgeyle geçilmez.** Ticari/üretim kabulü ve `main` merge işlemi HOLD kalır.

> Kaynak metinde bulunma, hukukî onay veya çiftçi hak edişi değildir.

## P0-10.7 — Kural/check kimliği, gerçek değişiklik metni ve yılı birbirinden ayırma

**Kaynak incelemesi:** SHA sabitli özgün `2025/42` Resmî Gazete HTML (74a911…9269) üzerinde `MADDE 2` metninin temel `2024/39 MADDE 4(3)` fıkrasının katsayı çarpımı formülünü değiştirdiği; `MADDE 15` metninin `EK-20`yi değiştirdiği; **GEÇİCİ MADDE 2**'nin 2025 üretim yılı başlatılmış işlemler için önceki hükümleri koruduğu ayrı ayrı gözlendi. 2026 EK-20'ye ilişkin değişiklik, kayıt zorunluluğunu düzenleyen `2024/39 MADDE 4(1)` için otomatik bir değişiklik ispatı değildir.

- `configs/p0_10_7_claim_source_matrix.json`: Özgün belge kimliği, SHA, değişiklik **MADDE**'si, hedef madde/fıkra, birebir pasaj ve kısıtlı üretim yılları. Kaynak kaydı onay değildir; imza ve içerik/yürürlük analizi ayrı.
- `citations/claim_source_matrix.py`: Kaynağın **özgün HTML bayt** SHA'sını, manifest kimliğini, DOM'da tam ve tekil pasajı ve doğru değişiklik maddesini kontrol eder. `MADDE 2`deki pasajı `MADDE 4(1)` olarak etiketlemek, farklı yıl veya farklı `rule_id` ile taşıma **HOLD**.
- İlk kontrollü örnek: `RULE_BASIC_SUPPORT_2026` / `BASIC_SUPPORT_2026` / 2026 / `passed_checks` metni “Çiftçi Kayıt Sistemi (ÇKS) kaydı aktif.” için `2024/39 MADDE 4(1)` **yalnız normatif kayıt şartının konum kanıtı**. Bu belge, gerçek çiftçinin ÇKS kaydının aktif olduğunu **ispatlamaz**; `fact_verified=false`, `claim_verified=false`, `acceptance=HOLD`. Veri eksik veya ifade farklıysa eşleşme üretilmez.
- `EK-20`: 2025/42 MADDE 15 değişiklik kaydı + bir sayfalık orijinal raster PDF + 12 satırlık görsel transkripsiyon teknik olarak ayrıştırılmıştır. Hücrelerin ikinci bağımsız doğrulaması, ürün/etmen uygunluğu ve hukukî geçerlilik olmadan hiçbir değeri `payable_amount` veya onaylı oran olarak kullanma.
- CLI `python -m tarim_destek_rag.citations.claim_coverage --input evaluation.json --output evidence-claim-audit.json --strict` çıktılarına kaynak adayları da eklenir. Gerçek her gerekçe için ayrı `claim_id` (kural+destek+alan+metin temelli), sabit yıl, aday span, olgusal doğrulama ve hukukî kontrol statüsü raporlanır. Eşleşme olsun olmasın genel kabul **HOLD**.

**Önemli sınır:** Bu kod hiçbir `VERIFIED` veya otomatik ödemeye geçiş yaratmaz. 2025/13, 10394, 11781 etkileri ve EK-20 içindeki her satır/hücre için bağımsız hukuki/görsel değerlendirme tamamlanmadan genel yayına izin verilmez.
