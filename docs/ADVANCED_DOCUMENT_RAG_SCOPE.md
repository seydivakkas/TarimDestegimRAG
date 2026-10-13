# TarımDestekRAG — Yeni Ürün Odağı: Gelişmiş Belge RAG

**Kapsam kararı (13 Ekim 2026):** Ana ürün bir *belgeyi okuma, bilgi bulma, karşılaştırmaya yardımcı olma ve gerçek kaynağı gösterme* asistanıdır. Hak ediş/ödeme aktivasyonu, iki imzalı hukukî onay zincirleri ve tarım kural motoru artık ana RAG kullanıcı deneyiminin parçası **değildir**. Eski ekran/kodlar geriye uyumluluk için \`legacy\` modunda kalabilir.

## Kullanıcı deneyimi

1. PDF, HTML, TXT belgesini yerel bilgisayardan yükle. Belge, \`data/user_documents/originals/<sha>.<format>\` dizininde SHA-256'ya bağlanır. Kullanıcı dosyası hiçbir zaman kendiliğinden "resmî Resmî Gazete belgesi" olarak etiketlenmez. Bu dizin \`.gitignore\` kapsamındadır.
2. Taranmış PDF için Tesseract \`tur+eng\` ile isteğe bağlı OCR seç. OCR mümkün değilse sayfa hâlâ orijinaldir ancak metin sorgusunda görünmeyebilir.
3. Kaynak listesinden belirli belgeyi seç veya tüm indeksli belgelerde ara.
4. Ara: BM25+Türkçe normalizasyon; isteğe bağlı, **zaten diskte kurulu** embedding modeli ile yerel dense RRF. \`TARIM_RAG_LOCAL_EMBEDDING_DIR\` yalnız disk klasörünü işaret eder; internetten otomatik model indirmez.
5. RAG cevabı **alıntılanabilir gerçek pasajlar** üzerinden üretir. Ürün tutarı, başvuru tarihi, ödeme takvimi gibi eski hazır şablonlar kullanılmaz. Kaynak yoksa "bulunamadı" denir.
6. Arama sonucunda belge adı, gerçek PDF sayfası veya HTML madde başlığı, yerel veya resmî kaynak linki, OCR yöntemi ve SHA görülür. PDF için özgün gerçek sayfa PNG görüntüsü ayrıca açılır. PDF metin katmanından çıkarılan tablo satırları ayrı, kaynak sayfaya bağlı parçalar olarak aranabilir.
7. PDF/HTML/TXT kaynakları beraber aranabilir. Yerel dosyalara HTTP erişimi varsayılan olarak yalnız localhost içindir.

## Kod dosyaları

- \`retrieval/document_rag.py\`: özgün kaynak baytları, kullanıcı kütüphanesi, PDF/HTML/TXT parçaları, OCR taslakları, BM25, isteğe bağlı yerel embedding, extractive cevaplar ve kaynak üstverisi.
- \`retrieval/user_documents.py\`: dosya alımı ve SHA-256 bağlı orijinaller, opsiyonel Tesseract OCR indeksleri.
- \`api/main.py\`: \`POST /ask/documents\`, \`POST /documents/import\`, \`GET /documents/status\`, özgün sayfa PNG yolları. \`POST /ask\` da belge odaklı aramaya yönelir.
- \`frontend_pc/pages/legal_assistant.py\`: yeni sade belge yükleme, arama, kaynak seçimi, OCR seçimi ve sohbet deneyimi.
- \`frontend_pc/services/faq_service.py\`: bulunan belgelere ve gerçek sayfa PNG bağlantılarına dayalı yanıtlar.
- \`frontend_pc/app.py\`: **varsayılan yalnız RAG ekranı**, \`TARIM_RAG_UI_MODE=legacy\` ile eski beş-sekmeli simülatör açılabilir.

## Windows / yerel çalıştırma

İlk defa kurulum için proje klasöründe:

\`\`\`powershell
python -m pip install -e ".[pdf-evidence]"
\`\`\`

İki ayrı PowerShell terminali:

\`\`\`powershell
$env:TARIM_RAG_SERVER_MODE="documents"
python -m uvicorn tarim_destek_rag.api.main:app --host 127.0.0.1 --port 8000
\`\`\`

\`\`\`powershell
$env:TARIM_RAG_UI_MODE="document_rag"
python frontend_pc/app.py
\`\`\`

Arayüz: \`http://127.0.0.1:7860\`. API dokümanları: \`http://127.0.0.1:8000/docs\`. OCR için yerel \`tesseract\` çalıştırılabilir olmalı ve \`tur\`, \`eng\` dil verileri kurulmalıdır.

Resmî arşivdeki beş manifesto kaynağının gerçek dosyaları \`$TARIM_RAG_UPDATE_ARCHIVE/originals\` içinde SHA adlı dosyalar olarak bulunmalıdır. Arşiv dosyası yoksa ilgili içerik sorgu yanıtında **uydurulmaz**.

## Mevcut yetenek sınırları

- Yanıt üretimi şimdilik **extractive RAG**: sistem gerçek parçaları seçip kullanıcıya sunar. Yerel LLM ile serbest dil sentezi isteğe bağlı gelecek bir özellik olabilir; mevcut kod bunu yapmış gibi pazarlanmaz.
- Taranmış sayfa OCR karakter veya sayı hatası yapabilir. OCR taslaklarında kullanıcı özgün görseli de açar.
- PDF tablosunun yerel metin katmanı varsa tablo satırları çıkarılabilir. Taranmış, kenarlıksız, birleşik hücreli ve grafik ağırlıklı belgelerde **her tablo hücresi/grafiğin semantik olarak eksiksiz çözüldüğü iddiası yoktur**.
- Gerçek belge/orijinal dosya bütünlüğü bir belgenin *doğru hukukî yorumu* anlamına gelmez; bu ürün bu tür bir onay hizmeti sunmaz.
- Bu yazılımın yeni feature hattı **henüz gerçek Windows cihazında uçtan uca kabul görmemiştir**. Kullanıcının özelliği önce tamamlayıp testleri en sona bırakma kararı korunur.

## Bundan sonraki yalnız RAG odaklı özellik işleri

- Kaynağa geri giden pasajı sayfa görüntüsünde görünür konumuyla yan yana açma.
- Taranmış tablo/şekil içerikleri için hücre/grup koordinatlı arama ve görsel açıklama adayları.
- Belgeler arası karşılaştırma ve tarih/sürüm farklarını **kaynak göstererek** özetleme (hukukî onay değil).
- İsteğe bağlı, bilgisayarda çalışan açık kaynak yerel LLM ile yalnız alıntılanabilir pasajlardan cevap sentezi, atıf denetimi ve "belgede yok" kapısı.
- OCR kalite önizlemesi, sayfa filtreleri, toplu belge yükleme, indeks yenileme, son aşama Windows/CI kabulü.

**Başarı tanımı:** Kullanıcı "Bunun cevabı belgenin neresinde?" dediğinde RAG ilgili metni, kaynağı, orijinal PDF ekran görüntüsünü/HTML bölümünü gösterebilmeli; belgede olmayan bir sonucu uydurmamalıdır.
