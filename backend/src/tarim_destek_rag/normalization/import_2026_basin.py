"""Manual DRAFT-only importer for reviewed 2026/27 basin extraction evidence."""

from __future__ import annotations

import argparse
from pathlib import Path

from tarim_destek_rag.database.connection import SessionLocal, init_db
from tarim_destek_rag.normalization.basin_2026 import stage_basin_districts


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--catalog", required=True, type=Path,
                        help="Source PDF extraction JSON from official-basin CI artifact")
    parser.add_argument("--pdf", type=Path,
                        help="Exact original official source PDF; mandatory for apply")
    parser.add_argument("--apply-draft", action="store_true",
                        help="Insert source-checked rows as DRAFT only")
    args = parser.parse_args()
    if not args.apply_draft:
        count = stage_basin_districts(None, args.catalog, apply=False)
        print(f"DRY RUN: {count} official district rows; no database was changed.")
        return 0
    if args.pdf is None:
        parser.error("--pdf is required with --apply-draft")
    init_db()
    with SessionLocal() as session:
        try:
            count = stage_basin_districts(
                session, args.catalog, apply=True, pdf_path=args.pdf
            )
            session.commit()
        except Exception:
            session.rollback()
            raise
    print(f"{count} district-year DRAFT snapshots staged; eligibility is still gated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
