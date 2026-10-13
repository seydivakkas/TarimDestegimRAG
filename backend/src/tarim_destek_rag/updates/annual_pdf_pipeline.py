"""Year-independent Gazette PDF OCR/research stage for operator-triggered discovery.

Each fetched PDF is stored as exact original bytes by the existing discovery
pipeline. This stage indexes only *verified* originals from that scan, gives
every passage a genuine PDF page and optional original-pixel word boxes, and
never activates rules, rates, year validity or payment. An OCR hypothesis is
not a legally approved original passage.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import re
import shutil
import subprocess
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

MAX_DOCUMENT_BYTES = 100_000_000
MAX_PAGES_PER_DOCUMENT = 120
MAX_TOTAL_PAGES_PER_CLICK = 160
MAX_STORED_CHARS_PER_PAGE = 60_000
MAX_WORDS_PER_PAGE = 3500
_ALLOWED = {"resmigazete.gov.tr", "www.resmigazete.gov.tr",
            "tarimorman.gov.tr", "www.tarimorman.gov.tr"}
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_PAGE_KEY = re.compile(r"([0-9a-f]{64}):([1-9][0-9]{0,3})\Z")


def _atomic_json(path: Path, obj: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=str(path.parent),
        prefix=".annual_", delete=False,
    ) as handle:
        temp = Path(handle.name)
        try:
            json.dump(obj, handle, ensure_ascii=False, sort_keys=True)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
        except BaseException:
            temp.unlink(missing_ok=True)
            raise
    try:
        os.replace(temp, path)
    finally:
        temp.unlink(missing_ok=True)


def _verify_doc(root: Path, meta: dict[str, Any]) -> bytes:
    """Ensure URL, recorded original digest and local bytes still coincide."""
    sha, url = meta["sha256"], meta["source_url"]
    if not isinstance(sha, str) or not _SHA.fullmatch(sha):
        raise ValueError("Unpinned PDF source")
    if not isinstance(url, str):
        raise ValueError("No source URL")
    uri = urlsplit(url)
    if (uri.scheme != "https" or uri.hostname not in _ALLOWED
            or uri.username or uri.password
            or uri.port not in (None, 443) or uri.fragment):
        raise ValueError("Non-official source URI")
    inventory_file = root / "inventory.json"
    inventory = json.loads(inventory_file.read_text(encoding="utf-8"))
    if inventory.get(url) != sha:
        raise ValueError("Source URL not pinned in discovery inventory")
    path = root / "originals" / f"{sha}.pdf"
    if (not path.is_file() or path.is_symlink()
            or not 0 < path.stat().st_size <= MAX_DOCUMENT_BYTES):
        raise ValueError("Verified original PDF missing/oversized")
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != sha or not raw.startswith(b"%PDF-"):
        raise ValueError("Original PDF SHA/signature mismatch")
    return raw


def _ocr_from_original_png(png: bytes) -> tuple[str, list[dict[str, Any]], str]:
    """Real Tesseract pixel geometry; no guessed positional alignments."""
    executable = shutil.which("tesseract")
    if not executable:
        return "", [], "OCR_ENGINE_MISSING"
    try:
        command = [executable, "stdin", "stdout", "-l", "tur+eng", "tsv"]
        run = subprocess.run(
            command, input=png, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, timeout=90, check=False,
        )
        if run.returncode != 0:
            return "", [], "OCR_ENGINE_FAILED"
        import csv
        rows = csv.DictReader(io.StringIO(
            run.stdout.decode("utf-8", errors="replace")), delimiter="\t")
        words = []
        for row in rows:
            if row.get("level") != "5":
                continue
            word = (row.get("text") or "").strip()
            if not word:
                continue
            x, y = int(row["left"]), int(row["top"])
            w, h = int(row["width"]), int(row["height"])
            if (min(x, y) < 0 or min(w, h) <= 0
                    or max(x, y, w, h) > 25000):
                continue
            words.append({
                "text": word[:180], "bbox_180dpi": [x, y, x+w, y+h],
                "confidence": float(row.get("conf") or "-1"),
                "status": "OCR_UNREVIEWED",
            })
            if len(words) == MAX_WORDS_PER_PAGE:
                break
        return (" ".join(x["text"] for x in words)[:MAX_STORED_CHARS_PER_PAGE],
                words, "OCR_UNREVIEWED" if words else "OCR_NO_WORDS")
    except (OSError, ValueError, KeyError, TypeError,
            subprocess.TimeoutExpired):
        return "", [], "OCR_ENGINE_FAILED"


def _index_one(root: Path, meta: dict[str, Any], *, max_pages: int) -> dict[str, Any]:
    import pymupdf

    raw = _verify_doc(root, meta)
    pages: list[dict[str, Any]] = []
    with pymupdf.open(stream=raw, filetype="pdf") as pdf:
        total = len(pdf)
        if not 1 <= total <= 2000:
            raise ValueError("Invalid original PDF page count")
        for page_no in range(1, min(total, max_pages)+1):
            page = pdf[page_no-1]
            native = page.get_text("text", sort=True).strip()
            method = "PDF_NATIVE_TEXT_UNREVIEWED"
            words: list[dict[str, Any]] = []
            if native:
                text = native[:MAX_STORED_CHARS_PER_PAGE]
                status = "TEXT_CANDIDATE_UNREVIEWED"
            else:
                pix = page.get_pixmap(dpi=180, alpha=False)
                png = pix.tobytes("png")
                text, words, status = _ocr_from_original_png(png)
                method = "TESSERACT_OCR_180DPI_UNREVIEWED"
            pages.append({
                "page": page_no,
                "method": method,
                "status": status,
                "text": text,
                "ocr_words": words,
                "source_sha256": meta["sha256"],
                "document_page_count": total,
                "legal_status": "HOLD",
                "payment_status": "HOLD",
            })
    return {
        "schema_version": 1,
        "source_sha256": meta["sha256"],
        "source_url": meta["source_url"],
        "source_title": meta.get("source_title") or "",
        "source_portal": meta.get("source_id") or "",
        "original_bytes": len(raw),
        "original_page_count": total,
        "indexed_page_count": len(pages),
        "complete_page_coverage": len(pages) == total,
        "status": "SEARCHABLE_UNREVIEWED"
            if len(pages) == total and all(p["text"] for p in pages)
            else "PARTIAL_OCR_OR_PAGE_LIMIT_HOLD",
        "legal_status": "HOLD",
        "pages": pages,
    }


def update_yearly_pdf_index(
    *, production_year: int, discovery_batch: dict[str, Any], root: Path,
) -> dict[str, Any]:
    """Consume one bounded official scan and index its verified PDF originals.

    Success means only technical indexing, never complete official search,
    applicability of any Gazette publication, or legal rule activation.
    """
    if not 2020 <= production_year <= 2100:
        raise ValueError("Production year outside allowed range")
    if discovery_batch.get("target_production_year") != production_year:
        raise ValueError("Discovery was run for another year")
    root = root.resolve()
    catalog_file = root / "annual_research" / "catalog.json"
    if catalog_file.exists():
        catalog = json.loads(catalog_file.read_text(encoding="utf-8"))
        if (catalog.get("schema_version") != 1
                or not isinstance(catalog.get("documents"), list)):
            raise ValueError("Invalid existing annual research catalog")
    else:
        catalog = {"schema_version": 1, "documents": []}
    originals = {
        row.get("sha256"): row
        for row in discovery_batch.get("documents", [])
        if isinstance(row, dict) and row.get("mime_type") == "application/pdf"
    }
    errors: list[dict[str, str]] = []
    indexed: list[dict[str, Any]] = []
    pages_remaining = MAX_TOTAL_PAGES_PER_CLICK
    for sha, row in originals.items():
        if pages_remaining <= 0:
            errors.append({"sha256": str(sha), "reason": "BATCH_PAGE_BUDGET_HOLD"})
            continue
        try:
            report = _index_one(root, row, max_pages=min(
                MAX_PAGES_PER_DOCUMENT, pages_remaining))
            pages_remaining -= report["indexed_page_count"]
            path = root / "annual_research" / f"{sha}.json"
            _atomic_json(path, report)
            short = {
                "sha256": sha,
                "source_url": row["source_url"],
                "source_title": row.get("source_title") or "",
                "original_page_count": report["original_page_count"],
                "indexed_page_count": report["indexed_page_count"],
                "index_status": report["status"],
                "observed_in_scan_years": [production_year],
                "legal_status": "HOLD",
            }
            old = [x for x in catalog["documents"] if x.get("sha256") == sha]
            if old:
                short["observed_in_scan_years"] = sorted(set(
                    old[0].get("observed_in_scan_years", []) + [production_year]))
                catalog["documents"] = [x for x in catalog["documents"]
                                        if x.get("sha256") != sha]
            catalog["documents"].append(short)
            indexed.append(short)
        except (OSError, ValueError, KeyError, TypeError, RuntimeError,
                ImportError) as exc:
            errors.append({"sha256": str(sha), "reason": type(exc).__name__})
    catalog["last_scan_year"] = production_year
    catalog["updated_utc"] = datetime.now(UTC).isoformat()
    catalog["complete_official_coverage_proven"] = False
    catalog["legal_approval"] = False
    catalog["payment_approval"] = False
    _atomic_json(catalog_file, catalog)
    return {
        "schema_version": 1,
        "target_production_year": production_year,
        "status": "INCOMPLETE_DISCOVERY_OR_OCR_HOLD",
        "scan_discovery_mode": discovery_batch.get("discovery_mode"),
        "scanned_pdf_count": len(originals),
        "indexed_pdf_count": len(indexed),
        "documents": indexed,
        "errors": errors,
        "complete_official_coverage_proven": False,
        "legal_approval": False,
        "payment_approval": False,
    }


def _catalog(root: Path) -> list[dict[str, Any]]:
    f = root / "annual_research" / "catalog.json"
    if not f.is_file() or f.stat().st_size > 10_000_000:
        return []
    raw = json.loads(f.read_text(encoding="utf-8"))
    if raw.get("schema_version") != 1:
        return []
    return raw["documents"][:1000]


def search_yearly_pdf(
    *, query: str, year: int, root: Path, limit: int = 20,
) -> list[dict[str, Any]]:
    """Read-only text candidates pointing to REAL PDF pages; never to rates."""
    if not 2020 <= year <= 2100 or not 2 <= len(query.strip()) <= 180:
        return []
    if not 1 <= limit <= 40:
        return []
    needle = " ".join(query.casefold().split())
    out = []
    for meta in _catalog(root):
        # Observed-in-scan-year is NOT legal applicability to this year.
        if year not in meta.get("observed_in_scan_years", []):
            continue
        try:
            raw = _verify_doc(root, {**meta, "sha256": meta["sha256"]})
            file = root / "annual_research" / (meta["sha256"] + ".json")
            if not file.is_file() or file.stat().st_size > 30_000_000:
                continue
            doc = json.loads(file.read_text(encoding="utf-8"))
            if (doc.get("source_sha256") != meta["sha256"]
                    or doc.get("original_bytes") != len(raw)
                    or doc.get("source_url") != meta["source_url"]):
                continue
            for page in doc.get("pages", []):
                text = page.get("text", "")
                if needle not in " ".join(text.casefold().split()):
                    continue
                out.append({
                    "page_key": f"{meta['sha256']}:{page['page']}",
                    "source_url": meta["source_url"] + f"#page={page['page']}",
                    "original_sha256": meta["sha256"],
                    "page_number": page["page"],
                    "source_title": meta["source_title"],
                    "extraction": page.get("method"),
                    "text_preview": text[:600],
                    "status": "PDF_PAGE_CANDIDATE_UNREVIEWED",
                    "legal_status": "HOLD",
                })
                if len(out) >= limit:
                    return out
        except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
            continue
    return out


def render_yearly_pdf_page(
    *, page_key: str, query: str, root: Path,
) -> tuple[bytes, dict[str, Any]]:
    """Generate a true original PDF screenshot with optional orange hit boxes.

    Native PDF exact query hits or original-pixel OCR word matches are not
    independent legal evidence. Never yellow or create artificial pages.
    """
    import pymupdf
    from PIL import Image, ImageDraw

    match = _PAGE_KEY.fullmatch(page_key or "")
    if not match or len(query) > 180:
        raise ValueError("Invalid original page locator")
    sha, number = match.group(1), int(match.group(2))
    records = [x for x in _catalog(root) if x.get("sha256") == sha]
    if len(records) != 1:
        raise ValueError("Unrecognized annual source")
    meta = records[0]
    raw = _verify_doc(root, meta)
    with pymupdf.open(stream=raw, filetype="pdf") as pdf:
        if number > len(pdf):
            raise ValueError("PDF page outside original")
        page = pdf[number - 1]
        pix = page.get_pixmap(dpi=180, alpha=False)
        image = Image.open(io.BytesIO(pix.tobytes("png"))).convert("RGB")
        boxes: list[tuple[int, int, int, int]] = []
        if query.strip():
            for rect in page.search_for(query.strip())[:30]:
                b = [int(round(v*180/72)) for v in (rect.x0, rect.y0, rect.x1, rect.y1)]
                boxes.append(tuple(b))
    if query.strip() and not boxes:
        index_file = root / "annual_research" / (sha + ".json")
        if index_file.is_file() and index_file.stat().st_size <= 30_000_000:
            report = json.loads(index_file.read_text(encoding="utf-8"))
            if report.get("source_sha256") == sha and report.get("source_url") == meta["source_url"]:
                matches = [p for p in report["pages"] if p.get("page") == number]
                if len(matches) == 1 and matches[0].get("method") == "TESSERACT_OCR_180DPI_UNREVIEWED":
                    words = matches[0].get("ocr_words", [])
                    tokens = set(query.casefold().split())
                    for word in words:
                        if word.get("text", "").casefold() in tokens:
                            b = word.get("bbox_180dpi", [])
                            if (len(b) == 4 and all(type(v) is int for v in b)):
                                boxes.append(tuple(b))
    draw = ImageDraw.Draw(image)
    for x0,y0,x1,y1 in boxes[:30]:
        if 0 <= x0 < x1 <= image.width and 0 <= y0 < y1 <= image.height:
            draw.rectangle((x0,y0,x1,y1), outline="#d97706", width=3)
    result = io.BytesIO()
    image.save(result, format="PNG")
    return result.getvalue(), {
        "source_sha256": sha,
        "page": number,
        "official_url": meta["source_url"] + f"#page={number}",
        "orange_candidate_boxes": len(boxes),
        "source_type": "OFFICIAL_ORIGINAL_PDF_BYTES_SHA_VERIFIED",
        "candidate_status": "TEXT_OR_OCR_UNREVIEWED",
        "legal_status": "HOLD",
        "payment_status": "HOLD",
    }
