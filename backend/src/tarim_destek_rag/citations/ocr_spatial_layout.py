"""Spatial OCR candidate layout extracted from a verified original PDF image.

The TSV word coordinates are OCR hypotheses, not original-PDF text evidence,
not verified EK-20 cells and never an automatic payout trigger.
"""
from __future__ import annotations

import csv
import io
import shutil
import subprocess
from collections import defaultdict
from typing import Any

from tarim_destek_rag.citations.pdf_page_indexer import (
    OfficialGazettePageRecord,
    OfficialPdfIndexer,
)

MAX_OCR_WORDS = 12000


def extract_ocr_geometry(
    indexer: OfficialPdfIndexer, record: OfficialGazettePageRecord,
    *, dpi: int = 180,
) -> dict[str, Any]:
    """Return original-image OCR word boxes, explicit status and line groups."""
    if shutil.which("tesseract") is None:
        return {"status": "OCR_NOT_INSTALLED", "dpi": dpi,
                "words": [], "lines": []}
    try:
        png, highlights, sha = indexer.screenshot(record, dpi=dpi)
        if highlights or sha != record.source_sha256:
            raise ValueError("Unexpected modified original-page screenshot")
        process = subprocess.run(
            ["tesseract", "stdin", "stdout", "-l", "tur+eng", "tsv"],
            input=png,
            capture_output=True,
            timeout=90,
            check=False,
        )
        if process.returncode != 0:
            raise ValueError("OCR engine returned nonzero status")
        data = process.stdout.decode("utf-8", errors="replace")
        rows = csv.DictReader(io.StringIO(data), delimiter="\t")
        words: list[dict[str, Any]] = []
        grouped: dict[tuple[int, int, int, int], list[dict[str, Any]]] = defaultdict(list)
        for row in rows:
            if row.get("level") != "5":
                continue
            text = (row.get("text") or "").strip()
            if not text:
                continue
            left = int(row["left"])
            top = int(row["top"])
            width = int(row["width"])
            height = int(row["height"])
            confidence = float(row.get("conf") or "-1")
            if (left < 0 or top < 0 or width <= 0 or height <= 0
                    or width > 12000 or height > 12000):
                continue
            word = {
                "text": text[:250],
                "pixel_bbox": [left, top, left + width, top + height],
                "confidence": confidence,
                "review_status": "OCR_UNREVIEWED",
            }
            words.append(word)
            key = tuple(int(row[k]) for k in (
                "page_num", "block_num", "par_num", "line_num"))
            grouped[key].append(word)
            if len(words) >= MAX_OCR_WORDS:
                break
        lines = []
        for key, sequence in sorted(grouped.items()):
            if not sequence:
                continue
            xs0 = [w["pixel_bbox"][0] for w in sequence]
            ys0 = [w["pixel_bbox"][1] for w in sequence]
            xs1 = [w["pixel_bbox"][2] for w in sequence]
            ys1 = [w["pixel_bbox"][3] for w in sequence]
            lines.append({
                "layout_key": list(key),
                "text": " ".join(w["text"] for w in sequence),
                "pixel_bbox": [min(xs0), min(ys0), max(xs1), max(ys1)],
                "review_status": "OCR_UNREVIEWED",
            })
        return {
            "status": "OCR_LAYOUT_UNREVIEWED" if words else "OCR_NO_WORDS",
            "dpi": dpi,
            "source_sha256": sha,
            "page_number": record.page_number,
            "words": words,
            "lines": lines,
            "table_cell_status": "NOT_STRUCTURALLY_VERIFIED",
            "graphics_status": "NOT_SEMANTICALLY_VERIFIED",
        }
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired,
            UnicodeError, KeyError, TypeError):
        return {"status": "OCR_LAYOUT_FAILED", "dpi": dpi,
                "words": [], "lines": []}
