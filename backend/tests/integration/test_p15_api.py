from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from tarim_destek_rag.api.main import app


@pytest.fixture(scope="module")
def client():
    """FastAPI lifespan'ini başlatan test istemcisi."""
    with TestClient(app) as c:
        yield c


def test_health_endpoint(client):
    """GET /health testi."""
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"


def test_supports_endpoint(client):
    """GET /supports testi."""
    response = client.get("/supports")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 5
    ids = [d["id"] for d in data]
    assert "BASIC_SUPPORT_2026" in ids


def test_sources_endpoint(client):
    """GET /sources testi."""
    response = client.get("/sources")
    assert response.status_code == 200
    data = response.json()
    assert len(data) >= 1
    assert data[0]["authority"] == "OFFICIAL_GAZETTE"


def test_eligibility_endpoint(client):
    """POST /eligibility testi."""
    payload = {
        "farmer": {
            "farmer_id": "FARMER-TEST",
            "province": "KONYA",
            "district": "KARATAY",
            "cks_status": True,
        },
        "parcel": {
            "parcel_id": "PARCEL-TEST",
            "farmer_id": "FARMER-TEST",
            "crop": "BUĞDAY",
            "area_da": 25.0,
            "production_year": 2026,
            "seed_certificate_available": True,
        },
    }
    response = client.post("/eligibility", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 5
    basic = next(d for d in data if d["support_id"] == "BASIC_SUPPORT_2026")
    assert basic["status"] == "REVIEW"
    assert "verified_support_rate" in basic["missing_fields"]


def test_calculate_endpoint(client):
    """POST /calculate testi."""
    payload = {
        "farmer": {
            "farmer_id": "FARMER-TEST",
            "province": "KONYA",
            "district": "KARATAY",
            "cks_status": True,
        },
        "parcel": {
            "parcel_id": "PARCEL-TEST",
            "farmer_id": "FARMER-TEST",
            "crop": "BUĞDAY",
            "area_da": 10.0,
            "production_year": 2026,
        },
    }
    response = client.post("/calculate", json=payload)
    assert response.status_code == 200
    data = response.json()
    basic_calc = next(d for d in data if d["support_id"] == "BASIC_SUPPORT_2026")
    assert basic_calc["estimated_amount"] is None
    assert basic_calc["status"] == "REVIEW"


def test_evaluate_full_endpoint(client):
    """POST /evaluate tam akış testi."""
    payload = {
        "farmer": {
            "province": "KONYA",
            "district": "KARATAY",
            "cks_status": True,
        },
        "parcel": {
            "crop": "BUĞDAY",
            "area_da": 10.0,
            "production_year": 2026,
            "seed_certificate_available": True,
        },
    }
    response = client.post("/evaluate", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "total_estimated_amount" in data
    assert data["total_estimated_amount"] is None
    assert all(c["estimated_amount"] is None for c in data["calculations"])
    assert len(data["explanations"]) == 5


def test_ask_endpoint(client):
    """POST /ask semantik soru sorma testi."""
    payload = {"question": "Temel destek başvuruları hangi tarihler arasında?", "top_k": 2}
    response = client.post("/ask", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert "summary_answer_tr" in data
    assert len(data["matched_chunks"]) > 0
