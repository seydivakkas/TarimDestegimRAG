"""Year-neutral declarative rate candidates and conservative rule interpretation.

This is a PREVIEW and DRAFT staging engine, not a substitute for the signed
production 2026 rate gate. It never says ELIGIBLE or returns a payable amount
until a distinct independently approved release mechanism is implemented.
All values in sample tests are synthetic, never asserted as real 2029 law.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from datetime import date
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from tarim_destek_rag.database.models import (
    DynamicRateModel, SentenceBoundingBoxModel, SourceDocumentModel,
)

_ALLOWED_FIELDS = {
    "cks_registered", "crop_code", "province", "district", "irrigation",
    "certified_seed", "certified_sapling",
}
_RULE_OPS = {"eq", "in"}
_IDENTIFIER = re.compile(r"^[A-Z0-9_]{2,96}$")
_SHA = re.compile(r"^[0-9a-f]{64}$")


def _decimal(value: Any, *, places: int) -> Decimal:
    if not isinstance(value, str):
        raise ValueError("Legal coefficients must be exact decimal strings")
    try:
        d = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError("Invalid legal coefficient") from exc
    if not d.is_finite() or d <= 0 or d.as_tuple().exponent < -places:
        raise ValueError("Nonpositive or overprecise legal coefficient")
    return d


@dataclass(frozen=True)
class CandidateResult:
    status: str
    payable_amount: None
    proposed_unit_amount: Decimal | None
    reason: str
    rule_checks: tuple[str, ...] = ()


class DynamicRuleEngine:
    """Allowlisted, declarative predicates; missing evidence is always REVIEW."""

    @staticmethod
    def check(rule: dict[str, Any], facts: dict[str, Any]) -> tuple[str, ...]:
        if set(rule) != {"all_of"} or not isinstance(rule["all_of"], list):
            raise ValueError("Only explicit all_of rules are accepted")
        if not 1 <= len(rule["all_of"]) <= 24:
            raise ValueError("Empty/too-large legal condition set")
        findings: list[str] = []
        for condition in rule["all_of"]:
            if not isinstance(condition, dict) or set(condition) != {"field", "op", "value"}:
                raise ValueError("Malformed legal condition")
            field = condition["field"]
            op = condition["op"]
            expected = condition["value"]
            if field not in _ALLOWED_FIELDS or op not in _RULE_OPS:
                raise ValueError("Unknown/unreviewed predicate must never be executed")
            if op == "in":
                if (
                    not isinstance(expected, list)
                    or not expected
                    or len(expected) > 1500
                    or any(not isinstance(x, (str, bool)) for x in expected)
                ):
                    raise ValueError("Invalid explicit legal membership list")
                if len({str(x) for x in expected}) != len(expected):
                    raise ValueError("Duplicate items in legal membership list")
            elif not isinstance(expected, (str, bool)):
                raise ValueError("Unbounded predicate value")
            if field not in facts or facts[field] is None:
                findings.append(f"UNKNOWN:{field}")
            elif op == "eq" and facts[field] != expected:
                findings.append(f"NOT_MATCHED:{field}")
            elif op == "in" and facts[field] not in expected:
                findings.append(f"NOT_MATCHED:{field}")
            else:
                findings.append(f"MATCHED:{field}")
        return tuple(findings)


class DynamicRateCatalog:
    """Compute exact Decimal candidate values while preserving legal HOLD."""

    @staticmethod
    def validate(candidate: dict[str, Any]) -> dict[str, Any]:
        required = {
            "schema_version", "program_key", "crop_code", "production_year",
            "province", "district", "base_coefficient", "category_multiplier",
            "official_unit_amount", "unit", "effective_from", "effective_to",
            "source_document_sha256", "source_sentence_id", "conditions",
            "review_status",
        }
        if set(candidate) != required or candidate["schema_version"] != 1:
            raise ValueError("Unsupported year-neutral rate candidate schema")
        if candidate["review_status"] != "DRAFT":
            raise ValueError("Automated imports may NEVER assert legal approval")
        year = candidate["production_year"]
        if not isinstance(year, int) or isinstance(year, bool) or not 2020 <= year <= 2100:
            raise ValueError("Invalid production year")
        if not all(isinstance(candidate[k], str) and _IDENTIFIER.fullmatch(candidate[k])
                   for k in ("program_key", "crop_code")):
            raise ValueError("Invalid year-neutral program/crop ID")
        if candidate["province"] != "*" or candidate["district"] != "*":
            if not all(isinstance(candidate[k], str) and len(candidate[k]) <= 64
                       and candidate[k] not in ("", "*") for k in ("province", "district")):
                raise ValueError("Invalid explicitly scoped geography")
        if candidate["unit"] != "TRY/da":
            raise ValueError("Unsupported legal monetary unit")
        if not isinstance(candidate["source_sentence_id"], int) or candidate["source_sentence_id"] <= 0:
            raise ValueError("Legal PDF sentence evidence id is mandatory")
        if not _SHA.fullmatch(candidate["source_document_sha256"]):
            raise ValueError("Source SHA-256 must match a verified PDF version")
        start = date.fromisoformat(candidate["effective_from"])
        end_raw = candidate["effective_to"]
        end = date.fromisoformat(end_raw) if end_raw else None
        if end is not None and end < start:
            raise ValueError("Invalid effective dates")
        # A 2030 production period may be introduced in 2029, but cannot be
        # silently imported from a totally unrelated historical period.
        if start.year not in (year - 1, year):
            raise ValueError("Year and legal-effective period need manual reconciliation")
        base = _decimal(candidate["base_coefficient"], places=2)
        multiplier = _decimal(candidate["category_multiplier"], places=4)
        value = _decimal(candidate["official_unit_amount"], places=2)
        computed = (base * multiplier).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if computed != value:
            raise ValueError("Source published amount differs from coefficient formula")
        DynamicRuleEngine.check(candidate["conditions"], {})
        return candidate

    @classmethod
    def stage(cls, session: Session, candidate: dict[str, Any]) -> DynamicRateModel:
        cls.validate(candidate)
        evidence = session.get(SentenceBoundingBoxModel, candidate["source_sentence_id"])
        if evidence is None or evidence.review_status != "DRAFT":
            raise ValueError("Original source PDF clause is not staged")
        document = session.get(SourceDocumentModel, evidence.document_id)
        if document is None or (
            document.production_year != candidate["production_year"]
            or document.document_sha256 != candidate["source_document_sha256"]
            or document.review_status != "DRAFT"
        ):
            raise ValueError("PDF clause is not anchored to requested production year")
        key = {
            "program_key": candidate["program_key"], "crop_code": candidate["crop_code"],
            "production_year": candidate["production_year"],
            "province": candidate["province"], "district": candidate["district"],
            "source_sentence_id": evidence.id,
        }
        existing = session.scalar(select(DynamicRateModel).filter_by(**key))
        if existing is not None:
            if (
                existing.base_coefficient != Decimal(candidate["base_coefficient"])
                or existing.category_multiplier != Decimal(candidate["category_multiplier"])
                or existing.proposed_unit_amount != Decimal(candidate["official_unit_amount"])
                or existing.effective_from != date.fromisoformat(candidate["effective_from"])
                or existing.review_status != "DRAFT"
            ):
                raise ValueError("Conflicting rate candidate cannot overwrite prior version")
            return existing
        row = DynamicRateModel(
            **key, base_coefficient=Decimal(candidate["base_coefficient"]),
            category_multiplier=Decimal(candidate["category_multiplier"]),
            proposed_unit_amount=Decimal(candidate["official_unit_amount"]),
            unit="TRY/da",
            effective_from=date.fromisoformat(candidate["effective_from"]),
            effective_to=(
                date.fromisoformat(candidate["effective_to"])
                if candidate["effective_to"] else None
            ),
            review_status="DRAFT",
        )
        session.add(row)
        session.flush()
        return row

    @staticmethod
    def preview(
        candidate: dict[str, Any],
        *,
        year: int,
        facts: dict[str, Any],
    ) -> CandidateResult:
        DynamicRateCatalog.validate(candidate)
        if candidate["production_year"] != year:
            return CandidateResult("REVIEW", None, None, "Wrong legal production year")
        conditions = DynamicRuleEngine.check(candidate["conditions"], facts)
        if any(x.startswith("UNKNOWN:") for x in conditions):
            return CandidateResult(
                "REVIEW", None, None, "Missing required farmer/legal facts", conditions
            )
        if any(x.startswith("NOT_MATCHED:") for x in conditions):
            return CandidateResult(
                "REVIEW", None, None, "Potential exception/exclusion needs legal review", conditions
            )
        # The displayed candidate is informational, NEVER a right or payment.
        return CandidateResult(
            "REVIEW", None, Decimal(candidate["official_unit_amount"]),
            "DRAFT simulated rate; only signed legal activation can authorize payment",
            conditions,
        )

    @staticmethod
    def read_json(path: Path) -> dict[str, Any]:
        payload = json.loads(path.read_text(encoding="utf-8"))
        return DynamicRateCatalog.validate(payload)
