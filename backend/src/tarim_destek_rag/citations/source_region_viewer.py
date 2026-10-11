"""Zoom into original PDF table, image, or vector regions without invention.

Region discovery is layout metadata, not a legal statement or a reliable
OCR transcription. The original SHA and the exact page are checked AGAIN
before cropping the independent original PDF bytes.
"""
from __future__ import annotations

import base64
import re
from html import escape

from tarim_destek_rag.citations.pdf_page_indexer import get_global_pdf_indexer

MAX_REGIONS = 100
REGION_KINDS = ("table", "image", "vector")


def _regions(page: object) -> list[tuple[str, tuple[float, float, float, float]]]:
    """Stable in-memory layout choices; fail closed rather than fabricate geometry."""
    import pymupdf

    candidates: list[tuple[str, tuple[float, float, float, float]]] = []
    bounds = page.rect

    def add(kind: str, rect: object) -> None:
        if len(candidates) >= MAX_REGIONS:
            return
        region = pymupdf.Rect(rect) & bounds
        if (region.is_empty or not region.is_finite
                or region.width < 15 or region.height < 10
                or region.get_area() > bounds.get_area() * 0.98):
            return
        candidates.append((kind, tuple(region)))

    try:
        for table in page.find_tables().tables[:40]:
            add("table", table.bbox)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        pass
    try:
        seen = set()
        for im in page.get_images(full=True)[:40]:
            for rect in page.get_image_rects(im[0]):
                coords = tuple(rect)
                if coords not in seen:
                    seen.add(coords)
                    add("image", rect)
    except (AttributeError, TypeError, ValueError, RuntimeError):
        pass
    # Vector bounds may cover decorative page borders. They are labeled
    # merely as drawing regions and never as official stamps/charts.
    for drawing in page.get_drawings()[:100]:
        rect = drawing.get("rect")
        if rect:
            add("vector", rect)
    return candidates


def _selected(
    choice: str,
) -> tuple[str, int, str, int] | None:
    if not isinstance(choice, str):
        return None
    match = re.fullmatch(
        r"([A-Z][A-Z0-9_]{2,79}):([1-9][0-9]*):(table|image|vector):(\d{1,3})",
        choice,
    )
    if not match:
        return None
    page, idx = int(match.group(2)), int(match.group(4))
    if idx >= MAX_REGIONS or page > 1000:
        return None
    return match.group(1), page, match.group(3), idx


def page_region_choices(page_key: str | None) -> list[tuple[str, str]]:
    """Only regions *inside a SHA-verified original PDF page* can be selected."""
    import pymupdf

    if not page_key or ":" not in page_key:
        return []
    doc_id, page_str = page_key.rsplit(":", 1)
    if not page_str.isdigit():
        return []
    indexer = get_global_pdf_indexer()
    record = indexer.get_page(doc_id, int(page_str))
    if record is None:
        return []
    try:
        source, original = indexer._verified_pdf(record.doc_id)
        if record.source_sha256 != source["original_sha256"]:
            return []
        with pymupdf.open(stream=original, filetype="pdf") as doc:
            if record.total_pages != len(doc):
                return []
            regions = _regions(doc[record.page_number-1])
    except (OSError, ValueError, RuntimeError, KeyError):
        return []
    return [
        (f"{kind} · Gerçek PDF sayfa {record.page_number} · bölge {i+1}",
         f"{doc_id}:{record.page_number}:{kind}:{i}")
        for i, (kind, _) in enumerate(regions)
    ]


def render_source_region(selected: str | None) -> str:
    """Crop original, preserving source SHA. Layout ROI != legal verification."""
    import pymupdf

    info = _selected(selected or "")
    if info is None:
        return "<p>Sayfadan bir gerçek bölge seçin; kaynak yoksa HOLD.</p>"
    doc_id, number, kind, idx = info
    indexer = get_global_pdf_indexer()
    record = indexer.get_page(doc_id, number)
    if record is None:
        return "<p>HOLD — Özgün kaynak veya sayfa bulunamadı.</p>"
    try:
        source, original = indexer._verified_pdf(doc_id)
        if (source["original_sha256"] != record.source_sha256
                or record.total_pages <= 0
                or record.official_url != source["url"] + f"#page={number}"):
            raise ValueError("Untrusted page provenance")
        with pymupdf.open(stream=original, filetype="pdf") as doc:
            if number > len(doc) or len(doc) != record.total_pages:
                raise ValueError("Incorrect page index")
            page = doc[number-1]
            regions = _regions(page)
            if idx >= len(regions) or regions[idx][0] != kind:
                raise ValueError("Region index changed")
            rectangle = pymupdf.Rect(regions[idx][1])
            padding = pymupdf.Rect(
                rectangle.x0-6, rectangle.y0-6,
                rectangle.x1+6, rectangle.y1+6,
            ) & page.rect
            img = page.get_pixmap(dpi=195, clip=padding, alpha=False)
            png = img.tobytes("png")
    except (OSError, ValueError, RuntimeError, KeyError):
        return "<p>HOLD — Bölgenin konumu özgün PDF'de doğrulanamadı.</p>"
    encoded = base64.b64encode(png).decode("ascii")
    href = escape(record.official_url, quote=True)
    return (
        '<section style="border:1px solid #cbd5e1;padding:12px">'
        '<strong>Özgün PDF'den kırpılmış gerçek görüntü — '
        f'{escape(kind)} bölgesi</strong>'
        f'<p>Sayfa {number}/{record.total_pages} · SHA-256: '
        f'<code>{escape(source["original_sha256"])}</code></p>'
        f'<img src="data:image/png;base64,{encoded}" '
        'style="display:block;max-width:100%;height:auto;border:1px solid #cbd5e1" '
        'alt="Özgün belgeden çıkarılmış, semantik doğrulaması bekleyen görsel bölge" />'
        f'<p><a href="{href}" target="_blank" rel="noopener noreferrer">'
        'Özgün PDF sayfasını aç ↗</a></p>'
        '<p><strong>HOLD:</strong> Bu görselin gerçekten kaynak dosyaya '
        'ait olduğu doğrulanır; grafik, tablo sütunu veya sayısal '
        'hükmün anlamı ayrıca incelenmelidir.</p></section>'
    )
