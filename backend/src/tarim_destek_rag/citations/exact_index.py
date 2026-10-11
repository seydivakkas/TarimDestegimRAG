"""Offline, SHA-pinned original-PDF quote index for the farmer-facing 'Neden?' panel.

An explanation or search hit is NOT an official quote. Records are accepted
only after the original archived PDF contains the exact quote at the stated
page, with matching PDF SHA and official URL from the pinned source manifest.
Indexing does not constitute legal approval or activate payable rules.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from pathlib import Path
from urllib.parse import urlsplit

from tarim_destek_rag.updates.pdf_evidence import (
    UnverifiableEvidence,
    evidence_deeplink,
    locate_pdf_quote,
)

_VALID_KEY = re.compile(r"^[A-Z][A-Z0-9_]{2,79}$")
_SHA = re.compile(r"^[a-f0-9]{64}$")
_ALLOWED_HOSTS = {"resmigazete.gov.tr", "www.resmigazete.gov.tr"}


def _paths() -> tuple[Path, Path]:
    root = Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive"))
    manifest = Path(os.getenv(
        "TARIM_RAG_ORIGINAL_SOURCE_MANIFEST",
        "configs/p0_10_3_original_source_manifest.json",
    ))
    return root, manifest


def _check(row: dict, *, root: Path, manifest: Path) -> dict:
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
        catalog = data["sources"]
        original = next(
            x for x in catalog
            if x["id"] == row["source_id"] and x["format"] == "pdf"
        )
        key = row["support_id"]
        sha = row["source_sha256"]
        url = row["source_url"]
        page = row["page_number"]
        quote = row["exact_quote"]
        section = row["section"]
        if (not isinstance(key, str) or not _VALID_KEY.fullmatch(key)
            or not isinstance(sha, str) or not _SHA.fullmatch(sha)
            or not isinstance(page, int) or not 1 <= page <= 500
            or not isinstance(section, str) or len(section.strip()) < 4
            or not isinstance(quote, str)):
            raise ValueError("Malformed source, section, SHA, page or exact quote")
        u = urlsplit(url)
        if (u.scheme != "https" or u.hostname not in _ALLOWED_HOSTS
            or u.username or u.password or u.port not in (None, 443)
            or u.query or u.fragment):
            raise ValueError("Noncanonical or unapproved original PDF URL")
        if sha != original["original_sha256"] or url != original["url"]:
            raise ValueError("Source ID, URL or SHA not in original pinned manifest")
        original_bytes = (root / "originals" / (sha + ".pdf")).read_bytes()
        if hashlib.sha256(original_bytes).hexdigest() != sha:
            raise ValueError("Original source bytes do not match pinned SHA-256")
        proof = locate_pdf_quote(
            original_bytes,
            expected_sha256=sha,
            page_1_indexed=page,
            exact_quote=quote,
        )
        # A correct page is not sufficient: a quoted sentence under MADDE 2
        # must never be mislabelled MADDE 1 merely because both share a page.
        article = re.search(r"\bMADDE\s+(\d+)\b", section.upper())
        if article:
            import pymupdf

            with pymupdf.open(stream=original_bytes, filetype="pdf") as doc:
                page_text = " ".join(doc[page - 1].get_text(sort=True).split())
            offset = page_text.index(proof.exact_quote)
            headings = [
                m for m in re.finditer(r"\bMADDE\s+(\d+)\s*[-–]", page_text, re.I)
                if m.start() <= offset
            ]
            if not headings or headings[-1].group(1) != article.group(1):
                raise ValueError("Quoted PDF text belongs to a different article")
    except (KeyError, TypeError, StopIteration, OSError, ValueError, ImportError, UnverifiableEvidence) as exc:
        raise ValueError("Original source quote cannot be independently verified") from exc
    return {
        "source_id": row["source_id"],
        "support_id": key,
        "source_url": url,
        "source_sha256": sha,
        "page_number": proof.page_1_indexed,
        "exact_quote": proof.exact_quote,
        "section": section.strip(),
        "title": str(row.get("title") or original["id"]),
        "year": int(row.get("year", 2026)),
        "verification_status": "EXACT_PDF_MATCH_PENDING_LEGAL_REVIEW",
        "highlighted_pdf_url": evidence_deeplink(proof),
    }


def lookup_exact_pdf_citation(support_id: str) -> dict | None:
    """Reads and re-verifies a single trusted offline index record; never fetches URLs."""
    if not isinstance(support_id, str) or not _VALID_KEY.fullmatch(support_id):
        return None
    root, manifest = _paths()
    try:
        index = json.loads((root / "verified_citations.json").read_text(encoding="utf-8"))
        entries = [r for r in index["citations"] if r.get("support_id") == support_id]
        if len(entries) != 1:
            return None
        return _check(entries[0], root=root, manifest=manifest)
    except (OSError, ValueError, TypeError, KeyError):
        return None


def index_quote(row: dict, *, root: Path, manifest: Path) -> dict:
    """Validate original bytes before publishing an offline content-addressed index."""
    proof = _check(row, root=root, manifest=manifest)
    path = root / "verified_citations.json"
    existing = json.loads(path.read_text(encoding="utf-8")) if path.is_file() else {
        "schema_version": 1, "citations": [],
    }
    entries = [x for x in existing["citations"] if x["support_id"] != row["support_id"]]
    entries.append({
        "support_id": proof["support_id"],
        "source_id": proof["source_id"],
        "source_url": proof["source_url"],
        "source_sha256": proof["source_sha256"],
        "page_number": proof["page_number"],
        "exact_quote": proof["exact_quote"],
        "section": proof["section"],
        "title": proof["title"],
        "year": proof["year"],
    })
    root.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=root, prefix=".citation_", delete=False
    ) as tmp:
        tmp_path = Path(tmp.name)
        json.dump({"schema_version": 1, "citations": entries},
                  tmp, ensure_ascii=False, indent=2)
        tmp.write("\n")
        tmp.flush()
        os.fsync(tmp.fileno())
    try:
        os.replace(tmp_path, path)
    finally:
        tmp_path.unlink(missing_ok=True)
    return proof


def main() -> int:
    parser = argparse.ArgumentParser(description="Add a genuinely matched official PDF quote")
    parser.add_argument("--support-id", required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--page", required=True, type=int)
    parser.add_argument("--quote", required=True)
    parser.add_argument("--section", required=True)
    parser.add_argument("--title", default="")
    args = parser.parse_args()
    root, manifest = _paths()
    row = {
        "support_id": args.support_id, "source_id": args.source_id,
        "source_url": next(
            item["url"] for item in json.loads(manifest.read_text(encoding="utf-8"))["sources"]
            if item["id"] == args.source_id
        ),
        "source_sha256": next(
            item["original_sha256"]
            for item in json.loads(manifest.read_text(encoding="utf-8"))["sources"]
            if item["id"] == args.source_id
        ),
        "page_number": args.page, "exact_quote": args.quote,
        "section": args.section, "title": args.title, "year": 2026,
    }
    proof = index_quote(row, root=root, manifest=manifest)
    print(json.dumps(proof, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
