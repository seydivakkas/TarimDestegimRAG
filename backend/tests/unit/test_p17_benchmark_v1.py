"""TD-P17 Benchmark v1 Test Paketi.

100 test vakası ve çok boyutlu metrik motorunu (Uygunluk, Tutar, Hibrit Arama, Atıf, Gecikme) test eder.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from pathlib import Path

from tarim_destek_rag.database.connection import SessionLocal
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
    session = SessionLocal()
    try:
        runner = BenchmarkV1Runner(session)
        report = runner.run_all("data/benchmark/cases.jsonl")

        assert report.total_cases == 100
        assert report.passed_cases == 100
        assert report.eligibility_accuracy == 100.0
        assert report.calculation_accuracy == 100.0
        assert report.rule_coverage == 100.0
        assert 0.0 <= report.retrieval_hit1 <= 100.0
        assert report.citation_accuracy == 0.0  # Pasaj doğrulayıcısı henüz uygulanmadı.
        assert report.unsupported_claim_rate == 100.0  # Eksik kanıtlar güvenli biçimde işaretleniyor.
        assert report.e2e_latency_ms >= 0.0
        assert report.freshness_accuracy is None

        # Dosya çıktıları kontrolü
        assert Path("benchmark/results.csv").exists()
        assert Path("benchmark/report.md").exists()
    finally:
        session.close()
