"""Spatial OCR candidate layout extracted from a verified original PDF image.

The TSV word coordinates are OCR hypotheses, not original-PDF text evidence,
not verified EK-20 cells and never an automatic payout trigger.
"""
from __future__ import annotations

import base64
import csv
import io
import re
from html import escape
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


def render_ocr_spatial_review(page_key: str | None) -> str:
    """Show measured OCR lines on the verified original-page pixels for review.

    Orange boxes always denote unreviewed OCR hypotheses, never legal proof.
    The source PDF remains untouched; overlays exist only in this preview.
    """
    from PIL import Image, ImageDraw

    if not isinstance(page_key, str) or ":" not in page_key:
        return "<p>HOLD — Önce özgün bir PDF sayfası seçin.</p>"
    doc_id, page_str = page_key.rsplit(":", 1)
    if (not re.fullmatch(r"[A-Z][A-Z0-9_]{2,79}", doc_id)
            or not re.fullmatch(r"[1-9][0-9]{0,3}", page_str)):
        return "<p>HOLD — PDF sayfa kimliği geçersiz.</p>"
    try:
        from tarim_destek_rag.citations.pdf_page_indexer import get_global_pdf_indexer

        idx = get_global_pdf_indexer()
        record = idx.get_page(doc_id, int(page_str))
        if record is None:
            raise ValueError("No verified page")
        source, _ = idx._verified_pdf(doc_id)
        if (record.source_sha256 != source["original_sha256"]
                or record.official_url != source["url"] + f"#page={record.page_number}"):
            raise ValueError("Original page URL/SHA mismatch")
        layout = extract_ocr_geometry(idx, record, dpi=180)
        if (layout.get("status") != "OCR_LAYOUT_UNREVIEWED"
                or layout.get("source_sha256") != source["original_sha256"]
                or layout.get("page_number") != record.page_number
                or layout.get("dpi") != 180):
            return (
                "<p><strong>HOLD — OCR satır koordinatları alınamadı.</strong> "
                f"Durum: {escape(str(layout.get('status', 'UNKNOWN')))}</p>"
            )
        png, highlights, digest = idx.screenshot(record, dpi=180)
        if highlights or digest != source["original_sha256"]:
            raise ValueError("OCR display source mismatch")
        with Image.open(io.BytesIO(png)) as source_image:
            image = source_image.convert("RGB")
        draw = ImageDraw.Draw(image)
        lines = layout["lines"]
        shown = []
        for index, line in enumerate(lines[:65], start=1):
            bounds = line.get("pixel_bbox")
            value = line.get("text", "")
            if (not isinstance(bounds, list) or len(bounds) != 4
                    or any(type(x) is not int for x in bounds)
                    or not isinstance(value, str)
                    or bounds[0] < 0 or bounds[1] < 0
                    or bounds[2] > image.width or bounds[3] > image.height
                    or bounds[0] >= bounds[2] or bounds[1] >= bounds[3]):
                continue
            draw.rectangle(bounds, outline="#d97706", width=3)
            shown.append(
                f"<tr><td>{index}</td><td><code>{escape(str(bounds))}</code></td>"
                f"<td>{escape(value[:260])}</td></tr>"
            )
        if not shown:
            return "<p>HOLD — Geçerli OCR satır kutusu bulunamadı.</p>"
        out = io.BytesIO()
        image.save(out, format="PNG")
        encoded = base64.b64encode(out.getvalue()).decode("ascii")
        return (
            '<section style="border:1px solid #d97706;padding:14px">'
            "<strong>HOLD — Gerçek sayfada OCR satır koordinatları</strong>"
            "<p>Turuncu kutular Tesseract satır tahminleridir. Kaynak metninin "
            "birebir doğrulandığı veya ilgili maddenin yürürlükte olduğu anlamına "
            "gelmez. OCR sonucu uygulamanın hukukî alıntısı yapılamaz.</p>"
            f'<p>Belge: <code>{escape(doc_id)}</code> · '
            f'Sayfa: {record.page_number}/{record.total_pages} · '
            'DPI: 180 · '
            f'SHA-256: <code>{escape(digest)}</code></p>'
            f'<img src="data:image/png;base64,{encoded}" '
            'alt="Doğrulanmış gerçek PDF sayfası üstünde OCR taslak satır kutuları" '
            'style="width:100%;max-width:100%;height:auto;border:1px solid #cbd5e1"/>'
            '<table><thead><tr><th>#</th><th>Piksel koordinatı</th>'
            '<th>OCR taslağı — onaysız</th></tr></thead><tbody>'
            + "".join(shown)
            + "</tbody></table>"
            f'<p><a href="{escape(record.official_url, quote=True)}" '
            'target="_blank" rel="noopener noreferrer">Özgün PDF sayfası ↗</a></p>'
            "</section>"
        )
    except (OSError, ValueError, KeyError, RuntimeError, TypeError, ImportError):
        return "<p>HOLD — Doğrulanmış OCR satır görüntüsü oluşturulamadı.</p>"
