"""Original Ministry PDF: pinpoint selected province/district and crop, never invent rows."""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
from urllib.parse import urlencode

from tarim_destek_rag.normalization.basin_2026 import (
    BASIN_SOURCE_URL,
    PINNED_BASIN_PDF_SHA256,
    validate_basin_catalog,
)

LABELS = {
    "ARPA": "Arpa", "ASPİR": "Aspir", "AYÇİÇEĞİ_YAĞLIK": "Ayçiçeği (Yağlık)",
    "BUĞDAY": "Buğday", "FASULYE_KURU": "Fasulye (Kuru)",
    "KANOLA": "Kolza (Kanola)", "MERCİMEK": "Mercimek",
    "MISIR_DANE": "Mısır (Dane)", "NOHUT": "Nohut",
    "PAMUK_KÜTLÜ": "Pamuk (Kütlü)", "PATATES": "Patates",
    "SOĞAN_KURU": "Soğan (Kuru)", "SOYA": "Soya",
    "YEM_BITKILERI_GROUP": "Yem Bitkileri",
}
ALIASES = {
    "KURU FASULYE": "FASULYE_KURU", "MISIR (DANE)": "MISIR_DANE",
    "AYÇİÇEĞİ (YAĞLIK)": "AYÇİÇEĞİ_YAĞLIK",
    "PAMUK (KÜTLÜ)": "PAMUK_KÜTLÜ",
    "YEM BİTKİLERİ": "YEM_BITKILERI_GROUP",
}
MAX_BYTES = 20 * 1024 * 1024


def _upper(value: str) -> str:
    return value.strip().replace("i", "İ").replace("ı", "I").upper()


def _paths() -> tuple[Path, Path]:
    return (
        Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive")),
        Path(os.getenv("TARIM_RAG_BASIN_CATALOG", "configs/2026_2027_basin_crop_draft.json")),
    )


def locate_basin_crop(
    province: str, district: str, crop: str, production_year: int,
    *, root: Path | None = None, catalog_path: Path | None = None,
) -> tuple[dict, bytes]:
    """Require unique district row and exact crop token inside its own cell."""
    import pymupdf

    if production_year not in (2026, 2027):
        raise ValueError("Selected year has no matching 2026-27 ministry list")
    p, d = _upper(province), _upper(district)
    code = ALIASES.get(_upper(crop), _upper(crop))
    if code not in LABELS:
        raise ValueError("Unknown or legally ambiguous crop subtype")
    default_root, default_catalog = _paths()
    data = json.loads((catalog_path or default_catalog).read_text(encoding="utf-8"))
    catalog_rows = validate_basin_catalog(data, require_national_coverage=False)
    if data["source_url"] != BASIN_SOURCE_URL or data["original_pdf_sha256"] != PINNED_BASIN_PDF_SHA256:
        raise ValueError("Official source URL/hash does not match pinned catalog")
    candidates = [r for r in catalog_rows if r["province"] == p and r["district"] == d]
    if len(candidates) != 1:
        raise ValueError("District not uniquely present in the official draft catalog")
    entry = candidates[0]
    if code not in entry["crop_codes"]:
        raise ValueError("Product is not in this district source row; do not fabricate a highlight")
    raw = ((root or default_root) / "originals" / (PINNED_BASIN_PDF_SHA256 + ".pdf")).read_bytes()
    if (len(raw) > MAX_BYTES or not raw.startswith(b"%PDF-")
        or hashlib.sha256(raw).hexdigest() != PINNED_BASIN_PDF_SHA256):
        raise ValueError("Original source bytes absent, too large or changed")

    page_no = entry["source_page"]
    with pymupdf.open(stream=raw, filetype="pdf") as pdf:
        if pdf.page_count != data["page_count"] or not 1 <= page_no <= pdf.page_count:
            raise ValueError("PDF page count diverges from indexed source")
        page = pdf[page_no - 1]
        found = []
        for table in page.find_tables().tables:
            for trow, cells in zip(table.rows, table.extract(), strict=True):
                if len(cells) < 2 or len(trow.cells) < 2 or not all(trow.cells[:2]):
                    continue
                left = _upper(" ".join((cells[0] or "").split()).rstrip("*"))
                if left == p + "/" + d and LABELS[code] in (cells[1] or ""):
                    found.append((trow, cells[0].strip().rstrip('*').strip()))
        if len(found) != 1:
            raise ValueError("Unique province/district/product row not found in original PDF")
        source_row, source_district = found[0]
        left_rect = pymupdf.Rect(source_row.cells[0])
        right_rect = pymupdf.Rect(source_row.cells[1])
        district_rects = [
            rect for rect in page.search_for(source_district)
            if left_rect.contains(rect)
        ]
        # Titles are exact official crop subtype labels, not generic synonyms.
        crop_rects = [
            rect for rect in page.search_for(LABELS[code]) if right_rect.contains(rect)
        ]
        if len(district_rects) != 1 or len(crop_rects) != 1:
            raise ValueError("Exact district or crop token coordinates are ambiguous")
        left, right = list(district_rects[0]), list(crop_rects[0])
    result = {
        "source_id": "TOB-2026-2027-BASIN-DESENI",
        "source_url": BASIN_SOURCE_URL, "source_sha256": PINNED_BASIN_PDF_SHA256,
        "page_number": page_no, "province": p, "district": d,
        "crop_code": code, "crop_label": LABELS[code], "production_year": production_year,
        "district_rect": left, "crop_rect": right,
        "verification_status": "ORIGINAL_PDF_ROW_AND_CROP_LOCATED_DRAFT_REVIEW",
        "eligible": None, "approved_rate": None,
    }
    result["highlighted_pdf_url"] = (
        "/evidence/highlight/basin/" + PINNED_BASIN_PDF_SHA256 + "?"
        + urlencode({"province": p, "district": d, "crop": code,
                     "production_year": production_year}) + f"#page={page_no}"
    )
    return result, raw


