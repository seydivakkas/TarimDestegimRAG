"""Local PDF/HTML/TXT document library for offline document analysis.

Uploaded files are *user documents*, not official Gazette originals. Only the
files' own SHA-256 binds their text and pages; no authentication of authorship
or legal source is claimed. Never derive filesystem paths from a filename.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import subprocess
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

MAX_UPLOAD = 25_000_000
MAX_PDF_PAGES = 250
_LOCK = Lock()
_ALLOWED_SUFFIXES = {".pdf": "pdf", ".html": "html",
                     ".htm": "html", ".txt": "txt"}


def library_root() -> Path:
    return Path(os.getenv("TARIM_RAG_USER_DOC_DIR", "data/user_documents"))


def _check_sha(value: str) -> str:
    if not isinstance(value, str) or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        raise ValueError("Invalid document SHA-256")
    return value


def library_entries(root: Path | None = None) -> list[dict[str, Any]]:
    root = root or library_root()
    manifest = root / "documents.json"
    if not manifest.is_file():
        return []
    if manifest.stat().st_size > 2_000_000:
        raise ValueError("Document library metadata is oversized")
    result = json.loads(manifest.read_text(encoding="utf-8"))
    if result.get("schema_version") != 1 or not isinstance(result.get("documents"), list):
        raise ValueError("Invalid local document manifest")
    return result["documents"]


def _write_metadata(root: Path, items: list[dict[str, Any]]) -> None:
    root.mkdir(parents=True, exist_ok=True)
    fd, path = tempfile.mkstemp(prefix=".document-meta-", dir=root)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump({"schema_version": 1, "documents": items},
                      stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(path, root / "documents.json")
    finally:
        Path(path).unlink(missing_ok=True)


def import_user_document(
    filename: str, raw: bytes, *,
    run_ocr: bool = False,
    root: Path | None = None,
    ocr_dir: Path | None = None,
) -> dict[str, Any]:
    """Add a local document without modifying official source manifests."""
    root = root or library_root()
    if not isinstance(filename, str) or not filename or len(filename) > 200:
        raise ValueError("Document name is missing or too long")
    fmt = _ALLOWED_SUFFIXES.get(Path(filename).suffix.lower())
    if fmt is None:
        raise ValueError("Only PDF, HTML and TXT are supported")
    if not isinstance(raw, bytes) or not 1 <= len(raw) <= MAX_UPLOAD:
        raise ValueError("Document is missing or exceeds maximum size")
    if fmt == "pdf" and not raw.startswith(b"%PDF-"):
        raise ValueError("Uploaded file is not a PDF")
    if fmt in {"html", "txt"}:
        raw.decode("utf-8", errors="strict")  # User documents use UTF-8.
    sha = hashlib.sha256(raw).hexdigest()
    source_id = "USER_" + sha[:24].upper()
    path = root / "originals" / f"{sha}.{fmt}"
    original_name = Path(filename.replace("\\", "/")).name
    with _LOCK:
        items = library_entries(root)
        identical = [
            item for item in items if item.get("sha256") == sha
        ]
        if identical:
            if not path.exists() or path.read_bytes() != raw:
                raise ValueError("Library document changed since index")
            item = identical[0]
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "xb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            item = {
                "id": source_id,
                "filename": original_name,
                "format": fmt,
                "sha256": sha,
                "bytes": len(raw),
                "imported_at": datetime.now(timezone.utc).isoformat(),
                "role": "USER_DOCUMENT",
            }
            items.append(item)
            _write_metadata(root, items)
    if run_ocr and fmt == "pdf":
        _ocr_uploaded_pdf(item, raw, ocr_dir=ocr_dir)
    return item


def _ocr_uploaded_pdf(
    item: dict[str, Any], raw: bytes, *,
    ocr_dir: Path | None,
) -> dict[str, Any]:
    """Opt-in OCR of image-only pages, without treating OCR as source truth."""
    import pymupdf

    destination = ocr_dir or Path(os.getenv(
        "TARIM_RAG_OCR_INDEX_DIR", "data/indexes"))
    original_sha = item["sha256"]
    records: list[dict[str, Any]] = []
    missing: list[int] = []
    with pymupdf.open(stream=raw, filetype="pdf") as doc:
        if len(doc) > MAX_PDF_PAGES:
            raise ValueError("Too many pages for a single local OCR request")
        for no, page in enumerate(doc, start=1):
            text = page.get_text("text", sort=True).strip()
            method = "PDF_NATIVE_TEXT_UNREVIEWED"
            if not text:
                method = "OCR_NOT_INSTALLED"
                try:
                    picture = page.get_pixmap(dpi=180, alpha=False).tobytes("png")
                    run = subprocess.run(
                        ["tesseract", "stdin", "stdout", "-l", "tur+eng"],
                        input=picture, capture_output=True, timeout=60,
                        check=False,
                    )
                    if run.returncode == 0:
                        text = run.stdout.decode("utf-8", "replace").strip()
                        method = "OCR_UNREVIEWED" if text else "OCR_NO_WORDS"
                    else:
                        method = "OCR_FAILED"
                except (FileNotFoundError, OSError, subprocess.TimeoutExpired):
                    method = "OCR_NOT_AVAILABLE"
                if not text:
                    missing.append(no)
            records.append({
                "page_number": no, "source_sha256": original_sha,
                "method": method, "text": text,
                "legal_approved": False, "claim_verified": False,
            })
        report = {
            "schema_version": 1,
            "document_id": item["id"],
            "original_sha256": original_sha,
            "original_url": f"/documents/view/{original_sha}",
            "original_page_count": len(doc),
            "indexed_page_count": len(records),
            "ocr_unavailable_page_numbers": missing,
            "technical_status": (
                "INCOMPLETE_OCR" if missing else "SEARCHABLE_REVIEW_REQUIRED"
            ),
            "pages": records,
        }
    destination.mkdir(parents=True, exist_ok=True)
    from tarim_destek_rag.citations.verified_ocr_index import write_index_atomic

    write_index_atomic(
        report, destination / f"verified_ocr_{original_sha}.json")
    return report


def load_user_original(
    sha: str, *, root: Path | None = None,
) -> tuple[dict[str, Any], bytes]:
    sha = _check_sha(sha)
    root = root or library_root()
    entries = [i for i in library_entries(root) if i.get("sha256") == sha]
    if len(entries) != 1:
        raise ValueError("Document not found or ambiguous")
    meta = entries[0]
    fmt = meta.get("format")
    if fmt not in ("pdf", "html", "txt") or meta.get("id") != "USER_" + sha[:24].upper():
        raise ValueError("Library source metadata is inconsistent")
    raw = (root / "originals" / f"{sha}.{fmt}").read_bytes()
    if (not raw or len(raw) > MAX_UPLOAD
            or len(raw) != meta.get("bytes")
            or hashlib.sha256(raw).hexdigest() != sha):
        raise ValueError("Uploaded document bytes have changed")
    return meta, raw
