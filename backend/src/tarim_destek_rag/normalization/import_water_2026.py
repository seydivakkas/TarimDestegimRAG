"""2026 water national legal scope: default dry-run, explicit DRAFT-only import.

Never upgrades review_status/coverage_complete; signed production activation is
handled solely by legal_approval_cli with real external officer identities.
"""
import argparse
from pathlib import Path

from tarim_destek_rag.database.connection import SessionLocal, init_db
from tarim_destek_rag.normalization.water_2026 import CATALOG, stage_water_scope


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", type=Path, default=CATALOG)
    parser.add_argument("--original-pdf", type=Path)
    parser.add_argument("--amendment-html", type=Path)
    parser.add_argument("--apply-draft", action="store_true")
    args = parser.parse_args()
    if not args.apply_draft:
        count = stage_water_scope(None, path=args.catalog)
        print(f"DRY RUN: {count} districts, 11 provinces; no DB changes, no approval.")
        return 0
    if not args.original_pdf or not args.amendment_html:
        parser.error("--apply-draft requires --original-pdf and --amendment-html")
    init_db()
    with SessionLocal() as session:
        try:
            count = stage_water_scope(
                session, path=args.catalog, apply=True,
                original_pdf_path=args.original_pdf,
                amendment_html_path=args.amendment_html,
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
    print(f"{count} inert DRAFT national-scope versions staged. NO VERIFIED status set.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
