# P0-8C — Kaynak Cümlesine Bağlı Mevzuat Diff + İmzalı Yıl Sürümü

**Ürün amacı:** TarımDesteğimRAG 2029–2030 ve sonraki üretim yıllarında eski hükümleri silmeden gerçek kaynaklardan yeni mevzuatı bulsun, değişen maddeleri ve fiyatları kanıtlasın, onaylı sürümü güvenle yayımlasın. Bu bir **kademeli geliştirme**; tüm resmî yayımlara kapsama garantisi ve kişisel hak edişin kesinliği henüz sağlanmamıştır.

## İşlem zinciri

1. PR #21: resmî portal kaynak keşfi → orijinal SHA-256 bayt arşivi (DRAFT).
2. PR #23: PDF gerçek sayfa ve cümle bbox/quad koordinatları → sadece kaynak hash ile eşleşen alıntı (DRAFT).
3. **Bu PR:** `legal_diff.py`, `legal_diff_repository.py` → birebir doğrulanmış eski/yeni cümle kayıtları karşılaştırılır. `TEXT_ADDED`, `TEXT_CHANGED`, `TEXT_REMOVED`, `TEXT_UNCHANGED` ve TL anmalarının öncesi/sonrası çıkarılır.
4. Yalnız bir metnin silinmesi **mülga hüküm** ispatı değildir. “Yürürlükten kaldırılmıştır” ifadesi bulunsa bile değişiklik tebliğinin bağlantısı/yürürlük tarihi hukuk uzmanı tarafından onaylanıncaya kadar `repeal_effect_confirmed=false` kalır.
5. `legal_diff_report.json`, JSON içerik SHA-256 özeti, sayfa/alıntı/kaynak belge SHA/kanıt ID'si ile incelenebilir. Ana index taramasının eksiksizliği teknik olarak henüz ispatlanmadığı için `complete_legal_search_proven=false`.
6. `legal_release_snapshots`: 2030 üretim yılı manifesti; kaynak sürüm SHA listesi, rate/candidate kimliği ve digestleri, orijinal PDF cümlesi, koşul DSL'si, coğrafi kapsam ve hukukî coverage kontrolü.
7. Mevcut P0-5 ve P0-7 şemasına `RELEASE` türü eklenmiştir. `LegalReleaseModel` manifesti hem `REVIEWER` hem `APPROVER` tarafından ayrı, bağımsız, haricî Ed25519 anahtarla imzalanır. Üretimde S3 Object Lock COMPLIANCE sürüm makbuzları her iki imza için ayrıca canlı olarak geri doğrulanır.
8. `resolve_active_release` yalnız bir (1) geçerli sürümü seçer. Birden fazla çakışan/geçersiz imza, belirsiz dönem, eksik hukukî coverage, geri alınan belge, değişmiş kaynak PDF, değiştirilmiş katsayı/koşul/digest, iptal veya haricî WORM kesintisi → `HOLD`.
9. `evaluate_release` imzalı sürüm bulsa bile **gerçek ÇKS/parsel yetkili verisi olmadan** yalnız `REVIEW` ve `estimated_amount=None` döner. Hesaplanan `simulated_amount` hak ediş değildir.

## Kaynaklı diff nasıl kullanılır?

Önce iki dönemin gerçek orijinal PDF cümleleri `sentence_bounding_boxes` kaydına SHA-256 ve sayfa eşleşmesiyle alınır. Ardından kayıt ID'leriyle:

```powershell
python scripts/build_legal_diff_report.py `
  --previous-year 2029 --target-year 2030 `
  --previous-evidence 11 12 `
  --current-evidence 21 22 `
  --output data/legal_diff_report.json
```

Buradaki 11/12/21/22 numaraları **örnek ID**'lerdir; gerçek 2030 mevzuatına dair kanıt değillerdir. Yalnız açıkça eşlenmiş madde/fıkra kimliği karşılaştırılır. Modül değişiklik metnini doğru sayfa üzerinde tutar; henüz Resmî Gazete'deki tüm değişiklikleri kendisi keşfetmez.

Yönetici API: `POST /admin/legal-updates/diff` JSON gövdesi: `previous_year`, `target_year`, `previous_sentence_ids`, `current_sentence_ids`. Mevcut admin anahtarı gereklidir; açık internet için ek IdP/oturum/CSRF gerekir.

