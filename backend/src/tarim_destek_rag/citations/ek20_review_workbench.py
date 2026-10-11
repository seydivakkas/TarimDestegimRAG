"""EK-20 original table + human transcription review workbench.

This NEVER authorizes payments, never promotes OCR numbers to approved tariff
values, and never claims an individual cell box has been independently located.
"""
from __future__ import annotations

import base64
import json
import os
from html import escape
from pathlib import Path
from typing import Any

from tarim_destek_rag.citations.pdf_page_indexer import get_global_pdf_indexer

FIELD_NAMES = {
    "biological_tl_da": "Biyolojik mücadele (TL/da)",
    "biotechnical_tl_da": "Biyoteknik mücadele (TL/da)",
    "feromone_trap_tl_da": "Feromon + tuzak (TL/da)",
    "feromone_only_tl_da": "Feromon (TL/da)",
}
EK_SOURCE_ID = "RG_AMENDMENT_2025_42_ANNEX"


def _table() -> dict[str, Any] | None:
    try:
        path = Path(os.getenv(
            "TARIM_RAG_EK20_TRANSCRIPTION",
            "configs/p0_10_4_ek20_visual_transcription.json",
        ))
        data = json.loads(path.read_text(encoding="utf-8"))
        if (
            data.get("source_document_id") != EK_SOURCE_ID
            or data.get("production_year") != 2026
            or data.get("source_pdf_page_count") != 1
            or data.get("table_pdf_page") != 1
            or data.get("transcription_status") !=
                "VISUAL_TRANSCRIPTION_PENDING_INDEPENDENT_REVIEW"
            or data.get("independent_legal_reviewer_approved") is not False
            or data.get("automatic_rate_activation") is not False
            or len(data.get("rows", [])) != 12
        ):
            return None
        return data
    except (OSError, ValueError, KeyError, TypeError):
        return None


def ek20_cell_choices() -> list[tuple[str, str]]:
    data = _table()
    if data is None:
        return []
    choices: list[tuple[str, str]] = []
    for row in data["rows"]:
        identifier = row.get("row_id")
        label = row.get("product_pest")
        if not isinstance(identifier, str) or not isinstance(label, str):
            continue
        for key, title in FIELD_NAMES.items():
            value = row.get(key)
            display = "— (belirtilmemiş)" if value is None else f"{value} TL/da (taslak)"
            choices.append((
                f"{label[:65]} · {title} · {display}",
                f"{identifier}:{key}",
            ))
    return choices


def render_ek20_candidate(
    selected: str | None, evaluation: dict[str, Any] | None,
) -> str:
    if not selected or ":" not in selected:
        return "<p>EK-20 için bir ürün satırı ve tutar sütunu seçin.</p>"
    if not isinstance(evaluation, dict):
        return "<p>HOLD — Önce üretim yılı belirlenmiş bir değerlendirme yapın.</p>"
    year = (evaluation.get("parcel") or {}).get("production_year")
    if type(year) is not int or year != 2026:
        return "<p>HOLD — Bu EK-20 taslak incelemesi yalnız 2026 üretim yılına aittir.</p>"
    data = _table()
    if data is None:
        return "<p>HOLD — EK-20 kaynak veya görsel aktarım kaydı eksik.</p>"
    row_id, cell_id = selected.rsplit(":", 1)
    if cell_id not in FIELD_NAMES:
        return "<p>HOLD — EK-20 sütun kimliği geçersiz.</p>"
    rows = [r for r in data["rows"] if r.get("row_id") == row_id]
    if len(rows) != 1:
        return "<p>HOLD — EK-20 satır kimliği belirsiz.</p>"
    row = rows[0]
    value = row.get(cell_id)
    if value is not None and (type(value) is not int or value < 0):
        return "<p>HOLD — Tutar biçimi beklenmiyor.</p>"
    indexer = get_global_pdf_indexer()
    original_page = indexer.get_page(EK_SOURCE_ID, 1)
    if original_page is None or original_page.total_pages != 1:
        return "<p>HOLD — EK-20 özgün PDF dosyasından sayfa alınamıyor.</p>"
    try:
        source, _ = indexer._verified_pdf(EK_SOURCE_ID)
        if (data["source_sha256"] != source["original_sha256"]
                or data["source_url"] != source["url"]
                or original_page.source_sha256 != source["original_sha256"]):
            raise ValueError("Original EK-20 source mismatched transcription")
        image, highlights, digest = indexer.screenshot(original_page, dpi=200)
        if highlights:
            raise ValueError("Unreviewed cell must not be visually highlighted")
    except (OSError, ValueError, KeyError):
        return "<p>HOLD — EK-20 kaynağı ile tablo aktarımı uyuşmuyor.</p>"
    from tarim_destek_rag.citations.ek20_cell_provenance import render_review_overlay

    # Separate original full-page image from the cryptographically gated overlay.
    # Never use OCR or a manually supplied bbox as a yellow legal citation.
    review_panel = render_review_overlay(selected)
    image_src = base64.b64encode(image).decode("ascii")
    text = "— (bu hücreye tutar girilmemiş)" if value is None else f"{value} TL/da"
    return (
        '<section style="padding:15px;border:1px solid #cbd5e1;'
        'border-radius:12px;background:white">'
        '<h4>EK-20 — Gerçek resmî tablo ve seçilen taslak hücre</h4>'
        '<p><strong>HOLD:</strong> Hücre metni insan tarafından ikinci kez '
        'doğrulanmadı. Bu sayısal değer hesaplamaya ve ödeme kararına aktarılamaz.</p>'
        f'<p><strong>Ürün/etmen:</strong> {escape(row["product_pest"])} · '
        f'<strong>Sütun:</strong> {escape(FIELD_NAMES[cell_id])} · '
        f'<strong>Aktarım:</strong> {escape(text)}</p>'
        f'<img src="data:image/png;base64,{image_src}" '
        'style="width:100%;max-width:100%;height:auto;border:1px solid #cbd5e1" '
        'alt="Orijinal tek sayfalık EK-20 tablosunun gerçek PDF görüntüsü"/>'
        f'<p>Özgün kaynak SHA-256: <code>{escape(digest)}</code></p>'
        f'<p><a href="{escape(original_page.official_url, quote=True)}" '
        'target="_blank" rel="noopener noreferrer">'
        'Resmî Gazete'nin özgün EK-20 PDF sayfasını aç ↗</a></p>'
        '<p>Kaynak üzerindeki sarı hücre işareti yalnız iki ayrı yetkili '
        'kriptografik görsel inceleme imzası doğrulandığında çizilir. '
        'Hukukî yürürlük ve ödeme her durumda HOLD kalır.</p>'
        + review_panel + '</section>'
    )
