"""P0-8C integration tests for /api/v1/grounding/program/{program_key} endpoint.

Tests:
1. Valid lookup returns exact PDF evidence, bounding boxes, and image link.
2. Missing year or program returns 404.
"""

from __future__ import annotations

import hashlib
from datetime import date
from decimal import Decimal

import pymupdf
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool
from tarim_destek_rag.api.main import app, get_db_session
from tarim_destek_rag.auto_updater.grounding_repository import stage_evidence
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.models import DynamicRateModel, SourceModel

URL = "https://www.resmigazete.gov.tr/eskiler/2030/08/kanun.pdf"
QUOTE = "2030 Tarimsal Destekleme Kanunu Ornek Metni Madde 5."


@pytest.fixture
def program_grounding_app(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(engine)

    # Generate synthetic PDF with quote
    doc = pymupdf.open()
    page = doc.new_page(width=595, height=842)
    page.insert_text((50, 100), QUOTE)
    raw = doc.tobytes()
    doc.close()

    sha = hashlib.sha256(raw).hexdigest()
    archive = tmp_path / "originals"
    archive.mkdir()
    (archive / (sha + ".pdf")).write_bytes(raw)
    monkeypatch.setenv("TARIM_RAG_UPDATE_ARCHIVE", str(tmp_path))

    with Session(engine) as session:
        session.add(SourceModel(
            source_id="KANUN-2030", url=URL,
            title="2030 Destekleme Kanunu",
            authority="OFFICIAL_GAZETTE", content_type="PDF", active=True,
        ))
        session.commit()

        sentence_rec = stage_evidence(
            session, archive_root=tmp_path,
            source_id="KANUN-2030", production_year=2030,
            sha256=sha, original_url=URL,
            page_number=1, exact_quote=QUOTE, article="Madde 5",
        )
        session.commit()

        rate_rec = DynamicRateModel(
            program_key="BASIC_SUPPORT",
            crop_code="BUĞDAY",
            production_year=2030,
            province="*",
            district="*",
            base_coefficient=Decimal("540.00"),
            category_multiplier=Decimal("1.0000"),
            proposed_unit_amount=Decimal("540.00"),
            unit="TRY/da",
            effective_from=date(2030, 1, 1),
            effective_to=date(2030, 12, 31),
            source_sentence_id=sentence_rec.id,
            review_status="DRAFT",
        )
        session.add(rate_rec)
        session.commit()

    def dependency():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = dependency
    try:
        with TestClient(app) as client:
            yield client
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        engine.dispose()


def test_get_grounding_by_program_success(program_grounding_app):
    client = program_grounding_app
    resp = client.get("/api/v1/grounding/program/BASIC_SUPPORT", params={"year": 2030, "crop_code": "BUĞDAY"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "DRAFT_NEEDS_HUMAN_LEGAL_REVIEW"
    assert data["program_key"] == "BASIC_SUPPORT"
    assert data["crop_code"] == "BUĞDAY"
    assert data["production_year"] == 2030
    assert data["exact_quote"] == QUOTE
    assert data["page_number"] == 1
    assert data["proposed_unit_amount"] == "540.00"
    assert len(data["bounding_boxes"]) >= 1
    assert data["legal_approval"] is False
    assert data["payable_amount"] is None


def test_get_grounding_by_program_not_found(program_grounding_app):
    client = program_grounding_app
    # Wrong program key
    resp = client.get("/api/v1/grounding/program/NON_EXISTENT", params={"year": 2030})
    assert resp.status_code == 404

    # Wrong year
    resp2 = client.get("/api/v1/grounding/program/BASIC_SUPPORT", params={"year": 2029})
    assert resp2.status_code == 404
