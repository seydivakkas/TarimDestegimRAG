from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.evaluation.benchmark_runner import (
    DecisionBenchmarkRunner,
    load_cases_from_jsonl,
)
from tarim_destek_rag.normalization.seed_data import seed_2026_support_data


def test_50_cases_decision_benchmark():
    """TD-P10 50 Senaryoluk Deterministik Karar ve Hesaplama Benchmark Kapısı."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)
    session = Session(engine)
    seed_2026_support_data(session, include_faqs=False)

    runner = DecisionBenchmarkRunner(session)
    cases = load_cases_from_jsonl("data/benchmark/cases.jsonl")

    assert len(cases) >= 50, f"En az 50 vaka bekleniyordu, {len(cases)} bulundu."

    metrics = runner.run_suite(cases[:50])

    # Detaylı hata mesajı için
    if metrics.failed_cases > 0:
        print("BAŞARISIZ VAKALAR:", metrics.failures)

    # Historical 50 gold labels use obsolete demo rates/unsourced geographic assumptions.
    # They must NOT be mistaken for a 100% legal compliance report.
    assert metrics.total_cases == 50
    assert metrics.passed_cases + metrics.failed_cases == 50
    assert metrics.failed_cases > 0
    assert metrics.eligibility_accuracy < 100.0
    assert metrics.calculation_accuracy < 100.0
