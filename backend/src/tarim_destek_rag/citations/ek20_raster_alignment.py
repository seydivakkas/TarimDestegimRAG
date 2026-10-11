"""Reviewer-driven EK-20 semantic cell <-> measured original pixel grid alignment.

This module does not guess semantic row order, register reviewer signatures,
save any approval, or promote OCR to a legally verified table value.
"""
from __future__ import annotations

import re
from html import escape
from typing import Any

from tarim_destek_rag.citations.ek20_cell_provenance import (
    DOC_ID,
    FIELD_IDS,
    prepare_roi,
    render_candidate_roi,
)
from tarim_destek_rag.citations.ek20_review_workbench import _table
from tarim_destek_rag.citations.raster_table_review import (
    _SELECTION,
    _ocr_words_for_candidate,
    _verified_page,
    raster_cell_choices,
)

SOURCE_PAGE = f"{DOC_ID}:1"
_EMPTY = (None, None, None, None)
_HOLD = (
    "<p><strong>HOLD — Özgün EK-20 hücresiyle eşleştirme yapılmadı.</strong> "
    "Belge, üretim yılı, ürün-sütun veya gerçek görüntü kutusu uyuşmuyor. "
    "Koordinatlar boş bırakıldı; hiçbir değer ya da görsel inceleme onaylanmadı.</p>"
)


def measured_ek20_cell_choices() -> list[tuple[str, str]]:
    """Expose ONLY geometrically detected boxes from original annex page 1."""
    return raster_cell_choices(SOURCE_PAGE)


def _matches_year(evaluation: dict[str, Any] | None) -> bool:
    if not isinstance(evaluation, dict):
        return False
    parcel = evaluation.get("parcel")
    return (isinstance(parcel, dict)
            and type(parcel.get("production_year")) is int
            and parcel["production_year"] == 2026)


def align_measured_cell_for_review(
    selected_semantic: str | None,
    selected_measured: str | None,
    evaluation: dict[str, Any] | None,
) -> tuple[int | None, int | None, int | None, int | None, str]:
    """Prefill manual ROI controls from exactly observed grid borders.

    A user selects both the semantic row/column and the physical grid cell.
    The application never asserts the two are equivalent; two independent
    source-image reviewers still need to approve the visual transcription.
    """
    if not _matches_year(evaluation):
        return (*_EMPTY, _HOLD)
    if (not isinstance(selected_semantic, str)
            or selected_semantic.count(":") != 1
            or not isinstance(selected_measured, str)):
        return (*_EMPTY, _HOLD)
    row_id, field = selected_semantic.split(":")
    data = _table()
    if (
        data is None
        or field not in FIELD_IDS
        or not re.fullmatch(r"[a-z][a-z0-9_]{1,60}", row_id)
        or len([r for r in data["rows"] if r.get("row_id") == row_id]) != 1
    ):
        return (*_EMPTY, _HOLD)
    parsed = _SELECTION.fullmatch(selected_measured)
    if parsed is None:
        return (*_EMPTY, _HOLD)
    doc_id, page_str, row_str, column_str, expected_digest = parsed.groups()
    if doc_id != DOC_ID or page_str != "1":
        return (*_EMPTY, _HOLD)
    found = _verified_page(SOURCE_PAGE)
    if found is None:
        return (*_EMPTY, _HOLD)
    record, original_png, digest, layout = found
    if (
        expected_digest != digest
        or digest != data["source_sha256"]
        or record.total_pages != 1
        or layout.get("status") != "RASTER_GRID_CANDIDATES_UNREVIEWED"
        or layout.get("dpi") != 180
    ):
        return (*_EMPTY, _HOLD)
    candidates = [
        cell for cell in layout["cells"]
        if cell["row_index"] == int(row_str)
        and cell["column_index"] == int(column_str)
        and cell["candidate_status"] == "RASTER_GRID_CANDIDATE_UNREVIEWED"
    ]
    if len(candidates) != 1:
        return (*_EMPTY, _HOLD)
    rect = candidates[0]["pixel_bbox"]
    if (
        not isinstance(rect, list) or len(rect) != 4
        or any(type(v) is not int for v in rect)
    ):
        return (*_EMPTY, _HOLD)
    try:
        candidate_proposal = prepare_roi(row_id, field, list(rect))
    except (OSError, ValueError, TypeError, KeyError, RuntimeError, ImportError):
        return (*_EMPTY, _HOLD)
    if (
        candidate_proposal.get("source_sha256") != digest
        or candidate_proposal.get("source_page") != 1
        or candidate_proposal.get("render_dpi") != 180
        or candidate_proposal.get("production_year") != 2026
        or candidate_proposal.get("pixel_bbox") != rect
        or candidate_proposal.get("image_size") != [
            layout.get("width_px"), layout.get("height_px"),
        ]
    ):
        return (*_EMPTY, _HOLD)
    from PIL import Image
    import io

    try:
        with Image.open(io.BytesIO(original_png)) as im:
            if list(im.size) != candidate_proposal["image_size"]:
                return (*_EMPTY, _HOLD)
    except (OSError, ValueError):
        return (*_EMPTY, _HOLD)
    words = _ocr_words_for_candidate(record, digest, rect)
    draft = " ".join(words) if words else "Kutuya bağlı OCR kelimesi bulunamadı"
    preview = render_candidate_roi(selected_semantic, *rect)
    if "ROI RGB SHA-256" not in preview:
        return (*_EMPTY, _HOLD)
    note = (
        '<section style="padding:12px;background:#fffbeb;border:1px solid #d97706">'
        "<strong>HOLD — Ölçülen kutu seçilen EK-20 alanına yalnız önerildi.</strong>"
        "<p>Izgara satır/sütun numarası, EK-20'nin ürün ve destek sütunuyla "
        "otomatik olarak eşleştirilmedi. Kullanıcı seçti; resmî belge ve iki "
        "bağımsız görsel incelemeci doğrulamadan geçerli kanıt değildir.</p>"
        f"<p>Özgün kaynak SHA: <code>{escape(digest)}</code> · "
        f"Ölçülen hücre piksel kutusu (180 DPI): <code>{escape(str(rect))}</code></p>"
        f"<p><strong>OCR taslağı, onaysız:</strong> {escape(draft[:600])}</p>"
        "</section>"
    )
    return (*rect, note + preview)
