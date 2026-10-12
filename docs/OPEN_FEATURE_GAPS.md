# Açık Mühendislik Eksikleri ve Çözüm Takip Listesi

**Son değerlendirme:** 2026-10-12 — Kod envanteri, PR #41. Gerçek Windows/GPU, bağımsız hukukî kabul ve 48 EK-20 insan onayı bu tarihte yapılmış sayılmaz.

**Tek kaynak:** configs/feature_gap_register.json. Bu okunabilir sayfa aynı veriden oluşturulmuştur. Yeniden üretmek için scripts/render_feature_gap_register.py --write.

**Toplam açık iş:** 30 • BLOCKED_EXTERNAL: 4 / OPEN: 20 / CODE_IN_PROGRESS: 3 / DEFERRED_F14: 3. Bunlar iş kalemidir; 48 EK-20 hücresi G05/G17'de ayrı izlenir.

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
| G10 | P0 | F06 | OPEN | Gerekçeden gerçek PDF sayfasına otomatik geçiş | Claim→source_id/page/bbox kabul kontratı; var olan dropdown/image viewer otomatik güncelle; sahte PDF sayfası engeli. | Bir claim için tek doğrulanmış PDF konumu varsa oraya gider, yoksa HOLD. |
| G11 | P1 | F06 | OPEN | PDF/HTML tek kanıt geçerlilik ekranı | HTML exact passage, PDF text, tablo ROI ve bağımsız sarı/amber statülerini tek gezginde birleştir. | Yellow yalnız doğrulanmış kanıt türünü gösterir; hukukî/geçerli yıl ayrı. |
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

## Mühendislik sırası / bağımlılıklar

1. Kaynak gerçekliği: G01 → G05 ve G12/G14. SHA olmayan özgün dosyadan koordinat veya madde üretme.
2. EK-20: G05 gerçek 48 ROI → G17 iki kişinin ayrı incelemesi → G19 iptal güvenliği. Eksik onay HOLD.
3. Navigasyon: G09 HTML metin düğümü → G10 PDF kaynak/ROI → G11 tek gezgin → G20 Neden/SSS/rapor/mobil.
4. Yıl geçerliliği: G12 tekil şartlar + G14 değişiklik grafiği → G15 2025/2026/2027 → G16 EK-20 izolasyonu.
5. Ürün: G22/G23 Windows/lisans, G24/G25 güncelleme, G26/G27 ödeme ayrımı → G28–G30 son F14.

Durum kodları: OPEN (özellik açığı), CODE_IN_PROGRESS (kodlanıyor), BLOCKED_EXTERNAL (gerçek kaynak, insan veya donanım), DEFERRED_F14 (son kabulde), CLOSED_IMPLEMENTED (özellik kodu kapandı, F14 hukukî/teknik PASS değil).

**PR politikası:** #41 DRAFT/unmerged, main değiştirilmez. Sarı görsel doğrulama, yürürlük ve ödeme onayı birbirinden ayrıdır.

