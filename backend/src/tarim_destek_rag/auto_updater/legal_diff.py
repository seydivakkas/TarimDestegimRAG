"""Source-pinned, deterministic legal change detection for future years.

A text difference is NOT a legal repeal: even explicit 'yürürlükten
kaldırılmıştır' may amend another article, and effective dates must be
reviewed. All output remains REVIEW_REQUIRED, never a payable legal rule.
Input snippets MUST first pass exact SHA/page/PDF validation.
"""

from __future__ import annotations

import difflib
import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from decimal import Decimal, InvalidOperation

from tarim_destek_rag.updates.pdf_evidence import SHA_PATTERN

_KEY = re.compile(r"^(MADDE|GEÇİCİ MADDE|EK MADDE)\s+[0-9]+(?:/[0-9]+)?(?:\s*/\s*[0-9a-zçğıöşü]+){0,2}$", re.I)
_REPEAL = re.compile(r"yürürlükten\s+kaldırılm|mülga", re.I)
_AMOUNT = re.compile(r"(?<![\d.,])(?P<number>\d{1,12}(?:\.\d{3})*(?:,\d{1,2})?)\s*(?P<unit>TL|TRY)(?:\s*/\s*(?P<area>da|dekar))?(?![\w])", re.I)


@dataclass(frozen=True)
class LegalClause:
    key: str
    document_sha256: str
    page: int
    exact_text: str
    evidence_id: int
    production_year: int
    source_id: str
    highlighted_page_url: str | None = None
    bounding_boxes: list[dict] | None = None
    normalized_quads: list[list[list[float]]] | None = None

    def __post_init__(self) -> None:
        if (
            not isinstance(self.key, str) or not _KEY.fullmatch(self.key.strip())
            or not SHA_PATTERN.fullmatch(self.document_sha256)
            or not isinstance(self.page, int) or self.page <= 0
            or not isinstance(self.evidence_id, int) or self.evidence_id <= 0
            or not isinstance(self.production_year, int)
            or not 2020 <= self.production_year <= 2100
            or not isinstance(self.source_id, str) or not self.source_id.strip()
            or not isinstance(self.exact_text, str) or len(self.exact_text.strip()) < 12
        ):
            raise ValueError("A legal diff requires a real source-pinned clause identity")


def _canonical_text(text: str) -> str:
    # Only whitespace is normalized; no spelling, numeric, year or modal-word
    # rewriting which could accidentally mask a changed legal obligation.
    return " ".join(text.split())


def _hash(data: dict) -> str:
    return hashlib.sha256(json.dumps(
        data, sort_keys=True, ensure_ascii=False, separators=(",", ":"), allow_nan=False
    ).encode("utf-8")).hexdigest()


def _numbers(text: str) -> list[dict]:
    """Return literal TL mentions to review, never a guessed base coefficient."""
    candidates = []
    for match in _AMOUNT.finditer(text):
        original = match.group("number")
        try:
            value = Decimal(original.replace(".", "").replace(",", "."))
        except InvalidOperation:
            continue
        candidates.append({
            "literal": match.group(0),
            "decimal": format(value, "f"),
            "unit": "TRY/da" if match.group("area") else "TRY",
            "status": "UNCLASSIFIED_LEGAL_NUMBER",
        })
    return candidates


def _index(clauses: Iterable[LegalClause], label: str) -> dict[str, LegalClause]:
    found = {}
    for record in clauses:
        key = " ".join(record.key.upper().split())
        if key in found:
            raise ValueError(f"Ambiguous duplicate {label} clause key: {key}")
        found[key] = record
    if not found:
        raise ValueError(f"No source-validated {label} legal clauses to compare")
    return found


def compare_clause_sets(
    *,
    previous_year: int,
    target_year: int,
    previous: Iterable[LegalClause],
    current: Iterable[LegalClause],
    prior_complete: bool = False,
    current_complete: bool = False,
) -> dict:
    """Build inspectable exact-text diff, not legal effect / enactment claims.

    'REMOVED' is only a *textual* removal even under complete source coverage;
    no auto-repeal of previous legal rate or exception is allowed.
    """
    if not 2020 <= previous_year < target_year <= 2100:
        raise ValueError("Strictly increasing production years required")
    before = _index(previous, "previous")
    after = _index(current, "current")
    if any(x.production_year != previous_year for x in before.values()):
        raise ValueError("Previous clause belongs to another production year")
    if any(x.production_year != target_year for x in after.values()):
        raise ValueError("Current clause belongs to another production year")

    changes = []
    counts = {"TEXT_ADDED": 0, "TEXT_REMOVED": 0, "TEXT_CHANGED": 0, "TEXT_UNCHANGED": 0}
    for key in sorted(set(before) | set(after)):
        old, new = before.get(key), after.get(key)
        old_text = _canonical_text(old.exact_text) if old else None
        new_text = _canonical_text(new.exact_text) if new else None
        if old is None:
            status = "TEXT_ADDED"
        elif new is None:
            status = "TEXT_REMOVED"
        elif old_text == new_text:
            status = "TEXT_UNCHANGED"
        else:
            status = "TEXT_CHANGED"
        counts[status] += 1
        changes.append({
            "clause_key": key,
            "change_type": status,
            "previous": asdict(old) if old else None,
            "current": asdict(new) if new else None,
            "previous_sentence_sha256": (
                hashlib.sha256(old_text.encode()).hexdigest() if old_text else None
            ),
            "current_sentence_sha256": (
                hashlib.sha256(new_text.encode()).hexdigest() if new_text else None
            ),
            "unified_text_diff": list(difflib.unified_diff(
                old_text.splitlines(keepends=True) if old_text else [],
                new_text.splitlines(keepends=True) if new_text else [],
                fromfile=f"{previous_year}/{key}", tofile=f"{target_year}/{key}",
            )) if status != "TEXT_UNCHANGED" else [],
            "repeal_language_detected": bool(new_text and _REPEAL.search(new_text)),
            "repeal_effect_confirmed": False,
            "same_regulatory_act_independently_confirmed": False,
            "old_tl_mentions": _numbers(old_text or ""),
            "new_tl_mentions": _numbers(new_text or ""),
            "numeric_change_needs_review": (
                _numbers(old_text or "") != _numbers(new_text or "")
            ),
            "effective_from": None,
            "effective_to": None,
            "human_legal_review_required": True,
        })
    report = {
        "schema_version": 1,
        "previous_year": previous_year,
        "target_year": target_year,
        "previous_coverage_complete_proven": bool(prior_complete),
        "current_coverage_complete_proven": bool(current_complete),
        "complete_legal_search_proven": False,
        "legal_continuity_independently_verified": False,
        "legal_status": "REVIEW_REQUIRED",
        "publication_activated": False,
        "summary": counts,
        "changes": changes,
    }
    report["report_sha256"] = _hash(report)
    return report
