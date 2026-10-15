"""G37: acquire *original HTTP bytes* into the local evidence archive.

Windows/Linux, Python stdlib only. This is NOT a legal approval tool.
Pinned original bytes can be activated only if SHA-256 AND byte length match
the existing original-source manifest. Unpinned historical additions are
QUARANTINED, never imported as proven legal passages.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import ssl
import sys
import tempfile
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

HOSTS = {"resmigazete.gov.tr", "www.resmigazete.gov.tr"}
FIXED = {
    "2024_39": {
        "source_id": "RG_COMMUNIQUE_2024_39",
        "url": "https://resmigazete.gov.tr/eskiler/2024/12/20241231M5-8.htm",
        "suffix": ".html",
    },
    "2025_42": {
        "source_id": "RG_AMENDMENT_2025_42",
        "url": "https://resmigazete.gov.tr/eskiler/2025/12/20251230-9.htm",
        "suffix": ".html",
    },
    "2025_13": {
        "source_id": None,  # no SHA-pinned primary original in manifest
        "url": "https://www.resmigazete.gov.tr/eskiler/2025/08/20250805-4.htm",
        "suffix": ".html",
    },
    "11781": {
        "source_id": None,  # must be reviewed and promoted separately
        "url": "https://www.resmigazete.gov.tr/eskiler/2026/09/20260908-7.pdf",
        "suffix": ".pdf",
    },
}


def _official_url(url: str) -> None:
    p = urllib.parse.urlsplit(url)
    if (
        p.scheme != "https" or p.hostname not in HOSTS
        or p.username or p.password or p.port not in (None, 443)
        or p.query or p.fragment
    ):
        raise ValueError("Only configured original official HTTPS sources allowed")


class NoCrossDomainRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        _official_url(newurl)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _fetch(url: str, suffix: str) -> bytes:
    _official_url(url)
    opener = urllib.request.build_opener(
        urllib.request.HTTPSHandler(context=ssl.create_default_context()),
        NoCrossDomainRedirect(),
    )
    # Limit text documents strictly; no infinite read or document guessing.
    limit = 4_000_000 if suffix == ".html" else 20_000_000
    with opener.open(urllib.request.Request(
        url, headers={"User-Agent": "TarimDestekRAG-OriginalArchive/1.0"}
    ), timeout=35) as resp:
        _official_url(resp.geturl())
        mime = resp.headers.get_content_type().lower()
        if suffix == ".html" and mime not in (
            "text/html", "application/xhtml+xml", "text/plain",
        ):
            raise ValueError("Not an HTML document: " + mime)
        if suffix == ".pdf" and mime not in (
            "application/pdf", "application/octet-stream",
        ):
            raise ValueError("Not a PDF document: " + mime)
        payload = resp.read(limit + 1)
        if not payload or len(payload) > limit:
            raise ValueError("Empty or oversized source response")
        if suffix == ".pdf" and not payload.startswith(b"%PDF-"):
            raise ValueError("PDF magic does not match")
        if suffix == ".html" and b"<" not in payload[:4096]:
            raise ValueError("Original HTML appears invalid")
        return payload


def _write_exact(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if path.exists():
        if path.read_bytes() == data:
            return
        raise ValueError("Existing original is different: " + str(path))
    fd, tmp = tempfile.mkstemp(
        prefix=".source-", dir=str(path.parent),
    )
    try:
        with os.fdopen(fd, "wb") as output:
            output.write(data)
            output.flush()
            os.fsync(output.fileno())
        # Never overwrite an existing file during a concurrent download.
        with path.open("xb") as target:
            target.write(Path(tmp).read_bytes())
            target.flush()
            os.fsync(target.fileno())
    except FileExistsError:
        if not path.is_file() or path.read_bytes() != data:
            raise
    finally:
        Path(tmp).unlink(missing_ok=True)


def acquire(key: str, *, manifest_path: Path, archive: Path) -> dict:
    source = FIXED[key]
    report = {
        "source_key": key,
        "source_url": source["url"],
        "status": "DOWNLOAD_FAILED_HOLD",
        "sha256": None,
        "original_bytes": None,
        "normative_claim_approved": False,
        "legal_year_approved": False,
        "payment_approved": False,
    }
    try:
        data = _fetch(source["url"], source["suffix"])
        digest = hashlib.sha256(data).hexdigest()
        report["sha256"] = digest
        report["original_bytes"] = len(data)
        if source["source_id"] is None:
            # Origin byte hash is recorded as an observation, NOT an
            # independently verified official original/curated legal source.
            target = archive / "quarantine" / (digest + source["suffix"])
            _write_exact(target, data)
            report["status"] = "UNPINNED_OFFICIAL_URL_BYTES_QUARANTINED_HOLD"
            report["relative_path"] = str(target)
        else:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
            rows = [s for s in manifest["sources"]
                    if s.get("id") == source["source_id"]]
            if len(rows) != 1 or rows[0].get("url") != source["url"]:
                raise ValueError("Original-source manifest identity mismatch")
            trusted = rows[0]
            if (trusted.get("format") != "html"
                    or trusted.get("original_sha256") != digest
                    or trusted.get("original_bytes") != len(data)):
                raise ValueError("Manifest SHA or original byte count mismatch")
            target = archive / "originals" / (digest + ".html")
            _write_exact(target, data)
            report["status"] = "ORIGINAL_SHA_AND_LENGTH_VERIFIED_LOCATION_REVIEW_PENDING"
            report["relative_path"] = str(target)
    except (OSError, ValueError, KeyError, urllib.error.URLError) as exc:
        report["status"] = "DOWNLOAD_OR_SHA_HOLD"
        report["error"] = type(exc).__name__ + ": " + str(exc)[:300]
    return report


def main() -> int:
    parser = argparse.ArgumentParser(description="Official bytes, SHA-safe local evidence acquisition")
    parser.add_argument("--sources", nargs="+", choices=tuple(FIXED), default=list(FIXED))
    parser.add_argument("--manifest", default="configs/p0_10_3_original_source_manifest.json")
    parser.add_argument("--archive", default="data/legal_update_archive")
    args = parser.parse_args()
    manifest, archive = Path(args.manifest), Path(args.archive)
    for key in args.sources:
        output = acquire(key, manifest_path=manifest, archive=archive)
        print(json.dumps(output, ensure_ascii=False, sort_keys=True))
    # These are source-acquisition states only: never grant a legal PASS.
    return 0


if __name__ == "__main__":
    sys.exit(main())
