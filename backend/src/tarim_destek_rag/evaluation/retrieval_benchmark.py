"""TD-P12 Retrieval Benchmark Runner.

BM25, Dense (FAISS) ve Hibrit (RRF) arama yöntemlerini
Hit@1, Hit@3, Hit@5 ve MRR metrikleri üzerinden ölçer ve karşılaştırır.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

import time
from typing import Any

from tarim_destek_rag.retrieval.bm25 import BM25Retriever
from tarim_destek_rag.retrieval.chunker import HeadingAwareChunker
from tarim_destek_rag.retrieval.hybrid import HybridRetriever
from tarim_destek_rag.retrieval.vector_store import VectorStore

GROUND_TRUTH_QUERIES = [
    {
        "query": "ÇKS kaydı olan çiftçilere mazot ve gübre desteği ne kadar verilir?",
        "expected_section": "MADDE 1",
        "expected_source": "RG-2026-BITKISEL",
    },
    {
        "query": "Tarım havzasında buğday ve arpa ekenlere planlı üretim desteği şartları",
        "expected_section": "MADDE 2",
        "expected_source": "RG-2026-BITKISEL",
    },
    {
        "query": "Yetkili tohum bayisinden faturalı sertifikalı tohum alanlara destek belgesi",
        "expected_section": "MADDE 3",
        "expected_source": "RG-2026-BITKISEL",
    },
    {
        "query": "Yeraltı su kısıtı olan kurak havzalarda münavebe ürünü ekimi ilave desteği",
        "expected_section": "MADDE 4",
        "expected_source": "RG-2026-BITKISEL",
    },
    {
        "query": "2026 yılı bitkisel üretim temel destek başvuru tarihleri ne zamandır?",
        "expected_section": "MADDE 1",
        "expected_source": "RG-2026-BITKISEL",
    },
    {
        "query": "Planlı üretim desteği kapsamında 465 TL ödeme kimlere verilir?",
        "expected_section": "MADDE 2",
        "expected_source": "RG-2026-BITKISEL",
    },
    {
        "query": "Fatura ibrazı zorunlu olan sertifikalı tohum kullanım desteği",
        "expected_section": "MADDE 3",
        "expected_source": "RG-2026-BITKISEL",
    },
    {
        "query": "Az su tüketen nohut ve mercimek ekenlere 250 TL su kısıtı desteği",
        "expected_section": "MADDE 4",
        "expected_source": "RG-2026-BITKISEL",
    },
]

REGULATION_TEXT = """
MADDE 1 - 2026 yılında Çiftçi Kayıt Sistemi (ÇKS) kayıtlı çiftçilere temel destek ödenir. Mazot ve gübre giderlerini karşılamak amacıyla dekar başına birim tutarlarla ödenir. Başvurular 1 Eylül 2026 ile 31 Aralık 2026 arasındadır.

MADDE 2 - Belirlenen Tarım Havzalarında öncelikli stratejik ürünleri üreten üreticilere Planlı Üretim Desteği kapsamında ilave ödeme yapılır. Buğday ve arpa için 465 TL/da ödenir.

MADDE 3 - Sertifikalı tohum desteği yetkili tohum bayilerinden faturalı tohum alan üreticilere verilir. Faturanın başvuru dosyasına eklenmesi zorunludur.

MADDE 4 - Yeraltı su kısıtı bulunan havzalarda az su tüketen münavebe ürünleri ekenlere dekar başına 250 TL ilave destek verilir.
"""


def setup_benchmark_retrievers() -> tuple[BM25Retriever, VectorStore, HybridRetriever]:
    """Test için BM25, Dense ve Hybrid arama motorlarını hazırlar."""
    chunks = HeadingAwareChunker.chunk_regulation_text(
        source_id="RG-2026-BITKISEL",
        title="2026 Bitkisel Üretim Destekleme Kararı",
        text=REGULATION_TEXT,
        year=2026,
    )
    bm25 = BM25Retriever()
    bm25.add_chunks(chunks)

    dense = VectorStore()
    dense.add_chunks(chunks)

    hybrid = HybridRetriever(dense_store=dense, bm25_retriever=bm25)
    return bm25, dense, hybrid


def evaluate_retriever(
    name: str,
    search_fn: Any,
    queries: list[dict[str, str]] | None = None,
) -> dict[str, float]:
    """Verilen arama fonksiyonunu Hit@1, Hit@3, Hit@5 ve MRR metriklerine göre değerlendirir."""
    test_queries = queries or GROUND_TRUTH_QUERIES
    n = len(test_queries)
    if n == 0:
        return {"hit@1": 0.0, "hit@3": 0.0, "hit@5": 0.0, "mrr": 0.0, "avg_latency_ms": 0.0}

    hits_at_1 = 0
    hits_at_3 = 0
    hits_at_5 = 0
    reciprocal_ranks = []
    ndcg_list = []
    latencies = []

    for item in test_queries:
        q = item["query"]
        expected_sec = item["expected_section"]

        t0 = time.perf_counter()
        results = search_fn(q, top_k=5)
        latencies.append((time.perf_counter() - t0) * 1000)

        found_rank = 0
        for rank, (chunk, _score) in enumerate(results, start=1):
            if chunk.section.startswith(expected_sec):
                found_rank = rank
                break

        if found_rank == 1:
            hits_at_1 += 1
        if 1 <= found_rank <= 3:
            hits_at_3 += 1
        import math
        if 1 <= found_rank <= 5:
            hits_at_5 += 1
            ndcg_list.append(1.0 / math.log2(found_rank + 1))
        else:
            ndcg_list.append(0.0)

        if found_rank > 0:
            reciprocal_ranks.append(1.0 / found_rank)
        else:
            reciprocal_ranks.append(0.0)

    return {
        "name": name,
        "hit@1": round(hits_at_1 / n, 4),
        "hit@3": round(hits_at_3 / n, 4),
        "hit@5": round(hits_at_5 / n, 4),
        "mrr": round(sum(reciprocal_ranks) / n, 4),
        "ndcg@5": round(sum(ndcg_list) / n, 4),
        "avg_latency_ms": round(sum(latencies) / n, 2),
    }


def run_retrieval_benchmark() -> dict[str, dict[str, float]]:
    """Tüm motorları karşılaştırmalı çalıştırır."""
    bm25, dense, hybrid = setup_benchmark_retrievers()

    res_bm25 = evaluate_retriever("BM25", lambda q, top_k: bm25.search(q, top_k=top_k))
    res_dense = evaluate_retriever("Dense (FAISS)", lambda q, top_k: dense.search(q, top_k=top_k))
    res_hybrid = evaluate_retriever("Hybrid (RRF)", lambda q, top_k: hybrid.search(q, top_k=top_k))

    return {
        "BM25": res_bm25,
        "Dense": res_dense,
        "Hybrid": res_hybrid,
    }


if __name__ == "__main__":
    results = run_retrieval_benchmark()
    print("=== TD-P12 RETRIEVAL BENCHMARK RESULTS ===")
    for model, m in results.items():
        print(
            f"{model:15}: Hit@1={m['hit@1']:.2f} | Hit@3={m['hit@3']:.2f} | Hit@5={m['hit@5']:.2f} | MRR={m['mrr']:.4f} | Latency={m['avg_latency_ms']:.2f}ms"
        )
