"""G33: one-click in-app proof navigator for exact RAG citation identity.

Identity chain: live chunk_id + SHA + (page) -> verified ORIGINAL bytes
-> actual PDF page/HTML body -> unique native/OCR phrase location if possible.
A textual/OCR candidate is orange, NEVER yellow or legal/payment PASS.
"""
from __future__ import annotations

import base64
import hashlib
import io
import json
import os
import re
import unicodedata
from html import escape
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

_SHA = re.compile(r"[0-9a-f]{64}\Z")
_CHUNK = re.compile(r"[0-9a-f]{24}\Z")
_WORD = re.compile(r"[^\W_]+", re.UNICODE)
_ALLOWED = {"resmigazete.gov.tr", "www.resmigazete.gov.tr",
            "tarimorman.gov.tr", "www.tarimorman.gov.tr"}


def _parts(value: str) -> list[str]:
    text = unicodedata.normalize("NFKC", value).casefold().replace("i\u0307", "i")
    return _WORD.findall(text)


def _unique_range(words: list[tuple[str, tuple[float, float, float, float]]],
                  content: str) -> tuple[list[tuple[float, float, float, float]], str]:
    """Only a UNIQUE contiguous exact source word sequence may get orange boxes.

    If complete text is not on the page as a consecutive sequence, search a
    bounded 12-word phrase. That is explicitly only a located *fragment*.
    No approximate fuzzy match can invent coordinates.
    """
    tokens = _parts(content)
    if len(tokens) < 5 or not words or len(words) > 90000:
        return [], "PAGE_ONLY_HOLD"
    source_tokens = [x[0] for x in words]
    for n, status in (
        (len(tokens), "EXACT_FULL_PASSAGE_CANDIDATE"),
        (min(12, len(tokens)), "UNIQUE_FRAGMENT_CANDIDATE"),
    ):
        if n < 5:
            continue
        target = tokens[:n]
        found = [i for i in range(0, len(source_tokens)-n+1)
                 if source_tokens[i:i+n] == target]
        if len(found) == 1:
            start = found[0]
            # For multi-paragraph text mark just a unique anchored excerpt;
            # all stored bboxes are true original word boxes.
            return [box for _,box in words[start:start+min(n,48)]], status
    return [], "PAGE_ONLY_HOLD"


def _verified_source(passage: Any) -> tuple[bytes, str, str | None]:
    """Re-check source SHA at click time; no source path chosen by URL or user."""
    from tarim_destek_rag.retrieval.document_rag import _read_original

    sha = passage.document_sha256
    key = passage.source_id
    if key.startswith("USER_"):
        from tarim_destek_rag.retrieval.user_documents import load_user_original
        meta, raw = load_user_original(sha)
        if meta.get("id") != key or meta.get("format") != passage.format:
            raise ValueError("User file identity does not match citation")
        if hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError("Changed local document")
        return raw, "USER_UPLOADED_DOCUMENT_NOT_OFFICIAL", None
    if key == "RG_DISCOVERED_" + sha[:16].upper():
        from tarim_destek_rag.updates.annual_pdf_pipeline import _catalog, _verify_doc
        root = Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
        meta = [x for x in _catalog(root) if x.get("sha256") == sha]
        if len(meta) != 1 or passage.format != "pdf":
            raise ValueError("Ambiguous annual original")
        raw = _verify_doc(root, meta[0])
        expected = meta[0]["source_url"]
    else:
        root = Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
        path = Path(os.getenv("TARIM_RAG_ORIGINAL_SOURCE_MANIFEST",
                             "configs/p0_10_3_original_source_manifest.json"))
        content = json.loads(path.read_text(encoding="utf-8"))
        sources = [x for x in content.get("sources", [])
                   if x.get("id") == key
                   and x.get("original_sha256") == sha
                   and x.get("format") == passage.format]
        if len(sources) != 1:
            raise ValueError("Missing unique official original")
        raw = _read_original(root, sources[0])
        expected = sources[0]["url"]
    parsed = urlsplit(expected)
    if (parsed.scheme != "https" or parsed.hostname not in _ALLOWED
            or parsed.username or parsed.password or parsed.port not in (None,443)):
        raise ValueError("Untrusted official URL")
    expected_url = expected + (f"#page={passage.page_number}"
                               if passage.page_number else "")
    if expected_url != passage.url:
        raise ValueError("Citation URL does not belong to original source")
    return raw, "SHA_VERIFIED_OFFICIAL_SOURCE", expected_url


