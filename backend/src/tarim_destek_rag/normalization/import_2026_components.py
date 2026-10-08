"""Read-only inspection and explicit DRAFT-only import of 2026 legal components."""

import argparse

from tarim_destek_rag.database.connection import SessionLocal, init_db
from tarim_destek_rag.normalization.legal_components_2026 import stage_component_rates


def main() -> int:
    parser = argparse.ArgumentParser(description="2026 mevzuat tutarları (yalnız DRAFT)")
    parser.add_argument("--apply-draft", action="store_true",
                        help="Explicitly insert 2026 components as DRAFT; NEVER VERIFIED")
    args = parser.parse_args()
    if not args.apply_draft:
        print(f"DRY RUN: {stage_component_rates(None)} belgeli bileşen (DB değişmedi)")
        return 0

    init_db()
    with SessionLocal() as session:
        try:
            count = stage_component_rates(session, apply=True)
            session.commit()
        except Exception:
            session.rollback()
            raise
    print(f"{count} DRAFT bileşen eklendi. Kaynak/hash/onay eksik; hesaplamaya kapalı.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
