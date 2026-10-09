"""One command to stage *newly discovered* official legal documents for any year.

This does NOT update the official legal rates/conditions or mark data VERIFIED.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tarim_destek_rag.updates.discovery import read_portals, scan_official_sources


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", required=True, type=int)
    parser.add_argument("--portals", type=Path,
                        default=Path("configs/official_update_portals.json"))
    parser.add_argument("--archive", type=Path,
                        default=Path("data/legal_update_archive"))
    args = parser.parse_args()
    results = scan_official_sources(
        production_year=args.year, portals=read_portals(args.portals),
        output=args.archive,
    )
    print(json.dumps({
        "year": args.year,
        "status": results["status"],
        "new_or_changed": results["new_or_changed"],
        "checked_documents": len(results["documents"]),
        "errors": len(results["errors"]),
        "report_path": results["report_path"],
        "publication_activated": results["publication_activated"],
    }, ensure_ascii=False, indent=2))
    # A source outage is *not* a clean "no changes" state.
    return 2 if results["errors"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
