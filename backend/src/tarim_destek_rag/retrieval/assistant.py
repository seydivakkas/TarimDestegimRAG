"""Tarımsal Destek Mevzuat ve Doğal Dil Soru-Cevap Motoru (Zero-LLM).

Master Plan Bölüm 7 (Structured DB vs. Vector Search) ve Bölüm 11 (RAG Contract)
prensiplerine göre deterministik, kuruş hassasiyetli, kapsamlı ve mevzuat atıflı yanıtlar üretir.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

import re
from typing import Any

from tarim_destek_rag.retrieval.hybrid import HybridRetriever, hybrid_retriever
from tarim_destek_rag.retrieval.knowledge_base import (
    CROP_SUPPORT_CATALOG,
    FARMER_FAQ_LIST,
    OFFICIAL_REGULATION_CHUNKS,
)
from tarim_destek_rag.retrieval.models import DocumentChunk


def turkish_lower_clean(text: str) -> str:
    """Türkçe karakter duyarlı küçük harfe dönüştürür."""
    replacements = {"İ": "i", "I": "ı", "Ğ": "ğ", "Ü": "ü", "Ş": "ş", "Ö": "ö", "Ç": "ç"}
    for upper_ch, lower_ch in replacements.items():
        text = text.replace(upper_ch, lower_ch)
    return text.lower()


class AssistantEngine:
    """Mevzuat, SSS Kütüphanesi ve Yapılandırılmış Destek Verilerini Birleştiren Doğal Dil Motoru."""

    def __init__(self, retriever: HybridRetriever | None = None) -> None:
        self.retriever = retriever or hybrid_retriever
        # İndekste henüz mevzuat parçaları yoksa varsayılan resmî parçaları otomatik yükle
        if hasattr(self.retriever, "bm25_retriever") and len(self.retriever.bm25_retriever._chunks) == 0:
            self.retriever.add_chunks(OFFICIAL_REGULATION_CHUNKS)

    def answer_question(
        self, question: str, top_k: int = 3
    ) -> tuple[str, list[DocumentChunk], list[str]]:
        """Kullanıcı sorusuna hibrit arama, SSS eşleştirme ve deterministik sentezleme ile yanıt üretir."""
        if not question or not question.strip():
            return (
                "Lütfen tarımsal destekler, ÇKS mevzuatı veya hak edişlerle ilgili bir soru giriniz.",
                [],
                [],
            )

        q_clean = turkish_lower_clean(question.strip())

        # 1. Hibrit Arama Yap (Vektör + BM25)
        matches = self.retriever.search(question, top_k=top_k)
        matched_chunks = [m[0] for m in matches]
        source_titles = list({c.title for c in matched_chunks})

        # 2. Deterministik Niyet Analizi (Intent Detection - 0 LLM)
        # Niyet A: Ürün Bazlı Destek Tutarı / Miktarı Sorgusu (16 Ürün Tam Katalog)
        crop_match = self._detect_crop(q_clean)
        is_amount_query = any(
            w in q_clean
            for w in [
                "ne kadar", "kaç", "tutar", "fiyat", "lira", "tl", "miktarı",
                "ücret", "oran", "ödeme", "hesap", "destekleri", "destek", "prim"
            ]
        )

        if crop_match and (is_amount_query or "destek" in q_clean):
            answer_text = self._build_crop_amount_answer(crop_match, q_clean)
            return answer_text, matched_chunks, source_titles

        # Niyet B: Genel ÇKS Kayıt Süreci ve Gerekli Evraklar Sorgusu (Kira/Hisse hariç)
        is_special_land = any(w in q_clean for w in ["kira", "kiralık", "hisse", "hisseli", "miras", "vefat", "intikal"])
        if not is_special_land and any(w in q_clean for w in ["çks", "kayıt", "başvuru"]):
            if any(w in q_clean for w in ["nasıl", "nereden", "evrak", "belge", "şart", "rehber"]):
                answer_text = self._build_cks_process_answer()
                return answer_text, matched_chunks, source_titles

        # Niyet C: Kadın ve Genç Çiftçi Kapsamlı Rehberi
        if any(w in q_clean for w in ["kadın", "genç", "41 yaş", "genç çiftçi", "kadın çiftçi"]):
            answer_text = self._build_women_young_farmer_answer()
            return answer_text, matched_chunks, source_titles

        # Niyet D: Yeraltı Su Kısıtı Havzaları Sorgusu
        if any(w in q_clean for w in ["su kısıtı", "yeraltı suyu", "kurak", "konya havzası", "münavebe"]):
            answer_text = self._build_water_basin_answer()
            return answer_text, matched_chunks, source_titles

        # Niyet E: Doğrulanmış Resmî Çiftçi SSS (FAQ) Eşleşmesi (Haciz, Kira, Hisseli Tapu, Miras, vb.)
        faq_match = self._match_faq(q_clean)
        if faq_match:
            answer_text = self._build_faq_answer(faq_match)
            return answer_text, matched_chunks, source_titles

        # Niyet F: Sertifikalı Tohum / Fidan / Kapama Bahçe Kriteri Sorgusu
        if any(w in q_clean for w in ["tohum", "fidan", "kapama bahçe", "fatura"]):
            answer_text = self._build_seed_sapling_answer(q_clean)
            return answer_text, matched_chunks, source_titles

        # Niyet G: Ödeme Takvimi ve Banka / İcmal Sorgusu
        if any(w in q_clean for w in ["ne zaman", "ödeme tarihi", "hangi ay", "askı", "icmal", "ziraat", "başak kart"]):
            answer_text = self._build_payment_schedule_answer()
            return answer_text, matched_chunks, source_titles

        # Niyet H: Genel Mevzuat Eşleşmesi (Extractive Multi-Chunk Sentezi)
        if matched_chunks:
            answer_text = self._build_general_retrieval_answer(matched_chunks)
        else:
            answer_text = (
                "⚠️ **Mevzuatta Doğrudan Eşleşme Bulunamadı**\n\n"
                "Sorunuza ilişkin yürürlükteki 2026 Resmî Gazete kararında kesin bir hüküm bulunamadı.\n"
                "Lütfen sorunuzu ürün adı (ör. *Buğday, Çeltik, Ayçiçeği*), destek türü (ör. *Sertifikalı Tohum, Su Kısıtı*) veya "
                "*ÇKS* anahtar kelimeleriyle detaylandırarak tekrar deneyiniz."
            )

        return answer_text, matched_chunks, source_titles

    def _match_faq(self, query: str) -> dict[str, Any] | None:
        """Kullanıcı sorusuyla en alakalı SSS (FAQ) öğesini yüksek hassasiyetle eşleştirir."""
        # 1. Öncelikli doğrudan kural anahtarları (Kesin vuruşlar)
        if any(w in query for w in ["haciz", "icra", "bloke", "banka borç", "kesinti"]):
            return next((f for f in FARMER_FAQ_LIST if f["id"] == "faq_haciz_yasagi"), None)

        if any(w in query for w in ["kiralık", "kiracı", "kira sözleşme", "kira kontrat"]):
            return next((f for f in FARMER_FAQ_LIST if f["id"] == "faq_cks_kira"), None)

        if any(w in query for w in ["hisseli", "müşterek", "imza vermeyen", "paydaş"]):
            return next((f for f in FARMER_FAQ_LIST if f["id"] == "faq_cks_hisseli"), None)

        if any(w in query for w in ["miras", "vefat", "intikal", "ölüm", "veraset"]):
            return next((f for f in FARMER_FAQ_LIST if f["id"] == "faq_cks_intikal"), None)

        if any(w in query for w in ["organik", "biyolojik mücadele", "otbis", "ilaçsız", "feromon"]):
            return next((f for f in FARMER_FAQ_LIST if f["id"] == "faq_organik_tarim"), None)

        if any(w in query for w in ["yeni model", "yeni sistem", "ne değişti", "3 yıllık", "farkı"]):
            return next((f for f in FARMER_FAQ_LIST if f["id"] == "faq_yeni_model"), None)

        if any(w in query for w in ["sahte beyan", "haksız destek", "5 yıl", "men cezası", "faiz"]):
            return next((f for f in FARMER_FAQ_LIST if f["id"] == "faq_ceza_men"), None)

        if any(w in query for w in ["çeltik ruhsat", "çeltik komisyon", "3039", "pirinç ekim"]):
            return next((f for f in FARMER_FAQ_LIST if f["id"] == "faq_celtik_ruhsat"), None)

        if "fındık" in query and any(w in query for w in ["ruhsat", "taban", "söküm", "alan bazlı"]):
            return next((f for f in FARMER_FAQ_LIST if f["id"] == "faq_findik_ruhsat"), None)

        if any(w in query for w in ["askı", "icmal", "5 gün", "itiraz"]):
            return next((f for f in FARMER_FAQ_LIST if f["id"] == "faq_aski_icmal"), None)

        # 2. Anahtar kelime ve başlık benzerliği puanlama (Skor Tabanlı)
        best_faq = None
        best_score = 0
        q_words = set(re.findall(r"\w+", query))

        for faq in FARMER_FAQ_LIST:
            score = 0
            # Soru cümlesi içindeki kelime örtüşmesi
            faq_q_words = set(re.findall(r"\w+", turkish_lower_clean(faq["question"])))
            common_words = q_words.intersection(faq_q_words) - {"ve", "ile", "için", "ne", "nasıl", "mi", "mı", "mu", "mü", "bu", "bir"}
            score += len(common_words) * 3

            # Etiket anahtar kelimeleri örtüşmesi
            for kw in faq.get("keywords", []):
                if kw in query:
                    score += 4

            if score > best_score and score >= 6:
                best_score = score
                best_faq = faq

        return best_faq

    def _build_faq_answer(self, faq: dict[str, Any]) -> str:
        """SSS eşleşmesini görsel olarak zengin ve resmi atıflı formata dönüştürür."""
        return (
            f"### 💡 {faq['category']} — {faq['question']}\n\n"
            f"{faq['answer']}\n\n"
            f"🏛️ **Resmî Yasal Dayanak:** *{faq['citation']}*\n\n"
            "> 📌 **Önemli Not:** Detaylı başvuru formu ve özel durum itirazlarınız için bağlı bulunduğunuz "
            "İl/İlçe Tarım ve Orman Müdürlüğü ÇKS birimine başvurabilirsiniz."
        )

    def _detect_crop(self, query: str) -> str | None:
        """Sorgu metninde geçen tarımsal ürünü 16 ürünlük geniş katalog üzerinden tespit eder."""
        for crop in CROP_SUPPORT_CATALOG.keys():
            crop_lower = turkish_lower_clean(crop)
            if re.search(rf"\b{crop_lower}\b", query) or crop_lower in query:
                return crop

        # Genişletilmiş Türkçe eşanlamlı ve ekli ürün sözlüğü
        aliases = {
            "buğday": "BUĞDAY", "bugday": "BUĞDAY", "ekmeklik": "BUĞDAY", "makarnalık": "BUĞDAY",
            "arpa": "ARPA",
            "mısır": "MISIR", "misir": "MISIR", "dane mısır": "MISIR",
            "pamuk": "PAMUK", "pamug": "PAMUK", "kütlü": "PAMUK",
            "ayçiçeği": "AYÇİÇEĞİ", "aycicegi": "AYÇİÇEĞİ", "günebakan": "AYÇİÇEĞİ", "ayçiçek": "AYÇİÇEĞİ",
            "mercimek": "MERCİMEK", "kırmızı mercimek": "MERCİMEK", "yeşil mercimek": "MERCİMEK",
            "nohut": "NOHUT",
            "fındık": "FINDIK", "findik": "FINDIK",
            "zeytin": "ZEYTİN", "zeytinyağ": "ZEYTİN",
            "çeltik": "ÇELTİK", "celtik": "ÇELTİK", "pirinç": "ÇELTİK", "pirinc": "ÇELTİK",
            "soya": "SOYA", "soya fasulyesi": "SOYA",
            "kanola": "KANOLA", "kolza": "KANOLA",
            "aspir": "ASPİR",
            "kuru fasulye": "KURU FASULYE", "fasulye": "KURU FASULYE", "fasulya": "KURU FASULYE",
            "patates": "PATATES",
            "yem bitkileri": "YEM BİTKİLERİ", "yem bitkisi": "YEM BİTKİLERİ", "yonca": "YEM BİTKİLERİ",
            "korunga": "YEM BİTKİLERİ", "fiğ": "YEM BİTKİLERİ", "fig": "YEM BİTKİLERİ",
            "silajlık mısır": "YEM BİTKİLERİ", "silaj": "YEM BİTKİLERİ"
        }
        for alias, main_crop in aliases.items():
            if alias in query:
                return main_crop
        return None

    def _build_crop_amount_answer(self, crop: str, query: str) -> str:
        """Ürün bazlı dekar başına kesin hak ediş tutarlarını formatlar."""
        info = CROP_SUPPORT_CATALOG[crop]
        temel = info["temel_destek_tl"]
        planli = info["planli_uretim_tl"]
        tohum = info["sertifikali_tohum_tl"]
        su_kisiti = info["su_kisiti_tl"]
        genc = info["kadin_genc_ilave_tl"]
        toplam = info["toplam_standart_tl"]
        aciklama = info.get("aciklama", "")

        lines = [
            f"### 🌾 2026 Yılı {crop} Destekleme Tutarları ve Ödeme Esasları",
            "",
            f"Tarım ve Orman Bakanlığı 2026 bitkisel üretim destekleme mevzuatına göre **{crop}** ürünü için belirlenen dekar başına (da) birim tutarlar şöyledir:",
            "",
            f"- 🔹 **Temel Destek (Mazot ve Gübre Yerine):** **{temel:,.2f} TL/da** (ÇKS kayıtlı her parsel alır)",
        ]

        if planli > 0:
            lines.append(f"- 🔹 **Planlı Üretim Desteği (Tarım Havzaları):** **{planli:,.2f} TL/da** (Havzasında stratejik üretim yapan parseller)")
        else:
            lines.append("- 🔹 **Planlı Üretim Desteği:** *Bu ürün için havza planlı üretim desteği tanımlanmamıştır.*")

        lines.append(f"- 🔹 **Standart Toplam Destek:** **{toplam:,.2f} TL/da**")

        if tohum > 0:
            lines.append(f"- 🔸 **Sertifikalı Tohum İlavesi:** **+{tohum:,.2f} TL/da** (Yetkili bayiden faturalı ve sertifikalı tohum)")
        if su_kisiti > 0:
            lines.append(f"- 🔸 **Yeraltı Su Kısıtı İlavesi:** **+{su_kisiti:,.2f} TL/da** (Su kısıtı olan kapalı havzalarda)")
        lines.append(f"- 🌟 **Genç veya Kadın Çiftçi İlavesi:** **+{genc:,.2f} TL/da** (Temel desteğin %100'ü kadar ek ödeme)")

        if aciklama:
            lines.extend(["", f"ℹ️ *{aciklama}*"])

        lines.extend([
            "",
            f"> 💡 **Örnek Hesap:** 100 dekar {crop.lower()} eken bir genç/kadın üretici, sertifikalı tohum kullanması durumunda dekar başına toplam **{(toplam + tohum + genc):,.2f} TL/da** destek alabilir (100 dekar için **{((toplam + tohum + genc) * 100):,.2f} TL**).",
            "",
            "🏛️ **Yasal Dayanak:** *2024-2026 Bitkisel Üretime Yönelik Desteklemeler Kararı (Resmî Gazete) — Madde 2 ve Ek Tablo.*"
        ])
        return "\n".join(lines)

    def _build_cks_process_answer(self) -> str:
        """ÇKS kayıt süreci ve evrak gereksinimlerini açıklar."""
        return (
            "### 📑 2026 Çiftçi Kayıt Sistemi (ÇKS) Başvuru Rehberi ve Gerekli Evraklar\n\n"
            "Çiftçi Kayıt Sistemi (ÇKS) kaydı, tüm tarımsal destekleme ödemelerinin **ön şartıdır**. ÇKS kaydı olmayan çiftçilere ve beyan edilmeyen parsellere destekleme ödemesi yapılmaz.\n\n"
            "#### 1. Başvuru Kanalları:\n"
            "- 🌐 **e-Devlet Kapısı:** `turkiye.gov.tr` adresindeki *'Çiftçi Kayıt Sistemi Başvurusu'* hizmeti üzerinden arazi beyanları ve ürün güncellemeleri dijital olarak yapılabilir.\n"
            "- 🏢 **İlçe Tarım ve Orman Müdürlüğü:** Arazinin bağlı bulunduğu İlçe Müdürlüğüne başvuru dosyası fiziki olarak teslim edilebilir.\n\n"
            "#### 2. İstenen Belgeler:\n"
            "- ✅ **Çiftçi Belgesi:** İlgili Ziraat Odasından onaylı güncel 2026 yılı belgesi.\n"
            "- ✅ **Tapu Fotokopisi:** Parselin mülkiyet durumunu gösteren belge.\n"
            "- ✅ **Kira Sözleşmesi:** Kiralık parseller için noter veya muhtar onaylı kira kontratı.\n"
            "- ✅ **Muvafakatname (Form 1 / Form 2):** Hisseli veya intikali yapılmamış araziler için hissedar onay beyanı veya üretim taahhütnamesi.\n"
            "- ✅ **C Belgesi:** Ekilen/dikilen ürünlerin dekar bazlı alan tespit beyannamesi.\n\n"
            "#### 3. Başvuru Takvimi:\n"
            "- 📅 **Başlangıç:** 1 Eylül 2026\n"
            "- 📅 **Bitiş:** 31 Aralık 2026 (Mesai bitimi)\n\n"
            "🏛️ **Yasal Dayanak:** *Çiftçi Kayıt Sistemi Yönetmeliği ve 2026 Uygulama Tebliği.*"
        )

    def _build_women_young_farmer_answer(self) -> str:
        """Kadın ve Genç Çiftçi avantajlarını açıklar."""
        return (
            "### 👩‍🌾 2026 Kadın ve Genç Çiftçi İlave Desteklemeleri\n\n"
            "Tarım ve Orman Bakanlığı, tarımsal üretimin sürdürülebilirliğini sağlamak ve aile işletmelerini güçlendirmek amacıyla kadın ve genç çiftçilere **%100 ilave destekleme katsayısı** uygulamaktadır.\n\n"
            "#### 🎯 Temel Şartlar ve Avantajlar:\n"
            "- 👶 **Genç Çiftçi Yaş Kriteri:** Başvuru yapılan üretim yılında **41 yaşından gün almamış** olmak (1985 ve sonrası doğumlular).\n"
            "- 👩 **Kadın Çiftçi:** Yaş şartı aranmaksızın ÇKS kaydını kendi adına açtıran tüm kadın üreticiler doğrudan yararlanır.\n"
            "- 💰 **İlave Ödeme Oranı:** Hak edilen **Temel Desteğin (Mazot/Gübre) %100'ü (1 kat ilave)** kadar ekstra nakit destek ödenir.\n"
            "- 🌾 **Örnek:** Buğday eken standart bir çiftçi 465 TL/da temel destek alırken, kadın veya genç çiftçi **465 TL + 465 TL = 930 TL/da** temel destek alır. Planlı üretimle birlikte bu tutar **1.395 TL/da** seviyesine ulaşır.\n"
            "- ⭐ **Hibe ve Proje Önceliği:** Kırsal Kalkınma (KKYDP) ve makine-ekipman hibe programlarında kadın ve genç üreticilere +10 ek değerlendirme puanı verilir.\n\n"
            "🏛️ **Yasal Dayanak:** *2024-2026 Bitkisel Üretime Yönelik Desteklemeler Kararı — Madde 5.*"
        )

    def _build_seed_sapling_answer(self, query: str) -> str:
        """Sertifikalı tohum ve fidan kriterlerini açıklar."""
        return (
            "### 🌱 2026 Sertifikalı Tohum ve Fidan Kullanım Destekleme Şartları\n\n"
            "Verim ve kaliteyi artırmak amacıyla yetkili tohumluk ve fidan kullanımına dekar başına ilave nakit destek sağlanır.\n\n"
            "#### 1. Sertifikalı Tohum Kullanım Desteği:\n"
            "- ✅ Bakanlıkça yetkilendirilmiş tohum bayilerinden satın alınmış faturalı tohum olmalıdır.\n"
            "- ✅ Faturanın üretim yılına ait olması ve tohum sertifika etiketinin ÇKS dosyasına eklenmesi zorunludur.\n"
            "- ❌ Kendi mahsulünden ayrılan veya sertifikasız tohumlara ödeme yapılmaz.\n"
            "- 💵 **Birim Tutar:** Buğday ve arpa için dekar başına **180 TL**, pamuk için **200 TL**, ayçiçeği ve mısır için **150 TL** ilave ödenir.\n\n"
            "#### 2. Sertifikalı Fidan ve Kapama Bahçe Şartı:\n"
            "- 🌳 **Kapama Bahçe Zorunluluğu:** Bodur ve yarı bodur meyve bahçelerinde asgari **5 dekar**, standart meyve türlerinde asgari **10 dekar** tek parça kapama bahçe kurulmalıdır.\n"
            "- ❌ Münferit, dağınık veya tarla kenarına dikilmiş ağaçlar destek kapsamı dışındadır.\n"
            "- 📑 Yetkili fidan üreticisinden alınmış fatura ve fidan sertifikası başvuru dosyasında yer almalıdır.\n\n"
            "🏛️ **Yasal Dayanak:** *BÜGEM Sertifikalı Tohum ve Fidan Destekleme Uygulama Talimatı.*"
        )

    def _build_water_basin_answer(self) -> str:
        """Yeraltı su kısıtı havzaları desteğini açıklar."""
        return (
            "### 💧 2026 Yeraltı Su Kısıtı Olan Havzalar Desteği (250 TL/da İlave)\n\n"
            "Devlet Su İşleri (DSİ) ve Tarım Bakanlığı verilerine göre yeraltı su seviyesinin kritik eşiğin altına indiği kapalı havzalarda su tasarrufu sağlayan üretim modelleri desteklenmektedir.\n\n"
            "#### 🌍 Kapsamdaki Başlıca Havzalar:\n"
            "- Konya Kapalı Havzası (Karatay, Çumra, Selçuklu, Cihanbeyli, Kulu vb.)\n"
            "- Karaman Merkez ve Kazımkarabekir\n"
            "- Aksaray Merkez, Eskil ve Sultanhanı\n"
            "- Niğde Bor ve Altunhisar havzaları\n\n"
            "#### 📋 Destekleme Kuralları:\n"
            "- 🟢 **Teşvik Edilen Ürünler:** Az su tüketen münavebe ürünleri olan **Kırmızı/Yeşil Mercimek**, **Nohut** ve **Yem Bitkileri** eken çiftçilere dekar başına **250 TL ilave su kısıtı desteği** verilir.\n"
            "- 🔴 **Kısıtlanan Ürünler:** Bu havzalarda çok su tüketen **Dane Mısır** ekimi yapılması durumunda planlı üretim desteği ödenmez (Yalnızca kuru temel destek ödenir).\n\n"
            "🏛️ **Yasal Dayanak:** *Yeraltı Sularının Yetersiz Olduğu Havzalar Kararı ve 2026 Bitkisel Üretim Tebliği.*"
        )

    def _build_payment_schedule_answer(self) -> str:
        """Ödeme takvimi ve askı icmalleri sürecini açıklar."""
        return (
            "### 💳 2026 Tarımsal Destek Ödeme Takvimi ve Askı İcmalleri Süreci\n\n"
            "Tarımsal destekleme ödemeleri hakediş tespiti, askı süreci ve Ziraat Bankası aktarımı olmak üzere 3 aşamada tamamlanır.\n\n"
            "#### 1. Askı İcmalleri (Hakediş Kontrolü):\n"
            "- 📋 İlçe Tarım ve Orman Müdürlüklerince hazırlanan çiftçi icmalleri, köy/mahalle muhtarlıklarında ve İlçe Müdürlüğü panolarında **5 (beş) iş günü** süreyle askıya çıkarılır.\n"
            "- ⚠️ Çiftçilerin ekilen alan, ürün türü ve hak ediş tutarını bu 5 gün içinde kontrol etmesi gerekir. Askı süresinden sonra yapılan itirazlar yasal olarak kabul edilmez.\n\n"
            "#### 2. Ödeme Takvimi ve Banka Aktarımı:\n"
            "- 🏦 **Ödeme Kanalı:** Ödemeler **T.C. Ziraat Bankası** aracılığıyla yapılır.\n"
            "- 💳 **Hesap Türü:** Üreticilerin T.C. kimlik numaralarına tanımlı **Başak Kart / Çiftçi Kart** vadesiz hesaplarına aktarılır.\n"
            "- 🔢 **Kimlik Sırası:** Yoğunluğu önlemek için ödemeler T.C. kimlik numarasının son hanesine göre (0-2, 4-6, 8) Cuma günleri saat 18:00'den sonra hesaplara yatırılır.\n"
            "- 📅 **Ödeme Dönemleri:** Mazot ve gübre temel destekleri genellikle ilkbahar ekim döneminden önce (Şubat-Nisan), fark ödemeleri ve planlı üretim destekleri ise hasat sonrası icmaller kesinleştikten sonra ödenir.\n\n"
            "🏛️ **Yasal Dayanak:** *Tarımsal Destekleme Ödemeleri Tebliği ve Ziraat Bankası Protokolü.*"
        )

    def _build_general_retrieval_answer(self, chunks: list[DocumentChunk]) -> str:
        """Çoklu mevzuat parçasını sentezleyerek açıklayıcı ve yapılandırılmış yanıt oluşturur."""
        first = chunks[0]
        lines = [
            f"### 🏛️ Mevzuat İnceleme Sonucu — {first.section}",
            "",
            "**Resmî Hüküm:**",
            f"{first.text}",
            "",
            f"📌 **Kaynak:** *{first.title} ({first.year})*",
        ]

        if len(chunks) > 1:
            lines.append("\n#### 📚 İlgili Diğer Mevzuat Hükümleri:")
            for i, c in enumerate(chunks[1:4], 1):
                clean_preview = c.text if len(c.text) <= 200 else c.text[:200] + "..."
                lines.append(f"- **[{i}] {c.section}:** *{clean_preview}* (Kaynak: {c.title})")

        lines.extend([
            "",
            "> ℹ️ **Danışma Notu:** Mevzuat uygulamaları İl/İlçe Tarım Komisyonları kararlarına tabidir. "
            "Resmî başvuru için İlçe Tarım ve Orman Müdürlüğünüze danışabilirsiniz."
        ])

        return "\n".join(lines)


# Tekil servis örneği
assistant_engine = AssistantEngine()
