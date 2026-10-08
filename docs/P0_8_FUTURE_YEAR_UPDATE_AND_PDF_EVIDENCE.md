# P0-8 — 2030 ve Sonrasında Tek Tıkla Mevzuat Güncelleme + PDF İçinde Birebir Kanıt

**Ürün vizyonu / ana kabul koşulu (8 Ekim 2026):** Kullanıcı repoyu herhangi bir yılda indirip "Resmî Mevzuatı Kontrol Et" dediğinde ülkenin *o üretim yılına ait* destek koşullarını, tutarlarını, yönetmelik/tebliğ kararlarını güncel resmî kaynaklardan bulup sürümleyebilmelidir. Eski yılların mevzuat kayıtları asla kaybolmamalıdır. İlgili hak ediş/ret gerekçesi **özgün belgenin SHA-256 değeri + PDF sayfa numarası + eşleşen birebir cümle + görsel vurgu koordinatı** ile gösterilebilmelidir.

**Mevcut çalışma seviyesi: P0-8A — Gerçek bir tarama/kanıt başlangıç altyapısı.** Bu PR daha sonra yapılması gereken *tam otomatik, 2030 hukuki kapsam garantili yayımlama* yerine geçmez.

## Kullanıcının göreceği tek işlem ve üç ayrı durum

```
[Üretim yılı: 2030] [Resmî Mevzuatı Kontrol Et]
   ↓ 1 — Güncellemeleri keşfet
Bilinen resmî siteleri ve o sitedeki güncel hukuk bağlantılarını tara
   ↓ 2 — Özgün kaynak sürümü arşivle
PDF / HTML → SHA-256 → içerik-adresli değişmez kopya ve URL geçmişi
   ↓ 3 — Anlamsal madde farklarını çıkar (P0-8B; henüz yapılmadı)
Eski hüküm ↔ yeni hüküm; tutar, katsayı, etkin yıl, ürün/ilçe, istisna, istisnanın kalkması
   ↓ 4 — PDF sayfa/metin koordinatlarını doğrula
Anotasyon / excerpt → birebir kaynak cümlesi ve PDF sayfası → doğrulama
   ↓ 5 — Önerilen kural versiyonunu oluştur (P0-8B/C)
DRAFT / REVIEW: eskileri koru, yeni veri ve hesap kurallarını devreye alma
   ↓ 6 — Hukukî iki bağımsız görevli onayı + haricî Ed25519/WORM (P0-7)
   ↓ 7 — Kural testleri / koşul-ürün coğrafya ve dönemi / çakışma / benchmark
   ↓ 8 — Güvenli yayın (P0-8D, kurum onayı ve güvenlik kontrolleri sonrası)
2030 veri seti atomik etkinleşir; eski 2026/2029 snapshot arşivde kalır
   ↓
"Bu tutar neden?" → orijinal PDF sayfa 4, ilgili cümle sarıyla işaretli
```

### P0-8A: Bu PR'da gerçekten çalışanlar

