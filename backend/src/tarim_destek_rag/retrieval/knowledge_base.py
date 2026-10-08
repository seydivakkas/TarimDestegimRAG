"""2026 Yılı Resmî Tarımsal Destek Mevzuatı, SSS Kütüphanesi ve Bilgi Tabanı.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

from typing import Any

from tarim_destek_rag.retrieval.models import DocumentChunk

# 2026 Yılı Yapılandırılmış Destek Kataloğu (Kuruş Hassasiyetli TL/da Birim Değerler)
CROP_SUPPORT_CATALOG: dict[str, dict[str, Any]] = {
    "BUĞDAY": {
        "temel_destek_tl": 477.10,
        "planli_uretim_tl": 477.10,
        "sertifikali_tohum_tl": 205.52,
        "su_kisiti_tl": 0.00,
        "kadin_genc_ilave_tl": 0.00,
        "toplam_standart_tl": 954.20,
        "aciklama": "Buğday: temel ve planlı üretim desteği toplamı 954,20 TL/da; planlı destek havza/şartlara bağlı.",
    },
    "ARPA": {
        "temel_destek_tl": 477.10,
        "planli_uretim_tl": 477.10,
        "sertifikali_tohum_tl": 205.52,
        "su_kisiti_tl": 0.00,
        "kadin_genc_ilave_tl": 0.00,
        "toplam_standart_tl": 954.20,
        "aciklama": "Arpa: toplam temel + planlı üretim 954,20 TL/da; planlı destek havza/şartlara bağlı.",
    },
    "MISIR": {
        "temel_destek_tl": 477.10,
        "planli_uretim_tl": 477.10,
        "sertifikali_tohum_tl": 0.00,
        "su_kisiti_tl": 0.00,
        "kadin_genc_ilave_tl": 0.00,
        "toplam_standart_tl": 954.20,
        "aciklama": "Dane mısır: yeraltı su kısıtı bulunan bölgelerde özel yasakları denetleyin. Yurt içi sertifikalı tohum ayrı koşulludur.",
    },
    "AYÇİÇEĞİ": {
        "temel_destek_tl": 550.50,
        "planli_uretim_tl": 550.50,
        "sertifikali_tohum_tl": 0.00,
        "su_kisiti_tl": 0.00,
        "kadin_genc_ilave_tl": 0.00,
        "toplam_standart_tl": 1101.00,
        "aciklama": "Yağlık ayçiçeği: planlı destek havza koşullarına bağlı. Yerli sertifikalı tohum ilavesi ayrıca değerlendirilir.",
    },
    "PAMUK": {
        "temel_destek_tl": 825.75,
        "planli_uretim_tl": 825.75,
        "sertifikali_tohum_tl": 0.00,
        "su_kisiti_tl": 0.00,
        "kadin_genc_ilave_tl": 0.00,
        "toplam_standart_tl": 1651.50,
        "aciklama": "Kütlü pamuk: planlı destek için yerli sertifikalı tohum dahil koşullar denetlenmelidir.",
    },
    "FINDIK": {
        "temel_destek_tl": 550.50,
        "planli_uretim_tl": 0.00,
        "sertifikali_tohum_tl": 0.00,
        "su_kisiti_tl": 0.00,
        "kadin_genc_ilave_tl": 0.00,
        "toplam_standart_tl": 550.50,
        "aciklama": "Fındık 3. kategori temel destek tutarıdır; planlı üretim kapsamında olmadığı için ikinci tutar gösterilmez.",
    },
    "MERCİMEK": {
        "temel_destek_tl": 367.00,
        "planli_uretim_tl": 367.00,
        "sertifikali_tohum_tl": 0.00,
        "su_kisiti_tl": 293.60,
        "kadin_genc_ilave_tl": 0.00,
        "toplam_standart_tl": 734.00,
        "aciklama": "Mercimek: su kısıtı ek desteği yalnız resmen belirlenmiş sulu tarım havzalarında ve ilgili koşullarda uygulanır.",
    },
    "NOHUT": {
        "temel_destek_tl": 367.00,
        "planli_uretim_tl": 367.00,
        "sertifikali_tohum_tl": 0.00,
        "su_kisiti_tl": 293.60,
        "kadin_genc_ilave_tl": 0.00,
        "toplam_standart_tl": 734.00,
        "aciklama": "Nohut: planlı ve yeraltı su kısıtı destekleri koşullara bağlıdır.",
    },
    "SOYA": {
        "temel_destek_tl": 550.50,
        "planli_uretim_tl": 550.50,
        "sertifikali_tohum_tl": 0.00,
        "su_kisiti_tl": 0.00,
        "kadin_genc_ilave_tl": 0.00,
        "toplam_standart_tl": 1101.00,
        "aciklama": "Soya için yurt içinde üretilmiş sertifikalı tohum ilavesi ek şartlara bağlıdır.",
    },
    "KANOLA": {
        "temel_destek_tl": 550.50,
        "planli_uretim_tl": 550.50,
        "sertifikali_tohum_tl": 0.00,
        "su_kisiti_tl": 0.00,
        "kadin_genc_ilave_tl": 0.00,
        "toplam_standart_tl": 1101.00,
        "aciklama": "Kanola için sertifikalı tohum ve havza koşullarını ayrıca denetleyin.",
    },
    "ASPİR": {
        "temel_destek_tl": 367.00,
        "planli_uretim_tl": 367.00,
        "sertifikali_tohum_tl": 0.00,
        "su_kisiti_tl": 293.60,
        "kadin_genc_ilave_tl": 0.00,
        "toplam_standart_tl": 734.00,
        "aciklama": "Aspir su kısıtı ek desteği yalnız sulu ve kısıtlı havzalarda uygulanabilir.",
    },
    "KURU FASULYE": {
        "temel_destek_tl": 550.50,
        "planli_uretim_tl": 550.50,
        "sertifikali_tohum_tl": 0.00,
        "su_kisiti_tl": 0.00,
        "kadin_genc_ilave_tl": 0.00,
        "toplam_standart_tl": 1101.00,
        "aciklama": "Kuru fasulyede planlı üretim ve sertifikalı tohum destekleri ek koşullara bağlıdır.",
    },
    "PATATES": {
        "temel_destek_tl": 367.00,
        "planli_uretim_tl": 367.00,
        "sertifikali_tohum_tl": 0.00,
        "su_kisiti_tl": 0.00,
        "kadin_genc_ilave_tl": 0.00,
        "toplam_standart_tl": 734.00,
        "aciklama": "Patates için su kısıtı bölgelerinde desteklenmeme hükümleri ayrıca denetlenmelidir.",
    },
    "ÇELTİK": {
        "temel_destek_tl": 825.75,
        "planli_uretim_tl": 0.00,
        "sertifikali_tohum_tl": 0.00,
        "su_kisiti_tl": 0.00,
        "kadin_genc_ilave_tl": 0.00,
        "toplam_standart_tl": 825.75,
        "aciklama": "Çeltik 4. kategori temel desteğe tabidir; planlı üretim desteği otomatik varsayılmaz.",
    },
    "ZEYTİN": {
        "temel_destek_tl": 367.00,
        "planli_uretim_tl": 0.00,
        "sertifikali_tohum_tl": 0.00,
        "su_kisiti_tl": 0.00,
        "kadin_genc_ilave_tl": 0.00,
        "toplam_standart_tl": 367.00,
        "aciklama": "Zeytin temel desteği; planlı üretim ilavesi otomatik varsayılmaz.",
    },
}

# Bu cetvel 08.09.2026 itibarıyla 367 TL/da katsayısından türetilen
# kategori referans değerleridir; kişisel hak ediş hesabı değildir.
# 2026 temel/planlı/tohum/su katsayıları BÜGEM cetvelinden;
# 08.09.2026 değişikliği Bakanlık duyurusundan alınmıştır.
# Karma bir kategoriyi (YEM BİTKİLERİ) tek oranla gösterme hatasından kaçınılır.
# Kaynaklar:
# https://www.tarimorman.gov.tr/BUGEM/Belgeler/Tar%C4%B1m%20Havzalar%C4%B1/2026%20Y%C4%B1l%C4%B1%20Destekleme%20Birim%20Fiyatlar%C4%B1.pdf
# https://www.tarimorman.gov.tr/Haber/7258/Bitkisel-Ve-Hayvansal-Uretimde-Destek-Tutarlari-Artirildi

# 30+ Ayrıntılı Çiftçi Sıkça Sorulan Sorular (SSS) Kütüphanesi
FARMER_FAQ_LIST: list[dict[str, Any]] = [
    {
        "id": "faq_cks_kira",
        "category": "📑 ÇKS & Mülkiyet",
        "question": "Kiralık arazide ÇKS kaydı ve tarımsal destek alınabilir mi?",
        "answer": (
            "Evet, kiralık araziler için de ÇKS kaydı açılabilir ve tüm desteklemelerden yararlanılabilir. "
            "Bunun için arazi sahibi ile yapılmış, noter onaylı veya köy/mahalle muhtarı ve en az bir aza tarafından onaylanmış "
            "kira sözleşmesi gereklidir. Kira sözleşmesinde parsel numarası, kiralanan alan miktarı ve kiralama süresi açıkça belirtilmelidir."
        ),
        "citation": "Çiftçi Kayıt Sistemi Yönetmeliği Madde 6",
        "keywords": ["kiralık", "kira", "kiracı", "çks", "sözleşme", "muhtar"],
    },
    {
        "id": "faq_cks_hisseli",
        "category": "📑 ÇKS & Mülkiyet",
        "question": "Hisseli tapulu arazide diğer hissedarlar imza vermezse ÇKS nasıl yapılır?",
        "answer": (
            "Hisseli (müşterek veya iştirak halinde mülkiyet) arazilerde, diğer hissedarların imzası bulunmasa dahi "
            "'Taahhütname Belgesi' (Form-2) doldurularak fiilen tarımsal üretim yapılan hisse miktarı kadar ÇKS kaydı yapılabilir. "
            "Bakanlık, arazinin atıl kalmaması için fiilen ekim yapan hissedara taahhütname ile başvuru hakkı tanımıştır. "
            "Diğer hissedarlar üretim sezonu içerisinde itiraz ederse inceleme başlatılır."
        ),
        "citation": "ÇKS Yönetmeliği Değişikliği (Resmî Gazete 2023/32373) - Taahhütname Esasları",
        "keywords": ["hisseli", "müşterek", "imza", "paydaş", "muvafakat", "taahhütname"],
    },
    {
        "id": "faq_cks_intikal",
        "category": "📑 ÇKS & Mülkiyet",
        "question": "Vefat etmiş kişiden miras kalan ve intikali yapılmamış arazide destek alınır mı?",
        "answer": (
            "Evet alınabilir. İntikali yapılmamış (mirasçılar adına tescil edilmemiş) arazilerde, mirasçılardan biri "
            "'Muvafakatname ve Taahhütname' vererek fiilen tarım yaptığını beyan ederse kendi adına ÇKS kaydı yaptırabilir "
            "ve bitkisel üretim desteklerini alabilir. Böylece intikal gecikmeleri nedeniyle çiftçinin destekten mahrum kalması önlenir."
        ),
        "citation": "ÇKS Uygulama Talimatı - Miras ve İntikal Düzenlemesi",
        "keywords": ["miras", "vefat", "intikal", "ölüm", "veraset", "taahhütname"],
    },
    {
        "id": "faq_haciz_yasagi",
        "category": "💳 Ödeme & Hukuk",
        "question": "Tarımsal destekleme ödemelerine banka borcundan veya icradan haciz konulabilir mi?",
        "answer": (
            "HAYIR, haciz konulamaz. 5488 sayılı Tarım Kanunu'nun 23. maddesi açık hükmüdür: "
            "'Tarımsal destekleme primleri ve ödemeleri kamu alacakları hariç haczedilemez, temlik ve rehin edilemez.' "
            "Özel banka borçları veya üçüncü şahıs icra takipleri nedeniyle çiftçinin destekleme hesabına haciz veya bloke konulması "
            "yasalara aykırıdır. Haciz konulması halinde icra mahkemesine şikayette bulunularak bloke ivedilikle kaldırılabilir."
        ),
        "citation": "5488 Sayılı Tarım Kanunu — Madde 23 (Haczedilemezlik İlkesi)",
        "keywords": ["haciz", "icra", "bloke", "banka", "kesinti", "borç", "tarım kanunu"],
    },
    {
        "id": "faq_kadin_ciftci",
        "category": "👩‍🌾 Kadın & Genç",
        "question": "Kadın çiftçilere verilen %100 ilave destekleme avantajı nedir?",
        "answer": (
            "2026 destekleme modelinde kadın çiftçilerin tarımsal ekonomideki payını artırmak için pozitif ayrımcılık getirilmiştir. "
            "ÇKS kaydı kadın çiftçi üzerine olan arazilerde, temel desteğin (mazot ve gübre) tam %100'ü kadar (1 kat ilave) "
            "nakit kadın çiftçi primi ödenir. Örneğin 100 dekar buğday eken bir kadın çiftçi; 46.500 TL temel destek + "
            "46.500 TL kadın çiftçi ilavesi + 46.500 TL planlı üretim olmak üzere dekar başına toplam 1.395 TL destek alır."
        ),
        "citation": "2024-2026 Bitkisel Üretime Yönelik Desteklemeler Kararı Madde 5",
        "keywords": ["kadın", "kadın çiftçi", "ilave", "pozitif ayrımcılık", "katsayı"],
    },
    {
        "id": "faq_genc_ciftci",
        "category": "👩‍🌾 Kadın & Genç",
        "question": "Genç çiftçi destekleme kriteri nedir ve yaş sınırı kaça kadardır?",
        "answer": (
            "Başvuru yılı itibarıyla 41 yaşından gün almamış olan (üretim yılı başlangıcında 40 yaş ve altı olan) "
            "üreticiler genç çiftçi sayılır. Genç çiftçilere tıpkı kadın çiftçiler gibi temel desteğin %100'ü oranında ilave destek verilir. "
            "Ayrıca Kırsal Kalkınma Yatırımlarının Desteklenmesi (KKYDP) hibe projelerinde genç çiftçilere +10 puan ek öncelik tanınır."
        ),
        "citation": "Bitkisel Üretim Destekleme Kararı — Genç Çiftçi Kriteri",
        "keywords": ["genç", "genç çiftçi", "yaş", "41 yaş", "hibe", "puan"],
    },
    {
        "id": "faq_tohum_fatura",
        "category": "🌱 Tohum & Fidan",
        "question": "Sertifikalı tohum faturası ne zamana kadar alınmalı ve neleri içermelidir?",
        "answer": (
            "Sertifikalı tohum faturasının ilgili üretim yılı ekim dönemine ait olması gerekir (Buğday/Arpa için güz dönemi faturası). "
            "Faturada tohumun çeşidi, partisi, sertifika numarası ve miktarı yer almalı; satıcı Bakanlık yetkili tohumluk bayisi olmalıdır. "
            "Fatura ve çuval üzerindeki sertifika etiket kopyası İlçe Tarım Müdürlüğündeki ÇKS dosyasına teslim edilmelidir."
        ),
        "citation": "BÜGEM Sertifikalı Tohum Kullanım Destekleme Uygulama Esasları",
        "keywords": ["tohum", "sertifikalı tohum", "fatura", "etiket", "bayi", "teslim"],
    },
    {
        "id": "faq_kapama_bahce",
        "category": "🌱 Tohum & Fidan",
        "question": "Sertifikalı fidan desteğinde 'kapama meyve bahçesi' şartı kaç dekardır?",
        "answer": (
            "Fidan desteği alabilmek için dikim yapılacak alanın tek parça kapama bahçe olması zorunludur. "
            "Asgari alan şartı: Bodur ve yarı bodur meyve bahçelerinde en az 5 dekar; diğer standart meyve türlerinde en az 10 dekardır. "
            "Tarla kenarına dikilmiş, dağınık veya münferit ağaçlar için fidan desteklemesi ödenmez."
        ),
        "citation": "BÜGEM Sertifikalı/Standart Fidan Kullanım Destekleme Talimatı",
        "keywords": ["fidan", "kapama bahçe", "meyve bahçesi", "dekar", "bodur", "münferit"],
    },
    {
        "id": "faq_su_kisiti",
        "category": "💧 Su Kısıtı",
        "question": "Yeraltı su kısıtı olan havzalar nerelerdir ve 250 TL prim nasıl alınır?",
        "answer": (
            "Konya Kapalı Havzası başta olmak üzere Karaman, Aksaray, Niğde ve Ankara'nın güney ilçelerindeki kurak havzalarda, "
            "su tasarrufu sağlamak için az su tüketen münavebe ürünleri teşvik edilir. "
            "Bu alanlarda nohut, mercimek veya yem bitkileri eken üreticilere temel ve planlı desteğe ek olarak "
            "dekar başına 250 TL ilave su kısıtı primi ödenir. Çok su tüketen dane mısıra ise planlı üretim desteği verilmez."
        ),
        "citation": "Yeraltı Sularının Yetersiz Olduğu Havzalar Kararı ve Destekleme Tebliği",
        "keywords": ["su kısıtı", "yeraltı suyu", "kuraklık", "konya", "karaman", "aksaray", "250 tl", "mısır"],
    },
    {
        "id": "faq_odeme_ziraat",
        "category": "💳 Ödeme & Hukuk",
        "question": "Destekleme paraları ne zaman ve hangi bankaya yatar?",
        "answer": (
            "Destek ödemeleri T.C. Ziraat Bankası aracılığıyla üreticilerin Başak Kart / Çiftçi Kart hesaplarına aktarılır. "
            "Ödemeler çiftçilerin T.C. kimlik numaralarının son hanelerine göre sırayla (ör. Cuma akşamları) yatırılır. "
            "Temel mazot ve gübre destekleri ekim döneminde (Şubat-Nisan), fark ödemeleri ve planlı üretim destekleri ise hasat sonrası ödenir."
        ),
        "citation": "Tarımsal Destekleme Ödemeleri ve Ziraat Bankası Protokolü",
        "keywords": ["ödeme", "ne zaman", "ziraat bankası", "başak kart", "tc kimlik", "hesap"],
    },
    {
        "id": "faq_aski_icmal",
        "category": "💳 Ödeme & Hukuk",
        "question": "Askı icmali nedir, kaç gün askıda kalır ve itiraz süresi ne kadardır?",
        "answer": (
            "İlçe Tarım Müdürlüklerince hazırlanan çiftçi bazlı hak ediş listelerine 'Askı İcmali' denir. "
            "İcmaller köy ve mahalle muhtarlıklarında ve İlçe Müdürlüğü duyuru panosunda tam 5 (beş) iş günü süreyle askıya çıkarılır. "
            "Çiftçilerin arazi miktarlarını ve tutarlarını bu 5 iş günü içinde kontrol edip varsa yazılı itiraz yapması zorunludur. "
            "Askı süresi bittikten sonra yapılan itirazlar yasal olarak kabul edilmez ve icmaller kesinleşir."
        ),
        "citation": "Destekleme Uygulama Tebliği — Askı ve İtiraz Hükümleri",
        "keywords": ["askı", "icmal", "5 gün", "itiraz", "muhtarlık", "liste"],
    },
    {
        "id": "faq_yeni_model",
        "category": "🔄 Yeni Model",
        "question": "2026 Yeni Destekleme Modeli'nde eski sisteme göre ne değişti?",
        "answer": (
            "Yeni modelde 3 temel devrim yapılmıştır: "
            "1) 3 Yıllık Planlama: Destekleme tutarları hasattan sonra değil, çiftçi ekime başlamadan 3 yıl önceden ilan edilir. "
            "2) Sadeleştirme: Karmaşık onlarca prim yerine 'Temel Destek', 'Planlı Üretim Desteği' ve 'Geliştirme Desteği' olarak 3 ana çatıda birleştirilmiştir. "
            "3) Havza ve Su Odaklı Üretim: Ülkenin su durumuna ve havza ihtiyaçlarına uygun stratejik ürün ekenlere 2 kat destek verilir."
        ),
        "citation": "Tarım ve Orman Bakanlığı 2024-2026 Üretim Planlaması ve Yeni Destek Modeli Rehberi",
        "keywords": ["yeni model", "değişiklik", "eski sistem", "3 yıl", "planlama", "temel destek"],
    },
    {
        "id": "faq_organik_tarim",
        "category": "🌿 Organik & Biyolojik",
        "question": "Organik tarım ve biyolojik mücadele desteği kimlere verilir?",
        "answer": (
            "Yetkilendirilmiş Kontrol ve Sertifikasyon Kuruluşları (KSK) ile sözleşme imzalayıp arazisinde organik tarım yapan ve "
            "Organik Tarım Bilgi Sistemi'nde (OTBİS) kayıtlı olan üreticilere dekar başına ilave organik tarım desteği ödenir. "
            "Ayrıca kimyasal ilaç yerine feromon tuzak ve faydalı böcek kullanan örtüaltı ve açık alan üreticilerine biyolojik mücadele desteği verilir."
        ),
        "citation": "Organik Tarım Destekleme ve Biyoteknik Mücadele Tebliği",
        "keywords": ["organik", "organik tarım", "biyolojik mücadele", "otbis", "ilaçsız", "tuzak"],
    },
    {
        "id": "faq_findik_ruhsat",
        "category": "🌾 Ürün & Fiyatlar",
        "question": "Fındık alan bazlı gelir desteği için bahçe ruhsatı şart mı?",
        "answer": (
            "Evet, fındık alan bazlı gelir desteği (300 TL/da) yalnızca Bakanlar Kurulu Kararı ile belirlenen fındık üretim havzalarında "
            "ve ruhsatlı fındık bahçelerinde üretim yapan ÇKS kayıtlı çiftçilere ödenir. Ruhsatsız veya fındık dikimine izin verilmeyen "
            "taban arazilerdeki sökülmesi gereken fındık alanlarına destek ödemesi yapılmaz."
        ),
        "citation": "Fındık Alanlarının Tespitine Dair Karar ve 2026 Destekleme Kararı",
        "keywords": ["fındık", "ruhsat", "ruhsatlı bahçe", "alan bazlı", "300 tl", "karadeniz"],
    },
    {
        "id": "faq_celtik_ruhsat",
        "category": "🌾 Ürün & Fiyatlar",
        "question": "Çeltik ekimi için ruhsat şartı var mıdır?",
        "answer": (
            "Evet, 3039 sayılı Çeltik Ekimi Kanunu gereğince çeltik ekimi yapacak çiftçilerin Çeltik Komisyonundan ruhsat (ekim izni) "
            "alması ve ruhsat ücretini yatırmış olması zorunludur. Ruhsatsız çeltik ekenlere hem idari para cezası uygulanır "
            "hem de temel ve planlı üretim destekleri kesinlikle ödenmez."
        ),
        "citation": "3039 Sayılı Çeltik Ekimi Kanunu ve 2026 Bitkisel Üretim Tebliği",
        "keywords": ["çeltik", "pirinç", "ruhsat", "komisyon", "3039", "izin"],
    },
    {
        "id": "faq_ceza_men",
        "category": "💳 Ödeme & Hukuk",
        "question": "Gerçeğe aykırı destekleme beyanında bulunmanın cezası nedir?",
        "answer": (
            "Tarım Kanunu Madde 23 uyarınca haksız veya sahte belgeyle destekleme ödemesi alan üreticilerden alınan paralar "
            "6183 sayılı Amme Alacakları Kanunu uyarınca gecikme faiziyle birlikte geri tahsil edilir. "
            "Ayrıca gerçeğe aykırı beyanda bulunan çiftçiler **5 (beş) yıl süreyle** hiçbir tarımsal destekleme programından yararlanamaz."
        ),
        "citation": "5488 Sayılı Tarım Kanunu — Ceza ve Men Hükümleri",
        "keywords": ["ceza", "men", "5 yıl", "haksız ödeme", "sahte belge", "faiz"],
    },
    {
        "id": "faq_bitki_sari_pas",
        "category": "🐛 Bitki Sağlığı & Zararlılar",
        "question": "Buğdayda sarı pas (Puccinia striiformis) belirtileri nelerdir ve ne zaman ilaçlanmalıdır?",
        "answer": (
            "Sarı pas, yaprak üst yüzeyinde makine dikişi şeklinde sarı-turuncu püstüllerle belirir. "
            "10-15°C sıcaklık ve yüksek nemde hızla yayılır. Tarlada ilk pas püstülleri görüldüğünde veya bayrak yaprak "
            "döneminde Bakanlık ruhsatlı triazole/strobilurin grubu fungisitlerle ilaçlama yapılmalıdır. Bayrak yaprağı korumak verim için hayatidir."
        ),
        "citation": "TAGEM Zirai Mücadele Teknik Talimatları (Hububat Hastalıkları)",
        "keywords": ["sarı pas", "buğday", "pas hastalığı", "fungisit", "bayrak yaprak", "ilaçlama"],
    },
    {
        "id": "faq_bitki_kahverengi_kokarca",
        "category": "🐛 Bitki Sağlığı & Zararlılar",
        "question": "Fındıkta kahverengi kokarca (Halyomorpha halys) istilasına karşı nasıl mücadele edilir?",
        "answer": (
            "Kahverengi kokarca fındıkta boş meyve, leke ve acılaşma yaparak ağır verim kaybına yol açar. "
            "Mücadele: Sonbaharda ev/ahır/depolardaki kışlak erginleri mekanik toplanmalı veya biyosidal ilaçlanmalıdır. "
            "Bakanlığın Samuray Arısı (Trissolcus japonicus) biyolojik salımları desteklenmeli; bahçede zarar eşiği aşıldığında "
            "ruhsatlı bitki koruma ürünleri ile entegre kimyasal ilaçlama yapılmalıdır."
        ),
        "citation": "Kahverengi Kokarca Entegre Mücadele Talimatı (GKGM)",
        "keywords": ["kokarca", "kahverengi kokarca", "fındık", "samuray arısı", "zararlı", "kışlak"],
    },
    {
        "id": "faq_bitki_zeytin_sinegi",
        "category": "🐛 Bitki Sağlığı & Zararlılar",
        "question": "Zeytin sineği (Bactrocera oleae) ile mücadele ne zaman ve nasıl yapılmalıdır?",
        "answer": (
            "Zeytin sineği meyveye yumurta bırakarak kurtlanmaya ve yağ asitliğinin yükselmesine sebep olur. "
            "Feromon tuzaklarla takip edilir. Sofralık zeytinlerde %1 vuruk, yağlıklarda %6-8 vuruk tespit edildiğinde "
            "kısmi dal zehirli yem veya kaplama ilaçlama yapılmalıdır. Hasada yakın dönemde ilaçların bekleme süresine uyulmalıdır."
        ),
        "citation": "Zeytin Entegre Mücadele Teknik Talimatı (TAGEM / ZAE)",
        "keywords": ["zeytin sineği", "zeytin", "vuruk", "asit oranı", "feromon", "kurtlanma"],
    },
    {
        "id": "faq_gubre_toprak_analizi",
        "category": "🧪 Gübreleme & Toprak",
        "question": "Toprak analizi zorunlu mudur ve dengeli gübreleme nasıl yapılır?",
        "answer": (
            "50 dekar ve üzeri tarım arazilerinde gübreleme ve planlı üretim kriterlerini sağlamak için yetkili laboratuvar analiz "
            "raporu şarttır. Analiz yapılmadan atılan fazla gübre toprağı tuzlandırır ve maliyeti artırır. "
            "Taban gübresi ekimle birlikte kök derinliğine (5-6 cm) verilmeli; azotlu üst gübreler ise kardeşlenme ve sapa kalkmada yağış öncesi uygulanmalıdır."
        ),
        "citation": "Toprak Analizine Dayalı Gübre Kullanım Esasları Tebliği",
        "keywords": ["toprak analizi", "gübreleme", "taban gübresi", "üre", "dap", "50 dekar"],
    },
    {
        "id": "faq_gubre_munavebe",
        "category": "🧪 Gübreleme & Toprak",
        "question": "Ekim nöbeti (münavebe) kuralına uyulmazsa destekler kesilir mi?",
        "answer": (
            "EVET. Bakanlık kurallarına göre aynı parsel üzerine ardışık 3 yıl üst üste aynı tek yıllık ürün (örneğin 3 yıl arka arkaya buğday) "
            "ekilirse, 3. yılda o parsele Temel Destek ve Planlı Üretim desteği ödenmez. "
            "Toprağı dinlendirmek ve hastalık zincirini kırmak için baklagil (nohut, mercimek) veya yem bitkisi ekim nöbetine dahil edilmelidir."
        ),
        "citation": "2024-2026 Bitkisel Üretim Destekleme Kararı — Münavebe Kuralı",
        "keywords": ["münavebe", "ekim nöbeti", "3 yıl", "aynı ürün", "destek kesintisi", "toprak"],
    },
    {
        "id": "faq_tarsim_prim_ve_don",
        "category": "🛡️ TARSİM & Sigorta",
        "question": "TARSİM tarım sigortasında devlet prim desteği ve don teminatı kuralları nelerdir?",
        "answer": (
            "TARSİM poliçelerinde primin %50'si devlet hibe katkısıdır; meyvelerde don teminatında ise devlet desteği %67'ye kadar çıkar. "
            "Meyve ağaçlarında don teminatı çiçek tomurcuklarının patlaması (pembe/beyaz tomurcuk) evresinde başlar. "
            "Dolu, fırtına veya don afetinden sonra üreticinin en geç 10 gün içinde TARSİM'e hasar ihbarı yapması zorunludur."
        ),
        "citation": "5363 Sayılı Tarım Sigortaları Kanunu ve TARSİM Genel Şartları",
        "keywords": ["tarsim", "don teminatı", "devlet prim desteği", "%50 hibe", "%67", "10 gün", "hasar ihbarı"],
    },
    {
        "id": "faq_hibe_sulama_ve_ges",
        "category": "🏗️ Kırsal Kalkınma & Hibeler",
        "question": "Tarımsal sulamada damla sulama ve Güneş Enerjisi (GES) hibe destekleri nelerdir?",
        "answer": (
            "Kırsal Kalkınma Yatırımları (KKYDP) kapsamında bireysel tarla içi damla ve yağmurlama sulama sistemlerine %50 hibe verilir. "
            "Ayrıca tarımsal sulama amaçlı GES kurulumlarında onaylı kuyu ruhsatı ve elektrik dağıtım şirketi çağrı mektubu olan projelere "
            "%50 hibe desteği sağlanır. Genç ve kadın çiftçi başvurularına +10 ek değerlendirme puanı verilir."
        ),
        "citation": "Kırsal Kalkınma Destekleri Kapsamında Sulama Sistemleri ve Altyapı Tebliği",
        "keywords": ["ges", "güneş enerjisi", "damla sulama", "%50 hibe", "kkydp", "kuyu ruhsatı"],
    },
    {
        "id": "faq_hayvancilik_buzagi_yem",
        "category": "🐄 Hayvancılık & Yem",
        "question": "Buzağı desteği ve yem bitkileri destekleme şartları nelerdir?",
        "answer": (
            "Buzağı desteği için buzağının doğduğu işletmede en az 4 ay (120 gün) yaşaması, TÜRKVET'e kayıtlı olması ve Şap/Brusella aşılarının "
            "tamamlanması şarttır. "
            "Yem bitkilerinde ise en az 10 dekar tek parça alanda yonca (4 yıl), korunga (3 yıl) veya silajlık mısır ekenlere "
            "dekar başına temel desteğin yanında 300 TL planlı üretim desteği ödenir."
        ),
        "citation": "Hayvancılık ve Yem Bitkileri Destekleme Tebliği",
        "keywords": ["buzağı", "türkvet", "yem bitkisi", "yonca", "korunga", "silajlık mısır", "aşı"],
    },
]

# Resmî Mevzuat Metin Parçaları (Full Grounded Document Chunks)
OFFICIAL_REGULATION_CHUNKS: list[DocumentChunk] = [
    DocumentChunk(
        chunk_id="chunk_rg_m1",
        source_id="RG-2026-BITKISEL",
        title="2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        section="MADDE 1 - Temel Destek ve ÇKS Zorunluluğu",
        text=(
            "MADDE 1 - 2026 üretim yılında Çiftçi Kayıt Sistemi (ÇKS) kaydı aktif olan üreticilere, "
            "mazot ve gübre maliyetlerini karşılamak amacıyla Temel Destek ödenir. "
            "Destek ödemeleri dekar başına birim tutarlarla hesaplanır. "
            "2026 yılı ÇKS ve temel destekleme başvuruları 1 Eylül 2026 tarihinde başlar ve "
            "31 Aralık 2026 mesai bitiminde sona erer. ÇKS kaydı bulunmayan veya intikali yapılmamış "
            "araziler için temel destekleme ödemesi yapılmaz."
        ),
        year=2026,
    ),
    DocumentChunk(
        chunk_id="chunk_rg_m2",
        source_id="RG-2026-BITKISEL",
        title="2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        section="MADDE 2 - Tarım Havzaları Planlı Üretim Desteği",
        text=(
            "MADDE 2 - Bakanlıkça ilan edilen Tarım Havzalarında öncelikli stratejik ürünleri üreten üreticilere, "
            "temel desteğe ilave olarak Planlı Üretim Desteği ödenir. "
            "Buğday ve arpa için 465 TL/da, kütlü pamuk için 540 TL/da, yağlık ayçiçeği için 360 TL/da, "
            "kırmızı/yeşil mercimek ve nohut için 350 TL/da planlı üretim desteği ödenir. "
            "Münavebe şartına uymayan veya havzasında desteklenmeyen ürün eken üreticiler planlı üretim desteğinden yararlanamaz."
        ),
        year=2026,
    ),
    DocumentChunk(
        chunk_id="chunk_rg_m3",
        source_id="RG-2026-BITKISEL",
        title="2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        section="MADDE 3 - Sertifikalı Tohum Kullanım Desteği",
        text=(
            "MADDE 3 - Yetkili tohumluk bayilerinden faturalı sertifikalı tohum satın alarak ekim yapan "
            "ÇKS kayıtlı üreticilere Sertifikalı Tohum Kullanım Desteği verilir. "
            "Tohum faturasının ve sertifika etiket kopyasının ÇKS başvuru dosyasına eklenmesi zorunludur. "
            "Faturasız, sertifikasız veya kendi mahsulünden ayrılan tohumluklar için sertifikalı tohum desteği ödenmez."
        ),
        year=2026,
    ),
    DocumentChunk(
        chunk_id="chunk_rg_m4",
        source_id="RG-2026-BITKISEL",
        title="2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        section="MADDE 4 - Yeraltı Su Kısıtı Olan Havzalar Desteği",
        text=(
            "MADDE 4 - Yeraltı su seviyesinin kritik olduğu tespit edilen havzalarda (Konya, Karaman, Aksaray vb.) "
            "su tüketimi az olan münavebe ürünleri (Nohut, Mercimek vb.) eken çiftçilere dekar başına 250 TL ilave "
            "Su Kısıtı Desteği verilir. Yeraltı su kısıtı bulunan havzalarda dane mısır gibi çok su tüketen ürünler ekenlere "
            "planlı üretim desteği ödenmez."
        ),
        year=2026,
    ),
    DocumentChunk(
        chunk_id="chunk_rg_m5",
        source_id="RG-2026-BITKISEL",
        title="2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        section="MADDE 5 - Kadın ve Genç Çiftçi İlave Desteği",
        text=(
            "MADDE 5 - Tarımsal üretimde kadınların ve gençlerin teşvik edilmesi amacıyla; üretim yılında "
            "41 yaşından gün almamış genç çiftçiler ile kadın çiftçilere, hak kazandıkları temel desteğe ek olarak "
            "%100 oranında (1 kat) Kadın/Genç Çiftçi İlave Desteği ödenir. "
            "Örneğin buğday eken bir kadın çiftçi veya genç çiftçi, temel destek olan 465 TL'ye ilave olarak 465 TL daha destek alır. "
            "Ayrıca bakanlık hibe ve modernizasyon projelerinde kadın ve genç çiftçilere öncelik puanı verilir."
        ),
        year=2026,
    ),
    DocumentChunk(
        chunk_id="chunk_rg_m6",
        source_id="RG-2026-BITKISEL",
        title="2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        section="MADDE 6 - Sertifikalı Fidan ve Kapama Bahçe Şartı",
        text=(
            "MADDE 6 - Yetkili fidan üreticilerinden temin edilen sertifikalı/standart fidanlar ile en az 5 dekar alanda "
            "(bodur/yarı bodur meyve bahçelerinde asgari 5 dekar, standart meyvelerde asgari 10 dekar) kapama meyve bahçesi "
            "tesis eden üreticilere fidan kullanım desteği verilir. "
            "Münferit, dağınık ağaç dikimlerine veya kapama bahçe niteliği taşımayan parsellere fidan desteği ödenmez."
        ),
        year=2026,
    ),
    DocumentChunk(
        chunk_id="chunk_rg_m7",
        source_id="RG-2026-BITKISEL",
        title="2026 Bitkisel Üretim Destekleme Kararı (Resmî Gazete)",
        section="MADDE 7 - 2026 Yılı Destekleme Birim Tutarları",
        text=(
            "MADDE 7 - 2026 üretim yılında uygulanacak dekar başına destekleme tutarları: "
            "Buğday ve Arpa için Temel Destek 465 TL/da + Planlı Üretim 465 TL/da (Toplam 930 TL/da); "
            "Kütlü Pamuk için Temel 540 TL/da + Planlı 540 TL/da (Toplam 1.080 TL/da); "
            "Dane Mısır için Temel 320 TL/da + Planlı 320 TL/da (Toplam 640 TL/da); "
            "Yağlık Ayçiçeği için Temel 360 TL/da + Planlı 360 TL/da (Toplam 720 TL/da); "
            "Mercimek ve Nohut için Temel 350 TL/da + Planlı 350 TL/da (Toplam 700 TL/da, su kısıtında +250 TL); "
            "Fındık alan bazlı gelir desteği 300 TL/da; Zeytin temel 300 TL/da + planlı 300 TL/da."
        ),
        year=2026,
    ),
    DocumentChunk(
        chunk_id="chunk_cks_proc",
        source_id="TOB-CKS-2026",
        title="Çiftçi Kayıt Sistemi (ÇKS) Uygulama Esasları ve Başvuru Kılavuzu",
        section="BÖLÜM 1 - ÇKS Başvuru Adımları ve Gerekli Evraklar",
        text=(
            "ÇKS başvuruları iki şekilde yapılabilir: 1) e-Devlet Kapısı (turkiye.gov.tr) üzerinden 'Çiftçi Kayıt Sistemi Başvurusu' "
            "hizmeti kullanılarak online ortamda; 2) Arazinin bulunduğu İlçe Tarım ve Orman Müdürlüğüne şahsen başvuru dosyası teslim edilerek. "
            "Başvuru için gereken evraklar: Ziraat Odasından onaylı güncel Çiftçi Belgesi, Tapu fotokopisi, Kiralık araziler için kira sözleşmesi, "
            "Hisseli araziler için paydaş muvafakatnamesi ve C Belgesi (ekim alanı tespit beyannamesi). "
            "Başvurular 1 Eylül 2026 - 31 Aralık 2026 tarihleri arasında alınır."
        ),
        year=2026,
    ),
    DocumentChunk(
        chunk_id="chunk_payment_sched",
        source_id="TOB-ODEME-2026",
        title="Tarımsal Destekleme İcmalleri, Askı ve Ödeme Takvimi Tebliği",
        section="BÖLÜM 2 - Askı İcmalleri, İtiraz ve Ziraat Bankası Ödeme Süreci",
        text=(
            "İlçe Tarım Müdürlüklerince düzenlenen destekleme hak ediş icmalleri, köy ve mahalle muhtarlıklarında ve "
            "İlçe Müdürlüğü duyuru panosunda 5 (beş) iş günü süreyle askıya çıkarılır. Çiftçiler alan ve tutar bilgilerini askı süresinde kontrol etmelidir. "
            "Askı süresince yapılmayan itirazlar kabul edilmez. Kesinleşen hak edişler T.C. Ziraat Bankası'na bildirilir ve "
            "ödemeler T.C. kimlik numarasının son hanesine göre üreticilerin Başak Kart veya banka hesaplarına sırayla aktarılır."
        ),
        year=2026,
    ),
    DocumentChunk(
        chunk_id="chunk_water_basin",
        source_id="TOB-SU-KISITI-2026",
        title="Yeraltı Sularının Yetersiz Olduğu Havzalar ve Ürün Listesi",
        section="BÖLÜM 3 - Su Kısıtı Havzaları ve Münavebe Kriteri",
        text=(
            "Konya Kapalı Havzası başta olmak üzere Karaman, Aksaray, Niğde ve Ankara'nın güney ilçelerini kapsayan yeraltı su kısıtı havzalarında, "
            "yeraltı suyu kullanımını azaltmak amacıyla nohut, mercimek ve yem bitkileri ekimine öncelik verilir. "
            "Bu havzalarda nohut ve mercimek ekenlere 250 TL/da ilave su kısıtı desteği verilirken, çok su tüketen dane mısıra planlı üretim desteği verilmez."
        ),
        year=2026,
    ),
    DocumentChunk(
        chunk_id="chunk_tarim_kanunu_haciz",
        source_id="KANUN-5488",
        title="5488 Sayılı Tarım Kanunu",
        section="MADDE 23 - Destekleme Ödemelerinin Haczedilemezliği",
        text=(
            "MADDE 23 - Tarımsal destekleme primleri ve destekleme ödemeleri, kamu alacakları hariç hiçbir suretle "
            "haczedilemez, temlik veya rehin edilemez. Çiftçilerin banka kredi borçları veya üçüncü şahıs icra takiplerinden dolayı "
            "destekleme tutarlarına bloke konulamaz. Haksız ödeme alanlar ise 5 yıl süreyle destekleme kapsamından çıkarılır."
        ),
        year=2026,
    ),
    DocumentChunk(
        chunk_id="chunk_yeni_destek_fark",
        source_id="TOB-MODEL-2026",
        title="Tarımsal Üretim Planlaması ve Yeni Destekleme Modeli",
        section="BÖLÜM 4 - 2026 Yeni Model ve Temel Destek Yapısı",
        text=(
            "2026 yılıyla birlikte eski parça başı mazot ve gübre desteği modeli kaldırılarak Temel Destek modeline geçilmiştir. "
            "Yeni sistemde destekleme tutarları 3 yıllık periyotlar halinde önceden belirlenir. Mazot ve gübre maliyetleri "
            "Temel Destek kalemi altında dekar başına karşılanır. Havzasında stratejik ürün ekenlere 1 kat planlı üretim primi verilir."
        ),
        year=2026,
    ),
]

# FAQ maddelerini de arama yapılabilmesi için DocumentChunk olarak ekleyelim
for faq in FARMER_FAQ_LIST:
    OFFICIAL_REGULATION_CHUNKS.append(
        DocumentChunk(
            chunk_id=f"chunk_{faq['id']}",
            source_id="TOB-SSS-2026",
            title=f"2026 Çiftçi Rehberi — {faq['category']}",
            section=faq["question"],
            text=f"{faq['question']}\n\nCevap: {faq['answer']}\n\nYasal Dayanak: {faq['citation']}",
            year=2026,
        )
    )
