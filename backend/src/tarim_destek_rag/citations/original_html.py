"""Locate exact quoted clauses in an immutable original official Gazette HTML.

2024/39's primary publication is HTML, not a fabricated PDF. A marked
copy keeps the official page's wording and markup; original bytes are never
changed. This does not activate eligibility, rates, or legal approval.
"""
from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlencode

from bs4 import BeautifulSoup, NavigableString

SOURCE_ID = "RG_COMMUNIQUE_2024_39"
SOURCE_SHA = "efb1ebea650cf836155728b6bd3599b76a0fbee70d1a8e5c85f2af4792734530"
SOURCE_URL = "https://resmigazete.gov.tr/eskiler/2024/12/20241231M5-8.htm"
MAX_BYTES = 2_000_000
ARTICLE = re.compile(r"\bMADDE\s+(\d+)\s*[-–]", flags=re.I)


def _paths() -> tuple[Path, Path, Path]:
    return (
        Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive")),
        Path(os.getenv("TARIM_RAG_ORIGINAL_SOURCE_MANIFEST",
                       "configs/p0_10_3_original_source_manifest.json")),
        Path(os.getenv("TARIM_RAG_HTML_CLAUSE_INDEX",
                       "configs/p0_10_6_2024_39_html_clauses.json")),
    )


def _verified(support_id: str, *, root: Path, manifest: Path,
              index: Path) -> tuple[dict, bytes, NavigableString, re.Match[str], BeautifulSoup]:
    if support_id != "BASIC_SUPPORT_2026":
        raise ValueError("This support has no reviewed official HTML quotation")
    sources = json.loads(manifest.read_text(encoding="utf-8"))["sources"]
    matches = [r for r in sources if r.get("id") == SOURCE_ID]
    if len(matches) != 1:
        raise ValueError("Original official HTML manifest identity ambiguous")
    source = matches[0]
    if (source.get("original_sha256") != SOURCE_SHA
        or source.get("url") != SOURCE_URL or source.get("format") != "html"):
        raise ValueError("Official HTML identity not pinned")
    cfg = json.loads(index.read_text(encoding="utf-8"))
    if cfg.get("schema_version") != 1:
        raise ValueError("Unknown source text index schema")
    clauses = [r for r in cfg["clauses"] if r.get("support_id") == support_id]
    if len(clauses) != 1:
        raise ValueError("No unique official clause found")
    row = clauses[0]
    if (row.get("source_id") != SOURCE_ID or row.get("source_url") != SOURCE_URL
        or row.get("source_sha256") != SOURCE_SHA or row.get("article") != "MADDE 4"
        or row.get("paragraph") != "1" or row.get("year") != 2026
        or row.get("verification_status") != "ORIGINAL_HTML_TEXT_LOCATED_PENDING_LEGAL_REVIEW"
        or row.get("legal_review_completed") is not False):
        raise ValueError("Unreviewed, incompatible or forged legal source metadata")
    quote = row.get("exact_quote")
    if not isinstance(quote, str) or not 90 <= len(quote) <= 500:
        raise ValueError("Invalid literal official quotation")
    raw = (root / "originals" / (SOURCE_SHA + ".html")).read_bytes()
    if not raw or len(raw) > MAX_BYTES or hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError("Official HTML original source hash or byte length differs")
    document = BeautifulSoup(raw, "html.parser")
    pattern = re.compile(r"\s+".join(re.escape(w) for w in quote.split()))
    article: str | None = None
    found: list[tuple[NavigableString, re.Match[str]]] = []
    for node in document.find_all(string=True):
        if node.parent.name in {"script", "style", "title"}:
            continue
        text = str(node)
        headings = ARTICLE.findall(text)
        if headings:
            article = headings[-1]
        hit = pattern.search(text)
        if hit:
            if article != "4" or not re.match(r"^\s*\(1\)\s", text):
                raise ValueError("Quote does not belong to the cited MADDE 4(1)")
            found.append((node, hit))
    if len(found) != 1:
        raise ValueError("Original article contains no unique exact quotation")
    node, hit = found[0]
    return row, raw, node, hit, document


def lookup_html_clause(support_id: str) -> dict | None:
    root, manifest, index = _paths()
    try:
        row, _, _, _, _ = _verified(support_id, root=root, manifest=manifest, index=index)
    except (OSError, ValueError, KeyError, TypeError, ImportError):
        return None
    return {
        "source_id": row["source_id"], "title": "2024/39 sayılı Tebliğ — Genel hükümler",
        "section": "MADDE 4 (1)", "year": 2026, "source_url": SOURCE_URL,
        "source_sha256": SOURCE_SHA, "exact_quote": row["exact_quote"],
        "verification_status": row["verification_status"],
        "highlighted_html_url": (
            f"/evidence/highlight/html/{SOURCE_SHA}?"
            + urlencode({"support_id": support_id}) + "#tarim-evidence-highlight"
        ),
    }


def highlighted_html_copy(support_id: str, *, expected_sha256: str) -> bytes:
    root, manifest, index = _paths()
    row, _, node, hit, document = _verified(
        support_id, root=root, manifest=manifest, index=index,
    )
    if expected_sha256 != row["source_sha256"]:
        raise ValueError("Requested HTML source differs from the original")
    text = str(node)
    marked = document.new_tag("mark", id="tarim-evidence-highlight")
    marked["style"] = "background:#ffed52;outline:2px solid #bf9300;padding:2px"
    marked.string = text[hit.start():hit.end()]
    node.replace_with(
        NavigableString(text[:hit.start()]),
        marked,
        NavigableString(text[hit.end():]),
    )
    return str(document).encode("utf-8")


def install_html_original() -> dict:
    """Explicit installation, pinned HTTPS TLS and SHA, never at request time."""
    import httpx

    root, manifest, _ = _paths()
    sources = json.loads(manifest.read_text(encoding="utf-8"))["sources"]
    rows = [r for r in sources if r.get("id") == SOURCE_ID]
    if len(rows) != 1 or rows[0].get("original_sha256") != SOURCE_SHA:
        raise ValueError("Unpinned HTML source")
    path = root / "originals" / (SOURCE_SHA + ".html")
    if path.exists():
        existing = path.read_bytes()
        if hashlib.sha256(existing).hexdigest() != SOURCE_SHA:
            raise ValueError("Existing immutable original does not match SHA")
        return {"sha256": SOURCE_SHA, "bytes": len(existing), "already_present": True}
    with httpx.Client(timeout=55, follow_redirects=False, trust_env=False) as client:
        with client.stream("GET", SOURCE_URL, headers={"Accept-Encoding": "identity"}) as response:
            if (response.status_code != 200 or str(response.url) != SOURCE_URL
                or response.headers.get("Content-Encoding", "identity").lower() != "identity"
                or "html" not in response.headers.get("Content-Type", "").lower()):
                raise ValueError("Original HTML server identity or MIME mismatch")
            chunks, size = [], 0
            for block in response.iter_raw():
                size += len(block)
                if size > MAX_BYTES:
                    raise ValueError("Original HTML exceeds maximum allowed bytes")
                chunks.append(block)
    raw = b"".join(chunks)
    if hashlib.sha256(raw).hexdigest() != SOURCE_SHA:
        raise ValueError("Official HTML now differs from pinned original")
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as stream:
        tmp = Path(stream.name)
        stream.write(raw)
        stream.flush()
        os.fsync(stream.fileno())
    try:
        if path.exists():
            raise ValueError("Concurrent immutable original archive conflict")
        os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)
    return {"sha256": SOURCE_SHA, "bytes": len(raw), "already_present": False}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(install_html_original(), ensure_ascii=False, indent=2))
