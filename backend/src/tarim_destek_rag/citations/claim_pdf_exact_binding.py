"""Manually curated exact support-reason -> ORIGINAL PDF native text location.

Fail-closed. Not OCR proof: scanned PDFs must use separate original-pixel
review/dual signatures, not machine text similarity. A human binding proposal
and exact source text position establish ONLY the provenance of normative text.
They do not establish legal effectiveness, payment or farmer eligibility.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_OFFICIAL = {"resmigazete.gov.tr", "www.resmigazete.gov.tr",
             "tarimorman.gov.tr", "www.tarimorman.gov.tr"}


def _config() -> Path:
    return Path(os.getenv("TARIM_RAG_CLAIM_PDF_BINDINGS",
                          "configs/claim_pdf_exact_bindings.json"))


def _original(meta: dict[str, Any]) -> bytes:
    """Fetch ONLY declared pinned original archive bytes, never an arbitrary URL."""
    from tarim_destek_rag.citations.claim_evidence_workbench import _paths
    from tarim_destek_rag.retrieval.document_rag import _read_original
    from tarim_destek_rag.updates.annual_pdf_pipeline import _catalog, _verify_doc

    sha, source_id, url = (
        meta["source_sha256"], meta["source_id"], meta["source_url"])
    if not isinstance(sha, str) or not _SHA.fullmatch(sha):
        raise ValueError("Bad source checksum")
    if not isinstance(source_id, str) or not isinstance(url, str):
        raise ValueError("Bad original source identity")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in _OFFICIAL
            or parsed.port not in (None,443) or parsed.username
            or parsed.password or parsed.query or parsed.fragment):
        raise ValueError("Not an official unmodified PDF URL")
    _, manifest, root = _paths()
    if source_id == "RG_DISCOVERED_" + sha[:16].upper():
        matches = [m for m in _catalog(root) if m.get("sha256") == sha
                   and m.get("source_url") == url]
        if len(matches) != 1:
            raise ValueError("Unpinned discovered source")
        return _verify_doc(root, matches[0])
    document = json.loads(manifest.read_text(encoding="utf-8"))
    originals = [m for m in document.get("sources", [])
                 if m.get("id") == source_id and m.get("format") == "pdf"
                 and m.get("original_sha256") == sha and m.get("url") == url]
    if len(originals) != 1:
        raise ValueError("Unrecognized manifest source")
    return _read_original(root, originals[0])


def _page_match(raw: bytes, *, number: int, quote: str
                ) -> tuple[list[list[int]], int]:
    """Require unique exact native text and actual original pixel coordinates."""
    import pymupdf
    if (type(number) is not int or not 1 <= number <= 2000
            or not isinstance(quote, str) or not 25 <= len(quote) <= 2000):
        raise ValueError("Invalid page/quote")
    with pymupdf.open(stream=raw, filetype="pdf") as pdf:
        if number > len(pdf):
            raise ValueError("Missing page")
        page = pdf[number-1]
        if page.rotation:
            raise ValueError("Rotated page requires manual coordinate review")
        text = " ".join(page.get_text("text", sort=True).split())
        exact = " ".join(quote.split())
        if not text or text.count(exact) != 1:
            raise ValueError("No unique exact original native PDF quote")
        # search_for may miss a wrapped quotation even when text is unique;
        # do not invent pixel geometry in that case.
        hits = page.search_for(exact)
        if not 1 <= len(hits) <= 24:
            raise ValueError("Original quote geometry missing/oversized")
        img = page.get_pixmap(dpi=180, alpha=False)
        rects = []
        for rect in hits:
            x0,y0,x1,y1 = [int(round(float(n)*180/72)) for n in
                           (rect.x0,rect.y0,rect.x1,rect.y1)]
            if not 0 <= x0 < x1 <= img.width or not 0 <= y0 < y1 <= img.height:
                raise ValueError("Native coordinates beyond page")
            rects.append([x0,y0,x1,y1])
        return rects, len(pdf)


def exact_pdf_binding(
    evaluation: dict[str, Any] | None, claim: dict[str, Any],
) -> dict[str, Any] | None:
    """Resolve one explicit year+rule+field+literal reason with real pixels."""
    try:
        path = _config()
        if not path.is_file() or path.stat().st_size > 2_000_000:
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("schema_version") != 1 or not isinstance(data.get("bindings"), list):
            return None
        entries = data["bindings"]
        if len(entries) > 5000:
            return None
        keys = [
            (r.get("rule_id"),r.get("support_id"),r.get("production_year"),
             r.get("check_id"))
            for r in entries if isinstance(r, dict)
        ]
        if len(entries) != len(keys) or len(keys) != len(set(keys)):
            return None
        if (claim.get("identity_status") != "RULE_EMITTED_STABLE_CHECK_ID"
                or not isinstance(claim.get("check_id"), str)):
            return None
        matching = [r for r in entries if (
            r.get("rule_id"), r.get("support_id"),r.get("production_year"),
            r.get("check_id")
        ) == (
            claim["rule_id"],claim["support_id"],claim["year"],
            claim["check_id"],
        )]
        if len(matching) != 1:
            return None
        item = matching[0]
        if (type(item.get("production_year")) is not int
                or item["production_year"] != claim["year"]
                or not isinstance(item.get("target_provision"), str)
                or not 3 <= len(item["target_provision"]) <= 130):
            return None
        raw = _original(item)
        sha = item["source_sha256"]
        if hashlib.sha256(raw).hexdigest() != sha:
            return None
        boxes, total_pages = _page_match(
            raw, number=item["pdf_page"], quote=item["exact_quote"],
        )
        return {
            "source_id": item["source_id"],
            "source_sha256": sha,
            "source_url": item["source_url"],
            "pdf_page": item["pdf_page"],
            "pdf_page_count": total_pages,
            "pixel_boxes_180dpi": boxes,
            "source_passage": item["exact_quote"],
            "target_provision": item["target_provision"],
            "source_location_status": "ORIGINAL_PDF_NATIVE_QUOTE_LOCATED_ONLY",
            "review_scope": "CURATED_LITERAL_BINDING_NO_TEMPORAL_APPROVAL",
            "legal_year_approved": False,
            "payment_approved": False,
        }
    except (OSError, ValueError, KeyError, TypeError, RuntimeError,
            ImportError, AttributeError):
        return None


def render_pdf_claim_original(source: dict[str, Any]) -> str:
    """Crop only actual verified native PDF word positions; never fake a PDF."""
    import base64
    from PIL import Image, ImageDraw
    import pymupdf
    try:
        raw = _original({
            "source_id": source["document_id"],
            "source_sha256": source["source_sha256"],
            "source_url": source["original_url"],
        })
        if hashlib.sha256(raw).hexdigest() != source["source_sha256"]:
            raise ValueError("Original source changed")
        quote = source["exact_quote"]
        page_number = source["pdf_page"]
        boxes, _ = _page_match(raw, number=page_number, quote=quote)
        if boxes != source["pixel_boxes_180dpi"]:
            raise ValueError("Unpinned candidate positions changed")
        with pymupdf.open(stream=raw, filetype="pdf") as pdf:
            pix = pdf[page_number-1].get_pixmap(dpi=180, alpha=False)
            image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        draw = ImageDraw.Draw(image)
        for box in boxes:
            draw.rectangle(tuple(box), outline="#d97706", width=3)
        output = io.BytesIO()
        image.save(output, format="PNG")
        png = base64.b64encode(output.getvalue()).decode("ascii")
        href = escape(source["original_url"] +
                      f"#page={page_number}", quote=True)
        return (
            '<section><p><strong>Gerçek PDF — native birebir metin '
            'konumu bulundu; turuncu işaret kaynak adayının konumudur.</strong> '
            'Üretim yılı ve ödeme HOLD.</p>'
            f'<p>Sayfa {page_number} · '
            f'SHA: <code>{escape(source["source_sha256"])}</code> · '
            f'{escape(source["target_provision"])}</p>'
            f'<p>Özgün metin: {escape(quote)}</p>'
            f'<p><a href="{href}" rel="noopener noreferrer" '
            'target="_blank">Resmî PDF içinde ilgili sayfayı aç ↗</a></p>'
            '<img alt="SHA doğrulanmış özgün PDF sayfası ve turuncu native '
            'metin kutusu" style="width:100%;max-width:950px" '
            'src="data:image/png;base64,' + png + '"/></section>'
        )
    except (OSError, ValueError, KeyError, TypeError, RuntimeError,
            ImportError, AttributeError):
        return "<p>HOLD — Birebir özgün PDF metin/kutu konumu artık doğrulanamadı.</p>"
