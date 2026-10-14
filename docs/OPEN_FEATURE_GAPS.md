# Açık Mühendislik Eksikleri ve Çözüm Takip Listesi

**Son değerlendirme:** 2026-10-14 — Kod envanteri, PR #41. Gerçek Windows/GPU, bağımsız hukukî kabul ve 48 EK-20 insan onayı bu tarihte yapılmış sayılmaz.

**Tek kaynak:** configs/feature_gap_register.json. Bu okunabilir sayfa aynı veriden oluşturulmuştur. Yeniden üretmek için scripts/render_feature_gap_register.py --write.

**Toplam açık iş:** 37 • BLOCKED_EXTERNAL: 5 / OPEN: 19 / CODE_IN_PROGRESS: 10 / DEFERRED_F14: 3. Bunlar iş kalemidir; 48 EK-20 hücresi G05/G17'de ayrı izlenir.

## F01–F14 özellik düzeyi

| Paket | Özellik | Mevcut geliştirme durumu |
|---|---|---|
| F01 | Özgün mevzuat arşivi | PARTIAL |
| F02 | Gerçek PDF sayfası | IMPLEMENTED_PENDING_F14 |
| F03 | PDF/OCR indeksleme | PARTIAL |
| F04 | Tablo ve hücre geometrisi | PARTIAL |
| F05 | Görsel/şekil bölgeleri | PARTIAL |
| F06 | PDF/HTML kanıt gezgini | PARTIAL |
| F07 | Tekil kural → kaynak | PARTIAL |
| F08 | Yürürlük ve değişiklik zinciri | PARTIAL |
| F09 | EK-20 çift inceleme | PARTIAL |
| F10 | Neden/SSS/rapor/mobil | PARTIAL |
| F11 | Windows offline paket | PARTIAL |
| F12 | Kaynak güncelleme ve geri alma | PARTIAL |
| F13 | Hak ediş ile onay ayrımı | PARTIAL |
| F14 | Nihai teknik/hukukî kabul | DEFERRED_FINAL |

## Tek tek açık işler: eksik → çözüm → kapanış

