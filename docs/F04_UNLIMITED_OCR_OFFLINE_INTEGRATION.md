# F04 — Baidu Unlimited-OCR yerel OCR adaptörü

Bu eklenti Baidu'nun 2026 yılında yayımladığı **Unlimited-OCR** belge
ayrıştırma modelidir; PaddleOCR veya unlimitedocr.com web sitesi değildir.

Resmî kod: https://github.com/baidu/Unlimited-OCR
Model: https://huggingface.co/baidu/Unlimited-OCR
Lisans: Baidu kaynak kodu MIT; Hugging Face model kartı da MIT belirtir.
Paketlemede MIT lisans bildirimi korunmalı; model, PyTorch, CUDA,
NVIDIA runtime ve kalan bağımlılıkların yeniden dağıtım hakları ayrı
kontrol edilmelidir.

## Özellik ve sınırlar

- Tesseract varlığını bozmayan isteğe bağlı ikinci OCR seçeneğidir.
- Kaynak: yerel arşivde SHA-256 eşleşmesi doğrulanmış Resmî Gazete PDF'sinin
  gerçek 180 DPI sayfa görüntüsü veya 2026 EK-20 orijinal piksel ROI'si.
- OCR motoru yalnız seçilen tam sayfayı veya insan tarafından belirlenen
  x0/y0/x1/y1 alanını işler. Resmî PDF dosyası hiç değiştirilmez.
- Baidu OCR çıktısı ve Tesseract (kuruluysa) sonucu yan yana **taslak**
  görüntülenir. Hiçbir OCR tahmini kesin hukukî alıntı, geçerli yıl,
  iki gerçek incelemecinin onayı, EK-20 hücre koordinatının otomatik
  tespiti, ödeme veya sarı kanıt vurgusu anlamına gelmez.
- Bu sürümde model indirip kurulmuş değildir; Windows GPU çalışma
  kabulü ve hata senaryolarının nihai doğrulaması F14'te kalır.

## Windows / çevrimdışı hazırlık

Baidu'nun yayımladığı Transformers reçetesi: Python 3.12.3, CUDA 12.9,
torch 2.10.0, torchvision 0.25.0, transformers 4.57.1, Pillow 12.1.1,
einops 0.8.2, addict 2.4.0, easydict 1.13, psutil 7.2.2 ve PyMuPDF.
Model GPU ve bfloat16 kullanır. Bu yapılandırmanın her Windows ve NVIDIA
ekran kartında doğrulanmış olduğunu varsaymıyoruz.

1. Ana uygulamanın Python ortamını değiştirmeden ayrı bir Python 3.12
   sanal ortamı oluşturun. Torch ve torchvision için Windows GPU'nuzla
   uyumlu CUDA wheel'ini resmî https://pytorch.org/get-started/locally/
   seçicisinden kurun. Yukarıdaki diğer sürüm bağımlılıklarını ayrıca kurun.
2. Modeli dağıtıma hazırlarken ağ erişimi olan bir makinede Hugging Face
   CLI ile tam bir **denetlenmiş sabit commit SHA** revizyonundan ayrı
   bir klasöre indirin; bir kullanıcı/müşteri işleminde indirmeyin:

~~~powershell
# <AUDITED_MODEL_COMMIT> yerinde incelenmiş gerçek commit SHA bulunmalı.
hf download baidu/Unlimited-OCR --revision <AUDITED_MODEL_COMMIT> --local-dir "C:\TarimDestek-Modeller\Baidu-Unlimited-OCR"
~~~

3. Bu modelin resmî inference yolu trust_remote_code=True kullandığından
   bu klasördeki yürütülebilir Python dosyalarını ve hash'lerini bağımsız
   gözden geçirin. Ayrı sanal ortam/alt işlem **işletim sistemi sandbox'ı
   değildir**; güvenli müşteri dağıtımında ayrı Windows hesabı,
   dosya ACL'leri, firewall ve güvenli kurulum politikası gerekir.
4. Kurulumdan **sonra** uygulamayı başlatan PowerShell oturumunda:

~~~powershell
$env:TARIM_RAG_UNLIMITED_OCR_ENABLED = "1"
$env:TARIM_RAG_UNLIMITED_OCR_TRUST_LOCAL_CODE = "I_AUDITED_THE_LOCAL_MODEL_CODE"
$env:TARIM_RAG_UNLIMITED_OCR_MODEL_DIR = "C:\TarimDestek-Modeller\Baidu-Unlimited-OCR"
$env:TARIM_RAG_UNLIMITED_OCR_PYTHON = "C:\TarimDestek-OCR-Venv\Scripts\python.exe"
~~~

Çalışma zamanı HF_HUB_OFFLINE, TRANSFORMERS_OFFLINE ve HF_DATASETS_OFFLINE
bayraklarını etkinleştirir, model local_files_only=True ile yüklenir,
otomatik model güncellemesi veya ücretli API kullanmaz. Ancak bu çevresel
bayraklar, özel model kodunun işletim sistemi seviyesinde ağ erişimini
kesmez. Gerekirse OS firewall ile dış bağlantıları engelleyin.

## Arayüzde kullanım

**Tam resmî PDF sayfası:**
Destek Analizi → Neden? → Özgün PDF/gerçek sayfa seç →
Baidu Unlimited-OCR paneli → Seçili özgün PDF sayfasını oku.

**2026 EK-20 hücresi:**
Destek Analizi → EK-20 ürün/etmen + destek alanı seç →
Özgün ızgara kutusunu veya gerçek 180 DPI piksel koordinatlarını
ayrıca seç → Baidu Unlimited-OCR ile seçili gerçek EK-20 hücre ROI'sini oku.

- Kaynak dosya, sayfa, üretim yılı ve ROI görüntü SHA'sı bağlanamıyorsa
  hiç OCR çalışmaz, açıkça HOLD döner.
- OCR motoru yoksa, güvenli yönetici onayı yoksa, CUDA yoksa veya model
  çıktısı boşsa da HOLD kalır.
- OCR sonucunda tutar/ürün adı göründüğünde bu değer mevcut
  F04/F09 imzalı EK-20 tablosuna veya ödeme motoruna otomatik yazılmaz.
- Modelin döndürdüğü metin/sade Markdown, yalnız geçici dizinde
  alınır; UI en fazla 8.000 karakter gösterir.

Kod: backend/src/tarim_destek_rag/citations/unlimited_ocr_review.py
ve backend/src/tarim_destek_rag/citations/unlimited_ocr_worker.py.

Önemli açık işler: EK-20 12x4 gerçek hücre koordinatları ve iki gerçek
incelemecinin bağımsız imzaları; F07/F08 yıl/yürürlük/madde/fıkra
eşlemeleri; F10 tüm kanallarda gerçek kanıt navigasyonu. Bunlar OCR
desteği ile tamamlanmış sayılmaz. F14 en son.
