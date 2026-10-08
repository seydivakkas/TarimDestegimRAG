"""Page-exact, SHA-pinned PDF evidence. Unmatched quotes NEVER become citations.

Each highlighting operation uses original official PDF bytes. A marked COPY may
be served to the reader; original source bytes remain immutable in the archive.
Scanned/OCR-incomplete PDFs are explicitly REVIEW until text coordinates are
human inspected. Page numbering is 1-based.
"""
from __future__ import annotations

import hashlib
import re
from dataclasses import asdict, dataclass
from urllib.parse import quote as url_quote

MAX_PDF_BYTES = 30 * 1024 * 1024
SHA_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class UnverifiableEvidence(ValueError):
    pass


@dataclass(frozen=True)
class PdfEvidence:
    source_sha256: str
    page_1_indexed: int
    exact_quote: str
    normalized_quads: list[list[list[float]]]
    match_count: int
    status: str = "EXACT_TEXT_LOCATED_PENDING_LEGAL_REVIEW"

    def as_json(self) -> dict:
        return asdict(self)


def locate_pdf_quote(
    pdf_bytes: bytes, *, expected_sha256: str, page_1_indexed: int, exact_quote: str,
) -> PdfEvidence:
    """Forbid false citations: hash mismatch, absent/duplicate/OCR loss => error."""
    import pymupdf

    if (
        not SHA_PATTERN.fullmatch(expected_sha256)
        or not pdf_bytes.startswith(b"%PDF-")
        or len(pdf_bytes) > MAX_PDF_BYTES
        or hashlib.sha256(pdf_bytes).hexdigest() != expected_sha256
    ):
        raise UnverifiableEvidence("Original PDF bytes do not match source SHA-256")
    quote = " ".join(exact_quote.split())
    if not 12 <= len(quote) <= 1500 or any(x in quote for x in ("<", ">")):
        raise UnverifiableEvidence("Invalid or overly short legal quotation")
    try:
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
            if not 1 <= page_1_indexed <= document.page_count:
                raise UnverifiableEvidence("PDF page does not exist")
            page = document[page_1_indexed - 1]
            raw = " ".join(page.get_text(sort=True).split())
            # Exact source character check, not search-engine fuzzy matches.
            if quote not in raw:
                raise UnverifiableEvidence(
                    "Exact source sentence not found; OCR/manual text review required"
                )
            if raw.count(quote) != 1:
                raise UnverifiableEvidence(
                    "Quoted text is ambiguous: multiple identical occurrences"
                )
            quads = page.search_for(quote, quads=True)
            if not quads:
                raise UnverifiableEvidence(
                    "Source string is present but cannot be highlighted at precise coordinates"
                )
            norm = []
            for quad in quads:
                norm.append([
                    [round(float(point.x / page.rect.width), 6),
                     round(float(point.y / page.rect.height), 6)]
                    for point in (quad.ul, quad.ur, quad.ll, quad.lr)
                ])
            if any(not (0 <= x <= 1 and 0 <= y <= 1)
                   for quad in norm for x, y in quad):
                raise UnverifiableEvidence("Highlight coordinates exceed PDF page bounds")
            return PdfEvidence(
                source_sha256=expected_sha256, page_1_indexed=page_1_indexed,
                exact_quote=quote, normalized_quads=norm, match_count=1,
            )
    except (RuntimeError, ValueError) as exc:
        if isinstance(exc, UnverifiableEvidence):
            raise
        raise UnverifiableEvidence("Cannot parse PDF to locate legal quote") from exc


def highlighted_pdf_copy(
    pdf_bytes: bytes, evidence: PdfEvidence,
) -> bytes:
    """Generate a separate view copy containing visible yellow annotations."""
    import pymupdf

    if hashlib.sha256(pdf_bytes).hexdigest() != evidence.source_sha256:
        raise UnverifiableEvidence("Original PDF version has changed")
    actual = locate_pdf_quote(
        pdf_bytes, expected_sha256=evidence.source_sha256,
        page_1_indexed=evidence.page_1_indexed,
        exact_quote=evidence.exact_quote,
    )
    if actual.normalized_quads != evidence.normalized_quads:
        raise UnverifiableEvidence("Page layout changed; regenerate source evidence")
    with pymupdf.open(stream=pdf_bytes, filetype="pdf") as document:
        page = document[evidence.page_1_indexed - 1]
        for quad in page.search_for(evidence.exact_quote, quads=True):
            annotation = page.add_highlight_annot(quad)
            annotation.set_colors(stroke=(1, 0.88, 0))
            annotation.update()
        return document.tobytes(garbage=4, deflate=True)


def evidence_deeplink(evidence: PdfEvidence) -> str:
    """Point to the actual content-addressed PDF-highlight API endpoint."""
    if not SHA_PATTERN.fullmatch(evidence.source_sha256) or evidence.page_1_indexed < 1:
        raise UnverifiableEvidence("Evidence link requires validated PDF SHA and page")
    return (
        f"/evidence/highlight/{evidence.source_sha256}"
        f"?page={evidence.page_1_indexed}&quote={url_quote(evidence.exact_quote, safe='')}"
    )
