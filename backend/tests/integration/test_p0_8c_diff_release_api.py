"""API never mislabels 2029/2030 draft legal differences as enacted law."""

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


@pytest.fixture
def app_fixture(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool
    )
    Base.metadata.create_all(engine)
    (tmp_path / "originals").mkdir()
    monkeypatch.setenv("TARIM_RAG_ADMIN_API_KEY", "fake-admin-key-for-ci-only")
    monkeypatch.setenv("TARIM_RAG_UPDATE_ARCHIVE", str(tmp_path))
    records = []
    with Session(engine) as session:
        for year, amt in ((2029, 100), (2030, 125)):
            text = f"Synthetic legal unit amount for this program is {amt},00 TL/da."
            file = pymupdf.open()
            page = file.new_page(width=595, height=842)
            page.insert_text((25, 110), text, fontsize=10)
            raw = file.tobytes()
            file.close()
            sha = hashlib.sha256(raw).hexdigest()
            (tmp_path / "originals" / f"{sha}.pdf").write_bytes(raw)
            url = f"https://www.resmigazete.gov.tr/eskiler/{year}/01/example-{year}.pdf"
            source = f"SYNTHETIC-RG-{year}"
            session.add(SourceModel(
                source_id=source, title="Synthetic regulatory clause",
                url=url, authority="OFFICIAL_GAZETTE", content_type="PDF", active=True,
            ))
            session.flush()
            sentence = stage_evidence(
                session, archive_root=tmp_path, source_id=source,
                production_year=year, sha256=sha, original_url=url,
                page_number=1, exact_quote=text, article="Madde 6",
            )
            records.append(sentence.id)
        session.commit()

    def db_session():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db_session] = db_session
    try:
        with TestClient(app) as client:
            yield client, records
    finally:
        app.dependency_overrides.pop(get_db_session, None)
        engine.dispose()


def payload(ids):
    return {
        "previous_year": 2029, "target_year": 2030,
        "previous_sentence_ids": [ids[0]], "current_sentence_ids": [ids[1]],
    }


def test_admin_year_diff_is_exactly_sourced_and_review_only(app_fixture):
    client, ids = app_fixture
    response = client.post(
        "/admin/legal-updates/diff",
        headers={"X-Admin-Key": "fake-admin-key-for-ci-only"},
        json=payload(ids),
    )
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["summary"]["TEXT_CHANGED"] == 1
    assert result["changes"][0]["numeric_change_needs_review"] is True
    assert result["changes"][0]["current"]["evidence_id"] == ids[1]
    assert result["changes"][0]["repeal_effect_confirmed"] is False
    assert result["legal_status"] == "REVIEW_REQUIRED"
    assert result["publication_activated"] is False


def test_no_admin_can_request_legal_review_diff(app_fixture):
    client, ids = app_fixture
    response = client.post("/admin/legal-updates/diff", json=payload(ids))
    assert response.status_code == 403


def test_cross_year_evidence_swap_cannot_be_considered_real_change(app_fixture):
    client, ids = app_fixture
    swapped = payload(ids)
    swapped["previous_sentence_ids"], swapped["current_sentence_ids"] = (
        swapped["current_sentence_ids"], swapped["previous_sentence_ids"]
    )
    response = client.post(
        "/admin/legal-updates/diff",
        headers={"X-Admin-Key": "fake-admin-key-for-ci-only"},
        json=swapped,
    )
    assert response.status_code == 409
    assert "another" in response.text.lower() or "outside" in response.text.lower()


def test_unsigned_2030_release_status_has_no_payable_amount(app_fixture):
    client, _ = app_fixture
    response = client.get(
        "/api/v1/legal-releases/2030", params={"as_of": "2030-04-01"}
    )
    assert response.status_code == 200, response.text
    info = response.json()
    assert info["status"] == "HOLD"
    assert info["farmer_eligibility_verified"] is False
    assert info["payable_amount"] is None
