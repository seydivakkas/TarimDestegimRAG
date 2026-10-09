"""P0-10.3: download and verify ORIGINAL official HTTP response bytes.

Never confuse third-party rendered HTML with the bytes served by the Gazette.
The first COLLECT pass records byte hashes; VERIFY requires pinned digests.
Neither mode can declare full-year legal coverage or authorize payments.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, datetime
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

MAX_BYTES = 24 * 1024 * 1024
APPROVED_HOSTS = frozenset({"resmigazete.gov.tr", "www.resmigazete.gov.tr"})


class SourceIntegrityError(ValueError):
    """A document, provenance link or expected digest cannot be verified."""


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise SourceIntegrityError("Redirect forbidden; provenance URL requires review")


class _Links(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for key, val in attrs:
            if key.lower() == "href" and val:
                self.hrefs.append(val)


def validate_url(url: str) -> str:
    target = urlsplit(url)
    if (
        target.scheme != "https"
        or (target.hostname or "").lower() not in APPROVED_HOSTS
        or target.username is not None
        or target.password is not None
        or target.port not in (None, 443)
        or target.fragment
    ):
        raise SourceIntegrityError("Source must be an exact approved HTTPS Gazette URL")
    return url


def fetch_original(url: str) -> tuple[bytes, str]:
    """Fetch identity-encoded HTTP entity bytes, with validated TLS and no redirects."""
    validate_url(url)
    request = Request(
        url,
        headers={
            "User-Agent": "TarimDestegimRAG-P0103-SourceAuditor/1.0",
            "Accept-Encoding": "identity",
            "Accept": "application/pdf,text/html;q=0.9",
        },
    )
    with build_opener(_NoRedirect,).open(request, timeout=25) as response:
        if response.geturl() != url:
            raise SourceIntegrityError("Unexpected final source URL")
        if response.headers.get("Content-Encoding", "identity").lower() != "identity":
            raise SourceIntegrityError("Compressed response is not a raw document identity body")
        mime = response.headers.get("Content-Type", "").split(";")[0].strip().lower()
        body = response.read(MAX_BYTES + 1)
    if not body or len(body) > MAX_BYTES:
        raise SourceIntegrityError("Empty or oversized official document")
    return body, mime


def _atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=path.parent, prefix=".source_", delete=False) as f:
        tmp = Path(f.name)
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    try:
        if path.exists():
            current = path.read_bytes()
            if current != data:
                raise SourceIntegrityError("Immutable archived source bytes have changed")
        else:
            os.replace(tmp, path)
    finally:
        tmp.unlink(missing_ok=True)


def _html_links(content: bytes, url: str) -> set[str]:
    # Only the href identity is needed. HTML source bytes are preserved unmodified.
    text = content.decode("windows-1254", errors="replace")
    parser = _Links()
    parser.feed(text)
    result = set()
    for href in parser.hrefs:
        candidate = urljoin(url, href).split("#", 1)[0]
        try:
            validate_url(candidate)
        except (SourceIntegrityError, ValueError):
            continue
        result.add(candidate)
    return result


def _assert_structure(document: dict, body: bytes, mime: str) -> dict:
    is_pdf = document["format"] == "pdf"
    if is_pdf:
        if body[:5] != b"%PDF-" or b"%%EOF" not in body[-4096:]:
            raise SourceIntegrityError("PDF magic/trailer missing")
        if mime not in ("application/pdf", "application/octet-stream"):
            raise SourceIntegrityError("Incorrect PDF response MIME")
        from pypdf import PdfReader
        from io import BytesIO

        pdf = PdfReader(BytesIO(body), strict=True)
        if not pdf.pages:
            raise SourceIntegrityError("Unreadable or zero-page PDF")
        page_count = len(pdf.pages)
        marker = document.get("expected_pdf_text_marker")
        # A genuine page with scanned/image-only text remains INCOMPLETE, not a match.
        pdf_text = "\n".join((p.extract_text() or "") for p in pdf.pages)
        marker_ok = not marker or marker.casefold() in pdf_text.casefold()
        if marker and not marker_ok:
            raise SourceIntegrityError("Expected annex text marker missing (OCR REVIEW)")
        return {"page_count": page_count, "pdf_text_marker_verified": marker_ok}
    if mime not in ("text/html", "application/xhtml+xml"):
        raise SourceIntegrityError("Unexpected HTML source MIME")
    if b"<html" not in body[:16384].lower():
        raise SourceIntegrityError("HTML source has no HTML root")
    return {"html_links": sorted(_html_links(body, document["url"]))}


def collect(
    manifest: dict,
    target: Path,
    *,
    mode: str,
    fetch=fetch_original,
) -> dict:
    if mode not in ("collect", "verify"):
        raise ValueError("Mode must be collect or verify")
    if manifest.get("complete_official_coverage_proven") is not False:
        raise SourceIntegrityError("Unreviewed discovery corpus cannot assert full-year coverage")
    source_rows = manifest.get("sources", [])
    if not isinstance(source_rows, list) or len(source_rows) != 5:
        raise SourceIntegrityError("Required five-source audit manifest is missing")
    source_ids = [row["id"] for row in source_rows]
    if len(set(source_ids)) != len(source_ids):
        raise SourceIntegrityError("Duplicate official source ID")
    results: list[dict] = []
    failures: list[dict] = []
    html_links: dict[str, set[str]] = {}
    for doc in source_rows:
        source_id = doc["id"]
        try:
            validate_url(doc["url"])
            body, mime = fetch(doc["url"])
            structure = _assert_structure(doc, body, mime)
            digest = hashlib.sha256(body).hexdigest()
            expected = doc.get("original_sha256")
            if mode == "verify":
                if not isinstance(expected, str) or not re.fullmatch(r"[a-f0-9]{64}", expected):
                    raise SourceIntegrityError("Unpinned original-source SHA-256: HOLD")
                if expected != digest:
                    raise SourceIntegrityError("Official source SHA-256 differs from pinned manifest")
            elif expected is not None and expected != digest:
                raise SourceIntegrityError("Collected source disagrees with existing pin")
            suffix = ".pdf" if doc["format"] == "pdf" else ".html"
            _atomic_bytes(target / "originals" / (digest + suffix), body)
            if "html_links" in structure:
                html_links[source_id] = set(structure.pop("html_links"))
            results.append(
                {
                    "id": source_id,
                    "url": doc["url"],
                    "sha256": digest,
                    "bytes": len(body),
                    "mime": mime,
                    "original_response": True,
                    "pinned": isinstance(expected, str) and expected == digest,
                    **structure,
                }
            )
        except Exception as exc:
            failures.append({"id": source_id, "error": str(exc), "stage": "FETCH_OR_VERIFY"})
    for doc in source_rows:
        if doc.get("parent_id"):
            parent = doc["parent_id"]
            if doc["url"] not in html_links.get(parent, set()):
                failures.append(
                    {"id": doc["id"], "stage": "PARENT_ANNEX_LINK",
                     "error": "Attachment URL absent from independently fetched parent HTML"}
                )
    status = "PASS" if not failures and len(results) == len(source_rows) else "HOLD"
    report = {
        "schema_version": 1,
        "fetched_utc": datetime.now(UTC).isoformat(),
        "mode": mode,
        "source_status": status,
        "year_scope_completeness": "NOT_PROVEN",
        "legal_activation": False,
        "payable_authorization": False,
        "documents": results,
        "errors": failures,
    }
    report_path = target / "report.json"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    # The scan report has a new timestamp per run and is NOT an immutable source.
    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", dir=target, prefix=".report_",
        delete=False,
    ) as f:
        temp = Path(f.name)
        json.dump(report, f, ensure_ascii=False, indent=2, sort_keys=True)
        f.write("\n")
        f.flush()
        os.fsync(f.fileno())
    try:
        os.replace(temp, report_path)
    finally:
        temp.unlink(missing_ok=True)
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("configs/p0_10_3_original_source_manifest.json"))
    parser.add_argument("--out", type=Path, default=Path("data/p0_10_3_original_source_evidence"))
    parser.add_argument("--mode", choices=("collect", "verify"), default="verify")
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text(encoding="utf-8"))
    result = collect(manifest, args.out, mode=args.mode)
    for row in result["documents"]:
        print(
            "ORIGINAL_SOURCE id={id} sha256={sha256} bytes={bytes} "
            "mime={mime} pinned={pinned}".format(**row),
            flush=True,
        )
    for err in result["errors"]:
        print("SOURCE_ERROR id={id} stage={stage} error={error}".format(**err), flush=True)
    print("SOURCE_STATUS", result["source_status"], "YEAR_COVERAGE", result["year_scope_completeness"])
    return 0 if result["source_status"] == "PASS" else 2


if __name__ == "__main__":
    raise SystemExit(main())
