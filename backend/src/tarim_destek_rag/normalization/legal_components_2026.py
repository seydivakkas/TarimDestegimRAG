"""Stage legal 2026 coefficient-derived component rates; never approve implicitly.

Source decision texts have been cross-checked, but original Gazette PDF bytes have
not been independently hashed/reviewed. Each staged record is DRAFT; the source
version uses an explicit non-hash marker. Runtime payment paths fail closed.
"""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from tarim_destek_rag.database.models import (
    SourceModel,
    SourceVersionModel,
    SupportProgramModel,
    VerifiedSupportRateModel,
)


CATALOG = (
    Path(__file__).resolve().parents[4] / "configs"
    / "2026_documented_component_rates_draft.json"
)
UNVERIFIED_CONTENT_HASH = "UNVERIFIED_PRIMARY_PDF_BYTES"
OFFICIAL_11781_URL = (
    "https://www.resmigazete.gov.tr/eskiler/2026/09/20260908-7.pdf"
)
PROGRAMS = {
    "BASIC_SUPPORT_2026",
    "PLANNED_PRODUCTION_2026",
    "CERTIFIED_SEED_2026",
    "CERTIFIED_SAPLING_2026",
    "WATER_RESTRICTION_2026",
}


def _positive_decimal(s: str) -> Decimal:
    if not isinstance(s, str):
        raise ValueError("Decimal values must be JSON strings")
    try:
        value = Decimal(s)
    except InvalidOperation as exc:
        raise ValueError("Invalid decimal value") from exc
    if not value.is_finite() or value <= 0 or value.as_tuple().exponent < -2:
        raise ValueError("Rate must be positive with at most two decimal places")
    return value


def load_component_catalog(path: str | Path = CATALOG) -> dict:
    """Validate component provenance and independent 2026 ministry totals."""
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if (
        data.get("schema_version") != 1
        or data.get("production_year") != 2026
        or data.get("approval_policy") != "NEVER_AUTO_APPROVE"
        or data.get("source_version", {}).get("content_hash") is not None
        or data.get("source_version", {}).get("source_id") != "RG-2026-11781"
    ):
        raise ValueError("Unsupported catalog schema, year, or source approval policy")
    gate = data.get("validation_gate", {})
    if not gate or any(gate.get(k) is not False for k in (
        "approval", "primary_pdf_byte_hash_verified",
        "source_excerpt_human_reviewed", "basin_matrix_verified",
    )):
        raise ValueError("Unverified legal-source gate cannot be bypassed")
    sources = {s["id"]: s for s in data["citations"]}
    if sources.get("RG-2026-11781", {}).get("url") != OFFICIAL_11781_URL:
        raise ValueError("Wrong gazette decision URL")
    if not sources.get("RG-2025-10394", {}).get("url", "").startswith(
        "https://www.resmigazete.gov.tr/eskiler/2025/09/"
    ):
        raise ValueError("Missing 2026 category decision citation")
    coefficient = _positive_decimal(data["base_coefficient"])
    if coefficient != Decimal("367.00"):
        raise ValueError("2026 coefficient must match 11781: 367 TL")
    if "2027" not in " ".join(data.get("not_applicable_to_2026", [])):
        raise ValueError("2027 exclusions are missing")

    seen = set()
    by_program_crop = {}
    for row in data["components"]:
        if row.get("review_status") != "DRAFT":
            raise ValueError("Published catalog must only contain DRAFT records")
        if row.get("program_id") not in PROGRAMS:
            raise ValueError("Unknown 2026 support program")
        if (
            row.get("production_year") != 2026
            or row.get("effective_from") != "2026-01-01"
            or row.get("effective_to") is not None
            or row.get("unit") != "TRY/da"
            or row.get("province") != "*"
            or row.get("district") != "*"
            or not isinstance(row.get("legal_clause"), str)
            or not row["legal_clause"].strip()
            or not isinstance(row.get("conditions"), str)
            or not row["conditions"].strip()
        ):
            raise ValueError("Incomplete period/location/source/conditions metadata")
        if not isinstance(row.get("crop_name"), str) or not row["crop_name"].strip():
            raise ValueError("Blank crop")
        key = (row["program_id"], row["crop_name"])
        if key in seen:
            raise ValueError("Duplicate component/crop in legal catalog")
        seen.add(key)
        amount = _positive_decimal(row["unit_amount"])
        factor = _positive_decimal(row["coefficient"])
        expected = (coefficient * factor).quantize(Decimal("0.01"))
        if amount != expected:
            raise ValueError(f"Coefficient mismatch for {key}: {amount} != {expected}")
        by_program_crop[key] = amount

    if not seen:
        raise ValueError("Empty catalog")
    for crop, published in data["ministry_combined_rounded_whole_tl"].items():
        basic = by_program_crop.get(("BASIC_SUPPORT_2026", crop))
        planned = by_program_crop.get(("PLANNED_PRODUCTION_2026", crop))
        if basic is None or planned is None:
            raise ValueError(f"Public combined amount lacks components: {crop}")
        computed = (basic + planned).quantize(Decimal("1"), rounding=ROUND_HALF_UP)
        if computed != Decimal(str(published)):
            raise ValueError(f"Ministry combined total mismatch: {crop}")
    return data


