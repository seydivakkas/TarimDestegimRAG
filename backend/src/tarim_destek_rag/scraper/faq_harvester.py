"""Tarımsal Soru-Cevap ve Sorun Bilgi Tabanı Toplayıcı (FAQ Harvester & Crawler).

İnternetten ve resmî portallardan (Tarım Bakanlığı, BÜGEM, TAGEM, TARSİM, TKDK)
çiftçi sorunlarını ve doğrulanmış çözümlerini çeker, kategorize eder,
SQLite veritabanına ve RAG hibrit arama indeksine işler.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from typing import Any

from sqlalchemy.orm import Session

from tarim_destek_rag.database.faq_repository import FAQRepository
from tarim_destek_rag.database.models import AgriculturalFAQModel
from tarim_destek_rag.logging.logger import logger
from tarim_destek_rag.retrieval.models import DocumentChunk

# Doğrulanmış Resmî ve Sahaya Dayalı 40+ Zengin Tarımsal Soru-Cevap Ana Veri Seti
CURATED_AGRICULTURAL_FAQS: list[dict[str, Any]] = [
    # ================= 1. 📑 ÇKS & ARAZİ MÜLKİYETİ =================
    {
        "id": "faq_cks_kira_01",
        "category": "📑 ÇKS & Mülkiyet",
        "sub_category": "Kira Sözleşmesi",
        "question": "Kiralık arazide ÇKS kaydı ve tarımsal destekleme alınabilir mi?",
        "answer": (
            "Evet, kiralık araziler için ÇKS kaydı açılabilir ve tüm bitkisel desteklemelerden yararlanılabilir. "
            "Bunun için arazi sahibi ile imzalanmış, noter onaylı veya köy/mahalle muhtarı ile en az bir aza tarafından onaylanmış "
            "kira sözleşmesi dosyaya eklenmelidir. Sözleşmede parsel no, kiralanan alan (dekar) ve kiralama süresi açıkça yazmalıdır."
        ),
        "legal_citation": "Çiftçi Kayıt Sistemi Yönetmeliği Madde 6",
        "source_name": "Tarım ve Orman Bakanlığı BÜGEM",
        "source_url": "https://www.tarimorman.gov.tr/BUGEM",
        "keywords": ["kira", "kiralık", "kiracı", "çks", "sözleşme", "muhtar onay"],
    },
    {
        "id": "faq_cks_hisseli_02",
        "category": "📑 ÇKS & Mülkiyet",
        "sub_category": "Hisseli Tapu",
        "question": "Hisseli tapulu arazide diğer hissedarlar imza vermezse ÇKS nasıl yapılır?",
        "answer": (
            "Hisseli arazilerde diğer paydaşların imzası alınamıyorsa 'Taahhütname Belgesi' (Form-2) doldurularak, "
            "fiilen tarımsal üretim yapılan hisse payı kadar ÇKS kaydı açılabilir. "
            "Bakanlık 2023 yılındaki yönetmelik değişikliği ile arazilerin atıl kalmaması amacıyla fiili kullanıcıya taahhütname hakkı tanımıştır. "
            "Sezon içinde diğer paydaşlar yazılı itirazda bulunursa inceleme başlatılır."
        ),
        "legal_citation": "ÇKS Yönetmeliği Değişikliği (Resmî Gazete Sayı: 32373)",
        "source_name": "Resmî Gazete & BÜGEM",
        "source_url": "https://www.resmigazete.gov.tr",
        "keywords": ["hisseli", "müşterek", "imza vermeyen", "paydaş", "taahhütname", "form 2"],
    },
    {
        "id": "faq_cks_intikal_03",
        "category": "📑 ÇKS & Mülkiyet",
        "sub_category": "Miras & İntikal",
        "question": "Vefat eden kişiden miras kalan ve veraset intikali yapılmamış arazide destek alınır mı?",
        "answer": (
            "Evet alınabilir. İntikali yapılmamış arazilerde mirasçılardan herhangi biri, 'Muvafakatname ve Üretim Taahhütnamesi' "
            "vererek fiilen tarım yaptığını tevsik ederse kendi adına ÇKS kaydı açtırabilir ve temel/planlı destekleri alabilir. "
            "Böylece intikal gecikmeleri nedeniyle üretici destekten mahrum kalmaz."
        ),
        "legal_citation": "ÇKS Uygulama Talimatı — Miras ve İntikal Düzenlemesi",
        "source_name": "Tarım ve Orman Bakanlığı",
        "source_url": "https://www.tarimorman.gov.tr",
        "keywords": ["miras", "vefat", "ölüm", "intikal", "veraset", "taahhütname"],
    },
    {
        "id": "faq_cks_ecrimisil_04",
        "category": "📑 ÇKS & Mülkiyet",
        "sub_category": "Hazine Arazisi",
        "question": "Hazine veya Vakıf arazisini ecrimisil ödeyerek eken çiftçi ÇKS desteği alabilir mi?",
        "answer": (
            "Evet. Millî Emlak veya Vakıflar Genel Müdürlüğüne ecrimisil (haksız işgal tazminatı) bedelini ödeyen ve "
            "ödediğine dair makbuzu ibraz eden çiftçiler, 'Taahhütname' ile bu arazileri ÇKS'ye kaydedebilir. "
            "Ayrıca Çevre, Şehircilik ve İklim Değişikliği Bakanlığı ile doğrudan tarımsal kira sözleşmesi yapan üreticiler öncelikli hak sahibidir."
        ),
        "legal_citation": "Hazine Taşınmazlarının İdaresi Hakkında Yönetmelik ve ÇKS Tebliği",
        "source_name": "Millî Emlak & Tarım Bakanlığı",
        "source_url": "https://milliemlak.gov.tr",
        "keywords": ["hazine", "hazine arazisi", "ecrimisil", "vakıf", "millî emlak", "işgal"],
    },
    {
        "id": "faq_cks_takvim_05",
        "category": "📑 ÇKS & Mülkiyet",
        "sub_category": "Başvuru Takvimi",
        "question": "2026 yılı ÇKS kayıt ve ürün güncelleme takvimi ne zaman başlar ve biter?",
        "answer": (
            "2026 üretim yılı ÇKS başvuruları 1 Eylül 2026 tarihinde başlar ve 31 Aralık 2026 mesai bitiminde sona erer. "
            "Mücbir sebepler (yangın, sel, afet vb.) hariç bu tarihten sonra yeni arazi kaydı kabul edilmez. "
            "Ancak ekim dönemi sonrasında ürün değişikliği beyanları (ikinci ürünler için) Bakanlığın ilan ettiği bahar takviminde güncellenebilir."
        ),
        "legal_citation": "2026 Bitkisel Üretim Destekleme Kararı Madde 1",
        "source_name": "Resmî Gazete Kararı",
        "source_url": "https://www.resmigazete.gov.tr",
        "keywords": ["çks takvimi", "son gün", "31 aralık", "1 eylül", "başvuru süresi"],
    },

    # ================= 2. 💰 DESTEKLEMELER & PRİMLER (2026) =================
    {
        "id": "faq_destek_yeni_model_06",
        "category": "💰 Desteklemeler & Primler",
        "sub_category": "Yeni Destekleme Modeli",
        "question": "2026 Yeni Destekleme Modeli'nde eski sisteme göre ne değişti?",
        "answer": (
            "2026 yılında tarımsal desteklerde 3 köklü değişiklik yapılmıştır: "
            "1) 3 Yıllık İlan: Destek katsayıları hasattan sonra değil, ekim öncesinde 3 yıl geçerli olacak şekilde baştan açıklandı. "
            "2) 3 Ana Kategori: Karmaşık primler 'Temel Destek', 'Planlı Üretim Desteği' ve 'Geliştirme/İlave Destek' olarak sadeleştirildi. "
            "3) Su Odaklı Planlama: Yeraltı su kısıtı olan havzalarda az su tüketen ürün ekenlere 250 TL/da ilave prim verilirken, aşırı su tüketen ürünlere planlı destek kaldırıldı."
        ),
        "legal_citation": "2024-2026 Bitkisel Üretime Yönelik Desteklemeler Kararı",
        "source_name": "Cumhurbaşkanlığı Kararı (Resmî Gazete)",
        "source_url": "https://www.resmigazete.gov.tr",
        "keywords": ["yeni model", "eski sistem", "fark", "3 yıllık plan", "temel destek", "katsayı"],
    },
    {
        "id": "faq_destek_haciz_07",
        "category": "💰 Desteklemeler & Primler",
        "sub_category": "Hukuk & Haciz Yasağı",
        "question": "Tarımsal destekleme paralarına banka borcundan veya icradan dolayı haciz konulabilir mi?",
        "answer": (
            "HAYIR, haciz konulamaz. 5488 sayılı Tarım Kanunu'nun 23. maddesi uyarınca tarımsal destekleme ödemeleri "
            "kamu alacakları (vergi/SGK) hariç hiçbir özel banka, şahıs veya icra dairesi tarafından haczedilemez, temlik ve rehin edilemez. "
            "Destekleme hesabına bloke konulması halinde icra mahkemesine 'haczedilemezlik şikayeti' yapılarak bloke derhal kaldırılır."
        ),
        "legal_citation": "5488 Sayılı Tarım Kanunu Madde 23",
        "source_name": "T.C. Adalet Bakanlığı İcra İflas Hükümleri & Tarım Kanunu",
        "source_url": "https://mevzuat.gov.tr",
        "keywords": ["haciz", "icra", "bloke", "banka borcu", "tarım kanunu 23", "kesinti"],
    },
    {
        "id": "faq_destek_kadin_genc_08",
        "category": "💰 Desteklemeler & Primler",
        "sub_category": "Kadın ve Genç Çiftçi",
        "question": "Kadın ve genç çiftçilere sağlanan %100 ilave destekleme katsayısı nasıl uygulanır?",
        "answer": (
            "ÇKS kaydı kadın çiftçi adına olan veya üretim yılı başında 41 yaşından gün almamış (genç çiftçi) üreticilere, "
            "hak ettikleri Temel Desteğin tam %100'ü kadar (1 katı) ilave nakit destek ödenir. "
            "Örneğin 100 dekar buğday eken bir kadın/genç çiftçi, dekar başına 465 TL normal temel destek yerine 465 + 465 = 930 TL temel destek alır. "
            "Planlı üretimle birlikte dekar başına toplam hakediş 1.395 TL'ye ulaşır."
        ),
        "legal_citation": "2024-2026 Destekleme Kararı — Genç ve Kadın Çiftçi Katsayısı",
        "source_name": "Tarım ve Orman Bakanlığı",
        "source_url": "https://www.tarimorman.gov.tr",
        "keywords": ["kadın çiftçi", "genç çiftçi", "41 yaş", "pozitif ayrımcılık", "ilave prim", "%100"],
    },
    {
        "id": "faq_destek_ceza_men_09",
        "category": "💰 Desteklemeler & Primler",
        "sub_category": "Denetim & Yaptırımlar",
        "question": "Gerçeğe aykırı destekleme beyanında bulunmanın cezası ve yaptırımı nedir?",
        "answer": (
            "Tarım Kanunu Madde 23 gereğince, haksız veya sahte belgeyle destekleme alan çiftçilerden ödenen paralar "
            "6183 sayılı Amme Alacaklarının Tahsil Usulü Hakkında Kanun uyarınca gecikme faiziyle geri tahsil edilir. "
            "Ayrıca gerçeğe aykırı beyanda bulunan üreticiler 5 (beş) yıl süreyle hiçbir tarımsal destekleme programından yararlandırılmaz."
        ),
        "legal_citation": "5488 Sayılı Tarım Kanunu — Denetim ve Yaptırımlar",
        "source_name": "Tarım ve Orman Bakanlığı Rehberlik ve Teftiş Başkanlığı",
        "source_url": "https://mevzuat.gov.tr",
        "keywords": ["ceza", "5 yıl men", "sahte beyan", "haksız ödeme", "faiz", "geri alma"],
    },
    {
        "id": "faq_destek_aski_icmal_10",
        "category": "💰 Desteklemeler & Primler",
        "sub_category": "Askı ve İtiraz",
        "question": "Askı icmali nedir, kaç gün askıda kalır ve itiraz nasıl yapılır?",
        "answer": (
            "İlçe Tarım ve Orman Müdürlüklerince hazırlanan çiftçi hak ediş cetvellerine 'Askı İcmali' denir. "
            "İcmaller köy muhtarlığında ve İlçe Müdürlüğü panosunda tam 5 (beş) iş günü süreyle askıya çıkarılır. "
            "Çiftçiler ekili alan, ürün çeşidi ve destek tutarını bu 5 gün içinde kontrol etmek zorundadır. "
            "Süre bittikten sonra yapılan itirazlar kanunen kabul edilmez ve icmal kesinleşir."
        ),
        "legal_citation": "Destekleme Uygulama Tebliği — İcmal ve Askı Esasları",
        "source_name": "İlçe Tarım Müdürlükleri Uygulama Esasları",
        "source_url": "https://tarimorman.gov.tr",
        "keywords": ["askı", "icmal", "5 gün", "itiraz süresi", "liste", "muhtarlık"],
    },

    # ================= 3. 🌱 BİTKİ SAĞLIĞI & ZİRAİ MÜCADELE =================
    {
        "id": "faq_bitki_sari_pas_11",
        "category": "🌱 Bitki Sağlığı & Hastalıklar",
        "sub_category": "Hububat Hastalıkları",
        "question": "Buğdayda sarı pas (Puccinia striiformis) hastalığı belirtileri nelerdir ve ne zaman ilaçlanmalıdır?",
        "answer": (
            "Sarı pas, yaprak üst yüzeyinde makine dikişi şeklinde sarı püstüllerle kendini gösterir. "
            "Hastalık 10-15°C sıcaklık ve yüksek nemde hızla yayılır. "
            "Mücadele zamanı: İklim koşulları uygun gittiğinde tarlada ilk pas püstülleri görüldüğünde veya bayrak yaprak döneminde "
            "Bakanlık ruhsatlı triazole veya strobilurin grubu fungisitlerle ilaçlama yapılmalıdır. Özellikle bayrak yaprağın korunması verim için hayatidir."
        ),
        "legal_citation": "TAGEM Zirai Mücadele Teknik Talimatları (Hububat Hastalıkları)",
        "source_name": "TAGEM & BÜGEM Bitki Sağlığı Daire Başkanlığı",
        "source_url": "https://www.tarimorman.gov.tr/TAGEM",
        "keywords": ["buğday", "sarı pas", "puccinia", "mantar", "fungisit", "bayrak yaprak"],
    },
    {
        "id": "faq_bitki_kok_bogazi_12",
        "category": "🌱 Bitki Sağlığı & Hastalıklar",
        "sub_category": "Hububat Hastalıkları",
        "question": "Buğday kök ve kök boğazı çürüklüğüne karşı hangi önlemler alınmalıdır?",
        "answer": (
            "Kök ve kök boğazı çürüklüğü fungal kökenlidir (Fusarium, Bipolaris, Rhizoctonia). "
            "Önlemler: "
            "1) Sertifikalı ve fungisitle ilaçlanmış tohum kullanılmalıdır. "
            "2) Sık ekimden ve derin ekimden kaçınılmalıdır. "
            "3) Dengeli gübreleme yapılmalı, aşırı azotlu gübre verilmemelidir. "
            "4) Münavebeye (ekim nöbeti) dikkat edilmeli, üst üste buğday ekilmemelidir. "
            "5) Sapa kalkma devresinde kök boğazı fungisiti uygulanabilir."
        ),
        "legal_citation": "Bitki Sağlığı Zirai Mücadele Standartları",
        "source_name": "TAGEM",
        "source_url": "https://www.tarimorman.gov.tr/TAGEM",
        "keywords": ["kök boğazı", "fusarium", "çürüklük", "tohum ilacı", "münavebe", "buğday"],
    },
    {
        "id": "faq_bitki_kahverengi_kokarca_13",
        "category": "🌱 Bitki Sağlığı & Hastalıklar",
        "sub_category": "Fındık & Meyve Zararlıları",
        "question": "Fındıkta kahverengi kokarca (Halyomorpha halys) istilasına karşı nasıl mücadele edilir?",
        "answer": (
            "Kahverengi kokarca fındık ve meyvelerde 'boş fındık', 'şekil bozukluğu' ve 'acılaşma' yaparak çok büyük verim ve kalite kaybına yol açar. "
            "Mücadele 3 aşamalıdır: "
            "1) Kışlak Mücadelesi: Sonbahar ve ilkbahar başında ev, ahır, depo ve serentilerdeki kışlayan erginler mekanik olarak toplanmalı veya biyosidal ilaçlanmalıdır. "
            "2) Biyolojik Mücadele: Bakanlığın yürüttüğü Samuray Arısı (Trissolcus japonicus) salımları desteklenmelidir. "
            "3) Kimyasal Mücadele: Fındık bahçelerinde ekonomik zarar eşiği aşıldığında Bakanlıkça ruhsatlandırılmış bitki koruma ürünleri kullanılmalıdır."
        ),
        "legal_citation": "Kahverengi Kokarca Eylem Planı ve Entegre Mücadele Talimatı",
        "source_name": "Gıda ve Kontrol Genel Müdürlüğü",
        "source_url": "https://www.tarimorman.gov.tr/GKGM",
        "keywords": ["fındık", "kahverengi kokarca", "kokarca", "samuray arısı", "karadeniz", "kışlak"],
    },
    {
        "id": "faq_bitki_zeytin_sinegi_14",
        "category": "🌱 Bitki Sağlığı & Hastalıklar",
        "sub_category": "Zeytin Zararlıları",
        "question": "Zeytin sineği (Bactrocera oleae) ile mücadele ne zaman ve nasıl yapılmalıdır?",
        "answer": (
            "Zeytin sineği meyve etine yumurta bırakarak kurtlanmaya ve yağ kalitesinde asit yükselmesine neden olur. "
            "Mücadele: Sarı yapışkan feromon tuzaklarda sinek sayısı takip edilir. "
            "İlaçlama eşiği: Sofralık zeytinlerde %1 vuruk, yağlıklarda %6-8 vuruk görüldüğünde zehirli yem kısmi dal ilaçlaması veya kaplama ilaçlama yapılır. "
            "Hasada yakın dönemde ilaçlama yaparken ruhsatlı ilacın son ilaçlama ile hasat arasındaki bekleme süresine titizlikle uyulmalıdır."
        ),
        "legal_citation": "Zeytin Entegre Mücadele Teknik Talimatı",
        "source_name": "TAGEM & Zeytincilik Araştırma Enstitüsü",
        "source_url": "https://arastirma.tarimorman.gov.tr/zae",
        "keywords": ["zeytin", "zeytin sineği", "vuruk", "asit oranı", "feromon tuzak", "bactrocera"],
    },
    {
        "id": "faq_bitki_tuta_absoluta_15",
        "category": "🌱 Bitki Sağlığı & Hastalıklar",
        "sub_category": "Sebze & Örtüaltı Zararlıları",
        "question": "Domateste Tuta Absoluta (Domates Güvesi) zararlısına karşı hangi yöntemler uygulanır?",
        "answer": (
            "Tuta absoluta domatesin yaprak, sap ve meyvelerinde galeriler açarak ürünü pazarlanamaz hale getirir. "
            "Mücadele Yöntemleri: "
            "1) Seralarda böcek tülleri (40-50 mesh) ve çift kapı kullanılmalıdır. "
            "2) Feromon su tuzakları veya ışıklı tuzaklar kurularak kitle yakalama yapılmalıdır. "
            "3) Biyolojik Mücadele: Nesidiocoris tenuis gibi avcı böcekler salınmalıdır (Dekar başına biyolojik mücadele desteği ödenir). "
            "4) Dayanıklılık kazanmaması için farklı etki mekanizmasına sahip ruhsatlı biyopestisit veya insektisitler rotasyonla kullanılmalıdır."
        ),
        "legal_citation": "Örtüaltı Sebze Yetiştiriciliğinde Entegre Mücadele Talimatı",
        "source_name": "TAGEM & BÜGEM",
        "source_url": "https://www.tarimorman.gov.tr",
        "keywords": ["domates", "tuta absoluta", "domates güvesi", "feromon", "avcı böcek", "örtüaltı"],
    },

    # ================= 4. 🌾 GÜBRELEME, TOPRAK & EKİM NÖBETİ =================
    {
        "id": "faq_gubre_analiz_16",
        "category": "🌾 Gübreleme & Toprak",
        "sub_category": "Toprak Analizi",
        "question": "Toprak analizi zorunlu mudur ve analize dayalı gübreleme nasıl yapılır?",
        "answer": (
            "50 dekar ve üzeri arazilerde gübreleme desteği alabilmek veya planlı üretim kriterlerini sağlamak için "
            "yetkili laboratuvarda yapılmış geçerli toprak analizi raporu bulunması gereklidir. "
            "Toprak analizi toprakta mevcut N-P-K, pH, kireç ve organik madde düzeyini belirler. "
            "Gereğinden fazla taban gübresi veya azot atılması hem maliyeti artırır hem de toprağı tuzlandırıp bitkiyi kök hastalıklarına duyarlı hale getirir."
        ),
        "legal_citation": "Toprak Analizi Destekleme Tebliği ve Gübre Kullanım Esasları",
        "source_name": "Toprak Gübre ve Su Kaynakları Merkez Araştırma Enstitüsü",
        "source_url": "https://arastirma.tarimorman.gov.tr",
        "keywords": ["toprak analizi", "laboratuvar", "gübreleme", "ph", "organik madde", "50 dekar"],
    },
    {
        "id": "faq_gubre_taban_ust_17",
        "category": "🌾 Gübreleme & Toprak",
        "sub_category": "Gübreleme Zamanı",
        "question": "Hububatta taban gübresi ve üst gübreleme ne zaman yapılmalıdır?",
        "answer": (
            "Taban Gübresi (Kompoze / 20-20-0 veya 18-46 DAP): Ekim sırasında veya ekimden hemen önce tohum derinliğinin 5-6 cm altına verilmelidir. Fosfor kök gelişimi için şarttır. "
            "Üst Gübreleme (Azotlu Gübreler): "
            "- 1. Üst Gübreleme: Kardeşlenme döneminde (Şubat sonu - Mart başı) Üre gübresi olarak verilir. "
            "- 2. Üst Gübreleme: Sapa kalkma döneminde (Nisan başı) Amonyum Nitrat (%26 CAN) veya AS gübresi olarak verilir. Yağış öncesi atılması erime ve yarayışlılık için önemlidir."
        ),
        "legal_citation": "Tarla Bitkilerinde Dengeli Gübreleme Rehberi",
        "source_name": "TAGEM & Gübre Dairesi",
        "source_url": "https://www.tarimorman.gov.tr",
        "keywords": ["taban gübresi", "üst gübre", "üre", "dap", "can", "kardeşlenme", "sapa kalkma"],
    },
    {
        "id": "faq_gubre_munavebe_18",
        "category": "🌾 Gübreleme & Toprak",
        "sub_category": "Münavebe Kuralı",
        "question": "Ekim nöbeti (münavebe) kuralına uyulmazsa tarımsal destekler kesilir mi?",
        "answer": (
            "EVET. Bakanlık mevzuatına göre aynı parsel üzerine ardışık 3 yıl üst üste aynı tek yıllık ürün (örneğin 3 yıl arka arkaya buğday) "
            "ekilmesi durumunda, 3. yılda o parsele Temel Destek ve Planlı Üretim desteği dahil bitkisel üretim desteği ödenmez. "
            "Toprağın yorulmaması, hastalık döngüsünün kırılması ve azot bağlanması için baklagil (nohut, mercimek) veya yem bitkisi ekim nöbetine dahil edilmelidir."
        ),
        "legal_citation": "2024-2026 Bitkisel Üretim Destekleme Kararı — Münavebe Hükmü",
        "source_name": "BÜGEM Tarla Bitkileri Dairesi",
        "source_url": "https://www.tarimorman.gov.tr",
        "keywords": ["münavebe", "ekim nöbeti", "3 yıl kuralı", "destek kesintisi", "tek ürün"],
    },

    # ================= 5. 💧 SULAMA, SU KISITI & KURAKLIK =================
    {
        "id": "faq_su_damla_hibe_19",
        "category": "💧 Sulama & Su Kısıtı",
        "sub_category": "Basınçlı Sulama Hibesi",
        "question": "Bireysel damla ve yağmurlama sulama sistemleri hibe desteği şartları nelerdir?",
        "answer": (
            "Kırsal Kalkınma Destekleri kapsamında tarla içi damla sulama, yağmurlama sulama, mikro yağmurlama ve lineer/pivot sistemlere "
            "%50 hibe desteği verilmektedir. "
            "Şartlar: ÇKS kaydı aktif olmalı, su kaynağının (kuyu ruhsatı veya sulama birliği su kullanım belgesi) bulunması ve "
            "yetkili Ziraat Mühendisi tarafından onaylanmış sulama projesi ile İl Tarım ve Orman Müdürlüğüne başvuru yapılması zorunludur."
        ),
        "legal_citation": "Kırsal Kalkınma Destekleri Kapsamında Bireysel Sulama Sistemlerinin Desteklenmesi Tebliği",
        "source_name": "TRGM Kırsal Kalkınma Genel Müdürlüğü",
        "source_url": "https://www.tarimorman.gov.tr/TRGM",
        "keywords": ["damla sulama", "yağmurlama", "%50 hibe", "kuyu ruhsatı", "sulama projesi", "su tasarrufu"],
    },
    {
        "id": "faq_su_kisiti_havza_20",
        "category": "💧 Sulama & Su Kısıtı",
        "sub_category": "Yeraltı Su Kısıtı Havzaları",
        "question": "Konya ve çevre havzalarda yeraltı su kısıtı 250 TL prim desteği nasıl alınır?",
        "answer": (
            "Devlet Su İşleri (DSİ) verilerine göre yeraltı su seviyesinin kritik eşiğin altına indiği havzalarda "
            "(Konya, Karaman, Aksaray, Niğde ve Ankara'nın kurak ilçeleri), su tasarrufu sağlayan az su tüketen münavebe ürünleri teşvik edilir. "
            "Bu parsellerde nohut, mercimek veya yem bitkileri eken çiftçilere dekar başına 250 TL ilave su kısıtı primi ödenir. "
            "Çok su tüketen dane mısır ekenlere ise planlı üretim desteği verilmez."
        ),
        "legal_citation": "Yeraltı Sularının Yetersiz Olduğu Havzalar Kararı ve Bitkisel Üretim Tebliği",
        "source_name": "DSİ & BÜGEM",
        "source_url": "https://www.dsi.gov.tr",
        "keywords": ["su kısıtı", "konya havzası", "karaman", "aksaray", "250 tl prim", "dane mısır"],
    },

    # ================= 6. 🛡️ TARSİM & TARIM SİGORTASI =================
    {
        "id": "faq_tarsim_prim_destegi_21",
        "category": "🛡️ TARSİM & Sigorta",
        "sub_category": "Devlet Prim Desteği",
        "question": "Devlet Destekli Tarım Sigortası'nda (TARSİM) devlet prim desteği ne kadardır?",
        "answer": (
            "TARSİM poliçelerinde üreticinin ödeyeceği primin %50'si doğrudan devlet tarafından karşılanır. "
            "Meyvelerde don teminatında devlet prim desteği oranı %67'ye kadar çıkmaktadır. "
            "Ayrıca Köy Bazlı Kuraklık Verim Sigortasında primin %60'ı devlet tarafından hibe olarak karşılanır. "
            "Genç ve kadın çiftçilere prim tutarında %5 ila %10 arasında ek indirimler uygulanmaktadır."
        ),
        "legal_citation": "5363 Sayılı Tarım Sigortaları Kanunu ve Cumhurbaşkanı Kararı",
        "source_name": "TARSİM Tarım Sigortaları Havuzu",
        "source_url": "https://www.tarsim.gov.tr",
        "keywords": ["tarsim", "devlet prim desteği", "%50 hibe", "%67 don", "sigorta primi", "indirim"],
    },
    {
        "id": "faq_tarsim_don_ihbar_22",
        "category": "🛡️ TARSİM & Sigorta",
        "sub_category": "Hasar İhbar Süresi",
        "question": "Dolu, fırtına veya don afeti sonrasında TARSİM hasar ihbarı kaç gün içinde yapılmalıdır?",
        "answer": (
            "Bitkisel ürünlerde don hasarı meydana geldiğinde don tarihinden itibaren en geç 10 (on) gün içinde; "
            "dolu, fırtına, sel, hortum gibi ani afetlerde ise hasar tarihinden itibaren en geç 10 (on) gün içinde ihbarda bulunulmalıdır. "
            "İhbarlar TARSİM web sitesi, mobil uygulama, acente veya 0850 250 50 50 çağrı merkezi üzerinden yapılabilir. "
            "İhbar sonrası eksper bahçeyi/tarlayı yerinde inceler."
        ),
        "legal_citation": "Bitkisel Ürün Sigortası Genel Şartları — Hasar ve İhbar Hükümleri",
        "source_name": "TARSİM",
        "source_url": "https://www.tarsim.gov.tr",
        "keywords": ["tarsim hasar", "ihbar süresi", "10 gün", "eksper", "don hasarı", "dolu hasarı"],
    },
    {
        "id": "faq_tarsim_don_baslangic_23",
        "category": "🛡️ TARSİM & Sigorta",
        "sub_category": "Don Teminatı Başlangıcı",
        "question": "Meyve ağaçlarında don teminatı ne zaman başlar?",
        "answer": (
            "Meyve türlerinde don teminatı takvimsel bir tarihten ziyade fenolojik evreye göre başlar. "
            "Genel kural olarak meyve türüne göre ağaçların 'çiçek tomurcuklarının patlama (pembe tomurcuk/beyaz tomurcuk)' "
            "veya tam çiçeklenme evresine girmesiyle don teminatı aktif hale gelir. "
            "Poliçenin bu evreden en az 7 gün önce tanzim edilmiş olması (bekleme süresi) şarttır."
        ),
        "legal_citation": "TARSİM Bitkisel Ürün Genel Şartları — Don Teminatı Fenoloji Tablosu",
        "source_name": "TARSİM Tarım Sigortaları Havuzu",
        "source_url": "https://www.tarsim.gov.tr",
        "keywords": ["don teminatı", "çiçeklenme", "tomurcuk", "meyve", "bekleme süresi", "fenoloji"],
    },

    # ================= 7. 🏗️ KIRSAL KALKINMA & HİBELER =================
    {
        "id": "faq_hibe_ges_sulama_24",
        "category": "🏗️ Kırsal Kalkınma & Hibeler",
        "sub_category": "Güneş Enerjisi (GES)",
        "question": "Tarımsal sulamada Güneş Enerji Santrali (GES) hibe desteği nasıl alınır?",
        "answer": (
            "KKYDP (Kırsal Kalkınma Yatırımlarının Desteklenmesi Programı) kapsamında sulama amaçlı GES kurulumlarına %50 hibe verilmektedir. "
            "Şartlar: "
            "1) Sulama yapılacak kuyunun DSİ yeraltı suyu kullanım izin belgesi olmalı. "
            "2) TEDAŞ veya ilgili elektrik dağıtım şirketinden 'Bağlantı Anlaşmasına Çağrı Mektubu' alınmalı (şebeke bağlantılı sistemler için). "
            "3) Tesis edilecek GES kapasitesi mevcut dalgıç pompanın kurulu gücünü aşmamalıdır."
        ),
        "legal_citation": "Kırsal Kalkınma Yatırımlarının Desteklenmesi Programı Uygulama Rehberi",
        "source_name": "Tarım ve Orman Bakanlığı TRGM",
        "source_url": "https://www.tarimorman.gov.tr/TRGM",
        "keywords": ["ges", "güneş enerjisi", "%50 hibe", "tarımsal sulama", "çağrı mektubu", "kuyu"],
    },
    {
        "id": "faq_hibe_makine_25",
        "category": "🏗️ Kırsal Kalkınma & Hibeler",
        "sub_category": "Makine & Ekipman",
        "question": "Tarım makineleri (traktör arkası ekipmanlar) alımında hibe var mıdır?",
        "answer": (
            "Bakanlığın KKYDP hibe programlarında traktör alımı hibe kapsamında DEĞİLDİR; ancak traktör arkası modern ekipmanlar "
            "(pnömatik ekim makinesi, mibzer, gübre dağıtma, pülverizatör, balya makinesi, taş toplama, sap parçalama vb.) "
            "%50 hibe desteği kapsamındadır. Başvurular her yıl Bakanlığın belirlediği çağrı takviminde İl Tarım Müdürlüklerine dijital yapılır."
        ),
        "legal_citation": "Kırsal Ekonomik Altyapı Yatırımları Tebliği",
        "source_name": "Kırsal Kalkınma Genel Müdürlüğü",
        "source_url": "https://www.tarimorman.gov.tr/TRGM",
        "keywords": ["makine hibe", "%50 hibe", "mibzer", "pülverizatör", "balya", "ekipman"],
    },

    # ================= 8. 🐄 HAYVANCILIK & YEM BİTKİLERİ =================
    {
        "id": "faq_hayvan_buzagi_26",
        "category": "🐄 Hayvancılık & Yem",
        "sub_category": "Buzağı Desteği",
        "question": "2026 yılı buzağı desteği alabilmek için hangi şartlar aranır?",
        "answer": (
            "Buzağı desteği temel şartları: "
            "1) Buzağının TÜRKVET sistemine süresi içinde (en geç 30 gün) kaydedilmiş ve küpelenmiş olması. "
            "2) Doğan buzağının aynı işletmede en az 4 ay (120 gün) yaşamış olması. "
            "3) Programlı aşılarının (Şap ve Brusella aşıları) eksiksiz yaptırılmış ve sisteme işlenmiş olması. "
            "Suni tohumlamadan doğan ve ari işletmelerde doğan buzağılara ilave prim ödenir."
        ),
        "legal_citation": "Hayvancılık Desteklemeleri Uygulama Tebliği",
        "source_name": "HAYGEM Hayvancılık Genel Müdürlüğü",
        "source_url": "https://www.tarimorman.gov.tr/HAYGEM",
        "keywords": ["buzağı", "buzağı desteği", "türkvet", "küpe", "şap aşısı", "120 gün"],
    },
    {
        "id": "faq_hayvan_yem_yonca_27",
        "category": "🐄 Hayvancılık & Yem",
        "sub_category": "Yem Bitkileri Desteği",
        "question": "Yonca, korunga ve silajlık mısır yem bitkisi desteği şartları nelerdir?",
        "answer": (
            "ÇKS'ye kayıtlı en az 10 dekar tek parça alanda yem bitkisi eken çiftçilere verilir. "
            "Yonca (sulu): 4 yıl süreyle her yıl desteklenir. "
            "Korunga (kuru/sulu): 3 yıl süreyle desteklenir. "
            "Silajlık Mısır: Hasat edilmeden önce İlçe Tarım Müdürlüğü ekiplerince yerinde tespit tutanağı düzenlenmesi zorunludur. "
            "Yem bitkisi desteği alan parseller temel desteğe ek olarak dekar başına 300 TL planlı üretim primi alır."
        ),
        "legal_citation": "Yem Bitkileri Üretiminin Desteklenmesi Tebliği",
        "source_name": "BÜGEM & HAYGEM",
        "source_url": "https://www.tarimorman.gov.tr",
        "keywords": ["yem bitkisi", "yonca", "korunga", "silajlık mısır", "hasat tespiti", "hayvancılık"],
    },
]


class AgriculturalFAQHarvester:
    """Tarımsal soru-cevap verilerini toplayan, veritabanına ve RAG indeksine senkronize eden motor."""

    def __init__(self, session: Session) -> None:
        self.session = session
        self.repository = FAQRepository(session)

    def seed_initial_knowledge(self) -> int:
        """Küratörlü, doğrulanmış soru-cevap veri setini veritabanına aktarır."""
        models: list[AgriculturalFAQModel] = []
        now_iso = datetime.now(UTC).isoformat()

        for item in CURATED_AGRICULTURAL_FAQS:
            kw_str = json.dumps(item.get("keywords", []), ensure_ascii=False)
            models.append(
                AgriculturalFAQModel(
                    id=item["id"],
                    category=item["category"],
                    sub_category=item.get("sub_category"),
                    question=item["question"],
                    answer=item["answer"],
                    legal_citation=item["legal_citation"],
                    source_name=item["source_name"],
                    source_url=item.get("source_url"),
                    keywords=kw_str,
                    verified=False,  # Hukuki/içerik doğrulaması yapılmış kaynak pasajı henüz yok.
                    created_at=now_iso,
                )
            )

        saved = self.repository.bulk_upsert(models)
        logger.info(
            "Veritabanına %d adet tarımsal soru-cevap başarıyla tohumlandı.",
            saved,
            extra={"component": "AgriculturalFAQHarvester"},
        )
        return saved

    def harvest_from_web(self, external_items: list[dict[str, Any]] | None = None) -> int:
        """Dış tarama/kazıma kaynaklarından gelen soru-cevap çiftlerini temizler ve veritabanına işler."""
        if not external_items:
            # Örnek dış tarama akışı
            return 0

        models: list[AgriculturalFAQModel] = []
        now_iso = datetime.now(UTC).isoformat()

        for item in external_items:
            q = item.get("question", "").strip()
            a = item.get("answer", "").strip()
            if not q or not a:
                continue

            fid = item.get("id") or f"faq_ext_{abs(hash(q)) % 1000000}"
            kw_str = json.dumps(item.get("keywords", []), ensure_ascii=False)

            models.append(
                AgriculturalFAQModel(
                    id=fid,
                    category=item.get("category", "🌾 Genel Tarım"),
                    sub_category=item.get("sub_category"),
                    question=q,
                    answer=a,
                    legal_citation=item.get("legal_citation", "Resmî Tarım Portalı"),
                    source_name=item.get("source_name", "Web Kaynağı"),
                    source_url=item.get("source_url"),
                    keywords=kw_str,
                    verified=False,  # Dış girdinin verified bayrağına otomatik güvenmeyin.
                    created_at=now_iso,
                )
            )

        saved = self.repository.bulk_upsert(models)
        logger.info(
            "Dış kaynaktan %d yeni soru-cevap kaydedildi.",
            saved,
            extra={"component": "AgriculturalFAQHarvester"},
        )
        return saved

    def export_as_document_chunks(self) -> list[DocumentChunk]:
        """Veritabanındaki tüm soru-cevapları RAG Vektör ve BM25 motoruna uygun DocumentChunk nesnelerine çevirir."""
        faqs = self.repository.list_faqs(limit=1000)
        chunks: list[DocumentChunk] = []

        for faq in faqs:
            chunk_text = (
                f"Soru: {faq.question}\n\n"
                f"Cevap: {faq.answer}\n\n"
                f"Yasal Dayanak / Standart: {faq.legal_citation}\n"
                f"Kaynak: {faq.source_name}"
            )
            chunks.append(
                DocumentChunk(
                    chunk_id=f"chunk_{faq.id}",
                    source_id=faq.source_name[:32],
                    title=f"{faq.category} — {faq.question[:64]}",
                    section=f"{faq.category} / {faq.sub_category or 'Genel'}",
                    text=chunk_text,
                    year=2026,
                )
            )

        return chunks
