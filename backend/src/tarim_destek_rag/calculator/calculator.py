from decimal import ROUND_HALF_UP, Decimal
from typing import Any

from pydantic import BaseModel, Field

from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.rules.base import RuleResult

DISCLAIMER_TEXT = "Tahmini ön değerlendirmedir; resmi ödeme veya hak sahipliği sonucu değildir."


class CalculationResult(BaseModel):
    """Destek tutarı hesaplama çıktısı."""

    support_id: str
    support_name: str
    status: EligibilityStatusEnum
    area_da: Decimal
    unit_amount: Decimal | None
    estimated_amount: Decimal | None
    formula: str
    unit: str = "TRY"
    disclaimer: str = DISCLAIMER_TEXT
    metadata: dict[str, Any] = Field(default_factory=dict)


class SupportCalculator:
    """Python Decimal hassasiyetinde deterministik destek hesaplayıcı."""

    @staticmethod
    def calculate(
        rule_result: RuleResult, area_da: Decimal, unit_amount: Decimal | None
    ) -> CalculationResult:
        """Kural sonucu ve birim tutara göre tahmini hak edişi hesaplar."""
        if rule_result.status != EligibilityStatusEnum.ELIGIBLE:
            return CalculationResult(
                support_id=rule_result.support_id,
                support_name=rule_result.support_name,
                status=rule_result.status,
                area_da=area_da,
                unit_amount=unit_amount,
                estimated_amount=None,
                formula="Hesaplama yapılmadı (Kriterler sağlanmadı veya eksik bilgi var)",
                unit="TRY",
            )

        if unit_amount is None or unit_amount <= Decimal("0.0"):
            return CalculationResult(
                support_id=rule_result.support_id,
                support_name=rule_result.support_name,
                status=rule_result.status,
                area_da=area_da,
                unit_amount=Decimal("0.0"),
                estimated_amount=Decimal("0.0"),
                formula=f"{area_da} da * 0.00 TL/da",
                unit="TRY",
            )

        # Kuruş hassasiyetinde çarpım
        total = (area_da * unit_amount).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        formula = f"{area_da} da * {unit_amount} TL/da = {total} TL"

        return CalculationResult(
            support_id=rule_result.support_id,
            support_name=rule_result.support_name,
            status=rule_result.status,
            area_da=area_da,
            unit_amount=unit_amount,
            estimated_amount=total,
            formula=formula,
            unit="TRY",
        )


support_calculator = SupportCalculator()
