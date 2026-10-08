import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

from tarim_destek_rag.config.settings import settings
from tarim_destek_rag.logging.logger import logger
from tarim_destek_rag.retrieval.models import DocumentChunk


class VectorStore:
    """FAISS ve Sentence-Transformers tabanlı yerel yoğun (dense) arama motoru."""

    def __init__(
        self,
        model_name: str | None = None,
        index_dir: str | None = None,
    ) -> None:
        self.model_name = model_name or settings.embedding_model_name
        self.index_dir = Path(index_dir or settings.index_path)
        self.index_dir.mkdir(parents=True, exist_ok=True)

        self._model: SentenceTransformer | None = None
        self._index: faiss.IndexFlatIP | None = None
        self._chunks: list[DocumentChunk] = []
        self.dimension = settings.vector_dimension

    @property
    def model(self) -> SentenceTransformer:
        """Embedding modelini ihtiyaç duyulduğunda (lazy) yükler."""
        if self._model is None:
            logger.info(
                "Embedding modeli yükleniyor: %s",
                self.model_name,
                extra={"component": "VectorStore"},
            )
            self._model = SentenceTransformer(self.model_name)
        return self._model

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Metin parçacıklarını vektörleştirir ve FAISS indeksine ekler."""
        if not chunks:
            return

        texts = [f"{c.title} - {c.section}: {c.text}" for c in chunks]
        embeddings = self.model.encode(texts, convert_to_numpy=True, normalize_embeddings=True)

        if self._index is None:
            self.dimension = embeddings.shape[1]
            self._index = faiss.IndexFlatIP(self.dimension)

        self._index.add(embeddings.astype(np.float32))
        self._chunks.extend(chunks)

        logger.info(
            "FAISS indeksine %d parça eklendi (Toplam: %d)",
            len(chunks),
            len(self._chunks),
            extra={"component": "VectorStore"},
        )

    def search(
        self,
        query: str,
        top_k: int = 3,
        source_id_filter: str | None = None,
    ) -> list[tuple[DocumentChunk, float]]:
        """Sorgu ile en yüksek benzerliğe sahip metin parçalarını döner."""
        if self._index is None or len(self._chunks) == 0:
            return []

        query_emb = self.model.encode([query], convert_to_numpy=True, normalize_embeddings=True)
        scores, indices = self._index.search(
            query_emb.astype(np.float32), min(top_k * 2, len(self._chunks))
        )

        results: list[tuple[DocumentChunk, float]] = []
        for score, idx in zip(scores[0], indices[0], strict=False):
            if idx == -1:
                continue
            chunk = self._chunks[idx]
            if source_id_filter and chunk.source_id != source_id_filter:
                continue
            results.append((chunk, float(score)))
            if len(results) >= top_k:
                break

        return results

    def save_to_disk(self) -> None:
        """İndeksi ve chunk üstverilerini diske yazar."""
        if self._index is None:
            return
        idx_path = self.index_dir / "faiss.index"
        meta_path = self.index_dir / "chunks.json"

        faiss.write_index(self._index, str(idx_path))
        raw_meta = [c.model_dump() for c in self._chunks]
        meta_path.write_text(json.dumps(raw_meta, ensure_ascii=False, indent=2), encoding="utf-8")

    def load_from_disk(self) -> bool:
        """Varsa diske kaydedilmiş indeksi yükler."""
        idx_path = self.index_dir / "faiss.index"
        meta_path = self.index_dir / "chunks.json"

        if idx_path.exists() and meta_path.exists():
            self._index = faiss.read_index(str(idx_path))
            raw_meta = json.loads(meta_path.read_text(encoding="utf-8"))
            self._chunks = [DocumentChunk(**item) for item in raw_meta]
            return True
        return False


vector_store = VectorStore()
