"""Authoritative 2026 water restriction *draft* catalog, not planning-basin flags.

2024/39 Article 6(3)(a) enumerates 52 districts, 11 provinces.
2025/42, effective 2026-01-01, repeals Article 6(3)(c)'s drip exception
and adds the grain maize/potato exclusion under Article 17(2)(j).

All records are DRAFT until a complete national scope has two independent
signatures binding BOTH instruments. No use of 2020 explanatory figures as
separate payment law; no fallback to historical water_restrictions seed.
"""

from __future__ import annotations

import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from tarim_destek_rag.database.models import (
    ReviewedWaterRestrictionScopeModel, SourceModel, SourceVersionModel,
)

CATALOG = Path(__file__).resolve().parents[4] / "configs/2026_water_restriction_52_draft.json"
PRIMARY_ID = "TOB-2024-39-WATER-LIST"
AMENDMENT_ID = "RG-2025-42-WATER-EXCEPTIONS"
PRIMARY_URL = (
    "https://www.tarimorman.gov.tr/BUGEM/Belgeler/Tar%C4%B1m%20Havzalar%C4%B1/"
    "2024-39%20Bitkisel%20%C3%9Cretime%20Y%C3%B6nelik%20Desteklemeler%20ile%20"
    "Di%C4%9Fer%20Baz%C4%B1%20Tar%C4%B1msal%20Desteklemelere%20%C3%96deme%20"
    "Yap%C4%B1lmas%C4%B1na%20Dair%20Tebli%C4%9F%20%28Tebli%C4%9F%20No%202024-39%29.pdf"
)
AMENDMENT_URL = "https://resmigazete.gov.tr/eskiler/2025/12/20251230-9.htm"

# An independent, code-reviewed whitelist from 2024/39 Article 6(3)(a);
# merely editing the JSON to add a 53rd district or replace one will fail CI.
PINNED_DISTRICTS = frozenset(
    pair.split("/", 1)[0] + "/" + pair.split("/", 1)[1] for pair in (
        "AKSARAY/MERKEZ", "AKSARAY/ESKİL", "AKSARAY/GÜLAĞAÇ",
        "AKSARAY/GÜZELYURT", "AKSARAY/SULTANHANI",
        "ANKARA/BALA", "ANKARA/GÖLBAŞI", "ANKARA/HAYMANA", "ANKARA/ŞEREFLİKOÇHİSAR",
        "ESKİŞEHİR/ALPU", "ESKİŞEHİR/BEYLİKOVA", "ESKİŞEHİR/ÇİFTELER",
        "ESKİŞEHİR/MAHMUDİYE", "ESKİŞEHİR/MİHALIÇÇIK", "ESKİŞEHİR/SİVRİHİSAR",
        "HATAY/KUMLU", "HATAY/REYHANLI",
        "KARAMAN/AYRANCI", "KARAMAN/KAZIMKARABEKİR", "KARAMAN/MERKEZ",
        "KIRŞEHİR/BOZTEPE", "KIRŞEHİR/MUCUR",
        "KONYA/AKÖREN", "KONYA/AKŞEHİR", "KONYA/ALTINEKİN",
        "KONYA/CİHANBEYLİ", "KONYA/ÇUMRA", "KONYA/DERBENT",
        "KONYA/DOĞANHİSAR", "KONYA/EMİRGAZİ", "KONYA/EREĞLİ",
        "KONYA/GÜNEYSINIR", "KONYA/HALKAPINAR", "KONYA/KADINHANI",
        "KONYA/KARAPINAR", "KONYA/KARATAY", "KONYA/KULU",
        "KONYA/MERAM", "KONYA/SARAYÖNÜ", "KONYA/SELÇUKLU", "KONYA/TUZLUKÇU",
        "MARDİN/ARTUKLU", "MARDİN/DERİK", "MARDİN/KIZILTEPE",
        "NEVŞEHİR/ACIGÖL", "NEVŞEHİR/DERİNKUYU", "NEVŞEHİR/GÜLŞEHİR",
        "NİĞDE/ALTUNHİSAR", "NİĞDE/BOR", "NİĞDE/ÇİFTLİK", "NİĞDE/MERKEZ",
        "ŞANLIURFA/VİRANŞEHİR",
    )
)


