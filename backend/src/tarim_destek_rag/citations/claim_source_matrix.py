"""Fail-closed, claim-level official source and amendment impact auditing.

A verified original HTML span is proof of LOCATION, not evidence that a farmer
met the factual condition, a table cell was approved, or a rule is in force.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup

from tarim_destek_rag.citations.original_html import lookup_html_clause

_PIN = re.compile(r"[0-9a-f]{64}\Z")
_ARTICLE = re.compile(r"^\s*MADDE\s+(\d+)\s*[-–]", re.I)


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
        if source_id == "RG_COMMUNIQUE_2024_39":
            # Preserve the existing strict paragraph (1) locator, which also
            # checks the article index and forbids guesses about article 4.
            proof = lookup_html_clause("BASIC_SUPPORT_2026")
            if (
                entry.get("span_id") != "BASE_2024_39_ART4_P1"
                or proof is None or proof["source_sha256"] != sha
                or proof["exact_quote"] != entry["exact_quote"]
                or entry.get("article") != "MADDE 4"
                or entry.get("target_provision") != "MADDE 4(1)"
            ):
                raise ValueError("Base provision proof differs from indexed original")
        else:
            pattern = _normalized_match(entry["exact_quote"])
            required_article = entry["article"]
            if not re.fullmatch(r"MADDE \d+", required_article):
                raise ValueError("Invalid amendment article identity")
            document = BeautifulSoup(raw, "html.parser")
            active_article = None
            located = 0
            for node in document.find_all(string=True):
                if node.parent.name in {"script", "style", "title"}:
                    continue
                found_heading = _ARTICLE.search(str(node))
                if found_heading:
                    active_article = "MADDE " + found_heading.group(1)
                if pattern.search(str(node)):
                    if active_article != required_article:
                        raise ValueError("Quote found under different amendment article")
                    located += 1
            if located != 1:
                raise ValueError("No unique exact clause within claimed amendment")
        result["source_location_status"] = "ORIGINAL_HTML_SPAN_LOCATED"
        result["verified_quote"] = entry["exact_quote"]
    except (OSError, ValueError, TypeError, KeyError, ImportError) as exc:
        result["reason"] = type(exc).__name__ + ": " + str(exc)
    return result


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
    matches = []
    for rule in evaluation.get("rules", []):
        if not isinstance(rule, dict):
            continue
        rule_id, support_id = rule.get("rule_id"), rule.get("support_id")
        for field in ("passed_checks", "failed_checks", "missing_fields"):
            for text in rule.get(field, []) or []:
                candidates = [
                    row for row in rows
                    for binding in row.get("claim_bindings", [])
                    if binding.get("rule_id") == rule_id
                    and binding.get("support_id") == support_id
                    and binding.get("field") == field
                    and binding.get("exact_claim_text") == text
                    and type(year) is int and year in row.get("production_years", [])
                ]
                key = hashlib.sha256(json.dumps(
                    [rule_id, support_id, field, text], ensure_ascii=False,
                    separators=(",", ":"),
                ).encode("utf-8")).hexdigest()[:24]
                source = candidates[0] if len(candidates) == 1 else None
                proof = location[source["span_id"]] if source else None
                proven = bool(proof and proof["source_location_status"] ==
                              "ORIGINAL_HTML_SPAN_LOCATED")
                matches.append({
                    "claim_id": key,
                    "rule_id": rule_id,
                    "support_id": support_id,
                    "claim_type": field,
                    "claim_text": text,
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
        # A 1-page image table is *not* a verified rate/claim span.
        ek_status = "VISUAL_TABLE_PENDING_INDEPENDENT_CELL_REVIEW"
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
        "ek20_payment_approved": False,
        "acceptance": "HOLD" if matches else "NO_CLAIMS_TO_AUDIT",
        "note": "Source location is not factual, legal-year or payment approval.",
    }