def _source_words(raw_page: Any, *, text_method: str) -> tuple[list[
    tuple[str, tuple[float,float,float,float]]], str]:
    """Word positions are taken from the authenticated page, never guessed."""
    if text_method not in ("OCR_DRAFT", "OCR_UNREVIEWED"):
        original_words = raw_page.get_text("words", sort=True)
        words = []
        for value in original_words:
            x0,y0,x1,y1,text = value[:5]
            bbox = (float(x0),float(y0),float(x1),float(y1))
            for token in _parts(str(text)):
                words.append((token,bbox))
        return words, "PDF_NATIVE_TEXT_UNREVIEWED"
    # Re-OCR original pixels on EACH click, ignoring any editable saved
    # OCR index bbox. Native page remains viewable if Tesseract is missing.
    from tarim_destek_rag.updates.annual_pdf_pipeline import _ocr_from_original_png
    png = raw_page.get_pixmap(dpi=180, alpha=False).tobytes("png")
    _, actual_words, status = _ocr_from_original_png(png)
    if status != "OCR_UNREVIEWED":
        return [], "OCR_ENGINE_MISSING_OR_FAILED"
    words = []
    for word in actual_words:
        x0,y0,x1,y1 = word["bbox_180dpi"]
        # OCR returns 180-DPI pixel coordinates; convert to PyMuPDF points.
        bbox = tuple(float(v)*72.0/180.0 for v in (x0,y0,x1,y1))
        for token in _parts(word["text"]):
            words.append((token,bbox))
    return words, "OCR_RECOMPUTED_FROM_ORIGINAL_PIXELS_UNREVIEWED"


def _pdf_view(raw: bytes, passage: Any) -> tuple[str, str, str]:
    import pymupdf
    from PIL import Image, ImageDraw
    with pymupdf.open(stream=raw, filetype="pdf") as doc:
        number = passage.page_number
        if type(number) is not int or not 1 <= number <= len(doc):
            raise ValueError("Invalid original page location")
        page = doc[number - 1]
        pix = page.get_pixmap(dpi=180, alpha=False)
        original = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        # PyMuPDF text-word boxes and the rendered pixmap can use distinct
        # reference frames on rotated pages; no guessed affine transforms.
        if page.rotation:
            words, text_method = [], "ROTATED_PAGE_COORDINATES_HOLD"
        else:
            words, text_method = _source_words(
                page, text_method=passage.extraction_method
            )
        positions, state = _unique_range(words, passage.text)
        img = original.copy()
        drawer = ImageDraw.Draw(img)
        valid = []
        for box in positions:
            box180 = tuple(int(round(coord*180/72)) for coord in box)
            x0,y0,x1,y1 = box180
            if 0 <= x0 < x1 <= img.width and 0 <= y0 < y1 <= img.height:
                drawer.rectangle(box180, outline="#d97706", width=3)
                valid.append(box180)
        if not valid:
            state = "PAGE_ONLY_HOLD"
        canvas = io.BytesIO()
        img.save(canvas, format="PNG")
        markup = ('<img alt="Özgün SHA-doğrulanmış PDF sayfası" '
                  'style="width:100%;height:auto;border:1px solid #cbd5e1" '
                  'src="data:image/png;base64,' +
                  base64.b64encode(canvas.getvalue()).decode("ascii") + '"/>')
        crop = ""
        if valid:
            bounds = (
                max(0, min(v[0] for v in valid)-35),
                max(0, min(v[1] for v in valid)-35),
                min(original.width, max(v[2] for v in valid)+35),
                min(original.height,max(v[3] for v in valid)+35),
            )
            if bounds[2]-bounds[0] > 5 and bounds[3]-bounds[1] > 5:
                panel = img.crop(bounds)
                out = io.BytesIO()
                panel.save(out, format="PNG")
                crop = ('<h3>İlgili gerçek sayfa bölgesi (turuncu aday)</h3>'
                        '<img alt="Özgün PDF söz dizisinin tespit edilmiş '
                        'gerçek bölgesi" style="max-width:100%;border:2px '
                        'solid #d97706" src="data:image/png;base64,' +
                        base64.b64encode(out.getvalue()).decode("ascii") + '"/>')
    return crop + "<h3>Özgün PDF sayfasının tamamı</h3>" + markup, state, text_method


