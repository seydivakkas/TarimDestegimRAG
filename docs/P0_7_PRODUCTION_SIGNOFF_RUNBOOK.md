# P0-7 — Üretim Yetkilendirme, Haricî Ed25519 İmzalama ve S3 WORM Denetimi

**Durum (8 Ekim 2026):** Uygulanabilir altyapı kodu, görevli kimliği doğrulama protokolü, ayrı PostgreSQL rolleri ve güvenlik testleri hazırlanmıştır. **GERÇEK ÜRETİM KURULUMU, KURUMSAL KİMLİK ATAMASI, KMS ANAHTARI VE S3 DEPOSU OLUŞTURULMAMIŞTIR.** PR, P0-6 üstüne **taslak** durumdadır. 2026 hukukî kaynak kayıtları hâlâ `DRAFT` ve hesaplama kilitlidir.

## 1. Güven sınırları

```
Kurum IdP (OIDC JWT, sabit JWKS, iss/aud/sub, kısa TTL, yeni MFA auth_time+acr)
  ↓
Değiştirilemez kurumsal görevli sicili: OIDC sub → REVIEWER/APPROVER → principal → Vault key
  ↓ [Operatör, kayıt + her iki mevzuat hash'inin kanonik SHA-256 değerini teyit eder]
HashiCorp Vault Transit (ed25519, her görevli farklı ACL, özel anahtar Vault dışına çıkmaz)
  ↓ [vault:vN:signature; yerel doğrulama bağımsız sabitlenmiş açık anahtarla]
Ayrı salt-okunur PostgreSQL oturumu / özel onay yazıcısı
  ↓
İki farklı principal'ın REVIEWER + APPROVER imzası, aynı immutable kayıt özeti
  ↓
AWS S3 Object Lock: COMPLIANCE, VersionId, >= 365 gün, SHA-256 ve bayt geri okuması
  ↓
PostgreSQL append-only olay/makbuz satırları + commit
  ↓
Her karar anında iki imza + kaynak + active + haricî COMPLIANCE makbuz yeniden doğrulama
  ↓
TARIM_RAG_LEGAL_ACTIVATION_ENABLED=true + TARIM_RAG_LEGAL_SECURITY_PROFILE=production
  ↓
2026 uygunluk/hak ediş (diğer kural koşulları da doğrulanmışsa)
```

**HashiCorp Vault Transit Ed25519** anahtar türünü ve `POST /v1/transit/sign/:name` uç noktasını destekler. <https://developer.hashicorp.com/vault/api-docs/secret/transit>. Bu anahtarın *kurumun onayladığı gerçek HSM güvence seviyesinde* olduğunun teyidi ayrıca zorunludur: yazılımsal Vault Transit key kullanılması kendiliğinden fiziksel HSM güvencesi değildir. FIPS 140-3 gerekliliği olan konuşlandırmalarda Vault'un Ed25519 FIPS sertifikasyon kapsamı kontrol edilmelidir; algoritma/protokol seçiminden önce kurumun güvenlik sorumlusu onayı gerekir.

**Amazon S3 Object Lock COMPLIANCE**, sürümlenmiş nesne sürümünün koruma dönemi içinde root dahil kullanıcılarca silinmesini/üzerine yazılmasını kısıtlar: <https://docs.aws.amazon.com/AmazonS3/latest/userguide/object-lock.html>. Bu politika **gerçekten yapılandırılıp denetlenmedikçe** kodun audit makbuzu `VERIFIED` sayılmaz.

## 2. Güvenilen ortam anahtarları (yalnız örnek alan isimleri)

