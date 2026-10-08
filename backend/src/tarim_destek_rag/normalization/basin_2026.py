"""Source-versioned 2026–27 basin list staging. Never auto-review or approve."""

from __future__ import annotations

import hashlib
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from sqlalchemy import select
from sqlalchemy.orm import Session

from tarim_destek_rag.database.models import (
    ReviewedBasinSnapshotModel, SourceModel, SourceVersionModel,
)

BASIN_SOURCE_ID = "TOB-2026-2027-BASIN-DESENI"
PINNED_BASIN_PDF_SHA256 = "60263e83a953659ecc4f581bcd1ef1a921cf397bc5b4469869852470473f0b21"
BASIN_SOURCE_URL = (
    "https://www.tarimorman.gov.tr/BUGEM/Belgeler/Tar%C4%B1m%20Havzalar%C4%B1/"
    "2026%20Y%C4%B1l%C4%B1%20Planlamaya%20Konu%20Havza%20%C3%9Cr%C3%BCn"
    "%20Deseni%20Listesi.pdf"
)
ALLOWED_CROPS = frozenset({
    "ARPA", "ASPİR", "AYÇİÇEĞİ_YAĞLIK", "BUĞDAY", "FASULYE_KURU",
    "KANOLA", "MERCİMEK", "MISIR_DANE", "NOHUT", "PAMUK_KÜTLÜ",
    "PATATES", "SOĞAN_KURU", "SOYA", "YEM_BITKILERI_GROUP",
})


def validate_basin_catalog(
    data: dict,
    *,
    require_national_coverage: bool = True,
) -> list[dict]:
    if (
        data.get("schema_version") != 1
        or data.get("production_years") != [2026, 2027]
        or data.get("source_url") != BASIN_SOURCE_URL
        or data.get("approval") != "DRAFT_REQUIRES_HUMAN_ROW_AND_FOOTNOTE_REVIEW"
        or data.get("original_pdf_sha256") != PINNED_BASIN_PDF_SHA256
    ):
        raise ValueError("Incorrect source, years, checksum, or draft approval gate")
    pages = data.get("page_count")
    if not isinstance(pages, int) or pages < 1:
        raise ValueError("Invalid page count")
    rows = data.get("districts")
    if not isinstance(rows, list) or not rows:
        raise ValueError("No basin rows")
    if data.get("district_count") != len(rows):
        raise ValueError("Reported district count differs from actual")
    keys = set()
    for row in rows:
        province = row.get("province")
        district = row.get("district")
        crops = row.get("crop_codes")
        page = row.get("source_page")
        if (
            not isinstance(province, str) or not province.strip()
            or not isinstance(district, str) or not district.strip()
            or not isinstance(page, int) or page < 1 or page > pages
            or row.get("review_status") != "DRAFT"
            or row.get("complete_row_verified_by_human") is not False
            or type(row.get("starred_drip_maize_condition")) is not bool
            or not isinstance(crops, list) or not crops
            or len(crops) != len(set(crops)) or not set(crops) <= ALLOWED_CROPS
        ):
            raise ValueError(f"Incomplete or unreviewed province/district row: {province}/{district}")
        key = (province, district)
        if key in keys:
            raise ValueError(f"Duplicate official district: {key}")
        keys.add(key)
    if require_national_coverage and (
        len(rows) < 800 or len({r["province"] for r in rows}) < 75
    ):
        raise ValueError("Partial dataset cannot be treated as national coverage")
    if data.get("province_count") != len({r["province"] for r in rows}):
        raise ValueError("Province count differs from actual data")
    return rows


def stage_basin_districts(
    session: Session,
    path: str | Path,
    *,
    apply: bool = False,
    pdf_path: str | Path | None = None,
) -> int:
    """Explicitly stage full PDF extraction as DRAFT. Caller controls transaction."""
    catalog = json.loads(Path(path).read_text(encoding="utf-8"))
    rows = validate_basin_catalog(catalog)
    if not apply:
        return len(rows)
    if pdf_path is None:
        raise ValueError("Official PDF bytes are mandatory to stage an extraction")
    raw_pdf = Path(pdf_path).read_bytes()
    if (
        not raw_pdf.startswith(b"%PDF-")
        or hashlib.sha256(raw_pdf).hexdigest() != catalog["original_pdf_sha256"]
    ):
        raise ValueError("Official PDF bytes do not match the extracted source hash")
    source = session.get(SourceModel, BASIN_SOURCE_ID)
    if source is None:
        source = SourceModel(
            source_id=BASIN_SOURCE_ID, url=BASIN_SOURCE_URL,
            authority="MINISTRY_OF_AGRICULTURE",
            title="2026-2027 Planlamaya Konu Havza Ürün Deseni",
            content_type="PDF", active=True, priority=0,
        )
        session.add(source)
        session.flush()
    elif source.url != BASIN_SOURCE_URL:
        raise ValueError("Basin source identifier is attached to another URL")
    checksum = catalog["original_pdf_sha256"]
    version = session.scalars(
        select(SourceVersionModel).where(
            SourceVersionModel.source_id == BASIN_SOURCE_ID,
            SourceVersionModel.content_hash == checksum,
        )
    ).first()
    if version is None:
        version = SourceVersionModel(
            source_id=BASIN_SOURCE_ID,
            content_hash=checksum,
            version=0,  # Imported but not authorized.
            detected_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
            superseded=False, effective_from="2026-01-01",
            effective_to="2027-12-31",
        )
        session.add(version)
        session.flush()
    existing = {
        (snap.province, snap.district, snap.production_year): snap
        for snap in session.scalars(
            select(ReviewedBasinSnapshotModel).where(
                ReviewedBasinSnapshotModel.source_version_id == version.id
            )
        )
    }
    created = 0
    for year in (2026, 2027):
        for row in rows:
            key = (row["province"], row["district"], year)
            normalized = json.dumps(
                row["crop_codes"], ensure_ascii=False, separators=(",", ":")
            )
            previous = existing.get(key)
            if previous:
                if (
                    previous.crop_codes_json != normalized
                    or previous.document_page != row["source_page"]
                    or previous.drip_required_for_grain_maize
                    != row["starred_drip_maize_condition"]
                ):
                    raise ValueError(f"Existing basin row changed: {key}; needs review")
                continue
            session.add(ReviewedBasinSnapshotModel(
                province=row["province"],
                district=row["district"],
                production_year=year,
                crop_codes_json=normalized,
                drip_required_for_grain_maize=row["starred_drip_maize_condition"],
                document_page=row["source_page"],
                source_version_id=version.id,
                review_status="DRAFT", coverage_complete=False,
                reviewed_by=None, reviewed_at=None, review_reference=None,
            ))
            created += 1
    session.flush()
    return created
