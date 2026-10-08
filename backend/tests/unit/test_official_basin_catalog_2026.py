"""Committed nationwide 2026–27 official basin PDF DRAFT snapshot guards.

The 945 rows are extracted from the Ministry's 81-page PDF. These tests validate
coverage/provenance, not a human's signoff or farmer entitlement.
"""

import json
from pathlib import Path

import pytest

from tarim_destek_rag.normalization.basin_2026 import validate_basin_catalog


CATALOG = (
    Path(__file__).resolve().parents[3]
    / "configs" / "2026_2027_basin_crop_draft.json"
)


def test_2026_2027_official_ministry_basin_source_matches_full_945_districts():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    rows = validate_basin_catalog(data)
    assert data["production_years"] == [2026, 2027]
    assert data["district_count"] == 945
    assert data["province_count"] == 81
    assert data["page_count"] == 81
    assert data["original_pdf_sha256"] == (
        "60263e83a953659ecc4f581bcd1ef1a921cf397bc5b4469869852470473f0b21"
    )
    assert len(rows) == 945
    assert all(row["review_status"] == "DRAFT" for row in rows)
    assert all(row["complete_row_verified_by_human"] is False for row in rows)


def test_known_reference_rows_and_maize_drip_footnote_are_preserved():
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    rows = {(r["province"], r["district"]): r for r in data["districts"]}
    adana = rows[("ADANA", "ALADAĞ")]
    assert adana["source_page"] == 1
    assert "MISIR_DANE" in adana["crop_codes"]
    assert adana["starred_drip_maize_condition"] is False

    karatay = rows[("KONYA", "KARATAY")]
    assert karatay["source_page"] == 53
    assert karatay["starred_drip_maize_condition"] is True
    assert {"BUĞDAY", "ARPA", "MISIR_DANE", "SOĞAN_KURU"} <= set(karatay["crop_codes"])

    eskil = rows[("AKSARAY", "ESKİL")]
    assert eskil["starred_drip_maize_condition"] is True
    assert "MISIR_DANE" in eskil["crop_codes"]


def test_partial_or_forged_complete_review_is_not_allowed(tmp_path):
    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    data["districts"] = data["districts"][:100]
    data["district_count"] = 100
    data["province_count"] = len({row["province"] for row in data["districts"]})
    with pytest.raises(ValueError, match="Partial"):
        validate_basin_catalog(data)

    data = json.loads(CATALOG.read_text(encoding="utf-8"))
    data["districts"][0]["review_status"] = "VERIFIED"
    with pytest.raises(ValueError, match="Incomplete or unreviewed"):
        validate_basin_catalog(data)