- `configs/official_update_portals.json`: URL/Yıl koda gömülmeden portal envanteri; gelecekte yeni resmî RSS, JSON API, HTML ve Resmî Gazete sağlayıcı adaptörleri takılabilir.
- `updates/discovery.py`: yalnız allowlist HTTPS resmî hostları; güvenli HTML bağlantı keşfi, belge indirme, SHA-256, geçmişi silmeyen `originals/<sha>.pdf/.html`, idempotent `inventory.json` ve zaman damgalı `batches`. **Ödemeler veya onaylı rakamlar değiştirilmez**.
- `scripts/scan_legal_updates.py --year 2030`: tek komut. Hem güncel kaynaklarda yeni metin bulan hem de URL değişmiş olsa daha önce arşivlenen kopyayı koruyan sürümleme.
- `POST /admin/legal-updates/scan?year=2030`: yalnız `TARIM_RAG_ADMIN_API_KEY` ile, var olan `require_admin_key` koruması üzerinden manuel tarama. İstemciden key header değerini serbestçe kabul edip üretim yayımlamaz.
- `frontend_pc/app.py`: yönetici sekmesinde yıl seçimi ve "Resmî Mevzuatı Kontrol Et" butonu; varsayılan kapalı. Sadece `TARIM_RAG_LOCAL_UPDATES_ENABLED=true` + yönetici anahtarı + yerel arka uç bağlantısıyla açılır. **Kamuya açık Gradio oturumuna yönetici işlemi açmak güvenli değildir**; gerçek kullanıcı kimliği/OIDC/CSRF/rate-limit altyapısı yapılmadan internete açık UI'de kullanılmamalıdır.
- `updates/pdf_evidence.py`: PDF SHA kontrolü, **birebir alıntı** kontrolü, tekil eşleşen cümlenin koordinatlarını normalize etme; ayrı sarı highlight anotasyonlu PDF görüntüleme kopyası. Eksik cümle, OCR'siz tarama, yanlış sayfa/hash, çoklu eşleşme otomatik **kanıt olarak reddedilir**.
- `GET /evidence/highlight/{sha256}?page=1&quote=...`: yalnız hash-adresli arşivdeki PDF'nin **işaretli kopyasını** döndürür; kaynak değişirse hata verir. `X-Legal-Evidence: EXACT_TEXT_LOCATED_PENDING_LEGAL_REVIEW` üstbilgisi görsel alıntının hukukî onaydan ayrı olduğunu belirtir.
- `backend/tests/unit/test_p0_8_year_agnostic_updates.py`: 2030 keşif, tekrar tarama, yeni/eski sürüm SHA, sahte alan adı, yayıncı kesintisi, belge tahrifi, birebir cümle bulma, PDF highlight anotasyonu ve olmayan/çoklu alıntı senaryoları.

**Önemli sınır:** Bir URL listesi taranmış ve "0 yeni belge" bulunmuş olması, 2030 destekleme mevzuatının tamamının tarandığını KESİNLİKLE kanıtlamaz. Bilinen resmî portallar yeni sayfalara, farklı yayın usullerine veya API'lere geçebilir. Resmî mevzuat arama / RG günlük yayın / Bakanlık ana yayımlama altyapısında haricî adapter ve kapsam testleri gereklidir.

### Örnek geliştirici kurulumu

```powershell
# Bu paketin gereksinimleri, prod kurulumu değil:
python -m pip install beautifulsoup4 PyMuPDF

# Mevzuat arama; 2030 için BELGE KEŞFİ ve DRAFT arşivi
python scripts/scan_legal_updates.py --year 2030

# Kurumun yerel ve kimliği doğrulanmış Gradio yöneticisinde:
# TARIM_RAG_ADMIN_API_KEY ve TARIM_RAG_LOCAL_UPDATES_ENABLED=true
# (kamuya açık/share=True gradio olmamalı)
```

### PDF içinde işaretlemenin teknik kanıt modeli

```json
{
  "document_sha256": "64-char-confirmed-actual-pdf-hash",
  "source_url": "https://official.example/....pdf",
  "production_year": 2030,
  "legal_effective_from": "2030-01-01",
  "legal_clause": "MADDE ...",
  "page_1_indexed": 3,
  "exact_quote": "PDF'nin sayfasında gerçekten geçen cümle",
  "normalized_quads": [
    [[0.1, 0.2], [0.4, 0.2], [0.1, 0.22], [0.4, 0.22]]
  ],
  "extraction_status": "EXACT_TEXT_LOCATED_PENDING_LEGAL_REVIEW",
  "authorization_status": "DRAFT"
}
```

JSON yalnız *şematik örnektir*: **uydurma resmi cümle veya tutar değildir**. Kaynağın resmî adresiyle dosya hash'i beraber saklanmalı; görünür PDF anotasyonu **yeni görüntüleme kopyasındadır**, arşivdeki orijinal asla değiştirilmez.

Mevcut `citations/document_links.py` **2026 sabitleri ve yazılmış örnek metinler** içeriyor. Bunlar birebir mevzuat satırı gibi gösterilmemeli. P0-8B kapsamında sabit `ARTICLE_PREVIEWS` kaldırılmalı ve tüm açıklamalar yalnız kaynağı kanıtlı `PdfEvidence` / HTML kaynak metni üzerinden üretilmeli. Testlerde sahte cümleler belgedeki bir cümle olarak kabul edilmeyecek.

