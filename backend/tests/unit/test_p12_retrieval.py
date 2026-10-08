"""TD-P12 BM25, Hibrit Arama ve Retrieval Benchmark Birim Testleri.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from tarim_destek_rag.evaluation.retrieval_benchmark import (
    evaluate_retriever,
    setup_benchmark_retrievers,
)
from tarim_destek_rag.retrieval.bm25 import BM25Retriever, tokenize_turkish, turkish_lower
from tarim_destek_rag.retrieval.chunker import HeadingAwareChunker


def test_turkish_tokenization():
    """Türkçe özel karakterlerin küçük harfe dönüştürülmesi ve tokenizasyon testi."""
    raw = "İSTANBUL Iğdır Şanlıurfa ÇKS Üretim Ödemesi 2026!"
    lowered = turkish_lower(raw)
    assert "istanbul" in lowered
    assert "ığdır" in lowered
    assert "şanlıurfa" in lowered

    tokens = tokenize_turkish(raw)
    assert "istanbul" in tokens
    assert "çks" in tokens
    assert "2026" in tokens


def test_bm25_retrieval_lifecycle():
    """BM25 indeksleme ve sözcüksel sorgu başarımı testi."""
    text = (
        "MADDE 1 - 2026 yılında ÇKS kayıtlı çiftçilere mazot ve gübre desteği verilir.\n\n"
        "MADDE 2 - Havzada buğday ve arpa ekenlere planlı üretim desteği 465 TL ödenir."
    )
    chunks = HeadingAwareChunker.chunk_regulation_text("RG-TEST", "Test Mevzuat", text)
    bm25 = BM25Retriever()
    bm25.add_chunks(chunks)

    results = bm25.search("mazot gübre", top_k=1)
    assert len(results) == 1
    assert "MADDE 1" in results[0][0].section

    results_crop = bm25.search("buğday arpa planlı", top_k=1)
    assert len(results_crop) == 1
    assert "MADDE 2" in results_crop[0][0].section


def test_retrieval_benchmark_hit_rates():
    """TD-P12 benchmark metriklerinin (Hit@1, Hit@3, MRR) hesaplanması."""
    bm25, dense, hybrid = setup_benchmark_retrievers()

    bm25_metrics = evaluate_retriever("BM25", lambda q, top_k: bm25.search(q, top_k=top_k))
    assert bm25_metrics["hit@3"] >= 0.8
    assert bm25_metrics["mrr"] > 0.8

    hybrid_metrics = evaluate_retriever("Hybrid", lambda q, top_k: hybrid.search(q, top_k=top_k))
    assert hybrid_metrics["hit@1"] >= 0.8
    assert hybrid_metrics["hit@3"] == 1.0
    assert hybrid_metrics["mrr"] >= 0.9
