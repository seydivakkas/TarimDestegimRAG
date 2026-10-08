from abc import ABC, abstractmethod
from typing import Any

from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from tarim_destek_rag.models.farmer_parcel import FarmerProfile, Parcel
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum


class RuleResult(BaseModel):
    """Kural değerlendirme neticesi ve izlenebilirlik izi (Decision Trace)."""

    rule_id: str
    support_id: str
    support_name: str
    status: EligibilityStatusEnum
    passed_checks: list[str] = Field(default_factory=list)
    failed_checks: list[str] = Field(default_factory=list)
    missing_fields: list[str] = Field(default_factory=list)
    source_ids: list[str] = Field(default_factory=list)
    trace: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)


class BaseRule(ABC):
    """Tüm deterministik kuralların temel arayüzü."""

    rule_id: str
    support_id: str
    support_name: str
    default_source_id: str = "RG-2026-BITKISEL"

    @abstractmethod
    def evaluate(self, farmer: FarmerProfile, parcel: Parcel, session: Session) -> RuleResult:
        """Kuralı işletir ve deterministik RuleResult döner."""
        pass
