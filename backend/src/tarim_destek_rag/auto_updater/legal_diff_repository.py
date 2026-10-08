"""Compare ONLY previously staged exact PDF sentences with original bytes.

This is a manual set-to-set clause comparison adapter. It is intentionally
not the future nationwide complete legal-consolidation crawler: amendment
articles cannot automatically be assumed to supersede the same-numbered
article of a prior decision.
"""

from __future__ import annotations

from pathlib import Path
from sqlalchemy.orm import Session

from tarim_destek_rag.auto_updater.grounding_repository import load_grounded_sentence
from tarim_destek_rag.auto_updater.legal_diff import LegalClause, compare_clause_sets


def report_from_evidence(
    session: Session,
    *,
    archive_root: Path,
    previous_year: int,
    target_year: int,
    previous_sentence_ids: list[int],
    current_sentence_ids: list[int],
) -> dict:
    if (
        not isinstance(previous_sentence_ids, list)
        or not isinstance(current_sentence_ids, list)
        or not 1 <= len(previous_sentence_ids) <= 300
        or not 1 <= len(current_sentence_ids) <= 300
        or len(previous_sentence_ids) != len(set(previous_sentence_ids))
        or len(current_sentence_ids) != len(set(current_sentence_ids))
    ):
        raise ValueError("Both bounded, nonduplicated evidence ID lists are required")

    def verified(ids: list[int], year: int) -> list[LegalClause]:
        found = []
        for sentence_id in ids:
            record, doc, grounded, original = load_grounded_sentence(
                session, archive_root=archive_root,
                evidence_id=sentence_id, year=year,
            )
            if not record.article_no:
                raise ValueError("A reviewed, explicit legal article key is required")
            pieces = [record.article_no]
            if record.paragraph_no:
                pieces.append(record.paragraph_no)
            if record.clause_no:
                pieces.append(record.clause_no)
            key = " / ".join(pieces)
            found.append(LegalClause(
                key=key,
                document_sha256=grounded.document_sha256,
                page=grounded.page_number,
                exact_text=grounded.exact_quote,
                evidence_id=record.id,
                production_year=year,
                source_id=doc.source_id,
            ))
        return found

    return compare_clause_sets(
        previous_year=previous_year, target_year=target_year,
        previous=verified(previous_sentence_ids, previous_year),
        current=verified(current_sentence_ids, target_year),
        # Comparing selected passages is NOT proof of whole-document
        # coverage, however many selected passages were supplied.
        prior_complete=False, current_complete=False,
    )