| ID | Öncelik | Paket | Durum | Açık iş / problem | Yapacağımız çözüm | Kapanış kriteri |
|---|---|---|---|---|---|---|
| G01 | P0 | F01 | BLOCKED_EXTERNAL | Resmî kaynakların ve ek PDF'lerin tam arşivi | 2024/39, 2025/13, 2025/42, 8859, 10394, 11781 ve ilgili eklerin özgün dosyalarını resmî kaynaktan elde edip SHA/URL/uzunlukla manifestle eşleştir. | Eksiksiz, SHA-pinned özgün kaynak listesi; olmayan belge HOLD. |
| G02 | P1 | F01 | OPEN | Kaynak edinme / güncelleme yetkisi | Kaynak keşif→indirme→karantina→SHA doğrulama→sürüm kaydı ve insan inceleme kapısı kur. | Orijinal olmayan dosya asla resmî kaynak yapılmaz. |
| G03 | P1 | F03 | OPEN | Bütün PDF sayfalarında OCR durumu | Sayfa başına native/OCR/boş/hata + DPI/SHA/geometri durumunu ortak indeksle, fail-closed. | Tüm arşiv sayfalarının durumları ve boş kalanların açık nedeni görülür. |
| G04 | P1 | F03 | BLOCKED_EXTERNAL | Baidu Unlimited-OCR gerçek Windows GPU çalışması | Yerel model revizyonunu sabitle; gerekli bağımlılıkları, CUDA uyumluluğunu ve yürütülebilir özel kodu incele; cihazda fiilen çalıştır. | Gerçek donanım kaydı ve gerekli lisans kanıtı; metin sonucu OCR_UNREVIEWED. |
| G05 | P0 | F04 | BLOCKED_EXTERNAL | EK-20 48 gerçek hücre ROI'si | Kaynağın tek sayfasındaki 12×4 hücreyi gerçek 180-DPI piksel kutularıyla insan gözetiminde eşleştir; tutar/null ayrımı koru. | 48/48 SHA/RGB/row/column/bbox birbiriyle tutarlı ve gerçek PDF üzerinde incelenmiş. |
| G06 | P1 | F04 | OPEN | Çizgisiz/birleşik raster tablolar | Satır/sütun/hücre ayrıştırıcıları + görsel OCR önerisi + insan seçimli belirsizlik yönetimi uygula. | Tahmine dayalı koordinat ve otomatik hücre PASS yok. |
| G07 | P2 | F04 | OPEN | Born-digital tablo coordinate mapping | PDF point→raster pixel dönüşümü ve kaynak kimliği/kolon span eşleştirmesi ekle. | Gerçek hücreler doğru sayfa ve DPI'ya bağlı. |
| G08 | P2 | F05 | OPEN | Şekil/çizim/tabloda semantik inceleme | Kaynak orijinaline bağlı ROI önizlemeyi açıklama/insan kanıt durumundan ayır. | Grafik anlamı OCR/detection'dan otomatik kesinleşmez. |
| G09 | P0 | F06 | CODE_IN_PROGRESS | Gerekçeden doğrulanmış HTML hükmüne tek tık | Özgün SHA'lı HTML'de birebir madde/alıntının indekslenen pasajını göster; tarayıcı text-fragment yönlendirmesi ekle. | Doğru madde/pasaj görünür; arşiv yoksa bağlantı üretilemez. |
| G10 | P0 | F06 | CODE_IN_PROGRESS | Gerekçeden gerçek PDF sayfasına otomatik geçiş | Claim→source_id/page/bbox kabul kontratı; var olan dropdown/image viewer otomatik güncelle; sahte PDF sayfası engeli. Tekil destek gerekçesi için curated native PDF SHA+sayfa+gerçek konum eşleşmesi ve otomatik Neden görüntüleme altyapısı eklendi. Şimdilik PDF bağları boş; gerçek kaynak ve bütün kural şartlarının doğrulanması bekliyor. | Bir claim için tek doğrulanmış PDF konumu varsa oraya gider, yoksa HOLD. |
| G11 | P1 | F06 | CODE_IN_PROGRESS | PDF/HTML tek kanıt geçerlilik ekranı | HTML exact passage, PDF text, tablo ROI ve bağımsız sarı/amber statülerini tek gezginde birleştir. Neden ekranında kaynağı bilinen HTML/PDF ile onaysız PDF/HTML RAG adayının durumlarını ayıran tekil kaynak inceleme paneli eklendi. EK-20 görsel insan onayı, tüm kanallar ve bağımsız hukukî kapsam henüz bütünleşmedi. | Yellow yalnız doğrulanmış kanıt türünü gösterir; hukukî/geçerli yıl ayrı. |
| G12 | P0 | F07 | OPEN | Tüm kural şartlarını tekil hükme bağlama | Her rule_id/support_id/year/field/exact_claim_text için kaynak madde/fıkra veya tablo hücresiyle curated binding üret. | Bütün destek gerekçeleri tekil olarak eşlenir ya da görünür HOLD kalır. |
| G13 | P1 | F07 | CODE_IN_PROGRESS | Kaynak kapsam sayacı ve bilinmeyen nedenler | Tüm destek şartları için unmapped/ambiguous/located/year-HOLD durumlarını arayüzde say. Eklenen özellik: güncel değerlendirmedeki tekil kaynak-konum eşleşen/eşleşmeyen gerekçeleri say ve Neden alanında açık kanıt kimlikleriyle göster; kapsam tamamlama henüz açık. | Eksik gerekçelerin listesi ve tam coverage yüzdesi doğrudan görülebilir. |
| G14 | P0 | F08 | OPEN | Mevzuat değişiklik/ilga grafiği | 2024/39, 2025/13, 2025/42, 8859, 10394, 11781 değişikliklerinin affected provision ve yürürlük etkisini madde bazında modellendir. | Değişiklik silsilesi ve ilga edilen hükümler kaynak kanıtıyla ilişkilidir. |
| G15 | P0 | F08 | OPEN | 2025/2026/2027 hukukî yıl geçerliliği | Geçiş ve geriye dönük koşullar dahil her hüküm için dönem/yıl applicability kararını doğrulanmış değişiklik zincirine bağla. | Yalnız tam kaynak yılı kanıtlanmış hükümlere temporal PASS verilebilir. |
| G16 | P1 | F08 | OPEN | EK-20 oranlarını yıllar arasında karıştırmama | 2026 annex aktarımını 2025/2027'ye taşımayı engelleyen yıl bazlı değişiklik/değer seçimini tamamla. | 2025 ve 2027 için 2026 EK-20 tutarı asla varsayılan kullanılmaz. |
| G17 | P0 | F09 | BLOCKED_EXTERNAL | 48 hücreye iki gerçek insan onayı | Her gerçek ROI için iki farklı kayıtlı kişinin görsel okumasını, Ed25519 imzasını ve uyuşmazlık/REJECT işlemlerini topla. | 48×2 gerçek onay veya alan bazlı açık REJECT/HOLD; sahte otomatik imza yok. |
| G18 | P1 | F09 | OPEN | ROI kaydetme ve inceleme UI iş akışı | Gradio'da öneri oluşturma/çatışma engeli, onay görev listesi ve kayıt durumlarını kontrollü operatör akışına geçir. | Ekrandan öneri yaratılabilir; istemci özel anahtar alamaz. |
| G19 | P1 | F09 | OPEN | İncelemeci yetkileri, iptal ve arşiv | Anahtar envanteri, kurum dışı imzalama, iptal, değiştirilemez operasyon kayıtları ve kimlik kontrolü kur. | Anahtar iptalinde görsel PASS düşer; kayıtlara kontrollü erişim. |
| G20 | P1 | F10 | OPEN | Mobil/SSS/rapor tam navigasyon | Aynı claim_id ve evidence_id için kanallar arasında kaynak açma, PDF ROI ve HOLD eşitliğini tamamla. | Her kanalda aynı gerçek kanıt konumu, farklı yıl/oturum sızıntısı yok. |
| G21 | P1 | F10 | OPEN | SSS/RAG alıntıların tekil hukukî sözleşmesi | Yakın anlamsal eşleşmeden kesin madde üretme; açık claim seçme veya ayrı kaynak kanıt pipeline'ı oluştur. | Tüm SSS kaynakları ya exact verified ya da HOLD. |
| G22 | P1 | F11 | OPEN | Offline Windows yayımlama paketi | Ana uygulama + ayrı opsiyonel OCR ortamı + kaynak arşivi yönetimi; kurulum ve sürümleme sihirbazı. | İnternetsiz normal kullanım ve özelleştirilebilir GPU yolu. |
| G23 | P1 | F11 | OPEN | Üçüncü taraf yeniden dağıtım lisansı | Baidu MIT, model revizyonu ve PyTorch/CUDA/NVIDIA/OCR bağımlılıklarının binary/weight dağıtım şartlarını dosyala. | Dağıtılan her dosya için kaynak/sürüm/lisans kanıtı. |
| G24 | P1 | F12 | OPEN | Mevzuat diff/onay görevleri | İndirilen yeni sürümü eklemeli kaynak grafına al, değişen madde/hücreleri HOLD inceleme kuyruğuna düşür. | Eski kural otomatik yeni yıl için geçerli kalmaz. |
| G25 | P1 | F12 | OPEN | Revizyon geri alma ve yeniden üretilebilir kanıt | Kaynak revision/sha ve açıklama/plan anlık durumlarını tut, kontrollü geri al. | Yanlış güncellemeden önceki kanıtlar hash ve dönemle ayrı bulunur. |
| G26 | P0 | F13 | CODE_IN_PROGRESS | Tahmini tutar vs ödeme onayı ayrımı | Destek kartı, KPI, rapor ve mobilde ekonomik simülasyon ile mevzuat/olgu ödeme yetkisini ayrı etiketle. Kod ek adımı: masaüstü ve mobilde null tutarı 0 TL diye sunma; raporu bağımsız olarak adlandır. Ayrı ödeme otorite geçidi hâlâ açık. | Hiçbir tahmini tutar ödeme kararı veya kesin hak ediş diye görünmez. |
| G27 | P0 | F13 | OPEN | Bütün eski endpoint'lerde fail-closed | Legacy API, hesaplama, RAG/SSS ve yeni kaynak sürümü girişlerinde aynı aktivasyon kapısı uygula. | Eksik hukukî onaylı tutar ücret/ödeme motorunu aktive etmez. |
| G28 | P3 | F14 | DEFERRED_F14 | Bütün fonksiyonel/regresyon/failure testleri | F01–F13 ve arayüz kapsamı bitince birikmiş sentetik+CI+gerçek kaynak negatif testleri çalıştır. | Referans sentetik/entegrasyon testleri ve açık kalan hatalar raporlanır. |
| G29 | P3 | F14 | DEFERRED_F14 | Gerçek Windows ve GPU kabulü | Windows 10/11, ekran kartı olan/olmayan, offline ve model-kurulu akışlarını sona bırak. | Donanım, OCR doğruluk, performans ve lisans paket kabul raporları. |
| G30 | P3 | F14 | DEFERRED_F14 | Bağımsız mevzuat ve kurumsal son kabul | Tüm iddiaları yetkili hukuki incelemeye bağla; ödeme aktivasyonu bağımsız karar. | Mevzuat/yıl/üretici ve veri yetki onayları ayrıştırılmış imza kaydı. |
| G31 | P0 | F01 | CODE_IN_PROGRESS | Resmî Gazete tüm yayın dönemlerini kapsayan keşif ve eksiksizlik defteri | Üretim yılından bağımsız yayın tarihi aralıklarında resmî RG gün sayfalarını ve gerçek kaynak bağlantılarını tara. 1–14 günlük bounded backfill var; dönem-bazlı tamamlanma, mükerrer/nos issue, başlık varyasyonları ve resmi arama API adaptörü ile eksiksizlik doğrulaması eksik. | Her tarih aralığı/gazete sayısı ve ilgili belge için başarı, erişilemeyen gün ve ekler izlenmiş; tam yıllık kapsam doğrulanmadan coverage PASS yok. |
| G32 | P0 | F03 | CODE_IN_PROGRESS | Her yeni resmî PDF için otomatik yerel OCR + arama indeksi | Güncelle→SHA-doğrulanmış PDF→sayfa native/Tesseract OCR→gerçek bbox→yıl arşivi araması ve özgün 180 DPI önizleme kodlandı; Baidu toplu fallback, büyük belgeye devam ederek tarama, performans, yeniden başlama ve Windows kurulum eksik. | İlgili tüm yeni resmî PDF sayfalarında OCR/native/başarısız/HOLD durumu ve gerçek sayfa kanıtı mevcut; indeks tamamlanmayan sayfalar ayrı görünür. |
| G33 | P0 | F06 | CODE_IN_PROGRESS | Her cevap/gerekçe için tek tıkla gerçek PDF madde, paragraf ve hücre | Yıllık aramada kaynak PDF/sayfa gösterimi eklendi; destek analizi Neden/SSS/RAG cümlesi→original SHA+sayfa+gerçek bbox otomatik yönlendirme/işaretleme ve tüm kanal/rapor bağlantısını tamamla. OCR-adayı turuncu, iki görsel onaylı kaynak sarı. Bu turda RAG alıntı SHA+chunk kimliğinden kaynak baytlarını yeniden doğrulayan yerel PDF/HTML kanıt görüntüleyicisi, benzersiz native/OCR kelime koordinatı turuncu aday çerçevesi ve Gradio Belge Analizi sekmesinde gömülü gerçek sayfa önizlemesi eklendi. Destek Analizi Neden/rapor/mobil bütün iddialarının exact ROI eşlemesi ve F14 kabulü henüz eksik. Her tekil Destek Analizi gerekçesi için bounded RAG kaynak araştırması, orijinal PDF/HTML adayını aynı ekran içinde açma, stale yıl/claim değişiminde temizleme ve curated native PDF birebir metin/piksel konumunu ortak claim_id/evidence_id üzerinden PC/rapor/mobil sözleşmesine taşıma kodu eklendi. Gerçek curated PDF kayıtları hâlen 0, HTML'de 2 exact rule bağlamı var; bunlar gerçek arşiv dosyasına erişimle doğrulanır. Tüm yılların tüm kural şartlarının madde-fıkra/ROI eşlemesi bekliyor. | Her gösterilen somut mevzuat gerekçesinde doğru PDF sayfası ve ilgili gerçek konum doğrudan açılır; yalnız HTML yayımlanan resmî belgeler HTML asli kanıt olarak belirtilir; bulunamazsa HOLD. |
| G34 | P0 | F08 | OPEN | Yeni OCR belgelerinden yıllık değişiklik zincirine güvenli kural güncelleme | Yeni arşivlenen belgeyi etkilenen hüküm/ek/yıl değişiklik önerisine dönüştür, insan incelemesi ve bağımsız yürürlük kanıtı olmadan 2025/2026/2027/yeni yıl tahmini tutarlarını değiştirme. | Her yıl ve destek şartı için yürürlük/ilga/değişiklik/önceki hüküm bağları kaynak konumlu; otomatik OCR kesin kural veya ödeme açamaz. |
| G35 | P0 | F10 | CODE_IN_PROGRESS | Tüm kanallar için bir merkezi kanıt servisi | CentralEvidenceEngine ve aynı canonical record API üzerinden PC Neden, SSS, rapor ve Flutter DTO tüketimini tekleştir. RAG araştırma adayını kesin normatif bağdan ayır. Kaynak SHA/ROI doğrulaması sadece ortak backend'de kalacak. Tüm legacy ekran çağrıları ve entegrasyon kabulü açık. | PC/mobil/SSS/rapor aynı rule/check/evaluation için aynı check_id, evidence_id, SHA, özgün hüküm konumu ve HOLD sonucunu gösterir; kanallar bağımsız source PASS üretmez. |
| G36 | P0 | F07 | CODE_IN_PROGRESS | Bütün deterministik kural kontrollerine metinden bağımsız check_id | RuleCheckEvent.check_id özelliğini kural çıktısına ekledik. 2026 Temel Destek ÇKS üç farklı sonuçta BASIC_CKS_REGISTRATION üretir. Diğer kurallarda eski dizi + field/ordinal geçici ID'si LEGACY_NO_SEMANTIC_CHECK_ID_HOLD kalır. Her kontrolün kaynağında stable check_id emit edilmesini ve kaynak matrisinde check_id bazlı migration'ı tamamla. Mühendislik sırası: G37 gerçek kaynak ve bağımsız yıl kabulü tamamlanmadan diğer kural şartlarını PASS'a yükseltme. RuleCheckEvent altyapısı ve ÇKS pilotu var; diğerleri LEGACY_HOLD. | Tüm aktif destek kural kontrolleri check_id alanını doğrudan kural üretiminde emiter; metin, ürün/alan ve geçerli/eksik/başarısız sonucu değişince check_id değişmez, iki farklı mantıksal kontrol aynı ID'yi paylaşmaz. |
| G37 | P0 | F08 | BLOCKED_EXTERNAL | 2026 Temel Destek ÇKS pilotunun tam kaynak/yıl/görsel bağımsız kabulü | 2024/39 MADDE 4(1) özgün HTML dosyasının SHA ve gerçek birebir pasajını fiilen aç; 2025/13, 2025/42 ve 11781 etkilerini ve 2026 yürürlük zincirini kaynaklarıyla tamamla; mevzuat konumu ve üretim yılı ayrı uzman incelemesinden geçsin. Sarı yalnız bağımsız görsel onaylı alanlarda; yoksa turuncu ve HOLD. 14.10.2026 resmî Bakanlık metni incelemesinde 2025/42 MADDE 3'ün 2024/39 MADDE 5(1)'i ÇKS/ÖKS/KOBÜKS'e genişlettiği, MADDE 16 ile 01.01.2026 yürürlüğünün düzenlendiği tespit edildi. Temel Destek kuralında CKS-only yanlış ret giderildi; ÖKS/KOBÜKS bilinmiyor ise REVIEW. Kullanıcı beyanı resmî 2026 parsel kaydı kanıtı değildir ve REVIEW korunur. Kaynak matrisine asıl Madde 5(1), değişiklik Madde 3, yürürlük Madde 16 eklendi. Merkezi pilot dört ayrı gerçek kaynak SHA/metin doğrulama durumunu verir. Gerçek orijinal arşiv baytlarının edinilmesi, 2025/13 ve 11781'in tam etki incelemesi ile bağımsız hukukî ve parsel doğrulaması bloklu. docs/G37_2026_CKS_ORIGINAL_AMENDMENT_REVIEW.md | ÇKS check_id PASS/FAIL/MISSING tüm varyantlarda aynı; yıl 2026 için yürürlük/ilga/istisna belgeleri, özgün SHA/hüküm, PC/mobil/SSS/rapor yönlendirmeleri aynı kanıtı gösterir. Bağımsız kanıt olmadan nihai PASS yok. |