def load_water_catalog(path: Path | str = CATALOG) -> dict:
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    sources = doc.get("legal_basis", [])
    if (
        doc.get("schema_version") != 1
        or doc.get("production_year") != 2026
        or doc.get("district_count") != 52
        or doc.get("province_count") != 11
        or doc.get("approval") != "DRAFT_REQUIRES_LEGAL_TWO_PERSON_SIGNOFF"
        or not isinstance(sources, list) or len(sources) != 2
        or sources[0].get("instrument") != "2024/39"
        or sources[0].get("url") != PRIMARY_URL
        or sources[1].get("instrument") != "2025/42"
        or sources[1].get("url") != AMENDMENT_URL
        or sources[1].get("effective_from") != "2026-01-01"
        or doc.get("rule_effective_from") != "2026-01-01"
        or doc.get("rule_effective_to") != "2026-12-31"
        or doc.get("constraints", {}).get("coverage_complete") is not False
    ):
        raise ValueError("Invalid 2026 legal source, effective period, or DRAFT constraints")
    policy = doc.get("exception_policies", {})
    if (
        policy.get("2026_2024_39_ART_6_3_C") != "REPEALED_AS_OF_2026-01-01"
        or policy.get("2026_2024_39_ART_17_2_J") !=
        "MAIZE_GRAIN_AND_POTATO_EXCLUSION_IN_DECLARED_WATER_RESTRICTION_ZONES_FOR_SUPPORTS_UNDER_ARTICLES_5_6_7"
        or policy.get("2026_2024_39_ART_6_3_B") !=
        "ADDITIONAL_WATER_SUPPORT_FOR_TABLO_3_CROPS_ON_IRRIGATED_LAND_ONLY"
        or policy.get("2025_ALREADY_BEGUN_APPLICATIONS") !=
        "GRANDFATHER_PREVIOUS_2025_RULES_ONLY"
    ):
        raise ValueError("Missing 2026 legal exceptions")
    rows = doc.get("districts", [])
    if not isinstance(rows, list) or len(rows) != 52:
        raise ValueError("Incomplete 2026 national district scope")
    found = set()
    for row in rows:
        if (
            not isinstance(row, dict)
            or not isinstance(row.get("province"), str)
            or not isinstance(row.get("district"), str)
            or row.get("review_status") != "DRAFT"
            or row.get("authoritative_membership_approved") is not False
        ):
            raise ValueError("An extracted district was altered or auto-approved")
        key = f'{row["province"]}/{row["district"]}'
        if key in found:
            raise ValueError("Duplicate water-restricted district")
        found.add(key)
    if found != PINNED_DISTRICTS:
        raise ValueError("2026 water scope differs from legal Article 6(3)(a) enumerated 52")
    if len({pair.split("/", 1)[0] for pair in found}) != 11:
        raise ValueError("Expected 11 provinces")
    return doc


def stage_water_scope(
    session: Session | None,
    *,
    path: Path | str = CATALOG,
    apply: bool = False,
    original_pdf_path: Path | str | None = None,
    amendment_html_path: Path | str | None = None,
) -> int:
    """Dry-run by default; explicit apply creates an inert, dual-source DRAFT."""
    doc = load_water_catalog(path)
    if not apply:
        return 52
    if session is None or original_pdf_path is None or amendment_html_path is None:
        raise ValueError("Explicit original PDF + amendment Gazette HTML required")
    original = Path(original_pdf_path).read_bytes()
    amendment = Path(amendment_html_path).read_bytes()
    if not original.startswith(b"%PDF-") or len(original) < 1000:
        raise ValueError("Missing original published PDF bytes")
    from pypdf import PdfReader

    page = PdfReader(io.BytesIO(original)).pages[8].extract_text()
    folded = page.casefold()
    if not all(token.casefold() in folded for token in ("Karatay", "Kızıltepe", "su kısıtı")):
        raise ValueError("Primary PDF Article 6(3)(a) is not intact")
    if not all(marker in amendment for marker in (b"2025/42", b"MADDE 16")):
        raise ValueError("The 2025/42 amendment HTML cannot be authenticated here")
    versions = []
    for key, url, title, authority, raw in (
        (PRIMARY_ID, PRIMARY_URL, "2024/39 m.6/3(a) legal 52 district scope",
         "MINISTRY_OF_AGRICULTURE", original),
        (AMENDMENT_ID, AMENDMENT_URL, "2025/42 - 2026 water exception changes",
         "OFFICIAL_GAZETTE", amendment),
    ):
        source = session.get(SourceModel, key)
        if source is None:
            source = SourceModel(
                source_id=key, url=url, title=title, authority=authority,
                content_type="PDF" if key == PRIMARY_ID else "HTML",
                active=True, priority=0,
            )
            session.add(source)
            session.flush()
        elif source.url != url:
            raise ValueError("A legal source identity was overwritten")
        digest = hashlib.sha256(raw).hexdigest()
        version = session.scalars(select(SourceVersionModel).where(
            SourceVersionModel.source_id == key,
            SourceVersionModel.content_hash == digest,
        )).first()
        if version is None:
            version = SourceVersionModel(
                source_id=key, content_hash=digest, version=0,
                detected_at=datetime.now(timezone.utc).isoformat(timespec="seconds"),
                effective_from="2026-01-01",
                effective_to="2026-12-31",
                superseded=False,
            )
            session.add(version)
            session.flush()
        versions.append(version)
    national = json.dumps(sorted(PINNED_DISTRICTS), ensure_ascii=False, separators=(",", ":"))
    current = session.scalars(select(ReviewedWaterRestrictionScopeModel).where(
        ReviewedWaterRestrictionScopeModel.production_year == 2026,
        ReviewedWaterRestrictionScopeModel.source_version_id == versions[0].id,
        ReviewedWaterRestrictionScopeModel.amendment_source_version_id == versions[1].id,
    )).first()
    if current is not None:
        if current.district_keys_json != national:
            raise ValueError("Existing water legal evidence differs; new version required")
        return 0
    session.add(ReviewedWaterRestrictionScopeModel(
        production_year=2026, district_keys_json=national,
        source_version_id=versions[0].id,
        amendment_source_version_id=versions[1].id,
        review_status="DRAFT", coverage_complete=False,
        reviewed_by=None, reviewed_at=None, review_reference=None,
    ))
    session.flush()
    return 1
