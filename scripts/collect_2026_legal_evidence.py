"""Evidence collector for official Gazette PDFs. Does not approve monetary rates.

Explicit manual script: downloads exact official URLs, validates PDF structure,
and records observed SHA-256. Never edits the database or approval status.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

SOURCES = {
    "8859": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf",
    "10394": "https://www.resmigazete.gov.tr/eskiler/2025/09/20250914-6.pdf",
    "11781": "https://www.resmigazete.gov.tr/eskiler/2026/09/20260908-7.pdf",
}
MAX_PDF_BYTES = 15 * 1024 * 1024


def fetch_pdf_evidence(url: str, output: Path) -> dict:
    from pypdf import PdfReader

    if url not in SOURCES.values():
        raise ValueError("Only exact 8859, 10394, 11781 official URLs are permitted.")
    request = Request(url, headers={"User-Agent": "TarimDestegimRAG-Legal-Audit/1.0"})
    with urlopen(request, timeout=25) as response:
        final = response.geturl()
        parsed = urlparse(final)
        if parsed.scheme != "https" or parsed.hostname != "www.resmigazete.gov.tr":
            raise ValueError("Unexpected PDF redirect; source integrity uncertain.")
        raw = response.read(MAX_PDF_BYTES + 1)
    if len(raw) > MAX_PDF_BYTES or not raw.startswith(b"%PDF-"):
        raise ValueError("Missing/truncated/non-PDF response; not legal evidence")
    # pypdf confirms that the fetched bytes are parseable rather than an HTML error.
    import io

    pdf = PdfReader(io.BytesIO(raw))
    if not pdf.pages:
        raise ValueError("PDF has no pages")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_bytes(raw)
    return {
        "source_url": url,
        "retrieved_url": final,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "pdf_bytes": len(raw),
        "pdf_pages": len(pdf.pages),
        "sha256_of_pdf_bytes": hashlib.sha256(raw).hexdigest(),
        "review_status": "FETCHED_HASHED_NOT_LEGALLY_APPROVED",
        "human_legal_excerpt_reviewed": False,
        "component_rate_approval": False,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output-dir", default="data/legal_evidence")
    parser.add_argument("--decision", action="append", choices=sorted(SOURCES),
                        help="Limit to specified decisions; default all three")
    args = parser.parse_args()
    folder = Path(args.output_dir)
    manifest: dict[str, dict] = {}
    errors: dict[str, str] = {}
    for decision in args.decision or list(SOURCES):
        try:
            manifest[decision] = fetch_pdf_evidence(
                SOURCES[decision], folder / f"decision_{decision}.pdf"
            )
            print(f"{decision}: SHA256={manifest[decision]['sha256_of_pdf_bytes']}")
        except Exception as exc:
            errors[decision] = str(exc)
            print(f"{decision}: FAILED to fetch/verify ({exc})")
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "manifest.json").write_text(json.dumps(
        {"documents": manifest, "errors": errors, "approval": False},
        ensure_ascii=False, indent=2
    ) + "\n", encoding="utf-8")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
