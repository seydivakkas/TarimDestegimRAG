"""Future-year official source change discovery, with NO implicit legal activation.

The user initiates one update *scan*. It archives original official bytes,
writes an inspectable change batch, and NEVER alters effective rules/rates.
Discovery is adapter-based and intentionally reports coverage/uncertainty:
a seed link scan is not proof that all official 2030 documents were found.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable
from urllib.parse import urljoin, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

from bs4 import BeautifulSoup

MAX_BYTES = 10 * 1024 * 1024
SUPPORTED_CONTENT_TYPES = ("application/pdf", "text/html", "application/xhtml+xml")
LEGAL_LINK_TERMS = (
    "destek", "tebli", "mevzuat", "tarım", "tarim", "üretim",
    "uretim", "havza", "çks", "cks", "resm", "karar",
)


@dataclass(frozen=True)
class OfficialPortal:
    source_id: str
    index_url: str
    allowed_hosts: tuple[str, ...]
    max_documents: int = 12


class UnsafeOfficialSource(ValueError):
    pass


def _official_url(url: str, hosts: tuple[str, ...]) -> str:
    parsed = urlsplit(url)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or not host or host not in hosts
        or parsed.username or parsed.password
        or parsed.port not in (None, 443)
        or parsed.fragment  # fragment never participates in source identity
    ):
        raise UnsafeOfficialSource("Only exact approved HTTPS official sources are permitted")
    return url


class _NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        raise UnsafeOfficialSource("HTTP redirects require explicit official-source review")


def _http_fetch(url: str, hosts: tuple[str, ...]) -> tuple[bytes, str]:
    _official_url(url, hosts)
    response = build_opener(_NoRedirect).open(
        Request(url, headers={"User-Agent": "TarimDestegimRAG-Audit/1.0"}),
        timeout=15,
    )
    with response:
        raw_type = response.headers.get("Content-Type", "").split(";")[0].lower().strip()
        raw = response.read(MAX_BYTES + 1)
        if len(raw) > MAX_BYTES:
            raise ValueError("Official document exceeds configured byte limit")
        if raw_type not in SUPPORTED_CONTENT_TYPES:
            raise ValueError("Unexpected official response MIME type")
        if raw_type == "application/pdf" and not raw.startswith(b"%PDF-"):
            raise ValueError("Document MIME claims PDF but bytes are not PDF")
        return raw, raw_type


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        mode="wb", dir=str(path.parent), prefix=".stage_", delete=False
    ) as file:
        temporary = Path(file.name)
        try:
            file.write(data)
            file.flush()
            os.fsync(file.fileno())
        except BaseException:
            temporary.unlink(missing_ok=True)
            raise
    try:
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _discover_links(
    portal: OfficialPortal, html_bytes: bytes, year: int
) -> list[tuple[str, str]]:
    soup = BeautifulSoup(html_bytes, "html.parser")
    seen: set[str] = set()
    result = []
    for a in soup.select("a[href]"):
        target = urljoin(portal.index_url, a.get("href") or "").split("#", 1)[0]
        title = " ".join(a.get_text(" ", strip=True).split())
        try:
            _official_url(target, portal.allowed_hosts)
        except UnsafeOfficialSource:
            continue
        # Match by legal vocabulary, not by a path hard-coded for year 2026;
        # document effective_year is NOT guessed from the filename.
        haystack = (title + " " + target).casefold()
        relevant = any(word in haystack for word in LEGAL_LINK_TERMS)
        if not relevant or target in seen or target == portal.index_url:
            continue
        seen.add(target)
        result.append((target, title))
        if len(result) >= portal.max_documents:
            break
    return result


def _content_name(content_type: str) -> str:
    return ".pdf" if content_type == "application/pdf" else ".html"


def scan_official_sources(
    *,
    production_year: int,
    portals: list[OfficialPortal],
    output: Path,
    fetch: Callable[[str, tuple[str, ...]], tuple[bytes, str]] = _http_fetch,
) -> dict:
    """Discover, archive and report. Never call database/rule activation APIs.

    No claim of complete national coverage, even when zero changes are found.
    Idempotent originals are keyed by actual SHA-256 and never overwritten.
    """
    if not 2020 <= production_year <= 2100:
        raise ValueError("Production year must be explicitly selected")
    if not portals:
        raise ValueError("At least one approved official source is required")
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    index_path = output / "inventory.json"
    inventory = json.loads(index_path.read_text(encoding="utf-8")) if index_path.exists() else {}
    if not isinstance(inventory, dict):
        raise ValueError("Archived source inventory is not a dictionary")
    previous = dict(inventory)
    discovered: list[dict] = []
    failures: list[dict] = []
    for portal in portals:
        _official_url(portal.index_url, portal.allowed_hosts)
        if not portal.max_documents or portal.max_documents > 50:
            raise ValueError("Document limit out of safe bounds")
        try:
            landing, mime = fetch(portal.index_url, portal.allowed_hosts)
            if mime != "text/html":
                raise ValueError("Portal landing page is not HTML")
            links = _discover_links(portal, landing, production_year)
        except Exception as exc:
            failures.append({"source": portal.source_id, "error": str(exc)})
            continue
        for url, title in links:
            try:
                data, content_type = fetch(url, portal.allowed_hosts)
                if content_type not in SUPPORTED_CONTENT_TYPES or not data:
                    raise ValueError("Unsupported or empty document")
                digest = hashlib.sha256(data).hexdigest()
                old_hash = previous.get(url)
                status = (
                    "UNCHANGED" if old_hash == digest
                    else "NEW_DOCUMENT" if old_hash is None
                    else "CHANGED_DOCUMENT"
                )
                archive = output / "originals" / (digest + _content_name(content_type))
                if archive.exists():
                    if hashlib.sha256(archive.read_bytes()).hexdigest() != digest:
                        raise ValueError("Immutable stored original has been modified")
                else:
                    _atomic_write(archive, data)
                inventory[url] = digest
                discovered.append({
                    "source_id": portal.source_id, "source_url": url,
                    "source_title": title, "mime_type": content_type,
                    "sha256": digest, "previous_sha256": old_hash,
                    "status": status,
                    "archive_relative": str(archive.relative_to(output)),
                    "legal_status": "DRAFT_NEEDS_CLAUSE_AND_HUMAN_REVIEW",
                    "legal_effective_from": None,
                    "verified_rates_imported": False,
                })
            except Exception as exc:
                failures.append({"source": portal.source_id, "url": url, "error": str(exc)})
    _atomic_write(index_path, (
        json.dumps(inventory, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8"))
    batch = {
        "schema_version": 1,
        "target_production_year": production_year,
        "scan_time_utc": datetime.now(timezone.utc).isoformat(),
        "status": "REVIEW_REQUIRED",
        "publication_activated": False,
        "complete_official_coverage_proven": False,
        "discovery_mode": "ALLOWLISTED_PORTAL_LINKS_NOT_COMPLETE_REGULATORY_SEARCH",
        "new_or_changed": sum(x["status"] != "UNCHANGED" for x in discovered),
        "documents": discovered,
        "errors": failures,
    }
    report_path = output / "batches" / (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%f") + ".json"
    )
    _atomic_write(report_path, (
        json.dumps(batch, ensure_ascii=False, sort_keys=True, indent=2) + "\n"
    ).encode("utf-8"))
    batch["report_path"] = str(report_path)
    return batch


def read_portals(path: Path) -> list[OfficialPortal]:
    raw = json.loads(path.read_text(encoding="utf-8"))
    portals = []
    for item in raw.get("portals", []):
        hosts = tuple(item["allowed_hosts"])
        if not hosts or any(not h.endswith(("tarimorman.gov.tr", "resmigazete.gov.tr")) for h in hosts):
            raise UnsafeOfficialSource("Portal host must be government-approved")
        portals.append(OfficialPortal(
            source_id=item["source_id"], index_url=item["index_url"],
            allowed_hosts=hosts,
            max_documents=int(item.get("max_documents", 12)),
        ))
    if not portals:
        raise ValueError("No official update portals configured")
    return portals
