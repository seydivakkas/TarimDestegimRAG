"""Test for Master Plan Section 41 Research Experiments (RQ1-RQ4).

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from tarim_destek_rag.evaluation.research_experiments import (
    run_rq1_experiment,
    run_rq3_experiment,
    run_rq4_experiment,
)


def test_rq1_deterministic_invariance():
    """RQ1: Deterministik kural motoru 50 koşuda sıfır varyans sergilemelidir."""
    rq1 = run_rq1_experiment()
    assert rq1["rule_engine_consistency"] == 100.0
    assert rq1["variance_rule_engine"] == 0.0


def test_rq3_freshness_filter():
    """RQ3: Sürümleme filtresi mülga mevzuat hatalarını engellemelidir."""
    rq3 = run_rq3_experiment()
    assert rq3["freshness_accuracy_filter_on"] == 100.0
    assert rq3["freshness_accuracy_filter_off"] < 100.0


def test_rq4_citation_guard():
    """RQ4: Atıf denetçisi sahte kaynakları tespit edip engellemelidir."""
    rq4 = run_rq4_experiment()
    assert rq4["unsupported_rate_guard_on"] == 0.0
    assert rq4["citation_accuracy_guard_on"] == 100.0
