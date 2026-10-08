# P0-5 — Haricî İmzalı Çift Onay, İptal ve Denetim Sınırı

**8 Ekim 2026 | PR #16 (DRAFT) | Üretim aktivasyonu KAPALI**

## Geliştirilen karar güvenliği

P0-2 ve P0-4 kapsamında `review_status="VERIFIED"`, `approved_by`, `reviewed_by` gibi alanların dolu olması tek başına hukuki onay **kanıtı değildi**. Artık `SupportRepository.get_amount` ve `BasinRepository.evaluate_official_crop`, onaylı görünen kaydı kullanmadan önce `two_person_approved` çalıştırır.

- **REVIEWER** ve **APPROVER**, birbirinden farklı `principal_id` değerlerine ve haricî Ed25519 açık anahtarlarına sahip olmalıdır.
- `TARIM_RAG_LEGAL_TRUSTED_KEYS_JSON` **deploy secrets/anahtar yönetiminde** sağlanır; üretim özel anahtarları repoya veya veritabanına konulmaz.
- Her imza, kanonik SHA-256 kaydına bağlıdır: program/ürün/yıl/yer/tutar/koşul/metin, ilgili kaynak sürümü, belge hash'i, resmi URL, sayfa ve havza listesi gibi alanlar.
- **Resmî yayıncı zorunluluğu**: kaynak aktif olacak, HTTPS üzerinden `resmigazete.gov.tr` veya `tarimorman.gov.tr` alanındaki Bakanlık/Resmî Gazete hostuna ait olacak ve kaynağın `authority` alanı bu resmî kaynak türüyle tutarlı olacak. Sahte veya taklit alan adı iki imzayla bile geçerli olamaz.
- Kaynağın `active` ve belge sürümünün `superseded` durumu da imzalanan kanonik içerikte yer alır.
- Bir kimlik veya rol eksikse, ikisi aynı kişiyse, anahtar değiştiyse, kaynak revize edildiyse, kayıt uyuşmuyorsa veya imza doğrulanmıyorsa sistem **fail-closed** davranır.
- Kaynak `superseded` veya `active=False` ise imza olsa bile onay geçmez. Birden fazla geçerli fiyat çakışması hâlinde P0-2 de hesabı engeller.
- Bir **APPROVER** tarafından haricî anahtarla imzalanmış iptal bildirimi `legal_approval_revocations` tablosuna eklendiğinde aynı konu kimliği yeni veri kabul edemez; yeni mevzuat sürümü/konu kaydı gerekir.
- Onay ve iptal satırları için ORM seviyesinde `UPDATE`/`DELETE` engeli bulunur.

**Sınır:** ORM koruması, veritabanına süper kullanıcı erişimini engellemez. PostgreSQL ayrı DB rolleri, sadece ekleme yetkisi, transaction audit, uzak WORM/S3 Object Lock veya haricî append-only kaydedici ve düzenli bağımsız denetim henüz bu PR'da kurulmamıştır. Bu nedenle bu paket **üretim hukuki onay altyapısının ilk güvenlik adımıdır**, nihai resmi onay sistemi değildir.

## Haricî imzalarla kullanılacak teknik sözleşme

Örnek *sahte anahtar içermeyen* dağıtım ortamı ayarı:

```text
TARIM_RAG_LEGAL_TRUSTED_KEYS_JSON={
  "legal-reviewer-identity": {"role":"REVIEWER","public_key_b64":"<KMS_PUBLIC_KEY>"},
  "independent-approver-identity": {"role":"APPROVER","public_key_b64":"<SECOND_KMS_PUBLIC_KEY>"}
}
```

- `python -m tarim_destek_rag.database.legal_approval_cli inspect --kind RATE --id <ID>` kayıt kimliğini, imzalanacak değişmez alanları, `subject_digest` ve belge hash'ini gösterir.
- Her iki yetkili, **farklı** haricî cihaz/KMS/HSM anahtarıyla `attestation_message` fonksiyonundaki kanonik JSON baytlarını imzalar.
- Yetkili operasyon, imzalı JSON zarfını `register_detached_approval` üzerinden aktarır. `legal_approval_cli apply-attestations --kind RATE --id <ID> --bundle <FILE>` varsayılan **dry-run**, `--commit` ile atomik aktarım sağlar.
- `legal_approval_cli revoke ... --bundle <SIGNED_FILE> --commit` yalnız haricen imzalanmış iptal olayını kaydeder.
- Bu işlemler **hiçbir veri kaydını otomatik VERIFIED yapmaz**. Onaylanacak kayıt durumu, içerik ve belge sürümü dış süreçte doğrulanıp kontrollü işlemle belirlenmelidir. PR #12/#13/#14'teki gerçek veri `DRAFT` olarak korunmuştur.
- `legal_approval_cli` public HTTP yolu değildir. Komutu çalıştıran operatörün OS/DB kimlik doğrulaması ve en az yetki kontrolleri dış konuşlandırma sorumluluğudur.

