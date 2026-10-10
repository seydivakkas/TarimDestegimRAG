"""Image-only official Gazette PDF evidence: original bytes + manually located rectangles.

The original source is never edited. A marked COPY is created only after
the source SHA-256, official URL, page and saved pixel-coordinate bounds match.
Manual visual location is distinct from independently approved legal meaning.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

ORIGINAL_LIMIT = 30 * 1024 * 1024
_SHA = re.compile(r"^[0-9a-f]{64}$")
_KEY = re.compile(r"^[A-Z][A-Z0-9_]{2,79}$")


def _paths() -> tuple[Path, Path, Path]:
    return (
        Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive")),
        Path(os.getenv(
            "TARIM_RAG_ORIGINAL_SOURCE_MANIFEST",
            "configs/p0_10_3_original_source_manifest.json",
        )),
        Path(os.getenv(
            "TARIM_RAG_VISUAL_CLAUSE_INDEX",
            "configs/p0_10_5_8859_visual_clause_index.json",
        )),
    )


def _validated(
    support_id: str, *, root: Path, manifest: Path, visual_index: Path,
) -> tuple[dict, bytes]:
    import pymupdf

    if not isinstance(support_id, str) or not _KEY.fullmatch(support_id):
        raise ValueError("Invalid support ID")
    manifest_data = json.loads(manifest.read_text(encoding="utf-8"))
    registry = json.loads(visual_index.read_text(encoding="utf-8"))
    if registry.get("schema_version") != 1:
        raise ValueError("Unsupported visual index schema")
    rows = [r for r in registry["records"] if r.get("support_id") == support_id]
    if len(rows) != 1:
        raise ValueError("No unique visual quote for this program")
    row = rows[0]
    if (row.get("source_id") != "RG_DECISION_8859"
        or row.get("source_type") != "ORIGINAL_PDF_SCANNED_PAGE"
        or row.get("quote_evidence_status") != "VISUAL_SOURCE_LOCATED_PENDING_SECOND_REVIEW"
        or row.get("manual_visual_location_approved") is not False
        or row.get("legal_provision_approved") is not False):
        raise ValueError("Unapproved or unrecognized visual source identity")
    digest = row.get("source_sha256")
    if not isinstance(digest, str) or not _SHA.fullmatch(digest):
        raise ValueError("Invalid original source digest")
    pinned = [
        x for x in manifest_data["sources"]
        if x["id"] == row["source_id"] and x.get("format") == "pdf"
    ]
    if len(pinned) != 1:
        raise ValueError("No unique pinned official PDF")
    source = pinned[0]
    raw_url = row.get("source_url")
    parsed = urlsplit(raw_url)
    if (parsed.scheme != "https" or parsed.hostname != "www.resmigazete.gov.tr"
        or parsed.username or parsed.password or parsed.port not in (None, 443)
        or parsed.fragment or parsed.query
        or raw_url != source["url"]
        or digest != source["original_sha256"]):
        raise ValueError("Source does not match pinned official URL and hash")
    original = (root / "originals" / (digest + ".pdf")).read_bytes()
    if (len(original) > ORIGINAL_LIMIT or not original.startswith(b"%PDF-")
        or hashlib.sha256(original).hexdigest() != digest):
        raise ValueError("Archived official original has changed")
    page_number = row.get("page_number")
    if type(page_number) is not int or not 1 <= page_number <= 500:
        raise ValueError("Page index invalid")
    if (row.get("article") != "MADDE 2" or row.get("paragraph") != "1"
        or row.get("production_year") != 2026):
        raise ValueError("Source clause/article/year scope does not match review")
    quoted = row.get("exact_visible_text")
    if not isinstance(quoted, str) or len(quoted) < 70 or len(quoted) > 900:
        raise ValueError("Missing source-image human-readable transcription")
    rectangles = row.get("highlight_rectangles_pdf_points")
    if not isinstance(rectangles, list) or not 1 <= len(rectangles) <= 10:
        raise ValueError("No valid reviewed image coordinates")

    with pymupdf.open(stream=original, filetype="pdf") as document:
        if document.page_count < page_number:
            raise ValueError("Page does not exist in pinned original")
        page = document[page_number - 1]
        if page.get_text().strip():
            raise ValueError("Visual-only grounding was applied to a text-based page")
        if not page.get_images(full=True):
            raise ValueError("No page image backing the visual evidence")
        for coords in rectangles:
            if (not isinstance(coords, list) or len(coords) != 4
                or any(type(v) not in (int, float) or not math.isfinite(v) for v in coords)):
                raise ValueError("Malformed visual evidence rectangle")
            x0, y0, x1, y1 = coords
            if (x0 < 0 or y0 < 0 or x0 >= x1 or y0 >= y1
                or x1 > page.rect.width or y1 > page.rect.height
                or (x1 - x0) * (y1 - y0) > page.rect.width * page.rect.height * .20):
                raise ValueError("Image highlight rectangle is outside original page")
    return row, original


def lookup_visual_pdf_citation(
    support_id: str, *, root: Path | None = None,
    manifest: Path | None = None, visual_index: Path | None = None,
) -> dict | None:
    """Failure means no citation, not permission to provide a fabricated one."""
    default_root, default_manifest, default_index = _paths()
    try:
        row, _ = _validated(
            support_id, root=root or default_root,
            manifest=manifest or default_manifest,
            visual_index=visual_index or default_index,
        )
    except (OSError, ValueError, KeyError, TypeError, ImportError, RuntimeError):
        return None
    sha = row["source_sha256"]
    page = row["page_number"]
    return {
        "support_id": support_id,
        "source_id": row["source_id"],
        "source_url": row["source_url"],
        "source_sha256": sha,
        "page_number": page,
        "exact_quote": row["exact_visible_text"],
        "section": row["article"] + " (" + row["paragraph"] + ")",
        "title": row["title"],
        "year": row["production_year"],
        "verification_status": "VISUAL_SOURCE_LOCATED_PENDING_SECOND_REVIEW",
        "highlighted_pdf_url": (
            f"/evidence/highlight/visual/{sha}?support_id={support_id}#page={page}"
        ),
    }


def render_visual_pdf_copy(
    support_id: str, *, expected_sha256: str,
    root: Path | None = None, manifest: Path | None = None,
    visual_index: Path | None = None,
) -> bytes:
    """Render annotations on a COPY of the 89-page official source PDF."""
    import pymupdf

    default_root, default_manifest, default_index = _paths()
    row, original = _validated(
        support_id, root=root or default_root,
        manifest=manifest or default_manifest,
        visual_index=visual_index or default_index,
    )
    if expected_sha256 != row["source_sha256"]:
        raise ValueError("Requested original source hash differs")
    with pymupdf.open(stream=original, filetype="pdf") as document:
        page = document[row["page_number"] - 1]
        for coordinates in row["highlight_rectangles_pdf_points"]:
            annotation = page.add_rect_annot(pymupdf.Rect(*coordinates))
            annotation.set_colors(stroke=(1, .75, 0), fill=(1, 1, 0))
            annotation.set_border(width=.5)
            annotation.set_opacity(.24)
            annotation.update()
        return document.tobytes(garbage=4, deflate=True)


def install_original_8859(
    *, root: Path | None = None, manifest: Path | None = None,
) -> dict:
    """Explicit installation only; no uncontrolled download on farmer requests."""
    import httpx

    default_root, default_manifest, _ = _paths()
    root = root or default_root
    manifest = manifest or default_manifest
    source = next(
        row for row in json.loads(manifest.read_text(encoding="utf-8"))["sources"]
        if row["id"] == "RG_DECISION_8859" and row["format"] == "pdf"
    )
    url = source["url"]
    if url != "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf":
        raise ValueError("Original Gazette URL unexpectedly changed")
    digest = source["original_sha256"]
    if not isinstance(digest, str) or not _SHA.fullmatch(digest):
        raise ValueError("Expected official original is not digest-pinned")
    target = root / "originals" / (digest + ".pdf")
    if target.exists():
        original = target.read_bytes()
        if hashlib.sha256(original).hexdigest() != digest:
            raise ValueError("Pinned local original is altered; will not overwrite")
        return {"sha256": digest, "bytes": len(original), "already_present": True}
    with httpx.Client(timeout=45, follow_redirects=False, trust_env=False) as client:
        with client.stream("GET", url, headers={
            "User-Agent": "TarimDestekRAG-OriginalEvidence/1.0",
            "Accept-Encoding": "identity",
        }) as response:
            if response.status_code != 200 or str(response.url) != url:
                raise ValueError("Direct official original download failed")
            if "pdf" not in response.headers.get("Content-Type", "").lower():
                raise ValueError("Official source did not return PDF bytes")
            total = 0
            chunks: list[bytes] = []
            for chunk in response.iter_raw():
                total += len(chunk)
                if total > ORIGINAL_LIMIT:
                    raise ValueError("Official document exceeds safe byte limit")
                chunks.append(chunk)
    body = b"".join(chunks)
    if hashlib.sha256(body).hexdigest() != digest:
        raise ValueError("Official document is not the reviewed original")
    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=target.parent, delete=False) as out:
        tmp_path = Path(out.name)
        out.write(body)
        out.flush()
        os.fsync(out.fileno())
    try:
        if target.exists():
            raise ValueError("Conflicting concurrent document installation")
        os.replace(tmp_path, target)
    finally:
        tmp_path.unlink(missing_ok=True)
    return {"sha256": digest, "bytes": len(body), "already_present": False}


def main() -> int:
    parser = argparse.ArgumentParser(description="Install verified 8859 official original PDF")
    parser.add_argument("--install-8859", action="store_true", required=True)
    args = parser.parse_args()
    if args.install_8859:
        result = install_original_8859()
        print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