## Yeni yıl için güvenli release

`release.py` içindeki `stage_release(session, manifest, source_version_id, effective_from)` yalnız **DRAFT** oluşturur. Veri sahibi incelemesi ayrı; imzalar her zaman bağımsız görevli/KMS tarafından üretilir. `legal_approval_cli --kind RELEASE` ile iki ayrı dış imza ithal edilip gerçek WORM kanıtıyla bağlanabilir. Bu paket, **gerçek kurumsal imzaları üretmez** ve `TARIM_RAG_LEGAL_ACTIVATION_ENABLED` bayrağını açmaz.

Önemli koşullar:
- Tüm rate bileşenleri kendi başına ayrı iki imzalı `VerifiedSupportRateModel` olmalıdır.
- Her rate, manifestteki program, ürün, yıl, il/ilçe ve onaylı dönem ile birebir uyuşmalıdır.
- Taslak `dynamic_rate_candidate` sadece imzalı digest içinde ve birebir aynı Decimal tutar/koşul bilgisiyle kullanılabilir.
- PDF delil dosyası, kayıtlı resmî kaynak URL'si ve kaynak sürüm SHA'sı hem arşivde hem veritabanında aynı olmalıdır.
- Alan, coğrafya, istisnalar, uygulama takvimi, gold-test, rate ve kaynak kapsama incelemelerinin **tamamı** kanonik manifestte hukukî signoff ile ilişkilendirilmelidir. Bu beyanlar tek başına resmî ispat değildir.
- Art arda yılların sürümleri birbirinden farklıdır; 2030 kaydı 2029'u değiştiremez.
- Art arda yayımlanan **aynı yıl** için iki geçerli release varsa otomatik öncelik seçilmez → HOLD; önce önceki release güvenle iptal edilmeli.

Read-only durum API'si: `GET /api/v1/legal-releases/2030?as_of=2030-04-01` (gerçek onay yoksa HOLD). Kişisel hak ediş vermez.

PostgreSQL migrasyonu: `deployment/sql/p0_8c_legal_release_schema.sql`. Mevcut iki kurum rolüne salt **SELECT**; manifestler için INSERT/UPDATE/DELETE/TRUNCATE verilmez. Review/VERIFIED yükseltmesi yalnız ayrı yetkili veri sahibi operasyonudur; sadece alan değiştirmek imza sayılmaz.

## Testler ve gerçek tamamlanma şartları

- `test_p0_8c_legal_diff.py`: 2029/2030 sentetik TL değişimi, explicit repeal text algılama, ancak yürürlük sonucunu kesinleştirmeme, kaynak yılı/çift anahtar/eksik kapsam ret.
- `test_p0_8c_signed_release.py`: 2030 sentetik PDF ile ayrı rate+release imzaları, kaybolan kaynak, manifest/draft fiyat değişmesi, eksik coverage, switch kapalı, yanlış üretim yılı ve ödeme yapılmaması.
- CI: `P0-8C Yearly Legal Diff and Signed Release Safety` ile tam karar/API/Gradio regresyonu.

**Kalan ürün hedefleri:** 2030 Resmî Gazete/BÜGEM/DSİ/Mevzuat Bilgi Sistemi eksiksiz keşif + yürürlükteki konsolide mevzuat rekonstrüksiyonu, tablo/OCR doğrulama, gerçek ÇKS/parsel/başvuru kanıtlarının yetkili kaynaklardan alınması, gold-set hukuk uzmanı sonuç karşılaştırması, atomik immutable release/rollback, her destek kartına PDF kanıt butonu ve Flutter PDF.js deneyimi. Gerçek iki resmî görevli, kurum onayı, Vault/HSM ve WORM [Issue #20](https://github.com/seydivakkas/TarimDestegimRAG/issues/20) sebebiyle hâlâ kurulmadı.

**Lisans:** Projede özel lisans / tüm haklar saklıdır. PyMuPDF kullanılıyorsa AGPL ve ticari lisans uyumluluğu dağıtımdan önce ayrıca değerlendirilmelidir. Bu PR eski mevzuat ya da para değerlerini tahmin ederek değiştirmez.