def lookup_basin_crop_evidence(province: str, district: str, crop: str,
                               production_year: int) -> dict | None:
    try:
        proof, _ = locate_basin_crop(province, district, crop, production_year)
        return proof
    except (ValueError, TypeError, KeyError, OSError, RuntimeError, ImportError):
        return None


def highlight_basin_crop_copy(province: str, district: str, crop: str,
                               production_year: int, *, expected_sha256: str) -> bytes:
    """Marks only the two actual tokens in a separate copy of the original PDF."""
    import pymupdf

    proof, raw = locate_basin_crop(province, district, crop, production_year)
    if proof["source_sha256"] != expected_sha256:
        raise ValueError("Original PDF digest mismatch")
    with pymupdf.open(stream=raw, filetype="pdf") as pdf:
        page = pdf[proof["page_number"] - 1]
        for rect, color in ((proof["district_rect"], (.18, .66, 1)),
                            (proof["crop_rect"], (1, .82, 0))):
            annot = page.add_rect_annot(pymupdf.Rect(rect))
            annot.set_colors(stroke=color, fill=color)
            annot.set_opacity(.3)
            annot.update()
        return pdf.tobytes(garbage=4, deflate=True)


def install_basin_original() -> dict:
    """Explicit one-time setup; never download sources during a farmer request."""
    import httpx

    root, _ = _paths()
    digest = PINNED_BASIN_PDF_SHA256
    file = root / "originals" / (digest + ".pdf")
    if file.exists():
        body = file.read_bytes()
        if hashlib.sha256(body).hexdigest() != digest:
            raise ValueError("Original source copy has changed")
        return {"sha256": digest, "bytes": len(body), "already_present": True}
    with httpx.Client(timeout=55, follow_redirects=False, trust_env=False) as client:
        with client.stream("GET", BASIN_SOURCE_URL, headers={"Accept-Encoding": "identity"}) as r:
            if r.status_code != 200 or str(r.url) != BASIN_SOURCE_URL:
                raise ValueError("Official original source could not be downloaded")
            if "pdf" not in r.headers.get("Content-Type", "").lower():
                raise ValueError("Official source returned a non-PDF document")
            parts, count = [], 0
            for chunk in r.iter_raw():
                count += len(chunk)
                if count > MAX_BYTES:
                    raise ValueError("Original PDF exceeds maximum source size")
                parts.append(chunk)
    raw = b"".join(parts)
    if hashlib.sha256(raw).hexdigest() != digest:
        raise ValueError("Downloaded source does not match reviewed SHA-256")
    file.parent.mkdir(parents=True, exist_ok=True)
    file.write_bytes(raw)
    return {"sha256": digest, "bytes": len(raw), "already_present": False}


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--install", action="store_true", required=True)
    parser.parse_args()
    print(json.dumps(install_basin_original(), indent=2))
