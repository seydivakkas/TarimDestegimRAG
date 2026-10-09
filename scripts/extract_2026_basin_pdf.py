"""Extract the official 2026–27 basin crop table for HUMAN REVIEW, not approval.

Fails on unknown crop labels, malformed table rows or missing provincial coverage.
Never writes repository/database state. CI stores JSON/PDF as review artifacts.
"""

from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse
from urllib.request import Request, urlopen

OFFICIAL_URL = (
    "https://www.tarimorman.gov.tr/BUGEM/Belgeler/Tar%C4%B1m%20Havzalar%C4%B1/"
    "2026%20Y%C4%B1l%C4%B1%20Planlamaya%20Konu%20Havza%20%C3%9Cr%C3%BCn"
    "%20Deseni%20Listesi.pdf"
)
MAX_BYTES = 20 * 1024 * 1024

CROP_CODES = {
    "Arpa": "ARPA",
    "Aspir": "ASPİR",
    "Ayçiçeği (Yağlık)": "AYÇİÇEĞİ_YAĞLIK",
    "Buğday": "BUĞDAY",
    "Fasulye (Kuru)": "FASULYE_KURU",
    "Kolza (Kanola)": "KANOLA",
    "Mercimek": "MERCİMEK",
    "Mısır (Dane)": "MISIR_DANE",
    "Nohut": "NOHUT",
    "Pamuk (Kütlü)": "PAMUK_KÜTLÜ",
    "Patates": "PATATES",
    "Soğan (Kuru)": "SOĞAN_KURU",
    "Soya": "SOYA",
    "Yem Bitkileri": "YEM_BITKILERI_GROUP",
}

def turkish_upper(value: str) -> str:
    return value.strip().replace("i", "İ").replace("ı", "I").upper()


def parse_table_rows(
    tables: list[list[list[str | None]]], page_number: int
) -> tuple[list[dict], list[str]]:
    """Return normalized district rows and review errors from one page."""
    result: list[dict] = []
    errors: list[str] = []
    for table in tables:
        for cells in table:
            if len(cells) < 2:
                continue
            basin = re.sub(r"\s+", " ", str(cells[0] or "")).strip()
            crops = re.sub(r"\s+", " ", " ".join(str(x or "") for x in cells[1:])).strip()
            if "HAVZA ADI" in basin.upper() or not basin:
                continue
            if "/" not in basin:
                # Table headers and notices must not become fictitious districts.
                continue
            province, district = basin.split("/", 1)
            starred = bool(re.search(r"\s*\*\s*$", district))
            district = re.sub(r"\s*\*\s*$", "", district).strip()
            if not province or not district:
                errors.append(f"page {page_number}: invalid basin {basin!r}")
                continue
            tokens = [re.sub(r"\s+", " ", item).strip() for item in crops.split(",")]
            unrecognized = [t for t in tokens if t not in CROP_CODES]
            if unrecognized:
                errors.append(
                    f"page {page_number} {basin}: unknown crop labels {unrecognized!r}"
                )
                continue
            if not tokens:
                errors.append(f"page {page_number} {basin}: no crops")
                continue
            codes = sorted({CROP_CODES[token] for token in tokens})
            result.append({
                "province": turkish_upper(province),
                "district": turkish_upper(district),
                "crop_codes": codes,
                "source_page": page_number,
                "starred_drip_maize_condition": starred,
                "review_status": "DRAFT",
                "complete_row_verified_by_human": False,
            })
    return result, errors


def extract_official_basin_pdf(pdf_bytes: bytes) -> dict:
    """Requires tabular text extraction; no guessing or OCR-based automatic approval."""
    import pdfplumber

    if not pdf_bytes.startswith(b"%PDF-"):
        raise ValueError("Official source is not a PDF")
    rows: list[dict] = []
    errors: list[str] = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as doc:
        if len(doc.pages) < 70:
            raise ValueError("Incomplete official 2026–27 basin list")
        for i, page in enumerate(doc.pages, start=1):
            tables = page.extract_tables(
                {"vertical_strategy": "lines", "horizontal_strategy": "lines"}
            )
            parsed, issues = parse_table_rows(tables, i)
            rows.extend(parsed)
            errors.extend(issues)
            if not parsed:
                errors.append(f"page {i}: no parsed districts")
        pages = len(doc.pages)

    keys = [(x["province"], x["district"]) for x in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("Duplicate province/district rows in official list")
    provinces = {x["province"] for x in rows}
    if len(rows) < 800 or len(provinces) < 75:
        raise ValueError(
            f"Incomplete coverage: {len(rows)} districts, {len(provinces)} provinces; "
            f"parse warnings: {errors[:6]}"
        )
    if errors:
        raise ValueError(f"Cannot claim complete extraction: {errors[:12]}")
    return {
        "schema_version": 1,
        "production_years": [2026, 2027],
        "source_url": OFFICIAL_URL,
        "original_pdf_sha256": hashlib.sha256(pdf_bytes).hexdigest(),
        "page_count": pages,
        "district_count": len(rows),
        "province_count": len(provinces),
        "approval": "DRAFT_REQUIRES_HUMAN_ROW_AND_FOOTNOTE_REVIEW",
        "conditions": [
            "Starred water-restricted districts require drip irrigation for grain maize.",
            "Crop presence in the planning list does not establish individual entitlement.",
            "Yem Bitkileri is a broad group, not permission for a specific crop subtype.",
        ],
        "districts": rows,
    }


def fetch_official_bytes() -> bytes:
    req = Request(OFFICIAL_URL, headers={"User-Agent": "TarimDestegimRAG/2026-Audit"})
    with urlopen(req, timeout=45) as response:
        final = urlparse(response.geturl())
        if final.scheme != "https" or final.hostname != "www.tarimorman.gov.tr":
            raise ValueError("Untrusted official PDF redirect")
        raw = response.read(MAX_BYTES + 1)
    if len(raw) > MAX_BYTES:
        raise ValueError("Official PDF exceeds maximum size")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="data/2026_basin_review")
    parser.add_argument(
        "--emit-log-bundle", action="store_true",
        help="Emit chunked PUBLIC draft JSON for an explicit, reviewed repository commit"
    )
    args = parser.parse_args()
    folder = Path(args.out_dir)
    folder.mkdir(parents=True, exist_ok=True)
    raw = fetch_official_bytes()
    (folder / "source_2026_basin.pdf").write_bytes(raw)
    manifest = {
        "retrieved_utc": datetime.now(UTC).isoformat(timespec="seconds"),
        "source_url": OFFICIAL_URL,
        "sha256": hashlib.sha256(raw).hexdigest(),
    }
    (folder / "source_manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    result = extract_official_basin_pdf(raw)
    (folder / "2026_2027_basin_crop_draft.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if args.emit_log_bundle:
        compact = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
        print("BASIN_DRAFT_JSON_BEGIN")
        for index in range(0, len(compact), 1500):
            print(f"BASIN_DRAFT_JSON_CHUNK:{index // 1500:05d}:{compact[index:index+1500]}")
        print("BASIN_DRAFT_JSON_END")
    print(
        f"PARSED_DRAFT: {result['district_count']} districts, "
        f"{result['province_count']} provinces, {result['page_count']} pages; "
        "NO AUTOMATIC APPROVAL"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
