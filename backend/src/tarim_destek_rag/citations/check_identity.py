"""Stable semantic check identity; presentation text is never part of the ID.

The rule engine must emit check_events containing check_id/field/display_text.
Legacy string-only check arrays are still shown but explicitly UNMIGRATED;
their temporary field/ordinal identities CANNOT receive normative mappings.
"""
from __future__ import annotations

import hashlib
import json
import re
from typing import Any

FIELDS = (
    ("passed_checks", "Sağlanan şart"),
    ("failed_checks", "Sağlanamayan şart"),
    ("missing_fields", "Eksik bilgi"),
)
_CHECK = re.compile(r"[A-Z][A-Z0-9_]{3,90}\Z")


def check_claim_id(rule_id: str, support_id: str, check_id: str) -> str:
    """Stable across word changes, status and production year, within rule."""
    if (not all(isinstance(v, str) and v for v in (rule_id, support_id, check_id))
            or not _CHECK.fullmatch(check_id)):
        raise ValueError("Invalid stable check identity")
    return hashlib.sha256(json.dumps(
        ["TRAG_CHECK_V2", rule_id, support_id, check_id],
        ensure_ascii=False, separators=(",", ":"),
    ).encode("utf-8")).hexdigest()[:24]


def extracted_checks(evaluation: dict[str, Any] | None) -> list[dict[str, Any]]:
    if not isinstance(evaluation, dict):
        return []
    year = (evaluation.get("parcel") or {}).get("production_year")
    year = year if type(year) is int else None
    output: list[dict[str, Any]] = []
    for rule in evaluation.get("rules", []):
        if not isinstance(rule, dict):
            continue
        rule_id, support_id = rule.get("rule_id"), rule.get("support_id")
        if not isinstance(rule_id, str) or not isinstance(support_id, str):
            continue
        events = rule.get("check_events") or []
        # Reject invalid structured emitters rather than silently trusting one
        # arbitrary event or distributing it to other check text.
        allowed: dict[tuple[str, str], str] = {}
        seen_ids: set[str] = set()
        if isinstance(events, list):
            for event in events:
                if not isinstance(event, dict):
                    continue
                check_id = event.get("check_id")
                field = event.get("field")
                phrase = event.get("display_text")
                if (isinstance(check_id, str) and _CHECK.fullmatch(check_id)
                        and field in dict(FIELDS) and isinstance(phrase, str)):
                    # Exactly one event per stable check in the current
                    # evaluation. Duplicate IDs cause HOLD for both.
                    if check_id in seen_ids:
                        for key, val in list(allowed.items()):
                            if val == check_id:
                                del allowed[key]
                        continue
                    seen_ids.add(check_id)
                    allowed[(field, phrase)] = check_id
        emitted: set[str] = set()
        for field, label in FIELDS:
            texts = rule.get(field) or []
            if not isinstance(texts, list):
                continue
            for ordinal, text in enumerate(texts):
                if not isinstance(text, str):
                    continue
                identity = allowed.get((field, text))
                # The same string may be present twice: it does not identify
                # which logical check emitted the event. Explicitly HOLD.
                if texts.count(text) != 1 or identity in emitted:
                    identity = None
                if identity is None:
                    # Temporary identity is intentionally incompatible with
                    # curator check IDs. Do not treat as a stable rule.
                    fallback = "LEGACY_" + field.upper() + "_" + str(ordinal)
                    uid = check_claim_id(rule_id, support_id, fallback)
                    check_id = None
                    state = "LEGACY_NO_SEMANTIC_CHECK_ID_HOLD"
                else:
                    uid = check_claim_id(rule_id, support_id, identity)
                    check_id = identity
                    state = "RULE_EMITTED_STABLE_CHECK_ID"
                    emitted.add(identity)
                output.append({
                    "id": uid,
                    "check_id": check_id,
                    "identity_status": state,
                    "year": year,
                    "rule_id": rule_id,
                    "support_id": support_id,
                    "field": field,
                    "kind": label,
                    "text": text,
                    "ordinal": ordinal,
                })
    return output
