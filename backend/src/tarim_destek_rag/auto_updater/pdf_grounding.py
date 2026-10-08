"""Layout-aware, SHA-256-pinned official PDF grounding.

All coordinates are produced by parsing the ORIGINAL archived PDF bytes.
The marked page is generated from a separate in-memory copy and is not a
claim that the cited clause is current, legally effective or human approved.
No OCR inference: image-only scanned PDFs fail closed.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from io import BytesIO
from typing import Any

from tarim_destek_rag.updates.pdf_evidence import (
    PdfEvidence,
    UnverifiableEvidence,
    locate_pdf_quote,
    SHA_PATTERN,
)

MAX_RENDER_PIXELS = 24_000_000


@dataclass(frozen=True)
class GroundedPage:
    document_sha256: str
    page_number: int
    exact_quote: str
    article: str | None
    paragraph: str | None
    clause: str | None
    boxes: tuple[tuple[float, float, float, float], ...]
    normalized_quads: list[list[list[float]]]
    status: str = "EXACT_PDF_COORDINATES_PENDING_LEGAL_REVIEW"

    def to_dict(self) -> dict[str, Any]:
        return {
            "document_sha256": self.document_sha256,
            "page_number": self.page_number,
            "exact_quote": self.exact_quote,
            "article": self.article,
            "paragraph": self.paragraph,
            "clause": self.clause,
            "bounding_boxes": [
                {"x0": b[0], "y0": b[1], "x1": b[2], "y1": b[3]}
                for b in self.boxes
            ],
            "normalized_quads": self.normalized_quads,
            "status": self.status,
        }


class PDFGroundingEngine:
    """Match exact passage and render yellow-marked WebP/PNG page bytes."""

    @staticmethod
    def ground(
        pdf_bytes: bytes,
        *,
        document_sha256: str,
        page_number: int,
        exact_quote: str,
        article: str | None = None,
        paragraph: str | None = None,
        clause: str | None = None,
    ) -> GroundedPage:
        import pymupdf

        evidence = locate_pdf_quote(
            pdf_bytes,
            expected_sha256=document_sha256,
            page_1_indexed=page_number,
            exact_quote=exact_quote,
        )
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            page = document[page_number - 1]
            quads = page.search_for(evidence.exact_quote, quads=True)
            if not quads:
                raise UnverifiableEvidence("Coordinates could not be recovered")
            boxes = tuple(
                (
                    round(float(quad.rect.x0), 3),
                    round(float(quad.rect.y0), 3),
                    round(float(quad.rect.x1), 3),
                    round(float(quad.rect.y1), 3),
                )
                for quad in quads
            )
            if any(x0 < 0 or y0 < 0 or x1 > page.rect.width + 0.01
                   or y1 > page.rect.height + 0.01 or x0 >= x1 or y0 >= y1
                   for x0, y0, x1, y1 in boxes):
                raise UnverifiableEvidence("Grounding box exceeds source page")
        return GroundedPage(
            document_sha256=document_sha256,
            page_number=page_number,
            exact_quote=evidence.exact_quote,
            article=article,
            paragraph=paragraph,
            clause=clause,
            boxes=boxes,
            normalized_quads=evidence.normalized_quads,
        )

    @staticmethod
    def render_highlighted_page(
        pdf_bytes: bytes,
        grounded: GroundedPage,
        *,
        dpi: int = 144,
        image_format: str = "png",
    ) -> tuple[bytes, str]:
        import pymupdf

        if image_format not in ("png", "webp") or not 72 <= dpi <= 200:
            raise UnverifiableEvidence("Unsupported page format or DPI")
        if not SHA_PATTERN.fullmatch(grounded.document_sha256) or (
            hashlib.sha256(pdf_bytes).hexdigest() != grounded.document_sha256
        ):
            raise UnverifiableEvidence("PDF hash changed after grounding")
        recomputed = PDFGroundingEngine.ground(
            pdf_bytes,
            document_sha256=grounded.document_sha256,
            page_number=grounded.page_number,
            exact_quote=grounded.exact_quote,
            article=grounded.article,
            paragraph=grounded.paragraph,
            clause=grounded.clause,
        )
        if recomputed.boxes != grounded.boxes or (
            recomputed.normalized_quads != grounded.normalized_quads
        ):
            raise UnverifiableEvidence("Source PDF layout changed after indexing")
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            page = document[grounded.page_number - 1]
            scale = dpi / 72
            if int(page.rect.width * scale) * int(page.rect.height * scale) > MAX_RENDER_PIXELS:
                raise UnverifiableEvidence("PDF render would exceed image pixel limit")
            # Mark actual text in a separate in-memory PDF, then rasterize it.
            for quad in page.search_for(grounded.exact_quote, quads=True):
                annot = page.add_highlight_annot(quad)
                annot.set_colors(stroke=(1.0, 0.91, 0.12))
                annot.set_opacity(0.42)
                annot.update()
            pixels = page.get_pixmap(dpi=dpi, alpha=False, annots=True)
            png = pixels.tobytes("png")
            if image_format == "png":
                return png, "image/png"
            # PyMuPDF does not export WebP directly. Pillow converts the
            # already-highlighted PNG without changing the source PDF.
            from PIL import Image

            buffer = BytesIO()
            with Image.open(BytesIO(png)) as visible:
                visible.save(buffer, format="WEBP", quality=90)
            return buffer.getvalue(), "image/webp"