| Gizli/config adı | Sahibi ve zorunluluk |
|---|---|
| `TARIM_RAG_LEGAL_IDP_TRUST_JSON` | Güvenlik yöneticisi: https issuer, aud, imzalı RS256 JWKS, `required_mfa_acr` |
| `TARIM_RAG_LEGAL_OFFICERS_JSON` | İkinci bağımsız yetkili: IdP kalıcı `sub` → rol / görevli kimliği / anahtar adı |
| `TARIM_RAG_LEGAL_TRUSTED_KEYS_JSON` | Kurum dışı değil, güvenlik ekibi: görevli → rol + 32 byte Ed25519 açık anahtar |
| `TARIM_RAG_VAULT_ADDR` | Kurumsal TLS doğrulanmış Vault HTTPS adresi, **koda gömülü değil** |
| `TARIM_RAG_LEGAL_DB_READER_URL` / `_ROLE` | Hukuk görevlisi ve onay inceleyicisi için *salt okunur* PostgreSQL login |
| `TARIM_RAG_LEGAL_DB_WRITER_URL` / `_ROLE` | Ayrı kontrollü aktarım işi için yazıcı PostgreSQL login |
| `TARIM_RAG_WORM_BUCKET` | Kurumun erişim politikaları ayrı tutulmuş S3 Object Lock bucket |
| `TARIM_RAG_WORM_RETENTION_DAYS` | Hukukî saklama süresi kurumca belirlenecek; kod >= 365 gün gerektirir |
| `TARIM_RAG_LEGAL_SECURITY_PROFILE` | Üretimde **production**. `isolated_test` sadece pytest sürecinde, kalıcı hizmette geçersiz |
| `TARIM_RAG_LEGAL_ACTIVATION_ENABLED` | Varsayılan KAPALI; tüm bağımsız kabuller tamamlandıktan sonra yalnız `true` |

Bu isimler **kimlik bilgilerinin kendisi değildir**. Hiçbir JWT, DB parolası, Vault token'ı, kişisel kimlik veya özel anahtar repoya koyulmamalıdır. Güvenilen JWKS, rol sicili ve açık anahtar config'i **ayrı güvenlik yönetici ekibi** tarafından sürümlenip denetlenmeli; görevliler bunları değiştirememelidir.

OIDC doğrulayıcı `PyJWT` ile yalnız pinlenmiş **RS256** imzasına izin verir; `none`, JWT `jku` üzerinden sahte JWKS, yanlış issuer/audience, süresi geçmiş token, 5 dakikadan eski ID token, 15 dakikadan eski MFA `auth_time`, kabul edilmeyen `acr` ve rol taklidi reddedilir. İleride OIDC sertifika rotasyonu, revocation/oturum sonlandırma ve MFA kapsamları kurum kurallarına bağlanmalıdır.

## 3. İki farklı görevlinin onay protokolü

1. Bir uzman resmî 2024/39, 2025/42, 11781 ve 2026 havza belgelerini doğrular. DRAFT kaydın içeriği ve hukukî kaynağı denetlenir. Kurumsal veri sahibi, aday kaydı **kontrollü ayrı süreçte** `VERIFIED` hâline getirebilir; bu bit alanı **henüz imzalı aktivasyon değildir**.
2. Görevli `legal_approval_cli inspect --kind WATER --id <ID>` ile **kanonik kayıt JSON** ve `subject_digest` alır. Belge hash'lerini ve coğrafî listeyi bağımsızca inceler.
3. Görevli, IdP üzerinden kısa süreli MFA'lı OIDC ID token ve **yalnız kendi Transit key'ine izinli** ayrı Vault token edinir. Gerçek operatör CLI bu tokenları **chmod 600 geçici dosyalardan** okur, argv/env değeri olarak taşımaz.
4. `legal_officer_cli --kind WATER --id <ID> --role REVIEWER --oidc-token-file /secure/id.jwt --vault-token-file /secure/vault.token --ack-subject-sha256 <DIGEST> --out-file /secure/reviewer.json --sign` çağrılır. Salt okunur DB rolü kullanır ve Transit'den gelen imzayı sabitlenmiş açık anahtarla tekrar doğrular. İmzalı zarfta token ve özel anahtar **yoktur**.
5. **Farklı kişi**, **ayrı Vault Transit anahtarı ve IdP `sub`**, aynı içerik özetine APPROVER imzası oluşturur. İki zarf tek `kind,id,attestations[]` JSON paketinde birleştirilir.
6. Kurumsal aktarım görevlisi, salt ekleme DB rolüyle `legal_approval_cli apply-attestations --kind WATER --id <ID> --bundle /secure/two-officer-bundle.json` komutuyla **dry-run** yapar; `--commit` ayrı izin gerektirir. Üretimde her imza için ayrı S3 **COMPLIANCE** nesne sürümü yazılıp geri okunmadan DB commit yapılmaz.
7. Canlı karar motoru iki imzayı, resmî kaynakları, makbuzların **tam JSON baytlarını**, SHA-256'larını, ObjectLockMode/retention bilgisini ve kayıt durumunu **her sorguda** doğrular. Dış depo erişilemezse sonuç `REVIEW`, ödeme tutarı **null** kalır.
8. İptalde APPROVER haricî imzalı iptal zarfı kullanılır; yeni **REVOCATION** WORM nesne sürümü arşivlenir; DB'ye kalıcı iptal kaydı eklenir. Aynı subject id yeniden açılmaz.