PDF vurgulaması için `PyMuPDF Page.search_for(..., quads=True)` ve `add_highlight_annot` kullanılıyor. [PyMuPDF dokümantasyonu](https://pymupdf.readthedocs.io/en/latest/page.html). **Lisans uyumluluğu ayrıca değerlendirilmelidir**: PyMuPDF AGPL/commercial lisans koşulları, kapalı haklar saklı tutulan bir ürünün dağıtımıyla çelişebilir. Üretim/dağıtım öncesi MIT lisanslı PDF.js + konum verisi, alternatif açık lisanslı araç veya ticari lisans kararı verilmelidir.

### Kabul testleri / gelecek paketler

| Paket | Beklenti |
|---|---|
| **P0-8A — Kaynak tarama ve PDF konum kanıtı** | 2030 taraması gerçek bağlantı üzerinden yeni belgeleri **DRAFT** arşivler; birebir cümleyi PDF'de sarıya boyayabilir; eski sürümü kaybetmez. Bu PR. |
| **P0-8B — Tam resmi kaynak keşfi ve değişiklik diff** | Resmî Gazete günlük indeksleri/RSS/API, Bakanlık güncel mevzuat ve duyurularının katalog bağlayıcıları; ek/iptal/yeniden numaralandırma/kısıt ve tablodaki rakam değişikliklerini yapısal tespit; kayıp kaynak uyarısı ve doğrulanmış sayfa/alıntı |
| **P0-8C — Dynamic rule DSL, bitemporal ledger** | `support_program_id` ile üretim yılı bağımsız kimlik, mevzuat etkin dönemleri, biliniş tarihi (transaction time), coğrafya ve istisna koşulları. Değişiklikler deklaratif DSL ile, kod değiştirmeden DRAFT kural haline gelir. Belirsiz yorum ≠ otomatik fiyat. |
| **P0-8D — Reviewed atomic release** | Dönem için eksiksiz veri coverage, rakam/bileşen kontrollü bağlama, iki gerçek onay ve WORM, tüm regression/golden testleri, atomik yayın ve geri alma. 2030 yeniden kurulabilir ve 2029 karşılaştırılabilir. |
| **P0-8E — PDF.js kanıt ekranı** | Evraktaki gerçek cümleyi seçili sayfada metin katmanında highlight/scroll, kaynak sürümü ve veri değişikliği diff paneli, mobil/PC paritesi, taranmış belgelere kontrollü OCR + insan kontrolü. |

### Ürün için gerekli negatif senaryolar

1. 2030 için bakanlık sitesine ulaşılamadı → **kaynak kesintisi**, kesinlikle "mevzuat güncel" değil.
2. Resmî belgede oran duyurusu var ama bileşen tablosu yok → **hesap NULL/REVIEW**, bileşen oranı tahmin edilmez.
3. Yeni 2030 yönetmelik, 2029 başvurularını geriye dönük etkilemiyor → eski yılı silme ya da yeni koşulu geriye uygulatma.
4. PDF'nin birinci sayfasında bir terim var ama destek koşulunun madde metni başka sayfada → **doğru sayfa ve cümle tespiti zorunlu**.
5. PDF tarama imajı; Türkçe OCR hatası → **kanıt oluşturma durur**, hukukî onay beklenir.
6. Tek destek için birden fazla düzenleme çelişkili → **REVIEW**, sıradaki yayını körü körüne üstüne yazma.
7. Geçersiz iki imza veya WORM erişilemiyor → yeni yıl **etkinleştirilemez**.
8. İki sistem kopyası aynı anda tararsa → hash idempotency ve DB transaction kilidi/yerel write-lock kurulmalı; bu ilk PR tek süreç varsayar.

**Başarının doğru ölçüsü:** Kod GitHub’dan indirildikten **4 yıl sonra bile** URL güncellemesi, üretim yılı sabiti düzenlemesi veya kaynak cümlesi uydurmadan **resmî yeni veri keşfini yapabilmek**, ekspertizden sonra güvenli hesap kuralına aktarabilmek ve her sonucu PDF’de orijinal metni işaretleyerek ispatlamak. Tam başarı P0-8B–E sonrası ölçülebilir.
