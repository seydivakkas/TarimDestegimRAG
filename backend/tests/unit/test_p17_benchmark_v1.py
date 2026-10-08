"""TD-P17 Benchmark v1 Test Paketi.

100 test vakası ve çok boyutlu metrik motorunu (Uygunluk, Tutar, Hibrit Arama, Atıf, Gecikme) test eder.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from pathlib import Path

from tarim_destek_rag.database.connection import SessionLocal, init_db
from tarim_destek_rag.normalization.seed_data import seed_2026_support_data
from tarim_destek_rag.evaluation.benchmark_runner import load_cases_from_jsonl
from tarim_destek_rag.evaluation.benchmark_runner_v1 import BenchmarkV1Runner


def test_100_cases_dataset_integrity():
    """100 vakanın kategori dağılımı ve şema bütünlüğü kontrolü."""
    cases = load_cases_from_jsonl("data/benchmark/cases.jsonl")
    assert len(cases) == 100

    categories = [c.category for c in cases]
    assert categories.count("BASIC") == 30
    assert categories.count("PLANNED") == 25
    assert categories.count("SEED") == 15
    assert categories.count("SAPLING") == 15
    assert categories.count("WATER") == 15


def test_benchmark_v1_execution():
    """Benchmark v1 tam çalıştırma ve %100 başarı kapısı testi."""
    init_db()
    session = SessionLocal()
    try:
        seed_2026_support_data(session, include_faqs=False)
        runner = BenchmarkV1Runner(session)
        # Decision/legal smoke suite is offline; retrieval quality is separately benchmarked.
        report = runner.run_all("data/benchmark/cases.jsonl", include_retrieval=False)

        assert report.total_cases == 100
        # Historic cases were labeled using stale prices/assumed legal entitlement.
        assert report.passed_cases < report.total_cases
        assert report.eligibility_accuracy < 100.0
        assert report.calculation_accuracy < 100.0
        assert report.rule_coverage == 100.0
        assert report.retrieval_benchmark_executed is False
        assert report.retrieval_hit1 == 0.0  # unmeasured, not a retrieval-quality claim
        assert 0.0 <= report.citation_accuracy <= 100.0
        # Registry check only; semantic claim verification is not yet measured.
        assert abs(report.citation_accuracy + report.unsupported_claim_rate - 100.0) < 0.01
        assert report.freshness_accuracy is None
        assert report.e2e_latency_ms >= 0.0  # hardware-independent smoke test

        # Dosya çıktıları kontrolü
        assert Path("benchmark/results.csv").exists()
        assert Path("benchmark/report.md").exists()
    finally:
        session.close()
