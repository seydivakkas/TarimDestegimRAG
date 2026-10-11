"""Explicit batch PDF/OCR page index. Every page remains bound to original SHA.

OCR/searchable text and detected table geometry are *review candidates*, not
official verbatim quotations or evidence of annual legal force.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import tempfile
from pathlib import Path
from typing import Any

from tarim_destek_rag.citations.pdf_page_indexer import (
    OfficialPdfIndexer,
    normalize_tr,
)
from tarim_destek_rag.citations.ocr_spatial_layout import extract_ocr_geometry

INDEX_SCHEMA = 1


def index_official_document(
    indexer: OfficialPdfIndexer, doc_id: str,
) -> dict[str, Any]:
    """Scan EVERY page of exactly one SHA-verified original PDF.

    Never silently accept an OCR-unavailable page as successfully transcribed.
    """
    source, _ = indexer._verified_pdf(doc_id)
    pages = indexer._records.get(doc_id)
    if not pages:
        indexer.load_verified_originals()
        pages = indexer._records.get(doc_id)
    if not pages:
        raise ValueError("Pinned PDF has no indexed original pages")
    if len(pages) != pages[0].total_pages:
        raise ValueError("Original PDF page list is incomplete")
    result: list[dict[str, Any]] = []
    unfinished = []
    for page in pages:
        # Revalidate every page's original PDF and position before accepting
        # either native text or OCR bytes. This does not validate OCR semantics.
        indexer.screenshot(page, dpi=120)
        spatial: dict[str, Any] = {
            "status": "NATIVE_PDF_TEXT_LAYOUT",
            "words": [],
            "lines": [],
        }
        if page.raw_text:
            text = page.raw_text
            method = "PDF_NATIVE_TEXT_UNREVIEWED"
        else:
            text, method = indexer.ocr_page(page)
            if method == "OCR_UNREVIEWED" and text:
                # The plain-text hypothesis and its image word coordinates
                # are stored independently. Neither is verified legal text.
                spatial = extract_ocr_geometry(indexer, page)
            if method != "OCR_UNREVIEWED" or not text:
                unfinished.append(page.page_number)
        result.append({
            "page_number": page.page_number,
            "source_sha256": source["original_sha256"],
            "method": method,
            "text": text,
            "ocr_spatial_layout": spatial,
            "tables_extracted_from_native_pdf": [
                {
                    "table_id": t.table_id,
                    "bbox": list(t.bbox),
                    "headers": t.headers,
                    "rows": t.rows,
                } for t in page.tables
            ],
            "table_semantic_status": "PENDING_INDEPENDENT_REVIEW",
            "graphics_semantic_status": "PENDING_INDEPENDENT_REVIEW",
            "claim_verified": False,
            "legal_approved": False,
        })
    return {
        "schema_version": INDEX_SCHEMA,
        "document_id": doc_id,
        "original_sha256": source["original_sha256"],
        "original_url": source["url"],
        "original_page_count": pages[0].total_pages,
        "indexed_page_count": len(result),
        "ocr_unavailable_page_numbers": unfinished,
        "technical_status": "INCOMPLETE_OCR_HOLD" if unfinished else "SEARCHABLE_REVIEW_REQUIRED",
        "claim_verified": False,
        "payable_activation": False,
        "pages": result,
    }


def write_index_atomic(report: dict[str, Any], dest: Path) -> None:
    sha = report.get("original_sha256")
    if not isinstance(sha, str) or not re.fullmatch(r"[a-f0-9]{64}", sha):
        raise ValueError("Cannot persist unpinned PDF index")
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=".ocr-index-", dir=dest.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(report, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(name, dest)
    finally:
        Path(name).unlink(missing_ok=True)


def search_ocr_candidates(
    indexer: OfficialPdfIndexer, query: str, *,
    index_dir: Path = Path("data/indexes"),
) -> list[dict[str, Any]]:
    """Offer OCR *candidates* only after full original SHA and page check."""
    phrase = normalize_tr(query)
    if len(phrase) < 3:
        return []
    matches: list[dict[str, Any]] = []
    for doc_id, pages in indexer._records.items():
        if not pages:
            continue
        try:
            original, _ = indexer._verified_pdf(doc_id)
            sha = original["original_sha256"]
            file = index_dir / ("verified_ocr_" + sha + ".json")
            report = json.loads(file.read_text(encoding="utf-8"))
            records = report["pages"]
            if (
                report.get("schema_version") != INDEX_SCHEMA
                or report.get("original_sha256") != sha
                or report.get("original_url") != original["url"]
                or report.get("document_id") != doc_id
                or report.get("original_page_count") != len(pages)
                or report.get("indexed_page_count") != len(pages)
                or len(records) != len(pages)
                or sorted(p["page_number"] for p in records) != list(
                    range(1, len(pages) + 1)
                )
            ):
                continue
            for candidate in records:
                if candidate.get("source_sha256") != sha:
                    continue
                if candidate.get("method") != "OCR_UNREVIEWED":
                    continue  # native exact text search is handled separately
                value = candidate.get("text")
                if not isinstance(value, str) or phrase not in normalize_tr(value):
                    continue
                real_page = indexer.get_page(doc_id, candidate["page_number"])
                if real_page is None:
                    continue
                matches.append({
                    "document_id": doc_id,
                    "page_number": real_page.page_number,
                    "source_sha256": sha,
                    "status": "OCR_CANDIDATE_UNREVIEWED",
                    "claim_verified": False,
                })
        except (OSError, ValueError, KeyError, TypeError, OverflowError):
            continue  # no fallback to fabricated/historically cached evidence
    return matches


def main() -> int:
    parser = argparse.ArgumentParser(description="Index every page of pinned PDF")
    parser.add_argument("--source-id", default="RG_DECISION_8859")
    parser.add_argument("--out-dir", type=Path, default=Path("data/indexes"))
    args = parser.parse_args()
    idx = OfficialPdfIndexer()
    idx.load_verified_originals()
    result = index_official_document(idx, args.source_id)
    out = args.out_dir / ("verified_ocr_" + result["original_sha256"] + ".json")
    write_index_atomic(result, out)
    print(json.dumps({
        "path": str(out),
        "indexed_page_count": result["indexed_page_count"],
        "missing_ocr_pages": result["ocr_unavailable_page_numbers"],
        "status": result["technical_status"],
    }, ensure_ascii=False, sort_keys=True))
    # A missing local Tesseract or OCR language model is a real failure, not PASS.
    return 2 if result["ocr_unavailable_page_numbers"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
