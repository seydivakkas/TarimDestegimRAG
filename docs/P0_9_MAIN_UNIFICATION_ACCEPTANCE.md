# P0-9 — Güncel Main Üzerinde P0-6–P0-8C Tam Entegrasyon Kabul Kapısı

**Başlangıç:** 9 Ekim 2026. Hedef: yeni özellik geliştirmeden önce güncel `main` üzerindeki karar, veri, arayüz ve mevzuat modüllerinin birlikte çalışmasını ispatlamak.

## Kök neden ve dal ilişkileri

PR #13, #14, #16, #18, #19, #21, #23, #24 GitHub üzerinde *merged* görünse de çoğu bir önceki **feature dalına**, **main'e değil** birleştirilmişti. PR #8 ise main'e gerçek merge edildi. Farklılaşma: main vs P0-8C `127 ahead / 93 behind`, iki tarafta ortak atadan itibaren aynı anda değişmiş 12 dosya. Bu nedenle "tüm PR'lar merged" ifadesi **main üzerinde fonksiyonel entegrasyon kanıtı değildir**.

P0-9 `integration/p0-9-main-unification` dalı güncel main commit'i `2b856485e8416d827fc33746e0a94d1003625cea` üstünde oluşturuldu; resmî mevzuatın fiyatları veya çiftçinin hak edişi üretimde değiştirilmedi.

## Uygulama özeti

1. İki tarafta çakışmayan P0-6–P0-8C **50 dosya** Git ağacı/blob SHA'ları kullanılarak main üzerine alındı. Main'e ait P0-8'dan daha yeni kodlar silinmedi.
2. `database/models.py`: mevcut `ReviewedWaterRestrictionDistrictModel`, moderasyon denetim kayıtları ve P0 veri modelleri korunarak `ReviewedWaterRestrictionScopeModel`, `LegalAuditReceiptModel`, `LegalReleaseModel`, `SourceDocumentModel`, `SentenceBoundingBoxModel`, `DynamicRateModel` eklendi.
3. `legal_approvals.py`: main'deki WATER per-district imza semantiği ve yeni ulusal WATER/RELEASE imza yükleri bir arada. Eksik `TARIM_RAG_LEGAL_ACTIVATION_ENABLED=true`, doğru security profile, 2 farklı görevli, doğrulanmış resmî kaynak ve üretim S3 COMPLIANCE WORM → **ret / REVIEW / None**.
4. `database/repository.py` ve `rules_impl.py`: 2026 su kısıtı değerlendirmesinde 2025/42 ile değiştirilmiş 52 ilçelik tam, kaynak hash'li, iki imzalı ulusal liste gerekir; eski ilçe seed/çift imzalı fakat eksik kapsamlı kayıt tek başına olumlu/olumsuz karar veremez. Bu, ilk main davranışına göre bilinçli bir fail-closed güvenlik sıkılaştırmasıdır.
5. `api/main.py`: main'deki SSS/moderasyon ve /evaluate API'leri korunurken `/admin/legal-updates/scan`, `/admin/legal-updates/diff`, `/api/v1/grounding/evidence/{id}`, `/api/v1/grounding/image/{id}/page/{page}`, `/api/v1/legal-releases/{year}` eklendi.
6. **Gradio 5 ana sekme** korunur: P0-8A/B kanıt ekranları eski 74kB monolitik arayüz kopyalanmadan mevcut `frontend_pc/pages/admin_validation.py` modülünde yer alır. Resmî tarama tuşu varsayılan kapalıdır; anahtar yalnız sunucu tarafında bulunur.
7. Yeni tam entegrasyon test dosyası: `backend/tests/integration/test_p0_9_main_integration.py`. Kod yollarını yalnız unit değil, aynı API/Gradio/TestClient oturumunda kontrol eder.
8. Yeni `p0-9-integration-acceptance.yml` CI: `.[dev,pdf-evidence]` kurulum, `compileall`, `ruff`, **bütün `backend/tests`**. Eski `p0-validation.yml` ve `ci.yml` test bağımlılıkları isteğe bağlı PyMuPDF/Pillow dahil edilerek hizalandı. Geçici bot yazma workflow'u güvenli import düzeltmesinden sonra silindi.

## Yapılması ve raporlanması zorunlu kabul ölçütleri

| Kapı | Kabul ölçütü |
|---|---|
| **Uygulama / kaynak** | P0-2/4/5/6/7/8A/B/C importları ve main FAQ/ÇKS/Gradio kodları tek HEAD'de birlikte |
| **Derleme ve bağımlılık** | Python 3.12 + eksiksiz dev/pdf-evidence kurulumu ile compileall ve import |
| **Ruff** | `ruff check backend/src backend/tests` → 0 hata, lint kuralı gevşetilmez |
| **Tam regresyon** | `pytest backend/tests -q --no-cov` → 0 fail, 0 collection error |
| **2026 belge ve oran** | Ulusal 52 ilçe ve Resmî Gazete PINNED SHA, tarihsel DRAFT oran asla payable olmaz |
| **2030 fail-closed** | İmzasız/eksik kaynakta `HOLD`, kaynak değişirse imza/kural geçersiz; metadata veya sahte alıntı ödeme izni değil |
| **UI** | 5 ana görev, eski ortak evaluation state, admin yıl taraması varsayılan kapalı, gerçek PDF vurgusu |
| **Operasyon** | Orijinal PDF/S3 WORM, 2 gerçek hukuk görevlisi ve kontrol dışı SQL değişikliği engellenmeden **production activation HOLD** |
| **GitHub** | Draft PR #28 main'e hedeflenir, yetkisiz merge yapılmaz; bütün required checks ve kod inceleme onayı olmadan merge yok |

## Çalıştırma

```bash
git fetch origin
git switch integration/p0-9-main-unification
python -m pip install -e ".[dev,pdf-evidence]"
python -m compileall -q backend/src frontend_pc scripts
ruff check backend/src backend/tests
python -m pytest backend/tests -q --no-cov
```

Gerçek üretim PostgreSQL veritabanı şemasının güncelleştirilmesi bu PR ile otomatik yapılmaz. `deployment/sql/p0_7_create_legal_audit_receipts.sql`, `p0_8b_create_grounding_and_dynamic_drafts.sql`, `p0_8c_legal_release_schema.sql` gibi migration'lar DBA onayı, çevrimdışı kontrol ve gerçek rol izni doğrulaması gerektirir.

**Açık işler:** [P0-9 Issue #27](https://github.com/seydivakkas/TarimDestegimRAG/issues/27), [2030+ ürün hedefi Issue #22](https://github.com/seydivakkas/TarimDestegimRAG/issues/22), [canlı kimlik/KMS/HSM/WORM aktivasyon Issue #20](https://github.com/seydivakkas/TarimDestegimRAG/issues/20). Gerçek kurum mevzuat yayını, tüm değişiklik tarihleri ve ÇKS kanıtları halen ayrı kabul şartıdır.

**Mevcut üretim kararı:** `FABRICATION/PRODUCTION ACTIVATION: HOLD`, `farmer entitlement: REVIEW/null`.
