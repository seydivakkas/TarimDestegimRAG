"""Fail-closed, claim-level official source and amendment impact auditing.

A verified original HTML span is proof of LOCATION, not evidence that a farmer
met the factual condition, a table cell was approved, or a rule is in force.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

_PIN = re.compile(r"[0-9a-f]{64}\Z")
_ARTICLE = re.compile(r"^\s*MADDE\s+(\d+)\s*[-–]", re.I)
_TRANSITION = re.compile(r"^\s*GEÇİCİ\s+MADDE\s+(\d+)\s*[-–]", re.I)


def _normalized_match(quote: str) -> re.Pattern[str]:
    if not isinstance(quote, str) or not 25 <= len(quote) <= 1200:
        raise ValueError("Source quotation is missing or outside allowed bounds")
    return re.compile(r"\s+".join(re.escape(piece) for piece in quote.split()))


def validate_source_span(
    entry: dict[str, Any], manifest: dict[str, Any], archive_root: Path,
) -> dict[str, Any]:
    """Locate one authentic span in an article of a SHA-pinned original HTML."""
    result: dict[str, Any] = {
        "span_id": entry.get("span_id"),
        "source_id": entry.get("source_id"),
        "target_provision": entry.get("target_provision"),
        "source_location_status": "HOLD",
        "legal_status": "HOLD",
        "verified_quote": None,
    }
    try:
        source_id = entry["source_id"]
        sources = [s for s in manifest["sources"] if s.get("id") == source_id]
        if len(sources) != 1:
            raise ValueError("Missing or duplicate original source")
        source = sources[0]
        sha = entry["source_sha256"]
        if (
            not isinstance(sha, str) or not _PIN.fullmatch(sha)
            or source.get("original_sha256") != sha
            or source.get("format") != "html"
            or source.get("url") != entry.get("source_url")
        ):
            raise ValueError("Official source identity/bytes not pinned")
        raw = (archive_root / "originals" / (sha + ".html")).read_bytes()
        if not raw or len(raw) > 2_000_000 or hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError("Original HTML bytes do not match official SHA")
        pattern = _normalized_match(entry["exact_quote"])
        required_article = entry["article"]
        if not re.fullmatch(r"(?:GEÇİCİ )?MADDE \d+", required_article):
            raise ValueError("Invalid legal source article identity")
        document = BeautifulSoup(raw, "html.parser")
        active_article = None
        located = 0
        for node in document.find_all(string=True):
            if node.parent.name in {"script", "style", "title"}:
                continue
            transition = _TRANSITION.search(str(node))
            found_heading = _ARTICLE.search(str(node))
            if transition:
                active_article = "GEÇİCİ MADDE " + transition.group(1)
            elif found_heading:
                active_article = "MADDE " + found_heading.group(1)
            if pattern.search(str(node)):
                if active_article != required_article:
                    raise ValueError("Quote found under different official article")
                if source_id == "RG_COMMUNIQUE_2024_39":
                    # Explicitly listed original paragraphs only; do NOT
                    # interpret a matching word under the wrong article.
                    valid_base = {
                        "BASE_2024_39_ART4_P1": ("MADDE 4", "MADDE 4(1)"),
                        "BASE_2024_39_ART5_P1": ("MADDE 5", "MADDE 5(1)"),
                    }
                    declaration = valid_base.get(entry.get("span_id"))
                    if (declaration != (
                        active_article, entry.get("target_provision")
                    ) or not re.match(r"^\s*\(1\)\s", str(node))):
                        raise ValueError(
                            "Original paragraph (1) identity missing or wrong"
                        )
                located += 1
        if located != 1:
            raise ValueError("No unique exact clause within claimed official article")
        result["source_location_status"] = "ORIGINAL_HTML_SPAN_LOCATED"
        result["verified_quote"] = entry["exact_quote"]
        if source_id == "RG_AMENDMENT_2025_42":
            from urllib.parse import urlencode

            result["highlighted_html_url"] = (
                f"/evidence/highlight/amendment/{sha}?"
                + urlencode({"span_id": entry["span_id"]})
                + "#tarim-evidence-highlight"
            )
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        result["reason"] = type(exc).__name__ + ": " + str(exc)
    return result


def highlighted_amendment_html_copy(
    span_id: str, expected_sha256: str, *,
    matrix_path: Path | None = None,
    manifest_path: Path | None = None,
    archive_root: Path | None = None,
) -> bytes:
    """Highlight exactly one located amendment span in an immutable copy."""
    from bs4 import NavigableString

    matrix_path = matrix_path or Path(os.getenv(
        "TARIM_RAG_CLAIM_SOURCE_MATRIX",
        "configs/p0_10_7_claim_source_matrix.json",
    ))
    manifest_path = manifest_path or Path(os.getenv(
        "TARIM_RAG_ORIGINAL_SOURCE_MANIFEST",
        "configs/p0_10_3_original_source_manifest.json",
    ))
    archive_root = archive_root or Path(os.getenv(
        "TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive",
    ))
    matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    matches = [s for s in matrix.get("spans", [])
               if s.get("span_id") == span_id]
    if len(matches) != 1:
        raise ValueError("Unknown or ambiguous amendment span")
    entry = matches[0]
    if (entry.get("source_id") != "RG_AMENDMENT_2025_42"
        or entry.get("source_sha256") != expected_sha256
        or not isinstance(expected_sha256, str)
        or not _PIN.fullmatch(expected_sha256)):
        raise ValueError("Unexpected original amendment identity")
    proof = validate_source_span(entry, manifest, archive_root)
    if proof["source_location_status"] != "ORIGINAL_HTML_SPAN_LOCATED":
        raise ValueError("Exact original amendment passage not verified")
    raw = (archive_root / "originals" / (expected_sha256 + ".html")).read_bytes()
    document = BeautifulSoup(raw, "html.parser")
    pattern = _normalized_match(entry["exact_quote"])
    found = []
    current = None
    for node in document.find_all(string=True):
        if node.parent.name in {"script", "style", "title"}:
            continue
        transition = _TRANSITION.search(str(node))
        regular = _ARTICLE.search(str(node))
        if transition:
            current = "GEÇİCİ MADDE " + transition.group(1)
        elif regular:
            current = "MADDE " + regular.group(1)
        hit = pattern.search(str(node))
        if hit:
            if current != entry["article"]:
                raise ValueError("Amendment quote shifted to another article")
            found.append((node, hit))
    if len(found) != 1:
        raise ValueError("Nonunique original amendment quote")
    node, hit = found[0]
    raw_text = str(node)
    marked = document.new_tag("mark", id="tarim-evidence-highlight")
    marked["style"] = "background:#ffedd5;outline:2px solid #d97706;padding:2px"
    marked.string = raw_text[hit.start():hit.end()]
    node.replace_with(
        NavigableString(raw_text[:hit.start()]),
        marked,
        NavigableString(raw_text[hit.end():]),
    )
    return str(document).encode("utf-8")


def audit_claim_matrix(
    evaluation: dict[str, Any], matrix: dict[str, Any],
    manifest: dict[str, Any], archive_root: Path,
) -> dict[str, Any]:
    """Source-linked REGULATORY claims remain HOLD until factual/legal review."""
    if matrix.get("schema_version") != 1 or not isinstance(matrix.get("spans"), list):
        raise ValueError("Invalid claim matrix schema")
    rows = matrix["spans"]
    span_ids = [row.get("span_id") for row in rows]
    if len(span_ids) != len(set(span_ids)):
        raise ValueError("Duplicate regulatory source-span identifier")
    location = {
        row["span_id"]: validate_source_span(row, manifest, archive_root)
        for row in rows
    }
    year = (evaluation.get("parcel") or {}).get("production_year")
    if type(year) is not int:
        year = None
    # The emitted semantic check_id is the canonical identity, not the
    # current wording or passed/failed/missing observation field.
    from tarim_destek_rag.citations.check_identity import extracted_checks

    matches = []
    for check in extracted_checks(evaluation):
        key = check["id"]
        check_id = check["check_id"]
        candidates = [
            row for row in rows
            for binding in row.get("claim_bindings", [])
            if (check["identity_status"] == "RULE_EMITTED_STABLE_CHECK_ID"
                and isinstance(binding, dict)
                and binding.get("rule_id") == check["rule_id"]
                and binding.get("support_id") == check["support_id"]
                and binding.get("check_id") == check_id
                and binding.get("production_year") == year
                and type(year) is int
                and year in row.get("production_years", []))
        ]
        # Duplicate normative candidates must not resolve; HOLD.
        source = candidates[0] if len(candidates) == 1 else None
        proof = location[source["span_id"]] if source else None
        proven = bool(proof and proof["source_location_status"] ==
                      "ORIGINAL_HTML_SPAN_LOCATED")
        matches.append({
            "claim_id": key,
            "check_id": check_id,
            "identity_status": check["identity_status"],
            "rule_id": check["rule_id"],
            "support_id": check["support_id"],
            "claim_type": check["field"],
            "claim_text": check["text"],
            "candidate_span_id": source["span_id"] if source else None,
            "source_location_status": (
                "ORIGINAL_HTML_SPAN_LOCATED_NORMATIVE_ONLY"
                if proven else "CLAIM_TO_SOURCE_SPAN_NOT_VERIFIED"
            ),
            "fact_verified": False,
            "temporal_legal_verified": False,
            "claim_verified": False,
            "acceptance": "HOLD",
            "highlighted_pdf_url": None,
        })
    ek = matrix.get("ek20") or {}
    ek_status = "HOLD"
    if (
        year == 2026 and ek.get("production_year") == 2026
        and ek.get("source_id") == "RG_AMENDMENT_2025_42_ANNEX"
        and any(s.get("id") == ek["source_id"]
                and s.get("original_sha256") == ek.get("source_sha256")
                for s in manifest.get("sources", []))
    ):
        # An annex digest/byte match proves only the original attachment.
        # Its raster-only cells have not been independently approved.
        try:
            sha = ek["source_sha256"]
            raw = (archive_root / "originals" / (sha + ".pdf")).read_bytes()
            if hashlib.sha256(raw).hexdigest() == sha and len(raw) == 695625:
                ek_status = "VISUAL_TABLE_PENDING_INDEPENDENT_CELL_REVIEW"
        except (OSError, ValueError, TypeError):
            pass

    cells: list[dict[str, Any]] = []
    if ek_status == "VISUAL_TABLE_PENDING_INDEPENDENT_CELL_REVIEW":
        transcript = matrix.get("ek20_visual_transcription")
        if isinstance(transcript, dict):
            if (
                transcript.get("source_sha256") != ek.get("source_sha256")
                or transcript.get("production_year") != 2026
                or transcript.get("table_pdf_page") != 1
                or transcript.get("source_pdf_page_count") != 1
                or transcript.get("transcription_status") !=
                    "VISUAL_TRANSCRIPTION_PENDING_INDEPENDENT_REVIEW"
                or transcript.get("automatic_rate_activation") is not False
                or transcript.get("independent_legal_reviewer_approved") is not False
            ):
                ek_status = "HOLD"
            else:
                row_items = transcript.get("rows", [])
                keys = ("biological_tl_da", "biotechnical_tl_da",
                        "feromone_trap_tl_da", "feromone_only_tl_da")
                if (
                    len(row_items) != 12
                    or len({row.get("row_id") for row in row_items}) != 12
                    or any(
                        not isinstance(row.get("row_id"), str)
                        or any(
                            row.get(key) is not None
                            and (type(row[key]) is not int or row[key] < 0)
                            for key in keys
                        )
                        for row in row_items
                    )
                ):
                    ek_status = "HOLD"
                else:
                    for row in row_items:
                        for key in keys:
                            amount = row.get(key)
                            cells.append({
                                "cell_id": "EK20_2026:" + row["row_id"] + ":" + key,
                                "source_sha256": ek["source_sha256"],
                                "pdf_page": 1,
                                "row_id": row["row_id"],
                                "cell_key": key,
                                "transcribed_value_tl_da": amount,
                                "transcription_status": (
                                    "DASH_NOT_ZERO" if amount is None
                                    else "VISUAL_PENDING_INDEPENDENT_REVIEW"
                                ),
                                "fact_verified": False,
                                "legal_verified": False,
                                "payable_amount": None,
                                "acceptance": "HOLD",
                                "highlighted_pdf_url": None,
                            })
    return {
        "schema_version": 1,
        "production_year": year,
        "claim_count": len(matches),
        "normative_source_located_count": sum(
            r["source_location_status"] == "ORIGINAL_HTML_SPAN_LOCATED_NORMATIVE_ONLY"
            for r in matches
        ),
        "claim_verified_count": 0,
        "source_spans": list(location.values()),
        "claims": matches,
        "ek20_status": ek_status,
        "ek20_cells": cells,
        "ek20_payment_approved": False,
        "acceptance": "HOLD" if matches else "NO_CLAIMS_TO_AUDIT",
        "note": "Source location is not factual, legal-year or payment approval.",
    }
