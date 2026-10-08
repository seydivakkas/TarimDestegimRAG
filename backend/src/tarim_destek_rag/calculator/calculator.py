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
            # Bilinmeyen/geçersiz birim tutar 0 TL hak ediş demek değildir.
            # ÇKS / havza uygunluğu tek başına mevzuat birim fiyatını doğrulamaz.
            return CalculationResult(
                support_id=rule_result.support_id,
                support_name=rule_result.support_name,
                status=EligibilityStatusEnum.REVIEW,
                area_da=area_da,
                unit_amount=unit_amount,
                estimated_amount=None,
                formula="Birim tutar doğrulanamadı; hesaplama yapılmadı.",
                unit="TRY",
                metadata={
                    "verification_required": True,
                    "reason_code": "MISSING_OR_INVALID_UNIT_AMOUNT",
                },
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
