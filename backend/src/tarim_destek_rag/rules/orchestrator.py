from sqlalchemy.orm import Session

from tarim_destek_rag.models.farmer_parcel import FarmerProfile, Parcel
from tarim_destek_rag.rules.base import BaseRule, RuleResult
from tarim_destek_rag.rules.rules_impl import (
    BasicSupportRule,
    CertifiedSaplingRule,
    CertifiedSeedRule,
    PlannedProductionRule,
    WaterRestrictionRule,
)


class DecisionOrchestrator:
    """Tüm deterministik kuralları yöneten ve işleten karar orkestratörü."""

    def __init__(self, rules: list[BaseRule] | None = None) -> None:
        self.rules: list[BaseRule] = rules or [
            BasicSupportRule(),
            PlannedProductionRule(),
            CertifiedSeedRule(),
            CertifiedSaplingRule(),
            WaterRestrictionRule(),
        ]

    def evaluate_all(
        self, farmer: FarmerProfile, parcel: Parcel, session: Session
    ) -> list[RuleResult]:
        """Çiftçi ve parsel için tanımlı tüm kuralları deterministik olarak değerlendirir."""
        results: list[RuleResult] = []
        for rule in self.rules:
            res = rule.evaluate(farmer, parcel, session)
            results.append(res)
        return results


decision_orchestrator = DecisionOrchestrator()
