"""Audit every displayed decision claim, rather than treating a program link as proof.

A citation for a support program DOES NOT establish each passed/failed rule check
as a verbatim legal clause. This auditor makes remaining claim-to-span gaps visible
and blocks a false all-complete declaration.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from tarim_destek_rag.citations.evidence_contract import verified_highlight_path

CLAIM_FIELDS = {
    "passed_checks": "PASSED_CHECK",
    "failed_checks": "FAILED_CHECK",
    "missing_fields": "MISSING_FIELD",
}


def audit_evaluation_claims(evaluation: dict[str, Any]) -> dict[str, Any]:
    """Report claim-level coverage without inventing any source passage."""
    explanations = {
        e["support_id"]: e for e in evaluation.get("explanations", [])
        if isinstance(e, dict) and isinstance(e.get("support_id"), str)
    }
    claims: list[dict[str, Any]] = []
    source_links: list[dict[str, str]] = []
    for rule in evaluation.get("rules", []):
        if not isinstance(rule, dict):
            continue
        sid = str(rule.get("support_id") or "")
        exp = explanations.get(sid, {})
        for citation in exp.get("citations", []):
            if not isinstance(citation, dict):
                continue
            path = verified_highlight_path(citation, sid)
            if path:
                source_links.append({
                    "support_id": sid,
                    "source_id": str(citation.get("source_id") or ""),
                    "section": str(citation.get("section") or ""),
                    "verification_status": str(citation.get("verification_status") or ""),
                    "highlighted_pdf_url": path,
                })
        for field, kind in CLAIM_FIELDS.items():
            for value in rule.get(field, []) or []:
                # Source-to-support links alone do not prove this individual
                # reason, even when a highlighted article exists elsewhere.
                claims.append({
                    "support_id": sid,
                    "rule_id": str(rule.get("rule_id") or ""),
                    "claim_type": kind,
                    "claim_text": str(value),
                    "status": "CLAIM_TO_SOURCE_SPAN_NOT_VERIFIED",
                    "highlighted_pdf_url": None,
                })
    basin = evaluation.get("basin_evidence")
    basin_path = verified_highlight_path(basin) if isinstance(basin, dict) else None
    return {
        "schema_version": 1,
        "decision_claim_count": len(claims),
        "claim_level_verified_count": 0,
        "unmatched_claim_count": len(claims),
        "located_source_count": len(source_links),
        "basin_row_located": basin_path is not None,
        "acceptance": "HOLD" if claims else "NO_CLAIMS_TO_AUDIT",
        "claims": claims,
        "related_source_locations": source_links,
        "note": (
            "A located document/page/paragraph is source evidence, not individual "
            "claim support, temporal validity, or eligibility. Human-approved "
            "claim-to-span mapping is still required."
        ),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Fail-closed per-claim evidence audit")
    parser.add_argument("--input", required=True, type=Path, help="Saved /evaluate JSON response")
    parser.add_argument("--output", type=Path, help="Optional JSON audit destination")
    parser.add_argument("--strict", action="store_true", help="Exit 2 while any claims remain unmapped")
    args = parser.parse_args()
    report = audit_evaluation_claims(json.loads(args.input.read_text(encoding="utf-8")))
    rendered = json.dumps(report, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")
    return 2 if args.strict and report["acceptance"] != "PASS" else 0


if __name__ == "__main__":
    raise SystemExit(main())
