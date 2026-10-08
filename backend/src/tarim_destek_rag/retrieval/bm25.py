"""BM25 Tabanlı Sözcüksel (Lexical) Arama Motoru.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

import re

from rank_bm25 import BM25Plus

from tarim_destek_rag.logging.logger import logger
from tarim_destek_rag.retrieval.models import DocumentChunk


def turkish_lower(text: str) -> str:
    """Türkçe karakter duyarlı küçük harfe dönüştürme."""
    replacements = {
        "İ": "i",
        "I": "ı",
        "Ğ": "ğ",
        "Ü": "ü",
        "Ş": "ş",
        "Ö": "ö",
        "Ç": "ç",
    }
    for upper_ch, lower_ch in replacements.items():
        text = text.replace(upper_ch, lower_ch)
    return text.lower()


TURKISH_STOPWORDS: set[str] = {
    "acaba", "ama", "ancak", "bana", "bence", "belki", "biri", "birkaç", "böyle",
    "da", "de", "daha", "dahi", "diye", "gibi", "hangi", "her", "ile", "için",
    "ise", "kadar", "mi", "mı", "mu", "mü", "nasıl", "ne", "neden", "nerede",
    "nereye", "nereden", "olan", "olarak", "oysa", "öyle", "şey", "ve", "veya",
    "ya", "yani"
}

# Tarımsal sık kullanılan kök haritalaması / son ek arındırma
AGRICULTURAL_STEM_MAP: dict[str, str] = {
    "buğdaya": "buğday", "buğdayın": "buğday", "buğdayda": "buğday", "buğdayı": "buğday",
    "arpaya": "arpa", "arpanın": "arpa", "arpada": "arpa", "arpayı": "arpa",
    "mısıra": "mısır", "mısırın": "mısır", "mısırda": "mısır", "mısırı": "mısır",
    "pamuğa": "pamuk", "pamuğun": "pamuk", "pamukta": "pamuk", "pamuğu": "pamuk",
    "fındığa": "fındık", "fındığın": "fındık", "fındıkta": "fındık", "fındığı": "fındık",
    "nohuda": "nohut", "nohudun": "nohut", "nohutta": "nohut", "nohudu": "nohut",
    "mercimeğe": "mercimek", "mercimeğin": "mercimek", "mercimekte": "mercimek",
    "ayçiçeğine": "ayçiçeği", "ayçiçeğinin": "ayçiçeği", "ayçiçeğinde": "ayçiçeği",
    "çeltikte": "çeltik", "çeltiğe": "çeltik", "çeltiğin": "çeltik",
    "çiftçiye": "çiftçi", "çiftçiler": "çiftçi", "çiftçilerin": "çiftçi", "çiftçilik": "çiftçi", "çiftçilere": "çiftçi",
    "kadına": "kadın", "kadınlar": "kadın", "kadınlara": "kadın", "kadının": "kadın",
    "gence": "genç", "gençler": "genç", "gençlere": "genç", "gencin": "genç",
    "tohumu": "tohum", "tohumun": "tohum", "tohumluk": "tohum", "tohumlar": "tohum", "tohumlara": "tohum",
    "fidana": "fidan", "fidanlar": "fidan", "fidanı": "fidan", "fidanların": "fidan",
    "desteği": "destek", "destekleri": "destek", "destekten": "destek", "desteğine": "destek", "destekleme": "destek", "desteklemeler": "destek",
    "havzası": "havza", "havzaları": "havza", "havzada": "havza", "havzalarda": "havza",
    "çksye": "çks", "çksli": "çks", "çkssi": "çks", "çksnin": "çks",
    "sulama": "sulama", "sulaması": "sulama", "sulamaya": "sulama", "sulanan": "sulu",
    "üreticiye": "üretici", "üreticiler": "üretici", "üreticilere": "üretici",
    "başvurusu": "başvuru", "başvuruları": "başvuru", "başvuruda": "başvuru",
    "ödemesi": "ödeme", "ödemeleri": "ödeme", "ödemede": "ödeme", "ödemeler": "ödeme",
}


def stem_turkish(word: str) -> str:
    """Tarımsal kelimeler için temel ek ayıklama yapar."""
    if word in AGRICULTURAL_STEM_MAP:
        return AGRICULTURAL_STEM_MAP[word]
    # Genel çekim eki budama (ör. -ler, -lar, -nin, -nin, -den, -dan)
    for suffix in ("lerden", "lardan", "lerine", "larına", "lerin", "ların", "lere", "lara", "ler", "lar", "nin", "nın", "den", "dan", "te", "ta", "de", "da"):
        if word.endswith(suffix) and len(word) - len(suffix) >= 3:
            base = word[:-len(suffix)]
            return AGRICULTURAL_STEM_MAP.get(base, base)
    return word


def tokenize_turkish(text: str) -> list[str]:
    """Türkçe metni küçük harfe çevirip sözcüklere ve köklere böler."""
    clean_text = turkish_lower(text)
    raw_tokens = re.findall(r"\b[a-zçğıöşü0-9]+\b", clean_text)
    result_tokens: list[str] = []
    for token in raw_tokens:
        result_tokens.append(token)
        stem = stem_turkish(token)
        if stem != token:
            result_tokens.append(stem)
    return result_tokens


class BM25Retriever:
    """BM25Plus tabanlı sözcüksel arama motoru."""

    def __init__(self) -> None:
        self._chunks: list[DocumentChunk] = []
        self._tokenized_corpus: list[list[str]] = []
        self._bm25: BM25Plus | None = None

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Metin parçacıklarını BM25 indeksine ekler."""
        if not chunks:
            return

        for chunk in chunks:
            content = f"{chunk.title} {chunk.section} {chunk.text}"
            tokens = tokenize_turkish(content)
            self._chunks.append(chunk)
            self._tokenized_corpus.append(tokens)

        self._bm25 = BM25Plus(self._tokenized_corpus)
        logger.info(
            "BM25 indeksine %d parça eklendi (Toplam: %d)",
            len(chunks),
            len(self._chunks),
            extra={"component": "BM25Retriever"},
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
        source_id_filter: str | None = None,
        year_filter: int | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """BM25 sorgusu yapar ve filtrelenmiş sonuçları skorlarıyla döner."""
        if self._bm25 is None or len(self._chunks) == 0:
            return []

        query_tokens = tokenize_turkish(query)
        if not query_tokens:
            return []

        meaningful_tokens = [t for t in query_tokens if t not in TURKISH_STOPWORDS]
        search_tokens = meaningful_tokens if meaningful_tokens else query_tokens

        scores = self._bm25.get_scores(search_tokens)
        search_token_set = set(search_tokens)
        scored_pairs: list[tuple[int, float]] = []
        for idx, score in enumerate(scores):
            doc_tokens = set(self._tokenized_corpus[idx])
            if search_token_set.intersection(doc_tokens):
                scored_pairs.append((idx, float(score)))

        scored_pairs.sort(key=lambda x: x[1], reverse=True)

        results: list[tuple[DocumentChunk, float]] = []
        for idx, score in scored_pairs:
            chunk = self._chunks[idx]
            if source_id_filter and chunk.source_id != source_id_filter:
                continue
            if year_filter and chunk.year != year_filter:
                continue
            results.append((chunk, score))
            if len(results) >= top_k:
                break

        return results

    def clear(self) -> None:
        """İndeksi sıfırlar."""
        self._chunks.clear()
        self._tokenized_corpus.clear()
        self._bm25 = None
