"""P0-8B read-only FastAPI PDF evidence response contract integration tests.

A synthetic 2030 page is used; no official future-year document or approved
rule is claimed. The API returns DRAFT warnings and no payment amount.
"""

from __future__ import annotations

import hashlib

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from tarim_destek_rag.api.main import app, get_db_session
from tarim_destek_rag.auto_updater.grounding_repository import stage_evidence
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.models import SourceModel

URL = "https://www.resmigazete.gov.tr/eskiler/2030/05/example.pdf"
QUOTE = "Synthetic official-source demonstration: this is NOT real legislation."


@pytest.fixture
def fixture_data(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((40, 96), QUOTE)
    raw = doc.tobytes()
    doc.close()
    sha = hashlib.sha256(raw).hexdigest()
    archive = tmp_path / "originals"
    archive.mkdir()
    (archive / (sha + ".pdf")).write_bytes(raw)
    monkeypatch.setenv("TARIM_RAG_UPDATE_ARCHIVE", str(tmp_path))
    with Session(engine) as session:
        session.add(SourceModel(
            source_id="SYNTH-2030", url=URL,
            title="Synthetic official legal test",
            authority="OFFICIAL_GAZETTE", content_type="PDF", active=True,
        ))
        session.commit()
        rec = stage_evidence(
            session, archive_root=tmp_path,
            source_id="SYNTH-2030", production_year=2030,
            sha256=sha, original_url=URL,
            page_number=1, exact_quote=QUOTE, article="TEST ARTICLE",
        )
        record_id = rec.id
        session.commit()

    def dependency():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = dependency
    try:
        with TestClient(app) as client:
            yield client, record_id, sha, archive
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        engine.dispose()


def test_grounding_evidence_id_returns_exact_original_page_and_quote(fixture_data):
    client, record_id, sha, _ = fixture_data
    reply = client.get(f"/api/v1/grounding/evidence/{record_id}", params={"year": 2030})
    assert reply.status_code == 200, reply.text
    data = reply.json()
    assert data["page_number"] == 1
    assert data["exact_quote"] == QUOTE
    assert data["original_pdf_sha256"] == sha
    assert data["article"] == "TEST ARTICLE"
    assert data["bounding_boxes"]
    assert data["legal_approval"] is False
    assert data["payable_amount"] is None
    assert data["status"] == "DRAFT_NEEDS_HUMAN_LEGAL_REVIEW"


def test_grounding_image_is_visibly_annotated_png_and_webp(fixture_data):
    client, record_id, sha, _ = fixture_data
    url = f"/api/v1/grounding/image/{record_id}/page/1"
    png = client.get(url, params={"year": 2030, "fmt": "png"})
    assert png.status_code == 200, png.text
    assert png.headers["content-type"] == "image/png"
    assert png.content[:8] == b"\x89PNG\r\n\x1a\n"
    assert png.headers["x-original-source-sha256"] == sha
    webp = client.get(url, params={"year": 2030, "fmt": "webp"})
    assert webp.status_code == 200, webp.text
    assert webp.headers["content-type"] == "image/webp"
    assert webp.content[:4] == b"RIFF"


def test_wrong_year_or_page_never_selects_different_document(fixture_data):
    client, record_id, _, _ = fixture_data
    assert client.get(
        f"/api/v1/grounding/evidence/{record_id}", params={"year": 2029}
    ).status_code == 404
    assert client.get(
        f"/api/v1/grounding/image/{record_id}/page/99", params={"year": 2030}
    ).status_code == 409


def test_tampered_original_closes_pdf_evidence_access(fixture_data):
    client, record_id, sha, archive = fixture_data
    (archive / (sha + ".pdf")).write_bytes(b"tampered source bytes")
    response = client.get(
        f"/api/v1/grounding/evidence/{record_id}", params={"year": 2030}
    )
    assert response.status_code == 409