def stage_component_rates(
    session: Session,
    *,
    path: str | Path = CATALOG,
    apply: bool = False,
) -> int:
    """Dry run by default; on explicit apply insert ONLY DRAFT source-backed rows.

    Database caller owns commit. No automatic approval, no overwrite, no mutation
    of previously verified rates, no edits to the legacy support_amounts table.
    """
    data = load_component_catalog(path)
    if not apply:
        return len(data["components"])

    missing_programs = PROGRAMS - {
        p.id for p in session.scalars(
            select(SupportProgramModel).where(
                SupportProgramModel.id.in_(PROGRAMS),
                SupportProgramModel.year == 2026,
            )
        ).all()
    }
    if missing_programs:
        raise ValueError(f"Unknown support programs: {sorted(missing_programs)}")

    source_id = data["source_version"]["source_id"]
    source = session.get(SourceModel, source_id)
    if source is None:
        source = SourceModel(
            source_id=source_id,
            url=OFFICIAL_11781_URL,
            authority="OFFICIAL_GAZETTE",
            title="11781 Karar / 2026 bitkisel destek katsayisi 367 TL",
            content_type="PDF",
            active=True,
            priority=0,
        )
        session.add(source)
    elif source.url != OFFICIAL_11781_URL:
        raise ValueError("Preexisting source identifier points to a different URL")
    session.flush()

    version = session.scalars(
        select(SourceVersionModel).where(
            SourceVersionModel.source_id == source_id,
            SourceVersionModel.content_hash == UNVERIFIED_CONTENT_HASH,
        )
    ).first()
    if version is None:
        version = SourceVersionModel(
            source_id=source_id,
            version=0,  # Unverified staging; never a reviewed PDF version.
            content_hash=UNVERIFIED_CONTENT_HASH,
            detected_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            effective_from="2026-01-01",
            effective_to=None,
            superseded=False,
        )
        session.add(version)
        session.flush()

    created = 0
    for row in data["components"]:
        existing = session.scalars(
            select(VerifiedSupportRateModel).where(
                VerifiedSupportRateModel.program_id == row["program_id"],
                VerifiedSupportRateModel.crop_name == row["crop_name"],
                VerifiedSupportRateModel.production_year == 2026,
                VerifiedSupportRateModel.province == "*",
                VerifiedSupportRateModel.district == "*",
                VerifiedSupportRateModel.source_version_id == version.id,
            )
        ).first()
        if existing is not None:
            # Do not overwrite reviewer edits or a previously approved rate.
            if (
                existing.unit_amount != Decimal(row["unit_amount"])
                or existing.legal_clause != row["legal_clause"]
            ):
                raise ValueError("Staged record drift: manual reconciliation required")
            continue
        session.add(VerifiedSupportRateModel(
            program_id=row["program_id"],
            crop_name=row["crop_name"],
            production_year=2026,
            province="*",
            district="*",
            unit_amount=Decimal(row["unit_amount"]),
            unit="TRY/da",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            source_version_id=version.id,
            legal_clause=row["legal_clause"],
            review_status="DRAFT",
            approved_by=None,
            approved_at=None,
            review_reference=None,
        ))
        created += 1
    session.flush()
    return created
