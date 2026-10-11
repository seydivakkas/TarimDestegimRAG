"""Explicit Windows/Linux original Gazette PDF installer; never invoked by UI.

Only pinned sources from the repository manifest are accepted. No redirects,
temporary fake Gazette pages or filesystem overwrites.
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

ALLOWED_HOSTS = {
    "resmigazete.gov.tr", "www.resmigazete.gov.tr",
    "www.tarimorman.gov.tr", "tarimorman.gov.tr",
}


def source_path(archive_root: Path, original_sha: str) -> Path:
    if not re.fullmatch(r"[a-f0-9]{64}", original_sha):
        raise ValueError("Invalid pinned original SHA-256")
    return archive_root / "originals" / (original_sha + ".pdf")


def install_original(
    source: dict, *, archive_root: Path,
    import_dir: Path | None = None,
) -> dict:
    """Download or import exactly one official PDF and validate its original bytes."""
    sha = source.get("original_sha256")
    expected_size = source.get("original_bytes")
    url = source.get("url")
    if (source.get("format") != "pdf"
            or not isinstance(sha, str)
            or not re.fullmatch(r"[a-f0-9]{64}", sha)
            or type(expected_size) is not int
            or not 20 <= expected_size <= 100_000_000
            or not isinstance(url, str)):
        raise ValueError("Original source manifest is incomplete")
    parsed = urlsplit(url)
    if (parsed.scheme != "https" or parsed.hostname not in ALLOWED_HOSTS
            or parsed.username is not None or parsed.password is not None
            or parsed.port not in (None, 443) or parsed.query or parsed.fragment):
        raise ValueError("Source is not an exact permitted official URL")

    target = source_path(archive_root, sha)
    if target.is_file():
        existing = target.read_bytes()
        if len(existing) != expected_size or hashlib.sha256(existing).hexdigest() != sha:
            raise ValueError("Already-installed official bytes tampered; HOLD")
        return {"id": source["id"], "status": "ALREADY_PINNED", "sha256": sha}

    if import_dir is not None:
        data = (import_dir / (sha + ".pdf")).read_bytes()
    else:
        import httpx

        # Only explicit command execution downloads; never on page view.
        with httpx.Client(timeout=25.0, follow_redirects=False, verify=True) as client:
            response = client.get(url)
            response.raise_for_status()
            if response.status_code != 200 or len(response.content) > 100_000_000:
                raise ValueError("Official source HTTP response unsuitable")
            data = response.content

    if (not data.startswith(b"%PDF-") or len(data) != expected_size
            or hashlib.sha256(data).hexdigest() != sha):
        raise ValueError("Original SHA-256/length/format mismatch: HOLD")

    target.parent.mkdir(parents=True, exist_ok=True)
    # Stage bytes in the final directory; no partial sources.
    descriptor, temporary = tempfile.mkstemp(prefix=".official-", dir=target.parent)
    try:
        with os.fdopen(descriptor, "wb") as handle:
            handle.write(data)
            handle.flush()
            os.fsync(handle.fileno())
        # Exclusive creation; do not overwrite or bless an altered existing file.
        with open(target, "xb") as dest:
            dest.write(Path(temporary).read_bytes())
            dest.flush()
            os.fsync(dest.fileno())
    finally:
        Path(temporary).unlink(missing_ok=True)
    return {"id": source["id"], "status": "PINNED_BYTES_INSTALLED", "sha256": sha}


def main() -> int:
    parser = argparse.ArgumentParser(description="Install pinned original Gazette PDFs")
    parser.add_argument("--manifest", type=Path,
                        default=Path("configs/p0_10_3_original_source_manifest.json"))
    parser.add_argument("--archive-root", type=Path,
                        default=Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE",
                                             "data/legal_update_archive")))
    parser.add_argument("--source-id", default="RG_DECISION_8859")
    parser.add_argument("--import-dir", type=Path)
    args = parser.parse_args()
    sources = json.loads(args.manifest.read_text(encoding="utf-8"))["sources"]
    found = [s for s in sources if s.get("id") == args.source_id]
    if len(found) != 1:
        raise SystemExit("HOLD: manifest does not contain exactly one source ID")
    result = install_original(
        found[0], archive_root=args.archive_root, import_dir=args.import_dir,
    )
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    print("Note: source-byte integrity is not OCR, clause or legal-year acceptance")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
