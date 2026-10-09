# ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
# Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
# Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim amaçlı olarak paylaşılmıştır.
# YASAKLAR: Kopyalanamaz, çoğaltılamaz, dağıtılamaz, satılamaz, tersine mühendislik yapılamaz.
# İZİN VERİLEN KULLANIM: GitHub üzerinde görüntüleme ve inceleme.

"""P0-10.4 additional official Gazette amendment originals; acquisition only.

Do not mark an unpinned first fetch as verified/legal-approved.
"""
from __future__ import annotations

import hashlib
import io
import json
from datetime import UTC, datetime
from pathlib import Path

from bs4 import BeautifulSoup
from pypdf import PdfReader

from scripts.p0_10_3_source_integrity import (
    _atomic_bytes,
    fetch_original,
    validate_url,
)

REQUIRED_NEW_IDS = (
    "communique_2025_13", "decision_10394", "decision_11781"
)


def collect_additions(
    inventory: dict, output: Path, fetch=fetch_original
) -> dict:
    by_id = {d["id"]: d for d in inventory["documents"]}
    records = []
    errors = []
    for doc_id in REQUIRED_NEW_IDS:
        d = by_id[doc_id]
        try:
            url = validate_url(d["url"])
            payload, mime = fetch(url)
            is_pdf = url.endswith(".pdf")
            if is_pdf:
                if not payload.startswith(b"%PDF-") or b"%%EOF" not in payload[-4096:]:
                    raise ValueError("Original PDF structure malformed")
                if mime not in ("application/pdf", "application/octet-stream"):
                    raise ValueError("Incorrect original PDF MIME")
                pdf = PdfReader(io.BytesIO(payload), strict=True)
                if len(pdf.pages) == 0:
                    raise ValueError("Empty decision PDF")
                page_count = len(pdf.pages)
                identity_text = pdf.pages[0].extract_text() or ""
            else:
                if mime not in ("text/html", "application/xhtml+xml"):
                    raise ValueError("Incorrect Gazette HTML MIME")
                identity_text = BeautifulSoup(payload, "html.parser").get_text(
                    " ", strip=True
                )
                page_count = None
            digest = hashlib.sha256(payload).hexdigest()
            expected = d.get("original_sha256")
            if expected is not None and digest != expected:
                raise ValueError("Pinned original differs from official bytes")
            suffix = ".pdf" if is_pdf else ".html"
            _atomic_bytes(output / "originals" / (digest + suffix), payload)
            records.append({
                "id": doc_id, "url": url, "sha256": digest,
                "bytes": len(payload), "mime": mime, "pdf_pages": page_count,
                "identity_text_extracted": d["number"] in identity_text,
                "original_sha_pinned": expected is not None,
                "original_bytes": True,
            })
        except Exception as exc:
            errors.append({"id": doc_id, "error": str(exc)})
    report = {
        "created_utc": datetime.now(UTC).isoformat(),
        "scope": "THREE_ADDITIONAL_OFFICIAL_DOCUMENTS_NOT_ALL_MEASURES",
        "fetched_originals": records, "errors": errors,
        "source_bytes_acquired": len(records) == 3 and not errors,
        "exhaustive_year_coverage_proven": False,
        "legal_approval": False,
        "payable_authorization": False,
    }
    output.mkdir(parents=True, exist_ok=True)
    (output / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8"
    )
    return report


def main() -> int:
    inventory = json.loads(
        Path("configs/p0_10_4_legal_inventory.json").read_text(encoding="utf-8")
    )
    result = collect_additions(inventory, Path("data/p0_10_4_additional_originals"))
    for row in result["fetched_originals"]:
        print(
            f"SOURCE_NEW id={row['id']} sha256={row['sha256']} "
            f"bytes={row['bytes']} mime={row['mime']} "
            f"pinned={row['original_sha_pinned']} "
            f"extractable_identity={row['identity_text_extracted']}",
            flush=True,
        )
    for err in result["errors"]:
        print(f"SOURCE_NEW_ERROR id={err['id']} error={err['error']}", flush=True)
    print(
        "ADDITIONAL_SOURCE_FETCH",
        "PASS" if result["source_bytes_acquired"] else "HOLD",
        "EXHAUSTIVE_YEAR_COVERAGE NOT_PROVEN", flush=True,
    )
    return 0 if result["source_bytes_acquired"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
