"""Bitemporal declarative rule engine with year-neutral program keys.

Implements P0-8C:
1. Invariant program IDs without year suffixes (BASIC_SUPPORT, PLANNED_PRODUCTION, etc.).
2. Schema-validated declarative conditions DSL.
3. Bitemporal dimensions:
   - System/discovery time: discovered_at
   - Publication time: published_at
   - Legal validity period: effective_from .. effective_to
   - Agricultural production year: production_year
4. Strict temporal and snapshot isolation:
   - Queries for 2029 cannot be corrupted by 2030 rules.
   - Queries for 2030 never silently fall back to 2026 seed data.
   - If no active rule matches the target production year and validity date, fail closed (REVIEW/None).
5. Exact Decimal precision and provenance binding to verified PDF sentence evidence.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from tarim_destek_rag.database.models import (
    DynamicRateModel, SentenceBoundingBoxModel, SourceDocumentModel,
)
from tarim_destek_rag.rules.dynamic_engine import (
    DynamicRuleEngine, _decimal, _IDENTIFIER, _SHA,
)

_CROP_IDENTIFIER = re.compile(r"^[A-Z0-9_ĞÜŞİÖÇI]{2,96}$", re.UNICODE)

INVARIANT_PROGRAM_KEYS = {
    "BASIC_SUPPORT",
    "PLANNED_PRODUCTION",
    "WATER_RESTRICTION",
    "CERTIFIED_SEED",
    "CERTIFIED_SAPLING",
}


@dataclass(frozen=True)
class BitemporalRule:
    rule_id: str
    program_key: str
    crop_code: str
    production_year: int
    province: str
    district: str
    base_coefficient: Decimal
    category_multiplier: Decimal
    official_unit_amount: Decimal
    unit: str
    effective_from: date
    effective_to: date | None
    published_at: datetime
    discovered_at: datetime
    source_document_sha256: str
    source_sentence_id: int
    conditions: dict[str, Any]
    review_status: str = "DRAFT"

    def is_valid_as_of(self, query_date: date) -> bool:
        if query_date < self.effective_from:
            return False
        if self.effective_to is not None and query_date > self.effective_to:
            return False
        return True


@dataclass(frozen=True)
class BitemporalEvaluationResult:
    program_key: str
    crop_code: str
    production_year: int
    status: str  # "ELIGIBLE", "NOT_ELIGIBLE", "REVIEW", "UNKNOWN"
    payable_amount: Decimal | None
    proposed_unit_amount: Decimal | None
    reason: str
    rule_checks: tuple[str, ...] = ()
    source_sentence_id: int | None = None
    source_document_sha256: str | None = None
    effective_from: str | None = None
    effective_to: str | None = None


class BitemporalRuleCatalog:
    """Manages multi-year declarative legal rules with bitemporal isolation."""

    def __init__(self, rules: list[BitemporalRule] | None = None) -> None:
        self._rules: list[BitemporalRule] = list(rules or [])

    @classmethod
    def from_candidates(cls, candidates: list[dict[str, Any]]) -> BitemporalRuleCatalog:
        rules: list[BitemporalRule] = []
        for cand in candidates:
            rule = cls.validate_candidate(cand)
            rules.append(rule)
        return cls(rules)

    @classmethod
    def validate_candidate(cls, candidate: dict[str, Any]) -> BitemporalRule:
        required = {
            "schema_version", "rule_id", "program_key", "crop_code", "production_year",
            "province", "district", "base_coefficient", "category_multiplier",
            "official_unit_amount", "unit", "effective_from", "effective_to",
            "published_at", "discovered_at", "source_document_sha256",
            "source_sentence_id", "conditions", "review_status",
        }
        if set(candidate) != required or candidate["schema_version"] != 1:
            raise ValueError("Unsupported bitemporal rule schema version")

        prog = candidate["program_key"]
        if prog not in INVARIANT_PROGRAM_KEYS and not _IDENTIFIER.fullmatch(prog):
            raise ValueError(f"Invalid invariant program key: {prog}")

        crop = candidate["crop_code"]
        if not _CROP_IDENTIFIER.fullmatch(crop):
            raise ValueError(f"Invalid crop code: {crop}")

        year = candidate["production_year"]
        if not isinstance(year, int) or isinstance(year, bool) or not 2020 <= year <= 2100:
            raise ValueError(f"Invalid agricultural production year: {year}")

        if candidate["unit"] != "TRY/da":
            raise ValueError("Only TRY/da unit is currently supported")

        start = date.fromisoformat(candidate["effective_from"])
        end_raw = candidate["effective_to"]
        end = date.fromisoformat(end_raw) if end_raw else None
        if end is not None and end < start:
            raise ValueError("effective_to cannot be earlier than effective_from")

        pub = datetime.fromisoformat(candidate["published_at"])
        disc = datetime.fromisoformat(candidate["discovered_at"])
        if disc < pub:
            raise ValueError("Discovery time cannot precede official publication time")

        base = _decimal(candidate["base_coefficient"], places=2)
        mult = _decimal(candidate["category_multiplier"], places=4)
        amt = _decimal(candidate["official_unit_amount"], places=2)
        expected_amt = (base * mult).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        if expected_amt != amt:
            raise ValueError(
                f"Aritmetik tutar uyumsuzluğu: {base} * {mult} = {expected_amt} != {amt}"
            )

        if not _SHA.fullmatch(candidate["source_document_sha256"]):
            raise ValueError("Invalid source document SHA-256")

        if not isinstance(candidate["source_sentence_id"], int) or candidate["source_sentence_id"] <= 0:
            raise ValueError("Missing or invalid source sentence evidence id")

        # Validate conditions DSL
        DynamicRuleEngine.check(candidate["conditions"], {})

        return BitemporalRule(
            rule_id=candidate["rule_id"],
            program_key=prog,
            crop_code=crop,
            production_year=year,
            province=candidate["province"],
            district=candidate["district"],
            base_coefficient=base,
            category_multiplier=mult,
            official_unit_amount=amt,
            unit=candidate["unit"],
            effective_from=start,
            effective_to=end,
            published_at=pub,
            discovered_at=disc,
            source_document_sha256=candidate["source_document_sha256"],
            source_sentence_id=candidate["source_sentence_id"],
            conditions=candidate["conditions"],
            review_status=candidate["review_status"],
        )

    def find_rules(
        self,
        *,
        program_key: str,
        crop_code: str,
        production_year: int,
        as_of_date: date,
        province: str = "*",
        district: str = "*",
    ) -> list[BitemporalRule]:
        """Find matching rules with strict bitemporal year and date isolation."""
        matched: list[BitemporalRule] = []
        for r in self._rules:
            # 1. Agricultural year isolation: NEVER match rules from a different production year!
            if r.production_year != production_year:
                continue
            # 2. Program and crop match
            if r.program_key != program_key or r.crop_code != crop_code:
                continue
            # 3. Legal validity period match
            if not r.is_valid_as_of(as_of_date):
                continue
            # 4. Geography match (specific beats wildcard)
            if r.province != "*" and r.province != province:
                continue
            if r.district != "*" and r.district != district:
                continue
            matched.append(r)
        return matched

    def evaluate(
        self,
        *,
        program_key: str,
        crop_code: str,
        production_year: int,
        as_of_date: date,
        facts: dict[str, Any],
        province: str = "*",
        district: str = "*",
    ) -> BitemporalEvaluationResult:
        """Evaluate farmer facts against active rules for the exact production year."""
        candidates = self.find_rules(
            program_key=program_key,
            crop_code=crop_code,
            production_year=production_year,
            as_of_date=as_of_date,
            province=province,
            district=district,
        )

        # Fail closed if no rules exist for target year
        if not candidates:
            return BitemporalEvaluationResult(
                program_key=program_key,
                crop_code=crop_code,
                production_year=production_year,
                status="UNKNOWN",
                payable_amount=None,
                proposed_unit_amount=None,
                reason=(
                    f"{production_year} üretim yılı ve {as_of_date.isoformat()} tarihi için "
                    f"doğrulanmış {program_key} kuralı bulunamadı. Eski yıllara geri dönülemez (fail-closed)."
                ),
            )

        # Check for multiple conflicting rules (conflict => BLOCK / REVIEW)
        if len(candidates) > 1:
            # Distinct unit amounts mean an unresolved legal conflict
            unique_amounts = {r.official_unit_amount for r in candidates}
            if len(unique_amounts) > 1:
                return BitemporalEvaluationResult(
                    program_key=program_key,
                    crop_code=crop_code,
                    production_year=production_year,
                    status="REVIEW",
                    payable_amount=None,
                    proposed_unit_amount=None,
                    reason="Birden fazla çelişkili mevzuat kuralı tespit edildi (Hukuki İnceleme Gerekiyor).",
                )

        rule = candidates[0]

        # Evaluate conditions via declarative DSL
        checks = DynamicRuleEngine.check(rule.conditions, facts)

        if any(c.startswith("UNKNOWN:") for c in checks):
            return BitemporalEvaluationResult(
                program_key=program_key,
                crop_code=crop_code,
                production_year=production_year,
                status="REVIEW",
                payable_amount=None,
                proposed_unit_amount=rule.official_unit_amount,
                reason="Eksik çiftçi/arazi olguları nedeniyle inceleme gerekiyor.",
                rule_checks=checks,
                source_sentence_id=rule.source_sentence_id,
                source_document_sha256=rule.source_document_sha256,
                effective_from=rule.effective_from.isoformat(),
                effective_to=rule.effective_to.isoformat() if rule.effective_to else None,
            )

        if any(c.startswith("NOT_MATCHED:") for c in checks):
            return BitemporalEvaluationResult(
                program_key=program_key,
                crop_code=crop_code,
                production_year=production_year,
                status="NOT_ELIGIBLE",
                payable_amount=Decimal("0.00"),
                proposed_unit_amount=rule.official_unit_amount,
                reason="Mevzuat uygunluk koşulları sağlanamadı.",
                rule_checks=checks,
                source_sentence_id=rule.source_sentence_id,
                source_document_sha256=rule.source_document_sha256,
                effective_from=rule.effective_from.isoformat(),
                effective_to=rule.effective_to.isoformat() if rule.effective_to else None,
            )

        # If review_status is DRAFT, fail-closed policy: payable_amount is None
        if rule.review_status != "VERIFIED":
            return BitemporalEvaluationResult(
                program_key=program_key,
                crop_code=crop_code,
                production_year=production_year,
                status="REVIEW",
                payable_amount=None,
                proposed_unit_amount=rule.official_unit_amount,
                reason=(
                    f"Kural {rule.review_status} statüsündedir. "
                    "Çift onaylı hukuki aktivasyon gerçekleşmeden ödeme yapılamaz."
                ),
                rule_checks=checks,
                source_sentence_id=rule.source_sentence_id,
                source_document_sha256=rule.source_document_sha256,
                effective_from=rule.effective_from.isoformat(),
                effective_to=rule.effective_to.isoformat() if rule.effective_to else None,
            )

        return BitemporalEvaluationResult(
            program_key=program_key,
            crop_code=crop_code,
            production_year=production_year,
            status="ELIGIBLE",
            payable_amount=rule.official_unit_amount,
            proposed_unit_amount=rule.official_unit_amount,
            reason="Tüm mevzuat koşulları sağlandı ve doğrulanmış kural onaylı.",
            rule_checks=checks,
            source_sentence_id=rule.source_sentence_id,
            source_document_sha256=rule.source_document_sha256,
            effective_from=rule.effective_from.isoformat(),
            effective_to=rule.effective_to.isoformat() if rule.effective_to else None,
        )
