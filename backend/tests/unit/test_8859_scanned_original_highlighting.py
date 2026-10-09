"""End-to-end scanned official PDF evidence, not forged OCR/search-engine text."""
from __future__ import annotations

import hashlib
import io
import json
from pathlib import Path

import pytest
from tarim_destek_rag.citations.visual_pdf import (
    lookup_visual_pdf_citation,
    render_visual_pdf_copy,
)


@pytest.fixture
def scanned_pdf_source(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> dict:
    fitz = pytest.importorskip("pymupdf")
    pillow = pytest.importorskip("PIL.Image")
    from PIL import ImageDraw

    document = fitz.open()
    page = document.new_page(width=382.677, height=615.119)
    image = pillow.new("RGB", (800, 1260), "white")
    ImageDraw.Draw(image).text(
        (45, 325), "MADDE 2- (1) Bu resimden metin cikarilamaz",
        fill="black",
    )
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    page.insert_image(page.rect, stream=buffer.getvalue())
    source = document.tobytes()
    document.close()
    digest = hashlib.sha256(source).hexdigest()
    root = tmp_path / "gazette"
    archive = root / "originals"
    archive.mkdir(parents=True)
    pdf_path = archive / (digest + ".pdf")
    pdf_path.write_bytes(source)
    url = "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf"
    manifest = tmp_path / "official_manifest.json"
    manifest.write_text(json.dumps({"sources": [{
        "id": "RG_DECISION_8859", "url": url, "format": "pdf",
        "original_sha256": digest,
    }]}), encoding="utf-8")
    cfg = {
        "schema_version": 1,
        "records": [{
            "support_id": "BASIC_SUPPORT_2026",
            "source_id": "RG_DECISION_8859",
            "source_url": url,
            "source_sha256": digest,
            "source_type": "ORIGINAL_PDF_SCANNED_PAGE",
            "page_number": 1, "article": "MADDE 2", "paragraph": "1",
            "production_year": 2026,
            "exact_visible_text": (
                "MADDE 2- (1) Bitkisel üretimin desteklenmesi için"
                " Bakanlıkça belirlenen kayıt sistemine kayıtlı olma"
                " şartı aranır ve bu örnek sözler görüntüdedir."
            ),
            "highlight_rectangles_pdf_points": [
                [22, 147, 350, 157],
                [22, 158, 340, 169],
            ],
            "quote_evidence_status": "VISUAL_SOURCE_LOCATED_PENDING_SECOND_REVIEW",
            "title": "8859 Cumhurbaşkanı Kararı",
            "manual_visual_location_approved": False,
            "legal_provision_approved": False,
        }],
    }
    index = tmp_path / "visual_index.json"
    index.write_text(json.dumps(cfg), encoding="utf-8")
    monkeypatch.setenv("TARIM_RAG_UPDATE_ARCHIVE", str(root))
    monkeypatch.setenv("TARIM_RAG_ORIGINAL_SOURCE_MANIFEST", str(manifest))
    monkeypatch.setenv("TARIM_RAG_VISUAL_CLAUSE_INDEX", str(index))
    return {
        "root": root, "manifest": manifest,
        "index": index, "original": pdf_path,
        "original_bytes": source, "hash": digest, "cfg": cfg,
    }


def test_8859_real_review_record_points_to_original_page_two() -> None:
    record = json.loads(Path(
        "configs/p0_10_5_8859_visual_clause_index.json"
    ).read_text(encoding="utf-8"))["records"][0]
    assert record["source_sha256"] == (
        "89df0b6222edb4eddf3d5f588a4007061458adec8d518e3fbdb86b46ae5ba85f"
    )
    assert record["page_number"] == 2
    assert record["article"] == "MADDE 2"
    assert record["paragraph"] == "1"
    assert len(record["highlight_rectangles_pdf_points"]) == 3
    assert record["legal_provision_approved"] is False
    assert "kayıt sistemlerine kayıtlı olma şartı aranır" in record["exact_visible_text"]


def test_scanned_source_opens_original_copy_with_real_highlights(
    scanned_pdf_source: dict,
) -> None:
    fitz = pytest.importorskip("pymupdf")
    src = scanned_pdf_source
    citation = lookup_visual_pdf_citation("BASIC_SUPPORT_2026")
    assert citation is not None
    assert citation["source_sha256"] == src["hash"]
    assert citation["verification_status"] == "VISUAL_SOURCE_LOCATED_PENDING_SECOND_REVIEW"
    assert "highlight/visual/" + src["hash"] in citation["highlighted_pdf_url"]
    assert "#page=1" in citation["highlighted_pdf_url"]
    stamped = render_visual_pdf_copy(
        "BASIC_SUPPORT_2026", expected_sha256=src["hash"],
    )
    with fitz.open(stream=stamped, filetype="pdf") as modified:
        assert modified.page_count == 1
        assert modified[0].get_text().strip() == ""
        assert len(list(modified[0].annots())) == 2
    with fitz.open(stream=src["original_bytes"], filetype="pdf") as original:
        assert original[0].first_annot is None
    assert src["original"].read_bytes() == src["original_bytes"]


def test_original_pdf_sha_tamper_never_serves_highlight(
    scanned_pdf_source: dict,
) -> None:
    src = scanned_pdf_source
    src["original"].write_bytes(src["original_bytes"] + b"forged")
    assert lookup_visual_pdf_citation("BASIC_SUPPORT_2026") is None
    with pytest.raises(ValueError, match="Archived official original"):
        render_visual_pdf_copy(
            "BASIC_SUPPORT_2026", expected_sha256=src["hash"],
        )


@pytest.mark.parametrize("boxes", [
    [[-1, 3, 90, 80]],
    [[0, 0, 9999, 10000]],
    [[30, 35, 10, 20]],
    [[float("nan"), 25, 60, 100]],
])
def test_unreviewed_invalid_rectangle_cannot_become_a_source(
    scanned_pdf_source: dict, boxes: list,
) -> None:
    src = scanned_pdf_source
    src["cfg"]["records"][0]["highlight_rectangles_pdf_points"] = boxes
    src["index"].write_text(json.dumps(src["cfg"]), encoding="utf-8")
    assert lookup_visual_pdf_citation("BASIC_SUPPORT_2026") is None


def test_source_metadata_cannot_claim_independent_approval(
    scanned_pdf_source: dict,
) -> None:
    src = scanned_pdf_source
    src["cfg"]["records"][0]["manual_visual_location_approved"] = True
    src["index"].write_text(json.dumps(src["cfg"]), encoding="utf-8")
    assert lookup_visual_pdf_citation("BASIC_SUPPORT_2026") is None


def test_visual_endpoint_returns_marked_copy_not_replacement(
    scanned_pdf_source: dict,
) -> None:
    from fastapi.testclient import TestClient

    from tarim_destek_rag.api.main import app

    src = scanned_pdf_source
    with TestClient(app) as client:
        response = client.get(
            f"/evidence/highlight/visual/{src['hash']}",
            params={"support_id": "BASIC_SUPPORT_2026"},
        )
        assert response.status_code == 200
        assert response.headers["Content-Type"].startswith("application/pdf")
        assert response.headers["X-Original-Source-SHA256"] == src["hash"]
        assert response.headers["X-Legal-Evidence"] == (
            "VISUAL_SOURCE_LOCATED_PENDING_SECOND_REVIEW"
        )
        assert response.content != src["original_bytes"]
        assert src["original"].read_bytes() == src["original_bytes"]
        bad = client.get(
            "/evidence/highlight/visual/" + "0" * 64,
            params={"support_id": "BASIC_SUPPORT_2026"},
        )
        assert bad.status_code == 409
