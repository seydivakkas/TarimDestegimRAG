"""Source-backed 2026 combined support reference amounts.

These figures are *not* program-level unit rates and MUST NOT be passed to the
individual entitlement calculator. Ministry announcement provenance is retained.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Mapping


DEFAULT_CATALOG = (
    Path(__file__).resolve().parents[4] / "configs" / "official_support_reference_2026.json"
)


@dataclass(frozen=True)
class CombinedSupportReference:
    crop_codes: tuple[str, ...]
    amount_per_da: Decimal
    production_year: int
    source_url: str
    legal_decision_number: str
    context: str
    rate_type: str = "BASIC_PLUS_PLANNED_REFERENCE_ONLY"
    individual_entitlement_approved: bool = False


@dataclass(frozen=True)
class LegacyRateDiscrepancy:
    crop_code: str
    legacy_sum: Decimal
    official_combined_reference: Decimal
    delta: Decimal


def _positive_currency(value: str) -> Decimal:
    if not isinstance(value, str):
        raise ValueError("Tutar değerleri TL sayısına çevrilmeden önce string tutulmalıdır.")
    try:
        number = Decimal(value)
    except InvalidOperation as exc:
        raise ValueError(f"Geçersiz Decimal tutar: {value!r}") from exc
    if not number.is_finite() or number <= 0 or number.as_tuple().exponent < -2:
        raise ValueError(f"Tutar pozitif, sonlu ve en çok iki ondalıklı olmalıdır: {value!r}")
    return number


def load_official_reference(path: str | Path = DEFAULT_CATALOG) -> dict[str, Any]:
    """Load and validate published combined totals without promoting them to rates."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if data.get("schema_version") != 1 or data.get("production_year") != 2026:
        raise ValueError("Destek kataloğu şeması veya üretim yılı beklenenden farklı.")
    source = data.get("source", {})
    if (
        source.get("published_on") != "2026-09-08"
        or not source.get("url", "").startswith("https://www.tarimorman.gov.tr/")
        or data.get("legal_reference", {}).get("decision_number") != "11781"
    ):
        raise ValueError("Kanonik Bakanlık kaynağı / karar ilişkisi doğrulanamadı.")
    constraints = data.get("legal_use_constraints", {})
    if (
        constraints.get("scope") != "REFERENCE_TOTAL_ONLY"
        or constraints.get("calculate_individual_entitlement_allowed") is not False
        or constraints.get("split_into_program_rates_allowed") is not False
    ):
        raise ValueError("Birleşik referanslar bireysel hesaplama için kullanılamaz.")

    _positive_currency(data["base_support_coefficient"]["amount"])
    if data["base_support_coefficient"].get("production_year") != 2026:
        raise ValueError("Katsayı üretim yılı eşleşmiyor.")
    if data["base_support_coefficient"].get("unit") != "TRY/da":
        raise ValueError("Katsayının birimi TRY/da olmalıdır.")

    seen: set[str] = set()
    records = data.get("combined_support_references", [])
    if not records:
        raise ValueError("Bakanlık kaynaklı birleşik destek verisi eksik.")
    for row in records:
        _positive_currency(row["amount_per_da"])
        crops = row.get("crop_codes")
        if not isinstance(crops, list) or not crops:
            raise ValueError("Bütün destek tutarları için ürün kodu zorunludur.")
        if not isinstance(row.get("context"), str) or not row["context"].strip():
            raise ValueError("Referans tutarın kapsam açıklaması zorunludur.")
        for crop in crops:
            if not isinstance(crop, str) or not crop.strip() or crop in seen:
                raise ValueError(f"Geçersiz veya yinelenen ürün kodu: {crop!r}")
            seen.add(crop)
    return data


def reference_rates_by_crop(
    path: str | Path = DEFAULT_CATALOG,
) -> dict[str, CombinedSupportReference]:
    """Only a non-additive published *combined* rate can be returned."""
    data = load_official_reference(path)
    return {
        crop: CombinedSupportReference(
            crop_codes=tuple(entry["crop_codes"]),
            amount_per_da=_positive_currency(entry["amount_per_da"]),
            production_year=data["production_year"],
            source_url=data["source"]["url"],
            legal_decision_number=data["legal_reference"]["decision_number"],
            context=entry["context"],
        )
        for entry in data["combined_support_references"]
        for crop in entry["crop_codes"]
    }


def find_legacy_rate_discrepancies(
    component_rates: Mapping[tuple[str, str], Decimal],
    path: str | Path = DEFAULT_CATALOG,
) -> list[LegacyRateDiscrepancy]:
    """Flag known disagreements; missing components remain unassessed, never 0."""
    discrepancies: list[LegacyRateDiscrepancy] = []
    for crop, official in reference_rates_by_crop(path).items():
        basic = component_rates.get(("BASIC_SUPPORT_2026", crop))
        planned = component_rates.get(("PLANNED_PRODUCTION_2026", crop))
        if basic is None or planned is None:
            continue
        old_total = Decimal(str(basic)) + Decimal(str(planned))
        if old_total != official.amount_per_da:
            discrepancies.append(
                LegacyRateDiscrepancy(
                    crop_code=crop,
                    legacy_sum=old_total,
                    official_combined_reference=official.amount_per_da,
                    delta=official.amount_per_da - old_total,
                )
            )
    return discrepancies