**Açık tehdit:** Uygulama, OIDC doğrulama ile Vault token yetkisini matematiksel olarak tek bir bileşik protokolle birbirine bağlamaz. Gerçek Vault ACL'leri kimliklere **yalnız kendi Transit anahtarını** tanımlayacak şekilde konfigüre edilmeli, kişisel tokenlar tekrar kullanılmamalı ve Vault audit logları kurumsal WORM'a ayrı aktarılmalıdır. Sadece bir Vault yönetici token'ına sahip olmak, kimlik-doğrulama garanti sınırını bozabilir. IdP ve Vault gerçek bağlantısı burada henüz yapılmadı.

## 4. PostgreSQL rol izolasyonu

`deployment/sql/p0_7_legal_role_grants.sql` şablonu, gerçek yetkili DBA tarafından tablolar oluşturulduktan sonra işletilir.

- **legal_reader**: sadece kaynak kayıtları ve approval/audit satırlarını okur. İmzalama CLI bu rolü kullanır.
- **legal_writer**: kaynaklara salt okuma; yalnız `legal_approval_attestations`, `legal_approval_revocations` ve `legal_audit_receipts` tablolarına INSERT izni. UPDATE/DELETE/TRUNCATE verilmez.
- **public API**: ne hukuk yazıcısı DB kimliği ne de Vault/HSM token'ı alır.
- **DB owner/superuser/migrator**: rutin runtime dışında kalır ve ayrı hesabın kontrolündedir.

`legal_runtime.py` her işte **psycopg PostgreSQL, TLS verify-full ve gerçek `current_user`** kontrolünü zorunlu kılar. Bu SQL, *mevcut başka login rollerinin önceden aldığı* özel izinleri otomatik silmez; DBA'nın GRANT envanteri ve GRANT/revoke denetimi ayrıca zorunludur. Role testleri gerçek geçici PostgreSQL CI servisi üzerinde çalışır; CI DB TLS kullanmaz ve gerçek dağıtım onayı yerine geçmez.

## 5. Haricî WORM hizmeti

`legal_audit.py` ayrı audit makbuzu tablosu kullanır:

`legal_audit_receipts(subject_type,subject_id,event_role,bucket,key,version,payload_sha256,retain_until)`.

Her imza/iptal olayı için ayrı benzersiz nesne anahtarı ve S3 Object Lock **COMPLIANCE** retention talebi kullanılır. S3 `VersionId` ve kaydedilen nesne versiyonu üzerinden getirilen JSON **gerçek baytlar ve saklama kilidiyle** tekrar doğrulanır. Nesne yazıldıktan sonra DB transaction rollback olursa arşivde yetim bir WORM nesne kalabilir; **bu güvenlik ihlali değil**, işletme ve masraf kayıtlarıyla takip edilecek bir olaydır.

**S3 politikası:** bucket için Versioning=Enabled ve ObjectLock=Enabled, varsayılan COMPLIANCE retention, ayrı IAM writer/reader, `s3:BypassGovernanceRetention` YASAK, encryption ve erişim/audit günlükleri açık. Saklama süresi resmî hukukî veri saklama yükümlülüğüne göre kararlaştırılır. Uygulamanın tek başına `put_object(ObjectLockMode='COMPLIANCE')` çağrısı, gerçek AWS hesabının Object Lock güvence seviyesinin başarıyla kurulduğuna dair yeterli kanıt değildir.

## 6. Üretime geçiş engelleri

