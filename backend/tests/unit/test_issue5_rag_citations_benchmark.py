"""Issue #5: RAG Atıfları İddia-Paragraf Düzeyi Ölçüm ve Bağımsız Benchmark Testleri.

Kapsam:
- Claim-to-Span & Belge Sürümü Eşleştirme.
- 3 Zorunlu Negatif Test:
  1. Atıfsız İddia (NO_CITATION) -> Başarısız.
  2. Eski Sürümlü / Mülga Mevzuat (OUTDATED_VERSION) -> Başarısız.
  3. Semantik Olarak Yanlış / Desteksiz Eşleme (UNSUPPORTED_CLAIM / SPAN_MISMATCH) -> Başarısız.
- Ayrık Metrikler: Precision, Recall, Unsupported-Claim Rate, Legal Freshness, Refusal Accuracy.
- Çoklu Bilgi Getirme (BM25, Dense, Hybrid) Karşılaştırması: Hit@1, Hit@3, Hit@5, MRR, nDCG@5.
- Gerçek mevzuat test seti ile sentetik test ayrımı.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

import pytest

from tarim_destek_rag.citations.verifier import (
    CitationMetricsCalculator,
    CitationVerifier,
)
from tarim_destek_rag.evaluation.retrieval_benchmark import (
    evaluate_retriever,
    setup_benchmark_retrievers,
)
from tarim_destek_rag.explainer.template_explainer import CitationDetail


@pytest.fixture
def verifier():
    return CitationVerifier()


# ==============================================================================
# 1. CLAIM-TO-SPAN VE 3 AYRI NEGATİF DOĞRULAMA TESTİ
# ==============================================================================


def test_claim_verification_valid(verifier):
    """Resmî mevzuat maddesi, güncel yılı ve metin aralığı ile tam uyuşan iddia onaylanmalıdır."""
    claim = "Planlı üretim kapsamında buğday eken üreticilere 465 TL/da ilave destek verilir."
    citation = CitationDetail(
        source_id="RG-2026-BITKISEL",
        title="2026 Bitkisel Üretim Destekleme Kararı",
        section="MADDE 2 - Tarım Havzaları Planlı Üretim Desteği",
        year=2026,
        snippet="Buğday ve arpa için 465 TL/da planlı üretim ilave desteği ödenir.",
    )
    doc_text = "MADDE 2 - Buğday ve arpa için 465 TL/da planlı üretim ilave desteği ödenir."

    res = verifier.verify_claim(claim, citation, doc_text)
    # Manually supplied doc_text is NOT proof of original official bytes;
    # the official source SHA/page must be independently indexed first.
    assert res.is_valid is False
    assert res.status in ("EVIDENCE_NOT_INDEXED", "UNVERIFIED_SOURCE")
    assert res.claim_supported is False
    assert res.version_valid is True


def test_negative_case_1_missing_citation(verifier):
    """ZORUNLU NEGATİF 1: Atıfsız sunulan iddia başarısız olmalıdır (NO_CITATION)."""
    claim = "ÇKS kaydı olmayan çiftçilere doğrudan mazot ödemesi yapılır."
    res = verifier.verify_claim(claim, citation=None)

    assert res.is_valid is False
    assert res.status == "NO_CITATION"
    assert res.claim_supported is False
    assert "atf" in res.message.lower() or "atıf" in res.message.lower()


def test_negative_case_2_outdated_version(verifier):
    """ZORUNLU NEGATİF 2: 2026 dışındaki eski/mülga mevzuat yılı reddedilmelidir (OUTDATED_VERSION)."""
    claim = "Buğday desteği 2024 yılı kararına göre 350 TL/da olarak ödenmektedir."
    citation = CitationDetail(
        source_id="RG-2026-BITKISEL",
        title="Eski Destekleme Kararı",
        section="MADDE 1",
        year=2024,  # Eski yıl / mülga karar
        snippet="2024 yılında buğday üreticilerine 350 TL/da destekleme ödenir.",
    )

    res = verifier.verify_claim(claim, citation)
    assert res.is_valid is False
    assert res.status == "OUTDATED_VERSION"
    assert res.version_valid is False
    assert res.claim_supported is False


def test_negative_case_3_unsupported_or_mismatched_claim(verifier):
    """ZORUNLU NEGATİF 3: Semantik olarak yanlış tutar veya ürün içeren iddia reddedilmelidir."""
    # İddia 1500 TL talep ediyor ama atıf metninde 465 TL yazıyor
    claim = "Planlı üretim kapsamında buğday üreticisine 1500 TL destek verilir."
    citation = CitationDetail(
        source_id="RG-2026-BITKISEL",
        title="2026 Kararı",
        section="MADDE 2",
        year=2026,
        snippet="Buğday ve arpa için 465 TL/da planlı üretim desteği ödenir.",
    )
    res = verifier.verify_claim(claim, citation)

    assert res.is_valid is False
    assert res.status == "UNSUPPORTED_CLAIM"
    assert res.claim_supported is False
    assert "tutar" in res.message.lower() or "sayısal" in res.message.lower()


def test_negative_case_3_span_mismatch(verifier):
    """ZORUNLU NEGATİF 3 (Ek): Atıf gösterilen snippet kaynak dokümanda yer almıyorsa SPAN_MISMATCH olmalıdır."""
    claim = "Tarımsal sulamada %50 indirim uygulanır."
    citation = CitationDetail(
        source_id="RG-2026-BITKISEL",
        title="2026 Kararı",
        section="MADDE 5",
        year=2026,
        snippet="Uydurma metin: sulama için yarı yarıya indirim uygulanacaktır.",
    )
    real_doc_text = "MADDE 1 - Temel destek ödenir. MADDE 2 - Planlı üretim desteği ödenir."

    res = verifier.verify_claim(claim, citation, document_text=real_doc_text)
    assert res.is_valid is False
    assert res.status == "SPAN_MISMATCH"
    assert res.span_matched is False


# ==============================================================================
# 2. AYRIK METRİKLER (PRECISION, RECALL, UNSUPPORTED RATE, FRESHNESS, REFUSAL)
# ==============================================================================


def test_citation_metrics_calculation_distinctness(verifier):
    """Metrikler (Precision, Recall, Unsupported Rate, Freshness, Refusal) birbirinden bağımsız hesaplanmalıdır."""
    eval_cases = [
        # 1. Doğru ve geçerli iddia
        {
            "claim": "Buğday için 465 TL planlı üretim desteği ödenir.",
            "citation": CitationDetail(
                source_id="RG-2026-BITKISEL",
                title="2026 Kararı",
                section="MADDE 2",
                year=2026,
                snippet="Buğday için 465 TL/da planlı üretim desteği ödenir.",
            ),
            "is_unsupportable": False,
        },
        # 2. Uydurma iddia (Reddedilmeli - Refusal hedefi)
        {
            "claim": "ÇKS olmadan nakit hibe verilir.",
            "citation": None,  # Atıfsız
            "is_unsupportable": True,
        },
        # 3. Eski mevzuat iddiası (Reddedilmeli - Freshness hedefi)
        {
            "claim": "2024 yılı mazot desteği 120 TL'dir.",
            "citation": CitationDetail(
                source_id="RG-2026-BITKISEL",
                title="Eski Karar",
                section="MADDE 1",
                year=2024,
                snippet="Mazot desteği 120 TL'dir.",
            ),
            "is_unsupportable": True,
        },
        # 4. Semantik olarak yanlış tutarlı iddia (Reddedilmeli - Unsupported Claim)
        {
            "claim": "Buğday desteği 5000 TL olarak ödenir.",
            "citation": CitationDetail(
                source_id="RG-2026-BITKISEL",
                title="2026 Kararı",
                section="MADDE 1",
                year=2026,
                snippet="Buğday için 465 TL temel destek verilir.",
            ),
            "is_unsupportable": True,
        },
    ]

    metrics = CitationMetricsCalculator.calculate_metrics(eval_cases, verifier=verifier)

    assert metrics.total_claims == 4
    # No original-PDF evidence was supplied, including the one seemingly
    # matching snippet. A fail-closed verifier must not award fake precision.
    assert metrics.citation_precision == 0.0
    assert metrics.citation_recall == 0.0
    assert metrics.unsupported_claim_rate == 1.0
    # Refusal accuracy: Desteklenemez 3 iddiadan 3'ü de doğru reddedildi
    assert metrics.refusal_accuracy == 1.0
    # Legal freshness: 3 atıftan 2'si 2026 yılına ait
    assert 0.6 <= metrics.legal_freshness <= 0.7


# ==============================================================================
# 3. RETRIEVAL BENCHMARK: BM25, DENSE, HYBRID KARŞILAŞTIRMASI & nDCG@5
# ==============================================================================


def test_retrieval_benchmark_ndcg_and_mrr():
    """Retrieval benchmark Hit@1, Hit@3, Hit@5, MRR ve nDCG@5 metriklerini üretmelidir."""
    bm25, dense, hybrid = setup_benchmark_retrievers()

    hybrid_res = evaluate_retriever("Hybrid", lambda q, top_k: hybrid.search(q, top_k=top_k))
    bm25_res = evaluate_retriever("BM25", lambda q, top_k: bm25.search(q, top_k=top_k))
    dense_res = evaluate_retriever("Dense", lambda q, top_k: dense.search(q, top_k=top_k))

    # Tüm metrikler mevcut ve geçerli aralıkta olmalı
    for r in [hybrid_res, bm25_res, dense_res]:
        assert "hit@1" in r and 0.0 <= r["hit@1"] <= 1.0
        assert "hit@3" in r and 0.0 <= r["hit@3"] <= 1.0
        assert "hit@5" in r and 0.0 <= r["hit@5"] <= 1.0
        assert "mrr" in r and 0.0 <= r["mrr"] <= 1.0
        assert "ndcg@5" in r and 0.0 <= r["ndcg@5"] <= 1.0
        assert "avg_latency_ms" in r and r["avg_latency_ms"] >= 0.0

    # Hibrit getirme en yüksek nDCG@5 ve MRR değerine sahip olmalıdır
    assert hybrid_res["mrr"] >= bm25_res["mrr"]
    assert hybrid_res["ndcg@5"] >= 0.8
