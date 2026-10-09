# ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
# Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlı olarak paylaşılmıştır.
# YASAKLAR: Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz, tersine mühendislik yapılamaz.
# İZİN VERİLEN KULLANIM: GitHub üzerinde görüntüleme ve inceleme.

"""P0-10.4 deterministic, fail-closed legal-inventory and EK-20 review auditor.

This module does NOT determine entitlement or activate payable rates.
A targeted inventory is not evidence of a complete official Gazette search.
"""
from __future__ import annotations

import argparse
import json
from datetime import date
from pathlib import Path
from typing import Any

REQUIRED_TYPES = {"DECISION", "DECISION_AMENDMENT", "COMMUNIQUE",
                  "COMMUNIQUE_AMENDMENT", "REPEALED_COMMUNIQUE"}
REQUIRED_YEARS = (2025, 2026, 2027)
REQUIRED_IDS = {
    "decision_8859", "communique_2024_39", "communique_2025_13",
    "decision_10394", "communique_2025_42", "decision_11781",
    "repealed_2022_32", "repealed_2022_34", "repealed_2023_48",
}


class CoverageContractError(ValueError):
    """Inventory is ambiguous, contradictory, or structurally inconsistent."""


def _parse_date(value: str) -> date:
    try:
        return date.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise CoverageContractError(f"Invalid ISO legal date: {value!r}") from exc


def validate_inventory(inventory: dict[str, Any]) -> None:
    docs = inventory.get("documents")
    if not isinstance(docs, list) or not docs:
        raise CoverageContractError("Empty inventory")
    by_id = {d["id"]: d for d in docs}
    if len(by_id) != len(docs):
        raise CoverageContractError("Duplicate legal document ID")
    if not REQUIRED_IDS.issubset(by_id):
        raise CoverageContractError("Missing identified official amendments/repeal targets")
    if inventory.get("coverage_status") != "INCOMPLETE":
        raise CoverageContractError("Targeted inventory must never claim completeness")
    if inventory.get("exhaustive_archive_index_scan_completed") is not False:
        raise CoverageContractError("No full Gazette/Ministry archive proof")
    if inventory.get("legal_approval") is not False:
        raise CoverageContractError("Missing independent legal reviewer approval")

    for d in docs:
        if d["kind"] not in REQUIRED_TYPES:
            raise CoverageContractError(f"Unrecognized legal type: {d['id']}")
        published = _parse_date(d["published"])
        if "effective_date" in d and d["effective_date"] is not None:
            _parse_date(d["effective_date"])
        for dt in d.get("article_effective_exceptions", {}).values():
            _parse_date(dt)
        for dt in d.get("retroactive_validity_from", {}).values():
            if _parse_date(dt) > published:
                raise CoverageContractError("Retroactive validity cannot begin after publication")
        if d.get("retroactive_valid_from"):
            if _parse_date(d["retroactive_valid_from"]) > published:
                raise CoverageContractError("Retroactive validity is after publication")
        for refkey in ("amends", "implements", "repealed_by"):
            target = d.get(refkey)
            if target and target not in by_id:
                raise CoverageContractError(f"Broken {refkey} reference for {d['id']}")
        if d.get("original_sha256") is not None:
            sha = d["original_sha256"]
            if not isinstance(sha, str) or len(sha) != 64 or any(c not in "0123456789abcdef" for c in sha):
                raise CoverageContractError(f"Invalid original SHA-256 pin: {d['id']}")
        if d["kind"] in {"DECISION_AMENDMENT", "COMMUNIQUE_AMENDMENT"}:
            if not d.get("amends"):
                raise CoverageContractError("Amendment without an explicit base document")
        if d["kind"] == "REPEALED_COMMUNIQUE" and not d.get("repealed_by"):
            raise CoverageContractError("Repealed legal source without its repealer")

    for doc_id in by_id:
        visiting: set[str] = set()
        current = doc_id
        while current:
            if current in visiting:
                raise CoverageContractError("Cycle in legal-amendment/repeal relations")
            visiting.add(current)
            d = by_id[current]
            current = d.get("amends") or d.get("implements") or d.get("repealed_by")
    if by_id["communique_2025_13"]["retroactive_valid_from"] != "2025-01-01":
        raise CoverageContractError("Retroactive 2025/13 baseline omitted")
    if by_id["communique_2025_42"].get("preserves_prior_year") != [2025]:
        raise CoverageContractError("2025 transition preservation omitted")
    if by_id["decision_10394"].get("preserves_prior_year") != [2025]:
        raise CoverageContractError("Decision 10394 2025 transition omitted")

    amendment_dates = [
        by_id[x]["published"] for x in (
            "communique_2025_13", "communique_2025_42"
        )
    ]
    if amendment_dates != sorted(amendment_dates):
        raise CoverageContractError("Amendment order must reflect publication chronology")