- İki **gerçek** bağımsız resmî hukuk görevlisinin IdP'ye atanması, MFA ve rol ayrımı.
- Vault sunucu ve Transit anahtarlarının gerçek kurulum/onay ve ayrık ACL'leri, varsa kurumun **HSM** güvence gereksiniminin ayrı doğrulanması.
- Üretim PostgreSQL loginleri, bağlantı TLS CA sertifikası, rol denetimi ve şema migration'ının kurum DBA'sınca uygulanması.
- Gerçek S3 hesabında Object Lock COMPLIANCE, IAM/bucket policy, retention ve bağımsız AWS API üzerinden koruma testi.
- Kişisel/özel veri taşımayan fakat mevzuat kimliklerini doğrulayan haricî denetim arşivi, kurumun GDPR/KVKK saklama prosedürü.
- Dağıtım öncesi `REVIEW → VERIFIED → çift imza → WORM → activation → revocation → REVIEW` uçtan uca canary; kaynak değişimi, IdP/KMS/S3 kesintisi, eski mevzuat ve rollout geri alma.
- Hukukî metinlerin bağımsız inceleme kaydı ve gerçek 2026 uygulama/parsel verisiyle gold-test doğrulaması.

**Yalnız kod, geçici RSA/Ed25519 test anahtarları ve emüle edilmiş S3 ile yapılan CI hiçbir biçimde yukarıdaki canlı kabulü yerine getirmez. Gerçek ödemeler kapalıdır.**


## 7. Hazır üretim belgeleri, kaynak ayırma ve son ön kontrol

- `deployment/sql/p0_7_create_legal_audit_receipts.sql`: üretim için yeni denetim makbuzlarının **ayrı DBA imzalı DDL migrasyonu** (önceki PR #12–18 tabloları önceden kurulmuş olmalıdır).
- `deployment/sql/p0_7_legal_role_grants.sql`: DBA'nın kontrollü GRANT/REVOKE şablonu. Rutin `init_db()` üretimde kullanılmaz.
- `deployment/vault/p0_7_reviewer_transit_policy.hcl` ve `p0_7_approver_transit_policy.hcl`: ayrı Transit imza key'lerine ayrık UPDATE izni; private key export/config/key rotation yoktur. **Gerçek anahtarlar ve OIDC entity-policy ataması hâlâ kurum tarafından yapılmalıdır.**
- `python -m tarim_destek_rag.database.legal_preflight`: **salt okunur canlı uygunluk kontrolü**. Payout switch kapalı değilse veya IdP/MFA/görevli sicili, iki ayrı DB rolü, S3 Versioning/Object Lock COMPLIANCE, PublicAccessBlock ya da bucket `aws:kms` şifreleme kontrollerinden biri başarısızsa hemen hata verir. Bu komut hiçbir altyapı oluşturmadan mevcut kurumsal hesabı denetler.
- `legal_runtime.legal_session`, `isolated_test` dışında **üretim profilini ve PostgreSQL'i zorunlu kılar**. `legal_approval_cli inspect` dahi üretimde otomatik SQLite şema oluşturamaz.
- Gerçek AWS bucket için önce kontrollü `PutObject(COMPLIANCE)` + `GetObject(VersionId)` testi, retention son tarihini doğrulayan gerçek bir **canary**, Vault iki görevli ayrı token sign testi ve PostgreSQL gerçek oturum rollback/commit + revocation testleri uygulanmalıdır. Mevcut CI **yalnız protokol ve PostgreSQL izinlerini** test eder; gerçek cloud hizmeti canlı denenmemiştir.

**Uyarı:** Bir Vault Transit Ed25519 yazılım anahtarı kurmak, otomatik olarak *kurumsal HSM sertifikalı anahtar* sağlamak anlamına gelmez. Gerçek fiziksel HSM/FIPS zorunluluğu varsa kurum, anahtar destek durumunu doğrulayıp gerekirse farklı algoritma ve verifier tasarımını ayrı değişiklikle değerlendirmelidir.

**Üretim kabul kararı:** Her adımın ayrı sorumlusu, onay tutanağı, kaynak hash'i, gerçek KMS/HSM kimliği, DB rol testleri, WORM canary kanıtı ve rollback protokolü tamamlanmadan bu PR **DRAFT** kalmalıdır.
