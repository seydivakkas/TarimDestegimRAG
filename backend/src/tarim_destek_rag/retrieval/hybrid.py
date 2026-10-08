"""Hibrit Arama Motoru (BM25 + FAISS Dense + Reciprocal Rank Fusion - RRF).

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from collections import defaultdict

from tarim_destek_rag.logging.logger import logger
from tarim_destek_rag.retrieval.bm25 import BM25Retriever
from tarim_destek_rag.retrieval.models import DocumentChunk
from tarim_destek_rag.retrieval.vector_store import VectorStore, vector_store


class HybridRetriever:
    """Yoğun vektör ve sözcüksel BM25 aramalarını RRF ile birleştiren hibrit motor."""

    def __init__(
        self,
        dense_store: VectorStore | None = None,
        bm25_retriever: BM25Retriever | None = None,
        rrf_k: int = 60,
        dense_weight: float = 0.5,
        bm25_weight: float = 0.5,
    ) -> None:
        self.dense_store = dense_store or vector_store
        self.bm25_retriever = bm25_retriever or BM25Retriever()
        self.rrf_k = rrf_k
        self.dense_weight = dense_weight
        self.bm25_weight = bm25_weight

    def add_chunks(self, chunks: list[DocumentChunk]) -> None:
        """Parçacıkları hem vektör deposuna hem de BM25 indeksine ekler."""
        if not chunks:
            return
        self.dense_store.add_chunks(chunks)
        self.bm25_retriever.add_chunks(chunks)
        logger.info(
            "Hibrit motora %d parça eklendi",
            len(chunks),
            extra={"component": "HybridRetriever"},
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
        source_id_filter: str | None = None,
        year_filter: int | None = None,
        pool_size: int = 20,
    ) -> list[tuple[DocumentChunk, float]]:
        """Sorguyu hem yoğun hem seyrek arar, RRF ile birleştirip sıralar."""
        dense_results = self.dense_store.search(
            query=query,
            top_k=pool_size,
            source_id_filter=source_id_filter,
        )
        bm25_results = self.bm25_retriever.search(
            query=query,
            top_k=pool_size,
            source_id_filter=source_id_filter,
            year_filter=year_filter,
        )

        # RRF Hesaplama: sum( weight / (k + rank) )
        chunk_map: dict[str, DocumentChunk] = {}
        rrf_scores: dict[str, float] = defaultdict(float)

        for rank, (chunk, _score) in enumerate(dense_results, start=1):
            if year_filter and chunk.year != year_filter:
                continue
            chunk_map[chunk.chunk_id] = chunk
            rrf_scores[chunk.chunk_id] += self.dense_weight / (self.rrf_k + rank)

        for rank, (chunk, _score) in enumerate(bm25_results, start=1):
            chunk_map[chunk.chunk_id] = chunk
            rrf_scores[chunk.chunk_id] += self.bm25_weight / (self.rrf_k + rank)

        if not rrf_scores:
            return []

        sorted_chunks = sorted(
            rrf_scores.items(),
            key=lambda item: item[1],
            reverse=True,
        )

        results: list[tuple[DocumentChunk, float]] = []
        for chunk_id, score in sorted_chunks[:top_k]:
            results.append((chunk_map[chunk_id], score))

        return results


hybrid_retriever = HybridRetriever()
