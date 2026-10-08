"""Generate legal_diff_report.json from verified, archived PDF sentence IDs.

Nothing is promoted to VERIFIED; an absent article is never deemed legally
repealed solely because it disappeared from this selected source text subset.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from tarim_destek_rag.auto_updater.legal_diff_repository import report_from_evidence
from tarim_destek_rag.database.connection import SessionLocal
from tarim_destek_rag.updates.discovery import _atomic_write


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--previous-year", type=int, required=True)
    parser.add_argument("--target-year", type=int, required=True)
    parser.add_argument("--previous-evidence", type=int, nargs="+", required=True)
    parser.add_argument("--current-evidence", type=int, nargs="+", required=True)
    parser.add_argument("--archive", type=Path,
                        default=Path("data/legal_update_archive"))
    parser.add_argument("--output", type=Path,
                        default=Path("data/legal_diff_report.json"))
    args = parser.parse_args()
    if os.environ.get("TARIM_RAG_LEGAL_SECURITY_PROFILE") == "production":
        parser.error("Production legal diff needs separately authenticated operator session")
    with SessionLocal() as session:
        report = report_from_evidence(
            session,
            archive_root=args.archive,
            previous_year=args.previous_year, target_year=args.target_year,
            previous_sentence_ids=args.previous_evidence,
            current_sentence_ids=args.current_evidence,
        )
        session.rollback()
    _atomic_write(
        args.output,
        (json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode(),
    )
    print(json.dumps({
        "report": str(args.output), "sha256": report["report_sha256"],
        "summary": report["summary"], "status": report["legal_status"],
        "publication_activated": False,
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