def validate_ek20(annex: dict[str, Any], source_manifest: dict[str, Any]) -> None:
    pinned = {
        d["id"]: d["original_sha256"]
        for d in source_manifest.get("sources", [])
    }
    if annex.get("source_sha256") != pinned.get("RG_AMENDMENT_2025_42_ANNEX"):
        raise CoverageContractError("EK-20 visual table not bound to pinned original PDF")
    if annex.get("production_year") != 2026 or annex.get("table_pdf_page") != 1:
        raise CoverageContractError("Only original 2026 EK-20 page 1 has been examined")
    if annex.get("source_pdf_page_count") != 1:
        raise CoverageContractError("Original source page count diverged")
    if annex.get("unit") != "TRY_PER_DECARE":
        raise CoverageContractError("Unsupported rate unit")
    if annex.get("transcription_status") != "VISUAL_TRANSCRIPTION_PENDING_INDEPENDENT_REVIEW":
        raise CoverageContractError("No independent table reviewer has approved the image")
    if annex.get("automatic_rate_activation") is not False:
        raise CoverageContractError("Visual transcript must not become a payable rate")
    rows = annex.get("rows", [])
    if len(rows) != 12 or len({r["row_id"] for r in rows}) != len(rows):
        raise CoverageContractError("Incomplete/duplicate 2026 EK-20 visual rows")
    for r in rows:
        cells = ["biological_tl_da", "biotechnical_tl_da",
                 "feromone_trap_tl_da", "feromone_only_tl_da"]
        if not any(r[c] is not None for c in cells):
            raise CoverageContractError("Row without a visible amount")
        for cell in cells:
            val = r[cell]
            if val is not None and (not isinstance(val, int) or val < 0):
                raise CoverageContractError("Cell must be a nonnegative integer or null (dash)")
    lookup = {r["row_id"]: r for r in rows}
    greenhouse = lookup["greenhouse_mixed"]
    citrus = lookup["citrus"]
    if greenhouse["biological_tl_da"] + greenhouse["feromone_trap_tl_da"] != annex["package_support"]["greenhouse_kobuks_tl_da"]:
        raise CoverageContractError("Greenhouse package is inconsistent with its table cells")
    if citrus["biological_tl_da"] + citrus["feromone_trap_tl_da"] != annex["package_support"]["open_field_tl_da"]:
        raise CoverageContractError("Open-field package is inconsistent with its table cells")
    if lookup["olive"]["biotechnical_tl_da"] != 310:
        raise CoverageContractError("Olive support row mismatch")
    if lookup["open_tomato"]["feromone_only_tl_da"] != 250:
        raise CoverageContractError("Open tomato only-pheromone row mismatch")


def audit_year(inventory: dict[str, Any], year: int) -> dict[str, Any]:
    validate_inventory(inventory)
    if year not in REQUIRED_YEARS:
        raise CoverageContractError("Requested production year out of scope")
    by_id = {d["id"]: d for d in inventory["documents"]}
    required = [
        d["id"] for d in inventory["documents"]
        if year in d.get("production_years", [])
        or d["kind"] == "REPEALED_COMMUNIQUE"
    ]
    unpinned = [x for x in required if not by_id[x].get("original_sha256")]
    temporal = []
    if year == 2025:
        temporal = ["2025/13_RETROACTIVE_FROM_2025_01_01",
                    "10394_AND_2025_42_PRESERVE_2025_PRECHANGE",
                    "11781_ARTICLE_4_RETROACTIVE_FROM_2025_01_01_REVIEW"]
    elif year == 2026:
        temporal = ["10394_EFFECTIVE_2026_01_01",
                    "2025_42_EFFECTIVE_2026_01_01",
                    "11781_ARTICLE_1_RETROACTIVE_2026_01_01_REVIEW"]
    else:
        temporal = ["11781_GENERAL_EFFECT_2027_01_01",
                    "2027_GAZETTE_FUTURE_UPDATES_NOT_FULLY_PUBLISHED_AS_OF_AUDIT"]
    return {
        "year": year,
        "status": "HOLD",
        "source_inventory_is_complete": False,
        "required_source_ids": required,
        "unpinned_or_unarchived_source_ids": unpinned,
        "legal_time_review_flags": temporal,
        "missing_gates": inventory["unresolved_requirements"],
        "automatic_rate_activation": False,
    }


def build_report(inventory: dict[str, Any], annex: dict[str, Any],
                 originals: dict[str, Any]) -> dict[str, Any]:
    validate_inventory(inventory)
    validate_ek20(annex, originals)
    return {
        "schema_version": 1,
        "source_as_of_date": inventory["as_of_date"],
        "ek20_original_pdf_visual_table_status": "TRANSCRIBED_NEEDS_INDEPENDENT_REVIEW",
        "ek20_rows_transcribed": len(annex["rows"]),
        "inventory_document_count": len(inventory["documents"]),
        "complete_official_coverage_proven": False,
        "production_year_assessments": [
            audit_year(inventory, year) for year in REQUIRED_YEARS
        ],
        "legal_approval": False,
        "payable_activation": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--inventory", type=Path, default=Path("configs/p0_10_4_legal_inventory.json"))
    parser.add_argument("--annex", type=Path, default=Path("configs/p0_10_4_ek20_visual_transcription.json"))
    parser.add_argument("--originals", type=Path, default=Path("configs/p0_10_3_original_source_manifest.json"))
    args = parser.parse_args()
    items = [json.loads(p.read_text(encoding="utf-8")) for p in
             (args.inventory, args.annex, args.originals)]
    result = build_report(*items)
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    # This is an intentionally partial source inventory, so legal closure is HOLD.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