İmza, `Ed25519` (RFC 8032) ve `cryptography` ile doğrulanır; özel anahtar üretimi/kullanımı sadece rasgele anahtarlı test yardımcılarında bulunur.

## Kaynak sürüm değişikliğinde otomatik güven iptali

1. Kaynak PDF SHA-256 değişirse kanonik `subject_digest` değişir; önceki imzalar geçersiz olur.
2. Ürün/ilçe, `TRY/da`, hukuki madde, yürürlük, özel damla sulama şartı veya ürün listesi değiştirilirse imzalar geçersiz olur.
3. Mevzuat kaldırılmış/geri çekilmişse `SourceVersionModel.superseded=True` veya kaynak `active=False` işlem güvenliğini kapatır.
4. Bağımsız onaylayıcının imzaladığı iptal kaydı aynı kayıt kimliğini kalıcı olarak kapatır.
5. DB üzerinde imzaların değiştirilmesi, haricî anahtarlardan yeni geçerli bir imza üretilmeden sistemi **açamaz**.

## Su kısıtı mevzuat uyuşmazlığı — KAPATILMAMIŞTIR

Resmî Bakanlık eğitim materyali `11 il / 52 ilçe` su kısıtı listesi verir. Örnek:
- [Bakanlık Sorularla Tarımsal Üretim Planlaması](https://www.tarimorman.gov.tr/EYDB/Belgeler/Sorularla_Tarimsal_Uretim_Planlamasi.pdf)
- [Bakanlık Tarımsal Yeraltı Su Kısıtı Bilgi Notu](https://www.tarimorman.gov.tr/BUGEM/Belgeler/Tar%C4%B1m%20Havzalar%C4%B1/Tar%C4%B1msal%20Yeralt%C4%B1%20Su%20K%C4%B1s%C4%B1t%C4%B1%20Bilgi%20Notu.pdf)

2025–2027 dönemi için Bakanlığın sitesinde yayımlanmış [Tebliğ 2024/39](https://kayseri.tarimorman.gov.tr/Belgeler/SOL%20MEN%C3%9C%20BELGELER%C4%B0/2025-2027%20Y%C4%B1llar%C4%B1nda%20Yap%C4%B1lacak%20Bitkisel%20%C3%9Cretim%20Destekleme%20Tebli%C4%9Fi%202024-39.pdf) metninde, eğitim tablosuna göre **Hatay/Kırıkhan, Konya/Yalıhüyük ve Mardin/Nusaybin** gibi ek ilçe adları görülebilmektedir. Bunun resmî yürürlük, değişiklik ve versiyon ayrımı kaynak PDF seviyesinde ayrıca doğrulanmalıdır; yalnız haber/metin alıntılarından kesin 2026 su kısıtı ret/uygunluk haritası çıkarılamaz.

Bu yüzden **su kısıtı için eski `water_restrictions` seed tablosu hukuki hak ediş kanıtı değildir**; `WaterRestrictionRule`, doğrulanmış resmî 2026 bölge/sulama/münavebe veri kaydı olmadan `verified_water_provenance` ve `REVIEW` üretmeye devam eder. 945 havza ürün deseni su kısıtı özel düzenlemesinin yerine geçmez.

## Test kabul ve canlıya geçiş durumu

- Kriptografik testler: tek imza, bağımsız iki imza, sahte imza, rol taklidi, anahtar rotasyonu, kayıt/tutar/SHA/URL değiştirme ve iptal.
- Geçmiş fiyat ve 945 ilçe testleriyle regresyon; kod değiştirilirken hiçbir eski seed satırı hak ediş üretmemeli.
- Üretim kurulumu için *eksik*: gerçek yetkili iki kişinin teyidi, haricî KMS/HSM anahtarları, işlemsel imza turu, ayrı DB yetkileri/WORM audit, 2026 güncel su kısıtı resmi sürümü, uzman hukuk incelemesi ve ödeme aktifleştirme kararı.

**Sonuç:** Kod seviyesinde iki kişilik kriptografik onay kapısı bulunur. Ancak gerçek yetkilendirme ve mevzuat verisi incelemesi bitmeden `DRAFT` satırları üretimde kullanılamaz.
