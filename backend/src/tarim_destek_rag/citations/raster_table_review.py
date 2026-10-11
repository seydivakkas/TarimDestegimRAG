"""Raster PDF table-cell *review candidates* bound to genuine source pixels.

Grid pixels are measured on a freshly SHA-verified original PDF screenshot.
Detected cells are only candidates. Neither OCR nor grid geometry validates a
table's row labels, column meanings, monetary values or legal applicability.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
from html import escape
from pathlib import Path
from typing import Any

from tarim_destek_rag.citations.pdf_page_indexer import get_global_pdf_indexer

REVIEW_DPI = 180
MAX_CELLS = 320
_HOLD = (
    "<p><strong>HOLD — Tarama tablosunun hücre koordinatı "
    "doğrulanamadı.</strong> Tahminî sarı vurgu üretilmedi.</p>"
)
_SELECTION = re.compile(
    r"([A-Z][A-Z0-9_]{2,79}):([1-9][0-9]{0,3}):"
    r"raster:([0-9]{1,2}):([0-9]{1,2}):([a-f0-9]{64})"
)


def _bands(counts: list[int], minimum: int, *, minimum_separation: int) -> list[int]:
    """Collapse adjacent dark scan lines to their observed pixel centres."""
    runs: list[list[int]] = []
    for offset, count in enumerate(counts):
        if count >= minimum:
            if runs and offset - runs[-1][-1] <= 3:
                runs[-1].append(offset)
            else:
                runs.append([offset])
    centres = [round(sum(run) / len(run)) for run in runs if len(run) <= 12]
    filtered: list[int] = []
    for value in centres:
        if not filtered or value - filtered[-1] >= minimum_separation:
            filtered.append(value)
    return filtered


def _dark_near(pixels: bytes, width: int, height: int, x: int, y: int) -> bool:
    for yy in range(max(0, y - 1), min(height, y + 2)):
        start = yy * width
        for xx in range(max(0, x - 1), min(width, x + 2)):
            if pixels[start + xx] < 165:
                return True
    return False


def _coverage(
    pixels: bytes, width: int, height: int, *, fixed: int,
    lo: int, hi: int, horizontal: bool,
) -> float:
    if hi <= lo:
        return 0.0
    step = max(1, (hi - lo) // 250)
    checked = 0
    found = 0
    for coordinate in range(lo, hi + 1, step):
        x, y = (coordinate, fixed) if horizontal else (fixed, coordinate)
        checked += 1
        if _dark_near(pixels, width, height, x, y):
            found += 1
    return found / checked if checked else 0.0


def detect_ruled_cells(png: bytes) -> dict[str, Any]:
    """Return measured pixel boxes only for a *complete visible ruled grid*.

    A borderless table, sparse rule, split page, or ambiguous geometry returns
    no cells. No synthetic cell boxes are interpolated from a transcription.
    """
    from PIL import Image, UnidentifiedImageError

    try:
        with Image.open(io.BytesIO(png)) as source:
            if source.format != "PNG":
                raise ValueError("Not an original PNG screenshot")
            width, height = source.size
            if not 300 <= width <= 5000 or not 300 <= height <= 8000:
                raise ValueError("Unexpected original image dimensions")
            gray = source.convert("L")
            pixels = gray.tobytes()
    except (ValueError, OSError, UnidentifiedImageError):
        return {"status": "RASTER_IMAGE_UNAVAILABLE", "cells": []}
    row_counts = [0] * height
    col_counts = [0] * width
    for index, intensity in enumerate(pixels):
        if intensity < 165:
            y, x = divmod(index, width)
            row_counts[y] += 1
            col_counts[x] += 1

    # Projections yield measured candidate ruling lines, NOT inferred table
    # positions from a 12-row/4-column OCR or transcription template.
    horizontal = _bands(
        row_counts, max(70, round(width * 0.35)), minimum_separation=13,
    )
    vertical = _bands(
        col_counts, max(65, round(height * 0.13)), minimum_separation=22,
    )
    if not 3 <= len(horizontal) <= 85 or not 3 <= len(vertical) <= 35:
        return {"status": "NO_COMPLETE_RASTER_GRID", "cells": []}

    # Require most visible border strokes to be continuous and to meet the
    # observed corners; columns aligned by printed text alone are rejected.
    xs, ys = vertical, horizontal
    full_h = [
        y for y in ys if _coverage(
            pixels, width, height, fixed=y, lo=xs[0], hi=xs[-1],
            horizontal=True,
        ) >= 0.75
    ]
    full_v = [
        x for x in xs if _coverage(
            pixels, width, height, fixed=x, lo=ys[0], hi=ys[-1],
            horizontal=False,
        ) >= 0.75
    ]
    if len(full_h) < 3 or len(full_v) < 3:
        return {"status": "GRID_BORDERS_INCOMPLETE", "cells": []}
    if len(full_h) != len(ys) or len(full_v) != len(xs):
        return {"status": "GRID_AMBIGUOUS", "cells": []}
    for x in xs:
        for y in ys:
            if not _dark_near(pixels, width, height, x, y):
                return {"status": "GRID_INTERSECTIONS_INCOMPLETE", "cells": []}

    if (len(xs) - 1) * (len(ys) - 1) > MAX_CELLS:
        return {"status": "TOO_MANY_CANDIDATE_CELLS", "cells": []}
    cells: list[dict[str, Any]] = []
    for row in range(len(ys) - 1):
        for col in range(len(xs) - 1):
            bbox = [xs[col], ys[row], xs[col + 1], ys[row + 1]]
            if bbox[2] - bbox[0] < 22 or bbox[3] - bbox[1] < 13:
                return {"status": "GRID_AMBIGUOUS", "cells": []}
            cells.append({
                "row_index": row,
                "column_index": col,
                "pixel_bbox": bbox,
                "candidate_status": "RASTER_GRID_CANDIDATE_UNREVIEWED",
                "claim_verified": False,
                "legal_approved": False,
                "payment_approved": False,
            })
    return {
        "status": "RASTER_GRID_CANDIDATES_UNREVIEWED",
        "width_px": width,
        "height_px": height,
        "dpi": REVIEW_DPI,
        "cells": cells,
    }


def _verified_page(key: str) -> tuple[Any, bytes, str, dict[str, Any]] | None:
    if not isinstance(key, str) or ":" not in key:
        return None
    doc_id, raw_number = key.rsplit(":", 1)
    if not re.fullmatch(r"[A-Z][A-Z0-9_]{2,79}", doc_id):
        return None
    if not raw_number.isdecimal() or len(raw_number) > 4:
        return None
    indexer = get_global_pdf_indexer()
    record = indexer.get_page(doc_id, int(raw_number))
    if record is None:
        return None
    try:
        source, _ = indexer._verified_pdf(doc_id)
        if (record.source_sha256 != source["original_sha256"]
                or record.official_url != source["url"] + f"#page={record.page_number}"):
            return None
        png, hits, digest = indexer.screenshot(record, dpi=REVIEW_DPI)
        if hits or digest != source["original_sha256"]:
            return None
        detected = detect_ruled_cells(png)
        detected["source_sha256"] = digest
        detected["source_id"] = doc_id
        detected["page_number"] = record.page_number
        return record, png, digest, detected
    except (OSError, ValueError, KeyError, RuntimeError, ImportError):
        return None


def raster_cell_choices(page_key: str | None) -> list[tuple[str, str]]:
    """Enumerate observed cells on a particular authentic PDF page only."""
    result = _verified_page(page_key or "")
    if result is None:
        return []
    record, _, digest, layout = result
    if layout["status"] != "RASTER_GRID_CANDIDATES_UNREVIEWED":
        return []
    return [
        (
            f"Taranmış hücre adayı · görsel satır {c['row_index'] + 1} / "
            f"sütun {c['column_index'] + 1} · {c['pixel_bbox']}",
            f"{record.doc_id}:{record.page_number}:raster:"
            f"{c['row_index']}:{c['column_index']}:{digest}",
        )
        for c in layout["cells"]
    ]


def _ocr_words_for_candidate(
    record: Any, digest: str, bbox: list[int],
) -> list[str]:
    """Read SHA-/page-bound OCR hypotheses; never silently run new OCR."""
    base = Path(os.getenv("TARIM_RAG_OCR_INDEX_DIR", "data/indexes"))
    try:
        report = json.loads(
            (base / f"verified_ocr_{digest}.json").read_text(encoding="utf-8")
        )
        if (report.get("schema_version") != 1
                or report.get("document_id") != record.doc_id
                or report.get("original_sha256") != digest
                or report.get("original_url") != record.official_url.split("#page=")[0]
                or report.get("original_page_count") != record.total_pages
                or report.get("indexed_page_count") != record.total_pages
                or len(report.get("pages", [])) != record.total_pages):
            return []
        matches = [
            page for page in report["pages"]
            if isinstance(page, dict)
            and page.get("page_number") == record.page_number
            and page.get("source_sha256") == digest
            and page.get("method") == "OCR_UNREVIEWED"
            and isinstance(page.get("ocr_spatial_layout"), dict)
            and page["ocr_spatial_layout"].get("status") == "OCR_LAYOUT_UNREVIEWED"
            and page["ocr_spatial_layout"].get("dpi") == REVIEW_DPI
        ]
        if len(matches) != 1:
            return []
        words = matches[0]["ocr_spatial_layout"].get("words", [])
        if not isinstance(words, list):
            return []
        selected: list[str] = []
        for word in words[:12000]:
            if not isinstance(word, dict):
                continue
            rect = word.get("pixel_bbox")
            value = word.get("text")
            if (not isinstance(rect, list) or len(rect) != 4
                    or any(type(v) is not int for v in rect)
                    or not isinstance(value, str)):
                continue
            mid_x, mid_y = (rect[0] + rect[2]) / 2, (rect[1] + rect[3]) / 2
            if bbox[0] < mid_x < bbox[2] and bbox[1] < mid_y < bbox[3]:
                selected.append(value[:100])
            if len(selected) >= 50:
                break
        return selected
    except (OSError, ValueError, KeyError, TypeError):
        return []


def render_raster_cell(selected: str | None) -> str:
    """Display actual source-page coordinates with an AMBER candidate outline."""
    try:
        from PIL import Image, ImageDraw
    except ImportError:
        return _HOLD

    matched = _SELECTION.fullmatch(selected or "")
    if matched is None:
        return _HOLD
    doc_id, raw_page, raw_row, raw_col, claimed_sha = matched.groups()
    reviewed = _verified_page(f"{doc_id}:{raw_page}")
    if reviewed is None:
        return _HOLD
    record, png, digest, layout = reviewed
    if (claimed_sha != digest
            or layout["status"] != "RASTER_GRID_CANDIDATES_UNREVIEWED"):
        return _HOLD
    row, col = int(raw_row), int(raw_col)
    matches = [
        candidate for candidate in layout["cells"]
        if candidate["row_index"] == row and candidate["column_index"] == col
    ]
    if len(matches) != 1:
        return _HOLD
    rect = matches[0]["pixel_bbox"]
    with Image.open(io.BytesIO(png)) as original:
        full = original.convert("RGB")
        crop_box = (
            max(0, rect[0] - 18), max(0, rect[1] - 18),
            min(full.width, rect[2] + 18), min(full.height, rect[3] + 18),
        )
        crop = full.crop(crop_box)
        # AMBER is deliberately not the yellow legal-proof highlight.
        ImageDraw.Draw(crop).rectangle(
            [rect[0] - crop_box[0], rect[1] - crop_box[1],
             rect[2] - crop_box[0], rect[3] - crop_box[1]],
            outline="#d97706", width=4,
        )
        image_out = io.BytesIO()
        crop.save(image_out, format="PNG")
        encoded = base64.b64encode(image_out.getvalue()).decode("ascii")
    words = _ocr_words_for_candidate(record, digest, rect)
    transcription = (
        escape(" ".join(words)) if words else
        "Koordinatı eşleşen SHA-bağlı OCR taslağı yok."
    )
    url = escape(record.official_url, quote=True)
    return (
        '<section style="padding:14px;border:1px solid #d97706;'
        'border-radius:10px;background:white">'
        '<strong>HOLD — Gerçek pikselden tespit edilmiş tablo hücresi adayı</strong>'
        '<p>Turuncu çerçeve yalnız görsel ızgara tespitidir. '
        'Satır/sütun başlığı, içerik, tutar ve yürürlük doğrulanmadı; '
        'bu alan resmî sarı hukukî vurgu değildir.</p>'
        f'<p>Belge: <code>{escape(doc_id)}</code> · '
        f'Sayfa: {record.page_number}/{record.total_pages} · '
        f'Görsel satır/sütun: {row+1}/{col+1} · '
        f'Piksel kutusu (180 DPI): <code>{escape(str(rect))}</code></p>'
        f'<img src="data:image/png;base64,{encoded}" '
        'style="max-width:100%;height:auto;border:1px solid #cbd5e1" '
        'alt="Gerçek PDF sayfa piksellerinden kırpılan onaysız hücre adayı"/>'
        f'<p><strong>OCR taslağı (onaysız):</strong> {transcription}</p>'
        f'<p>Özgün SHA-256: <code>{escape(digest)}</code></p>'
        f'<p><a href="{url}" target="_blank" rel="noopener noreferrer">'
        'Resmî kaynaktaki gerçek PDF sayfasını aç ↗</a></p>'
        '<p>EK-20 taslak satır/hücre kimliğiyle eşleştirilmedi. '
        'Bağımsız ikinci görsel inceleme ve hukukî onay olmadan ödeme HOLD.</p>'
        '</section>'
    )
