# G33 — Tek Tıkla Özgün Belge Konumu (RAG Alıntı Navigasyonu)

## Hedef

TarımDestekRAG bir belge parçasından cevaba ulaştığında kullanıcının kaynak sayfayı, ilgili paragrafı veya gerçekten saptanmış görsel bölgeyi **uygulama içinde** görmesi. Her gösterilen bölüm SHA/yerel orijinal PDF/HTML baytlarına tekrar bağlanır.

## Bu kod paketinde eklenen

- `backend/src/tarim_destek_rag/citations/rag_exact_location.py`: SHA + 24 haneli chunk_id üzerinden önce güncel RAG pasaj kimliğini tekilleştirir; sonra orijinal resmî manifest, yıllık keşif envanteri veya kullanıcı dosya manifestinden özgün dosya baytlarını yeniden doğrular.
- PDF kaynağında tam gerçek sayfa 180 DPI olarak orijinal PDF’den yeniden render edilir. Native PDF kelimelerinin gerçek koordinatları veya yine orijinal görüntü üzerinde yeniden çalıştırılmış Tesseract TSV sözcükleri kullanılır.
- Benzersiz tam pasaj dizisi veya özgün kaynaktaki tekil 12 sözcüklük kesit birebir bulunursa yalnız **turuncu aday** işaretleme ve orijinal sayfa içinden kesilmiş gerçek bölge önizlemesi vardır. Tahmini piksel kutusu, suni PDF, onaysız sarı vurgu yoktur.
- Kelime dizisi benzersiz değilse, OCR çalışmazsa veya koordinatlar (ör. döndürülmüş sayfa) güvenilir değilse `PAGE_ONLY_HOLD` ile özgün sayfa işaretsiz gösterilir. Belge kimliği de doğrulanamazsa konum bağlantısı `HOLD`/404 olur.
- Yalnız özgün HTML olarak yayımlanmış belgeler PDF’ye çevrilerek resmî belgeymiş gibi gösterilmez; orijinal HTML metnindeki tekil pasaj turuncu inceleme adayı olabilir; eşleşmiyorsa `DOCUMENT_ONLY_HOLD`.
- Yerel FastAPI yolu: `GET /documents/evidence/{sha}/chunk/{chunk_id}`. İstek için yerel erişim denetimi gerekir; kaynak belgedeki gerçek alıntı ve PDF piksellerinden üretilen görüntü aynı uygulamanın salt okunur HTML kanıt sayfasında yer alır.
- **Belge Analizi & RAG** yanıtındaki her gerçek SHA+chunk alıntısı artık `[Kanıtı uygulamada aç]` bağlantısıyla bu sayfayı açabilir. Aynı RAG sekmesindeki kaynak seçici, yeni sekme açmadan orijinal gerçek sayfa/paragraf önizlemesini gömülü panelde gösterebilir. Örnek sorular ve SSS üzerinden RAG soruları da bu seçiciye bağlandı.
- Kişisel belge dosyaları kaynak türü `USER_UPLOADED_DOCUMENT_NOT_OFFICIAL` olarak ayrılır; resmî mevzuat olduğu iddia edilmez.

## Denetim durumları

| Seviye | Gösterim | Anlamı |
|---|---|---|
| SHA doğrulanamadı | HOLD | Kaynak kanıtı üretilmez |
| Özgün PDF SHA ve gerçek sayfa var; birebir konum yok | PAGE_ONLY_HOLD | Gerçek sayfa, işaretsiz; paragraf yeri kesinleşmedi |
| Birebir tekil native/OCR kelime dizisi gerçek sayfada saptandı | Turuncu kaynak-adayı | OCR/native metin konumu bulundu, bağımsız hukukî onay değil |
| Birebir tekil orijinal HTML pasajı saptandı | Turuncu HTML-adayı | Gerçek metin eşleşmesi; hukukî yürürlük ayrı |
| İki gerçek incelemeciyle görsel doğrulanmış hücre | Sarı **görsel** kanıt | Yalnız incelenen doğru hücre ve aktarım; ödeme/yürürlük değil |

## Tamamlanmayan işler

- **G10 / G12 / G33:** Destek Analizi **Neden?** altındaki *her kural şartını* kaynak PDF sayfa+gerçek fıkra/ROI ile birebir eşlemek. Şu an curated HTML gerekçeleri kendi gezgininde açılıyor; RAG PDF alıntıları için bu turda ayrı kanıt gezgini eklendi. Aralarında henüz tam kural/PDF ROI kapsama ve otomatik eşleştirme yok.
- **G11 / G20:** PDF/HTML, EK-20 tablo hücresi, SSS, rapor ve Flutter mobil sayfalarının tümünde aynı evidence_id/claim_id üzerinden doğrudan açılan **tek** ortak konum sözleşmesi.
- **G05 / G17:** 48 adet gerçek EK-20 kaynak hücresi, her birinin bağımsız iki incelemecisi ve 96 gerçek imzalı görsel okuma hâlâ bekliyor.
- **G31/G32:** Bütün üretim yıllarının mevzuat eksiksizliği, çok sayfalı OCR devamı ve gerçek Windows/GPU model koşulları henüz kapanmadı.
- **F14:** Kapsamlı regresyon, gerçek Windows/Flutter kabulü ve bağımsız hukukî inceleme özellikle son aşamada; bu geliştirmede yürütüldüğü iddia edilmiyor.

## Güvenlik

Tam sayfa görüntüsü asla sıfırdan sentezlenmez; orijinal dosya görüntüsüdür. Turuncu aday yalnız benzersiz kaynak sözcük eşleşmesinden doğar. Üretim yılı yürürlük statüsü, destek uygunluğu ve ödeme hakkı her durumda ayrı `HOLD` alanlarıdır.

İş takip listesi: [OPEN_FEATURE_GAPS.md](OPEN_FEATURE_GAPS.md). G33 `CODE_IN_PROGRESS`, PR #41 `DRAFT` ve `main` değişmez.
