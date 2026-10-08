"""Fetch and hash the published 2024/39 PDF and original 2025/42 Gazette HTML.

No database edits, no status promotion, no arbitrary URLs, no private keys.
If a primary source cannot be retrieved, the job fails and reports incomplete
legal evidence; it never fabricates a SHA-256 or approval.
"""

import hashlib
import io
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from pypdf import PdfReader

_catalog_path = Path(__file__).resolve().parents[1] / "configs/2026_water_restriction_52_draft.json"
_source_data = json.loads(_catalog_path.read_text(encoding="utf-8"))
PRIMARY_URL = _source_data["legal_basis"][0]["url"]
AMENDMENT_URL = _source_data["legal_basis"][1]["url"]
if (
    not PRIMARY_URL.startswith("https://www.tarimorman.gov.tr/BUGEM/Belgeler/")
    or "2024-39" not in PRIMARY_URL
    or AMENDMENT_URL != "https://resmigazete.gov.tr/eskiler/2025/12/20251230-9.htm"
):
    raise ValueError("Invalid official legal source whitelist")

MAX_BYTES = 12 * 1024 * 1024


def retrieve(url: str, host: str) -> bytes:
    with urlopen(Request(url, headers={"User-Agent": "TarimDestegimRAG-LegalAudit/1.1"}),
                 timeout=35) as response:
        end = urlparse(response.geturl())
        if end.scheme != "https" or end.hostname not in (host, "www." + host):
            raise ValueError("Official source redirected to an unexpected host")
        raw = response.read(MAX_BYTES + 1)
    if not raw or len(raw) > MAX_BYTES:
        raise ValueError("Official legal document download missing or oversized")
    return raw


def inspect_primary(raw: bytes) -> None:
    if not raw.startswith(b"%PDF-"):
        raise ValueError("2024/39 source is not PDF")
    pages = PdfReader(io.BytesIO(raw)).pages
    if len(pages) < 9:
        raise ValueError("2024/39 page 9 absent")
    text = " ".join((pages[8].extract_text() or "").split()).casefold()
    for token in ("karatay", "kızıltepe", "sarayönü", "su kısıt"):
        if token not in text:
            raise ValueError("2024/39 Article 6(3)(a) not found: " + token)


def inspect_amendment(raw: bytes) -> None:
    soup = BeautifulSoup(raw, "html.parser")
    text = " ".join(soup.get_text(" ", strip=True).split()).casefold()
    for token in ("2025/42", "madde 4", "madde 12", "madde 16", "mısır (dane)", "patates"):
        if token not in text:
            raise ValueError("Original Gazette amendment section missing: " + token)
    if "yürürlükten kaldırılmıştır" not in text or "1/1/2026" not in text:
        raise ValueError("2026 repeal/effective date was not independently confirmed")


def run(output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    documents = {}
    failures = {}
    for key, url, host, filename, inspector in (
        ("2024/39", PRIMARY_URL, "tarimorman.gov.tr", "2024_39.pdf", inspect_primary),
        ("2025/42", AMENDMENT_URL, "resmigazete.gov.tr", "2025_42.htm", inspect_amendment),
    ):
        try:
            raw = retrieve(url, host)
            inspector(raw)
            (output_dir / filename).write_bytes(raw)
            documents[key] = {
                "source_url": url,
                "sha256_of_fetched_bytes": hashlib.sha256(raw).hexdigest(),
                "byte_count": len(raw),
                "retrieved_at_utc": datetime.now(timezone.utc).isoformat(),
                "status": "SOURCE_BYTES_CAPTURED_AND_CLAUSE_CHECKED_NOT_LEGALLY_APPROVED",
            }
            print(f"{key}: SHA256 {documents[key]['sha256_of_fetched_bytes']}")
        except Exception as exc:
            failures[key] = str(exc)
            print(f"{key}: SOURCE_NOT_PROVEN: {exc}")
    (output_dir / "manifest.json").write_text(
        json.dumps({
            "documents": documents, "errors": failures,
            "authorized_human_review": False,
            "production_activation": False,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    if failures:
        raise RuntimeError("Primary legal evidence is incomplete; no production approval permitted")


if __name__ == "__main__":
    run(Path("data/water_legal_evidence_2026"))