## Mühendislik sırası / bağımlılıklar

1. Kaynak gerçekliği: G01 → G05 ve G12/G14. SHA olmayan özgün dosyadan koordinat veya madde üretme.
2. EK-20: G05 gerçek 48 ROI → G17 iki kişinin ayrı incelemesi → G19 iptal güvenliği. Eksik onay HOLD.
3. Navigasyon: G09 HTML metin düğümü → G10 PDF kaynak/ROI → G11 tek gezgin → G20 Neden/SSS/rapor/mobil.
4. Yıl geçerliliği: G12 tekil şartlar + G14 değişiklik grafiği → G15 2025/2026/2027 → G16 EK-20 izolasyonu.
5. Ürün: G22/G23 Windows/lisans, G24/G25 güncelleme, G26/G27 ödeme ayrımı → G28–G30 son F14.

6. Yıl bağımsızlığı: G31 tam Resmî Gazete dönem kapsamı, G32 otomatik tüm ilgili PDF OCR, G33 her iddiadan PDF gerçek konuma geçiş, G34 yeni yılın değişiklik/kural güvenli kapısı.

7. Merkezi kanıt: G35 ortak kanıt motoru → G36 bütün kurallarda stable check_id → G37 2026 ÇKS pilotunda özgün/yıl/bağımsız kabul; sonra diğer yıllara genelleştirme.

Durum kodları: OPEN (özellik açığı), CODE_IN_PROGRESS (kodlanıyor), BLOCKED_EXTERNAL (gerçek kaynak, insan veya donanım), DEFERRED_F14 (son kabulde), CLOSED_IMPLEMENTED (özellik kodu kapandı, F14 hukukî/teknik PASS değil).

**PR politikası:** #41 DRAFT/unmerged, main değiştirilmez. Turuncu kaynak adayı, bağımsız imzalı sarı görsel kanıt, yürürlük ve ödeme onayı birbirinden ayrıdır.