def _html_view(raw: bytes, passage: Any) -> tuple[str, str, str]:
    from bs4 import BeautifulSoup
    encoding = "utf-8" if passage.source_id.startswith("USER_") else "cp1254"
    doc = BeautifulSoup(raw.decode(encoding, errors="replace"), "html.parser")
    for element in doc(["style","script","noscript"]):
        element.decompose()
    visible = " ".join(doc.get_text(" ", strip=True).split())
    full = " ".join(passage.text.split())
    matches = list(re.finditer(re.escape(full), visible, flags=re.IGNORECASE)) if full else []
    if len(matches) != 1:
        return ("<p>Özgün HTML metin düğümü birebir eşleşemedi. "
                "Kullanıcının seçtiği kaynak orijinali SHA ile doğrulandı, "
                "ancak paragraf konumu HOLD.</p>", "DOCUMENT_ONLY_HOLD",
                "HTML_ORIGINAL_TEXT")
    at, endpoint = matches[0].span()
    lo,hi = max(0,at-220),min(len(visible),endpoint+220)
    excerpt = (
        escape(visible[lo:at]) +
        '<span style="border:2px solid #d97706;background:#ffedd5">' +
        escape(visible[at:endpoint]) + "</span>" +
        escape(visible[endpoint:hi])
    )
    return ('<h3>Özgün HTML içinde eşleşen pasaj (turuncu aday)</h3>'
            '<blockquote style="border-left:4px solid #d97706;padding:12px">'
            + excerpt + "</blockquote>"), "HTML_UNIQUE_PASSAGE_CANDIDATE", "HTML_ORIGINAL_TEXT"


def render_rag_citation_proof(sha: str, chunk_id: str) -> str:
    """Full-page read-only self-contained HTML proof; location never auto-PASS."""
    if (not isinstance(sha,str) or not _SHA.fullmatch(sha)
            or not isinstance(chunk_id,str) or not _CHUNK.fullmatch(chunk_id)):
        raise ValueError("Bad citation identifier")
    from tarim_destek_rag.retrieval.document_rag import get_document_rag
    candidates = [p for p in get_document_rag().passages
                  if p.chunk_id == chunk_id and p.document_sha256 == sha]
    if len(candidates) != 1:
        raise ValueError("Unrecognized or ambiguous original passage")
    passage = candidates[0]
    raw, source_kind, official_url = _verified_source(passage)
    if passage.format == "pdf":
        display, location, method = _pdf_view(raw, passage)
    elif passage.format == "html":
        display, location, method = _html_view(raw, passage)
    else:
        if passage.source_id.startswith("USER_"):
            display = "<pre style='white-space:pre-wrap'>" + escape(passage.text) + "</pre>"
            location, method = "USER_DOCUMENT_TEXT_UNREVIEWED", "USER_TEXT"
        else:
            raise ValueError("Untrusted non-PDF/HTML official source")
    link = ('<p><a href="' + escape(official_url, quote=True) +
            '" rel="noopener noreferrer" target="_blank">Özgün resmî '
            'belgeyi kaynak sitesinde aç ↗</a></p>') if official_url else ""
    body = (
        "<h2>Kanıt Konumu — Özgün Belgede Göster</h2>"
        '<p><strong>Kaynak türü:</strong> ' + escape(source_kind) +
        ' · <strong>Gerçek sayfa:</strong> ' +
        escape(str(passage.page_number if passage.page_number is not None else
                   "HTML / sayfa numarası yok")) +
        ' · <strong>Konum:</strong> ' + escape(location) + "</p>"
        '<p><strong>Belge SHA-256:</strong> <code>' + sha + '</code>'
        ' · <strong>Alıntı ID:</strong> <code>' + chunk_id + '</code></p>'
        '<p><strong>Okuma yöntemi:</strong> ' + escape(method) + '</p>'
        '<p><strong>Kaynak metni / OCR taslağı:</strong> ' +
        escape(passage.text[:1600]) + "</p>"
        '<p><strong>HOLD:</strong> Turuncu işaret, orijinal sayfada '
        'yeniden bulunan birebir kelime adayıdır; bağımsız görsel/hukukî '
        'inceleme veya sarı onay değildir. Doğrulanmış birebir alan '
        'bulunamazsa yalnız gerçek sayfa gösterilir. Üretim yılı, '
        'mevzuat değişikliği, hak ediş ve ödeme HOLD.</p>'
        + link + display
    )
    return ('<!doctype html><html lang="tr"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1">'
            '<title>Kaynak Kanıt Konumu — HOLD</title>'
            '<style>body{font:15px/1.55 system-ui, sans-serif;'
            'max-width:1100px;margin:20px auto;padding:16px;color:#172033}'
            'pre{white-space:pre-wrap}code{overflow-wrap:anywhere}'
            '</style></head><body>' + body + '</body></html>')
