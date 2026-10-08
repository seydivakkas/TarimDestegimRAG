"""Regression tests: fail-closed result semantics and citation set validation."""

from decimal import Decimal
from types import SimpleNamespace

from tarim_destek_rag.calculator.calculator import SupportCalculator
from tarim_destek_rag.evaluation.benchmark_runner_v1 import citations_are_verifiable
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.rules.base import RuleResult


class StubVerifier:
    def verify(self, citation):
        return SimpleNamespace(is_valid=citation == "registered")


def eligible_rule() -> RuleResult:
    return RuleResult(
        rule_id="BASIC_RULE",
        support_id="BASIC_SUPPORT_2026",
        support_name="Temel Destek",
        status=EligibilityStatusEnum.ELIGIBLE,
    )


def test_empty_citation_list_never_passes():
    assert citations_are_verifiable([], StubVerifier()) is False


def test_all_citations_must_pass_registry_check():
    assert citations_are_verifiable(["registered"], StubVerifier()) is True
    assert citations_are_verifiable(["registered", "unknown"], StubVerifier()) is False


def test_missing_rate_requires_manual_verification_not_zero():
    result = SupportCalculator.calculate(eligible_rule(), Decimal("12.4"), None)
    assert result.status == EligibilityStatusEnum.REVIEW
    assert result.estimated_amount is None
    assert result.unit_amount is None
    assert result.metadata["verification_required"] is True


def test_invalid_zero_rate_cannot_be_reported_as_zero_payout():
    result = SupportCalculator.calculate(eligible_rule(), Decimal("12.4"), Decimal("0.00"))
    assert result.status == EligibilityStatusEnum.REVIEW
    assert result.estimated_amount is None


def test_supported_positive_rate_keeps_decimal_precision():
    result = SupportCalculator.calculate(eligible_rule(), Decimal("12.4"), Decimal("465.00"))
    assert result.status == EligibilityStatusEnum.ELIGIBLE
    assert result.estimated_amount == Decimal("5766.00")
