"""Manually stage a sentence from an ALREADY archived official PDF.

This does not download arbitrary URLs or change payment rules. It stores
DRAFT-only page geometry. Production provenance/authorization is separate.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from tarim_destek_rag.auto_updater.grounding_repository import stage_evidence
from tarim_destek_rag.database.connection import SessionLocal, init_db


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--original-url", required=True)
    parser.add_argument("--sha256", required=True)
    parser.add_argument("--page", type=int, required=True)
    parser.add_argument("--quote", required=True)
    parser.add_argument("--article")
    parser.add_argument("--paragraph")
    parser.add_argument("--clause")
    parser.add_argument("--archive", type=Path, default=Path("data/legal_update_archive"))
    parser.add_argument("--apply-draft", action="store_true")
    args = parser.parse_args()
    if os.environ.get("TARIM_RAG_LEGAL_SECURITY_PROFILE") == "production":
        parser.error("Production ingestion requires independently authorized admin workflow")
    if not args.apply_draft:
        print("DRY RUN: legal clause geometry is not persisted; use --apply-draft locally.")
        return 0
    init_db()
    with SessionLocal() as session:
        try:
            record = stage_evidence(
                session, archive_root=args.archive,
                source_id=args.source_id,
                original_url=args.original_url,
                production_year=args.year,
                sha256=args.sha256, page_number=args.page,
                exact_quote=args.quote, article=args.article,
                paragraph=args.paragraph, clause=args.clause,
            )
            print(
                f"DRAFT legal evidence staged: id={record.id}, page={record.page_number}, "
                f"document_id={record.document_id}; NOT APPROVED"
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
