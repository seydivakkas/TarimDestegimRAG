"""Kontrollü resmî belge indirimi ve gerçek atıf pasajı sorgulaması.

Kullanım:
python -m tarim_destek_rag.citations.ingest --source-id TOB-2026-KATSAYI
python -m tarim_destek_rag.citations.ingest --source-id TOB-2026-KATSAYI --section "DESTEK TUTARLARI" --snippet "DESTEK KATSAYI DEĞERİ 367 TL OLARAK GÜNCELLENDİ"
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from tarim_destek_rag.citations.evidence import EvidenceError, EvidenceStore
from tarim_destek_rag.scraper.registry import SourceRegistry


def main() -> int:
    parser = argparse.ArgumentParser(description="Resmî PDF/HTML belge + SHA-256 kayıt ve pasaj doğrulaması")
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--sources", default="configs/sources.yaml")
    parser.add_argument("--store", default="data/evidence")
    parser.add_argument("--snippet", default="")
    parser.add_argument("--section", default="")
    parser.add_argument("--offline", action="store_true", help="Yalnız önceden kaydedilmiş hash doğrulamalı dosyayı oku")
    args = parser.parse_args()

    registry = SourceRegistry.load_from_yaml(args.sources)
    source = registry.get_source(args.source_id)
    store = EvidenceStore(Path(args.store))
    try:
        snapshot = store.load_snapshot(source) if args.offline else store.ingest_official(source)
        if snapshot is None:
            print(json.dumps({"status": "EVIDENCE_NOT_INDEXED", "source_id": args.source_id}))
            return 2
        matched, page = (
            store.match(source, snippet=args.snippet, section=args.section)
            if args.snippet else (None, None)
        )
        outcome = {
            "source_id": snapshot.source_id,
            "url": snapshot.source_url,
            "sha256": snapshot.sha256,
            "fetched_at": snapshot.fetched_at,
            "page_count": len(snapshot.pages),
            "status": (
                "VERIFIED" if matched else "PASSAGE_NOT_FOUND"
                if args.snippet else "SNAPSHOT_SAVED_NOT_VERIFIED"
            ),
            "matched_page": page,
        }
        print(json.dumps(outcome, ensure_ascii=False, indent=2))
        return 0 if not args.snippet or matched else 3
    except (EvidenceError, OSError, ValueError) as exc:
        print(json.dumps({"status": "FAILED", "reason": str(exc)}, ensure_ascii=False))
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
