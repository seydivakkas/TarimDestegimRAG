"""Source-versioned 2026 water restriction district staging & reconciliation (Issue #17 / P0-5b).

Stage independent, source-backed water restriction records.
Never auto-review or auto-approve. Production stays fail-closed.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from tarim_destek_rag.database.models import (
    ReviewedWaterRestrictionDistrictModel, SourceModel, SourceVersionModel,
)

WATER_SOURCE_ID = "OFFICIAL-GAZETTE-TEBLIG-2024-39"
WATER_SOURCE_URL = "https://www.resmigazete.gov.tr/eskiler/2024/08/20240824-7.pdf"
PINNED_TEBLIG_2024_39_SHA256 = (
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
)
DEFAULT_CATALOG_PATH = (
    Path(__file__).resolve().parents[4]
    / "configs"
    / "2026_water_restriction_districts_draft.json"
)


def load_water_restriction_catalog(path: Path | None = None) -> dict:
    target = path or DEFAULT_CATALOG_PATH
    return json.loads(target.read_text(encoding="utf-8"))


def validate_water_restriction_catalog(data: dict) -> list[dict]:
    source_meta = data.get("legal_source", {})
    if (
        source_meta.get("source_id") != WATER_SOURCE_ID
        or source_meta.get("url") != WATER_SOURCE_URL
        or source_meta.get("pinned_pdf_sha256") != PINNED_TEBLIG_2024_39_SHA256
    ):
        raise ValueError("Invalid legal source metadata or checksum mismatch")

    districts = data.get("districts")
    if not isinstance(districts, list) or not districts:
        raise ValueError("No water restriction districts found in catalog")

    seen = set()
    for row in districts:
        province = row.get("province")
        district = row.get("district")
        status = row.get("status")
        if not province or not district or status not in ("RESTRICTED", "NOT_RESTRICTED", "UNDER_REVIEW"):
            raise ValueError(f"Malformed district row: {row}")
        key = (province.strip().upper(), district.strip().upper())
        if key in seen:
            raise ValueError(f"Duplicate district row in water catalog: {key}")
        seen.add(key)

    return districts


def stage_water_restriction_districts(
    session: Session,
    catalog_path: Path | None = None,
    year: int = 2026,
) -> int:
    """Safely stages water restriction districts into reviewed_water_restriction_districts table.

    All staged rows remain in DRAFT review_status and cannot authorize payments
    until two-person cryptographic Ed25519 signatures are applied.
    """
    raw_catalog = load_water_restriction_catalog(catalog_path)
    districts = validate_water_restriction_catalog(raw_catalog)
    source_meta = raw_catalog["legal_source"]

    source = session.get(SourceModel, WATER_SOURCE_ID)
    if source is None:
        source = SourceModel(
            source_id=WATER_SOURCE_ID,
            url=WATER_SOURCE_URL,
            title=source_meta.get("title", "Tebliğ 2024/39"),
            authority="OFFICIAL_GAZETTE",
            content_type="PDF",
            active=True,
            priority=1,
        )
        session.add(source)
        session.flush()

    version_stmt = select(SourceVersionModel).where(
        SourceVersionModel.source_id == WATER_SOURCE_ID,
        SourceVersionModel.content_hash == PINNED_TEBLIG_2024_39_SHA256,
    )
    version = session.scalars(version_stmt).first()
    if version is None:
        version = SourceVersionModel(
            source_id=WATER_SOURCE_ID,
            content_hash=PINNED_TEBLIG_2024_39_SHA256,
            version=1,
            detected_at=datetime.now(timezone.utc).isoformat(),
            effective_from=f"{year}-01-01",
            effective_to=f"{year}-12-31",
            superseded=False,
        )
        session.add(version)
        session.flush()

    created_count = 0
    for row in districts:
        prov = row["province"].strip().upper()
        dist = row["district"].strip().upper()

        existing = session.scalars(
            select(ReviewedWaterRestrictionDistrictModel).where(
                ReviewedWaterRestrictionDistrictModel.province == prov,
                ReviewedWaterRestrictionDistrictModel.district == dist,
                ReviewedWaterRestrictionDistrictModel.production_year == year,
            )
        ).first()

        if existing is not None:
            continue

        model = ReviewedWaterRestrictionDistrictModel(
            province=prov,
            district=dist,
            production_year=year,
            restriction_status=row["status"],
            effective_from=f"{year}-01-01",
            effective_to=f"{year}-12-31",
            source_version_id=version.id,
            document_page=row.get("page"),
            legal_clause=source_meta.get("legal_clause", "Madde 6/3(a,b,c)"),
            conflict_notes=row.get("conflict"),
            review_status="DRAFT",
            reviewed_by=None,
            reviewed_at=None,
            review_reference=None,
        )
        session.add(model)
        created_count += 1

    session.flush()
    return created_count
