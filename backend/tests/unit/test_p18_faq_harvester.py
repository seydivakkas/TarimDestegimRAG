"""TD-P18 Tarımsal Soru-Cevap Harvester ve Bilgi Tabanı Test Paketi.

Tüm internetten ve resmî portallardan derlenen tarımsal sorun ve çözümlerin
veritabanı modeli, repository, harvester motoru ve FastAPI uç noktalarını test eder.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

import uuid

from fastapi.testclient import TestClient
from tarim_destek_rag.api.main import app
from tarim_destek_rag.database.connection import SessionLocal
from tarim_destek_rag.database.faq_repository import FAQRepository
from tarim_destek_rag.database.models import AgriculturalFAQModel
from tarim_destek_rag.scraper.faq_harvester import (
    CURATED_AGRICULTURAL_FAQS,
    AgriculturalFAQHarvester,
)


def test_curated_faqs_integrity():
    """Küratörlü tarımsal SSS veri setinin temel bütünlüğü ve alan kontrolleri."""
    assert len(CURATED_AGRICULTURAL_FAQS) >= 20
    categories = {faq["category"] for faq in CURATED_AGRICULTURAL_FAQS}
    assert any("Bitki Sağlığı" in c for c in categories)
    assert any("Toprak" in c for c in categories)
    assert any("TARSİM" in c for c in categories)
    assert any("Kırsal Kalkınma" in c for c in categories)

    for faq in CURATED_AGRICULTURAL_FAQS:
        assert faq["id"].strip()
        assert faq["category"].strip()
        assert faq["question"].strip()
        assert faq["answer"].strip()
        assert faq["legal_citation"].strip()
        assert len(faq["keywords"]) > 0


def test_faq_repository_crud():
    """FAQRepository CRUD ve arama filtreleme işlevlerinin doğrulanması."""
    import json

    from tarim_destek_rag.database.connection import init_db
    init_db()

    session = SessionLocal()
    try:
        repo = FAQRepository(session)
        test_id = f"test_faq_{uuid.uuid4().hex[:8]}"
        faq = AgriculturalFAQModel(
            id=test_id,
            category="Test Kategori",
            sub_category="Test Alt",
            question="Deneme tarımsal soru?",
            answer="Deneme tarımsal cevap.",
            legal_citation="Test Kanunu Madde 1",
            source_name="Test Kaynak",
            source_url="https://test.tarim.gov.tr",
            keywords=json.dumps(["deneme", "test"]),
            verified=True,
            created_at="2026-10-07T12:00:00Z",
        )

        # 1. Upsert
        inserted = repo.upsert(faq)
        assert inserted.id == test_id

        # 2. Get By ID
        fetched = repo.get_by_id(test_id)
        assert fetched is not None
        assert fetched.question == "Deneme tarımsal soru?"

        # 3. List Faqs with Category filter
        cat_list = repo.list_faqs(category="Test Kategori")
        assert any(f.id == test_id for f in cat_list)

        # 4. List Faqs with Search filter
        search_list = repo.list_faqs(search_query="tarımsal soru")
        assert any(f.id == test_id for f in search_list)

        # 5. Categories
        cats = repo.get_categories()
        assert "Test Kategori" in cats

        # 6. Stats
        stats = repo.get_stats()
        assert stats["total_count"] >= 1
        assert stats["verified_count"] >= 1
        assert "Test Kategori" in stats["category_counts"]
    finally:
        session.close()


def test_agricultural_faq_harvester():
    """Harvester sınıfının tohumlama ve DocumentChunk dönüştürme yetenekleri."""
    session = SessionLocal()
    try:
        harvester = AgriculturalFAQHarvester(session)
        seed_count = harvester.seed_initial_knowledge()
        assert seed_count >= len(CURATED_AGRICULTURAL_FAQS)

        # Chunk üretimi
        chunks = harvester.export_as_document_chunks()
        assert len(chunks) >= len(CURATED_AGRICULTURAL_FAQS)
        assert all(c.chunk_id.startswith("chunk_") for c in chunks)
        assert all("soru" in c.text.lower() or "cevap" in c.text.lower() for c in chunks)
    finally:
        session.close()



def test_api_faq_endpoints(monkeypatch):
    """FastAPI /faqs, /faqs/stats ve /faqs/harvest uç noktalarının testi."""
    with TestClient(app) as client:
        # 1. GET /faqs
        resp = client.get("/faqs")
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)
        assert len(data) >= 1

        # 2. GET /faqs with filter
        resp_filter = client.get("/faqs?search=pas")
        assert resp_filter.status_code == 200
        filtered_data = resp_filter.json()
        assert isinstance(filtered_data, list)

        # 3. GET /faqs/stats
        resp_stats = client.get("/faqs/stats")
        assert resp_stats.status_code == 200
        stats = resp_stats.json()
        assert "total_count" in stats
        assert "verified_count" in stats
        assert "category_counts" in stats

        # 4. Yönetici yazma uç noktası varsayılan olarak erişime kapalı.
        monkeypatch.delenv("TARIM_RAG_ADMIN_API_KEY", raising=False)
        assert client.post("/faqs/harvest").status_code == 503

        # Yanlış/eksik anahtar erişim sağlamaz.
        monkeypatch.setenv("TARIM_RAG_ADMIN_API_KEY", "regression-test-secret")
        assert client.post("/faqs/harvest").status_code == 403
        assert client.post(
            "/faqs/harvest", headers={"X-Admin-Key": "invalid"}
        ).status_code == 403

        resp_harvest = client.post(
            "/faqs/harvest", headers={"X-Admin-Key": "regression-test-secret"}
        )
        assert resp_harvest.status_code == 200
        harvest_res = resp_harvest.json()
        assert harvest_res["status"] == "SUCCESS"
        assert "harvested_count" in harvest_res
        assert "indexed_chunks" in harvest_res

