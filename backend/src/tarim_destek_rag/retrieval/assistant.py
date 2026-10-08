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
        # Module import must never download an embedding model from the network.
        # Seed the lexical fallback only; lifespan can build dense vectors later.
        if hasattr(self.retriever, "bm25_retriever") and not self.retriever.bm25_retriever._chunks:
            self.retriever.bm25_retriever.add_chunks(OFFICIAL_REGULATION_CHUNKS)

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
        """Katalogdaki referans birim tutarlarını gösterir; kesin hak ediş değildir."""
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
            f"- 🔹 **Temel Destek (Mazot ve Gübre Yerine):** **{temel:,.2f} TL/da** (kayıt ve ürün koşulları sağlanırsa)",
        ]

        if planli > 0:
            lines.append(f"- 🔹 **Planlı Üretim Desteği (Tarım Havzaları):** **{planli:,.2f} TL/da** (Havzasında stratejik üretim yapan parseller)")
        else:
            lines.append("- 🔹 **Planlı Üretim Desteği:** *Bu referans katalogda planlı üretim tutarı yok; kesin ret anlamına gelmez.*")

        lines.append(f"- 🔹 **Standart Toplam Destek:** **{toplam:,.2f} TL/da**")

        if tohum > 0:
            lines.append(f"- 🔸 **Sertifikalı Tohum İlavesi:** **+{tohum:,.2f} TL/da** (Yetkili bayiden faturalı ve sertifikalı tohum)")
        if su_kisiti > 0:
            lines.append(f"- 🔸 **Yeraltı Su Kısıtı İlavesi:** **+{su_kisiti:,.2f} TL/da** (Su kısıtı olan kapalı havzalarda)")
        lines.append("- ℹ️ **Kadın / Genç Çiftçi İlavesi:** Otomatik ilave varsayılmaz; KOBÜKS ve diğer mevzuat koşulları ayrıca değerlendirilir.")

        if aciklama:
            lines.extend(["", f"ℹ️ *{aciklama}*"])

        lines.extend([
            "",
            f"> **Koşullu örnek:** Gerekli şartları karşılayan 100 da {crop.lower()} üretiminde yalnız temel ve planlı toplamı **{toplam * 100:,.2f} TL** olabilir; bunun kesin hak ediş olduğu varsayılamaz.",
            "",
            "🏛️ **Kaynaklar:** *BÜGEM 2026 kategori cetveli ve Bakanlığın 08.09.2026 tarihli 367 TL/da katsayı duyurusu.*"
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
        """Genel otomatik hak iddiası yerine özel kayıt şartlarını açıklar."""
        return (
            "### Kadın ve Genç Çiftçi Destekleri (2026)\n\n"
            "Her kadın veya genç üreticiye temel desteğin otomatik %100'ü kadar ödeme "
            "yapılacağı varsayılamaz. BÜGEM 2026 cetvelinde KOBÜKS kayıtlı kapalı ortam "
            "üreticileri için özel katsayı yer almaktadır.\n\n"
            "Bireysel uygunluk için işletme kaydı, üretim tipi ve programın koşulları doğrulanmalıdır.\n\n"
            "Kaynak: BÜGEM 2026 Birim Fiyat Cetveli (Temel Destek)."
        )

    def _build_seed_sapling_answer(self, query: str) -> str:
        """Güncel katsayılı tohum ve fidan referanslarını verir."""
        return (
            "### Sertifikalı Tohum ve Fidan Desteği (2026)\n\n"
            "Sertifika, fatura, bitki türü ve uygulama tebliği koşulları ayrıca doğrulanmalıdır.\n\n"
            "- Buğday / arpa sertifikalı tohum: 0,56 × 367 = **205,52 TL/da**.\n"
            "- Sertifikalı fidan için cetvel katsayısı: 5 × 367 = **1.835,00 TL/da** "
            "(tür ve kapama bahçe şartlarına bağlı).\n\n"
            "Kaynak: BÜGEM 2026 cetveli ve Bakanlığın 08.09.2026 katsayı duyurusu."
        )

    def _build_water_basin_answer(self) -> str:
        """Sulu tarım şartına bağlı su kısıtı ek desteğini açıklar."""
        return (
            "### Yeraltı Su Kısıtı İlave Desteği (2026)\n\n"
            "Bu destek yalnız resmen belirlenmiş su kısıtı havzalarındaki **sulu tarım "
            "arazileri** ve mevzuatta belirtilen ürün/üretim koşulları için değerlendirilir.\n\n"
            "- Mercimek, nohut ve aspir gibi uygun 1. kategori ürünler için "
            "0,8 × 367 = **293,60 TL/da** referans ilave tutardır.\n"
            "- Diğer ürün kategorilerinin katsayıları farklıdır.\n"
            "- Havza, sulama ve münavebe doğrulanmadan kesin ödeme söylenemez.\n\n"
            "Kaynak: BÜGEM 2026 cetveli ve Bakanlığın 08.09.2026 katsayı duyurusu."
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
