# G35–G37 — Merkezi Kanıt Motoru, Sabit check_id ve 2026 ÇKS Pilotu

## Tek mimari kural

**Yalnız backend, tek bir CentralEvidenceEngine üzerinden normatif bir kanıt kaydı üretir.** Masaüstü (Neden?), SSS, rapor ve mobil o kaydı kullanır. Arayüzler kendi başlarına OCR metnini resmî hüküm ilan edemez; URL, piksel koordinatı veya mevzuat yılını tahmin edemez. İç kaynak doğrulayıcılar (orijinal HTML, PDF, SHA, EK-20 imzaları) merkeze bağlanabilir, fakat karar sonuca tek noktadan çıkar.

İşlevsel zincir:

```text
RuleCheckEvent(check_id, field, display_text)
  → check_identity.extracted_checks
  → CentralEvidenceEngine.for_check / for_claim / for_evaluation
  → canonical_evidence_contract (SHA, URL, madde, gerçek sayfa/HTML pasajı)
  → {check_id, claim_id, evidence_id, production_year, source, statuses}
  → PC Neden? / SSS / rapor / /api/v1/evidence/evaluation / Flutter
```

## Sabit kimlik kuralları

- `check_id` kural kodunda tanımlanan semantik kontrol kimliğidir; üretilen cümleye, ürüne, alana, olgusal koşulun geçip geçmemesine veya OCR sonucuna bağlı değildir.
- `claim_id = SHA256(["TRAG_CHECK_V2", rule_id, support_id, check_id])[:24]`. Aynı kuralın olumlu/olumsuz/eksik çıktıları tek bir claim_id taşır.
- `evidence_id` aynı claim_id'nin ilgili `production_year` ve özgün `source_sha256`/span veya PDF sayfasına bağlanmış ayrı kaydıdır; üretim yılı değişirse kanıt kimliği aynı tutulmaz.
- `field` yalnız sonucun `passed_checks/failed_checks/missing_fields` durumudur. `display_text` yalnız kullanıcıya gösterilen cümledir; ikisi kimliği belirlemez.
- Eski kural çıktısında `check_events` yoksa görüntüleme kaybolmaz; buna rağmen field+ordinal geçici anahtar `LEGACY_NO_SEMANTIC_CHECK_ID_HOLD` taşır. Bu eski geçici kimlikler normatif kaynak kabul kapısını geçemez ve bütün kurallara check_id eklenene kadar G36 açık kalır.

## İlk gerçek pilot: 2026 Temel Destek / ÇKS kayıt şartı

| Aşama | Sabit değer / durum |
|---|---|
| Kural kimliği | `RULE_BASIC_SUPPORT_2026` |
| Destek kimliği | `BASIC_SUPPORT_2026` |
| Sabit kontrol | `BASIC_CKS_REGISTRATION` |
| ÇKS aktif | `passed_checks` ve değişken gösterim metni; aynı check_id |
| ÇKS pasif | `failed_checks` ve değişken gösterim metni; aynı check_id |
| ÇKS bilgisi eksik | `missing_fields`, aynı check_id |
| Kuratör kaynak kaydı | `BASE_2024_39_ART4_P1` / Resmî Gazete 2024/39 MADDE 4(1) |
| Özgün belge SHA | `efb1ebea650cf836155728b6bd3599b76a0fbee70d1a8e5c85f2af4792734530` (manifestte kayıtlı, bu tur fiilen indirilip incelenmedi) |
| Kaynak türü | HTML asıl hüküm; arşivde gerçek dosya doğrulanmazsa `HOLD` |
| Üretim yılı yürürlük/istisna zinciri | 2025/13, 2025/42, 11781 kapsamı doğrulanmadan `HOLD` |
| Çiftçinin gerçek uygunluğu | Bağımsız denetlenmedi, `HOLD` |
| Ödeme | `HOLD` |

### PC'de kullanım

2026 parselini hesapla → Destek Analizi → Neden? → **Pilot — 2026 Temel Destek / ÇKS** → *2026 ÇKS kanıt zincirini kontrol et*. ÇKS kayıt durumu değişse de aynı `check_id` görünür. Özgün Resmî Gazete HTML dosyası yerel SHA envanterinde gerçekten bulunuyorsa ilgili maddenin birebir metni turuncu işaretli görünür; kaynağa ulaşılamıyorsa `HOLD`. Turuncu kaynak metni, hükmün ilgili yıl geçerliliğini kanıtlamaz.

### Tekil merkezi API

- `POST /api/v1/evidence/evaluation` — mevcut değerlendirmedeki bütün sabit/geçici kontrol kayıtlarını, çiftçi kimlik bilgisi döndürmeden verir.
- `POST /api/v1/evidence/check/RULE_BASIC_SUPPORT_2026/BASIC_CKS_REGISTRATION` — mevcut değerlendirmeyi yeniden hesaplayıp yalnız söz konusu sabit check_id için tek merkez kaydını döndürür. İstek gövdesi mevcut değerlendirme isteğidir.
- Mobil: `CanonicalClaimEvidence.checkId`, `identityStatus`, `claimId`, `evidenceId`, `source`, `sourceLocationStatus` ve ayrı `temporalLegalStatus/paymentStatus` alanlarını okur; hukuken PASS üretmez.
- PC Neden, SSS ve rapor `CentralEvidenceEngine` üzerinden aynı kaydı okur. RAG arama adayları hukuki kaynak kaydına terfi ettirilmez.

## Sarı / turuncu ayrımı

**Turuncu:** SHA ile bulunan gerçek, birebir kaynağın inceleme adayı; HTML paragrafı veya native PDF metin konumu. **Sarı:** yalnız gerekli bağımsız görsel inceleme imzaları doğrulanmış birebir bölge; bu da yürürlük, ödeme veya hak ediş izni değildir. Pilot HTML pasajı için imzasız sarı kullanılmaz.

## Kapanış ölçütleri

- G35: bütün PC/mobil/SSS/rapor ekranlarının kaynakla ilgili durumlarını sadece merkezi servis API sözleşmesinden edinmesi; eski ayrı doğrulama yollarının kontrollü kaldırılması.
- G36: bütün mevcut ve yeni kuralların her semantik şart için doğrudan `check_events` üretmesi; legacy geçici kimlik kalmaması ve kimlik tekrarlarının fail-closed olması.
- G37: 2026 ÇKS şartı kaynak HTML'de birebir doğrulanmış, değişiklik ve yürürlük zinciri bağımsız incelenmiş, PC–mobil–SSS–rapor aynı check_id/evidence_id durumunu göstermiş olmalı. Henüz gerçek kaynak arşivi ve bağımsız inceleme tamamlanmadığından bu pilot **tamamlandı denemez**.
- G33: bütün destek gerekçeleri doğrudan gerçek kaynak konumuna gidene ve eksik kalanlar açıkça HOLD raporlanana kadar açık.

Özellik geliştirme ve arayüz bütünleşmesi bitince F14'te toplu test, Windows/Flutter gerçek kabul ve bağımsız hukukî doğrulama yapılır. PR #41 DRAFT, main değiştirilmez.