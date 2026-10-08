"""P0-9 master integration acceptance: no unsafe defaults across P0-6 to P0-8C.

These are architecture/contract tests run against the SAME checked-out main-
derived integration branch. Never require real institutional signing keys.
"""
from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tarim_destek_rag.api.main import app
from tarim_destek_rag.auto_updater.release import resolve_active_release
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.models import (
    DynamicRateModel,
    LegalApprovalAttestationModel,
    LegalApprovalRevocationModel,
    LegalAuditReceiptModel,
    LegalReleaseModel,
    ReviewedWaterRestrictionDistrictModel,
    ReviewedWaterRestrictionScopeModel,
    SentenceBoundingBoxModel,
    SourceDocumentModel,
)
from tarim_destek_rag.database.repository import WaterRestrictionRepository


def test_old_water_district_and_complete_new_water_scope_coexist_without_payout():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    required_tables = {
        "reviewed_water_restriction_districts",
        "reviewed_water_restriction_scopes",
        "legal_release_snapshots",
        "legal_audit_receipts",
        "source_documents",
        "sentence_bounding_boxes",
        "dynamic_rate_candidates",
    }
    assert required_tables <= set(Base.metadata.tables)
    with Session(engine) as session:
        assessment = WaterRestrictionRepository(session).assess_2026(
            "KONYA", "KARATAY", 2026,
        )
        assert assessment.outcome == "UNKNOWN"
        assert assessment.source_version_id is None
        release, _ = resolve_active_release(
            session, year=2030, when=date(2030, 4, 1),
            archive_root=__import__("pathlib").Path("data/legal_update_archive"),
        )
        assert release.status == "HOLD"
    engine.dispose()


def test_live_approval_mutation_endpoints_are_not_public():
    registered = {
        (method, route.path)
        for route in app.routes
        for method in getattr(route, "methods", [])
    }
    expected = {
        ("POST", "/admin/legal-updates/scan"),
        ("POST", "/admin/legal-updates/diff"),
        ("GET", "/api/v1/legal-releases/{year}"),
        ("GET", "/api/v1/grounding/evidence/{sentence_id}"),
        ("GET", "/api/v1/grounding/image/{sentence_id}/page/{page_number}"),
    }
    assert expected <= registered
    assert not any(
        "sign" in path or "approve-legal" in path or "apply-attestation" in path
        for method, path in registered if method in {"POST", "PUT", "PATCH"}
    )


def test_admin_diff_and_scan_require_key_even_if_year_is_specified(monkeypatch):
    monkeypatch.setenv("TARIM_RAG_ADMIN_API_KEY", "test-p0-9-only-admin")
    with TestClient(app) as client:
        scan = client.post("/admin/legal-updates/scan", params={"year": 2030})
        assert scan.status_code == 403
        diff = client.post("/admin/legal-updates/diff", json={
            "previous_year": 2029, "target_year": 2030,
            "previous_sentence_ids": [1], "current_sentence_ids": [2],
        })
        assert diff.status_code == 403


def test_pr8_modular_ui_kept_with_admin_pdf_controls():
    from frontend_pc.app import build_ui

    ui = build_ui()
    config = ui.get_config_file()
    tabs = [
        x.get("props", {}).get("label", "")
        for x in config["components"]
        if x.get("type", "").lower() == "tabitem"
    ]
    assert len(tabs) == 5
    assert any("Yönetim & Doğrulama" in tab for tab in tabs)
    buttons = [
        x.get("props", {}).get("value", "")
        for x in config["components"]
        if x.get("type", "").lower() == "button"
    ]
    assert "Resmî Mevzuatı Kontrol Et" in buttons
    assert "Sarı İşaretli Sayfayı Göster" in buttons


def test_imported_models_are_distinct_and_not_parallel_approval_backdoors():
    assert ReviewedWaterRestrictionDistrictModel.__tablename__ != ReviewedWaterRestrictionScopeModel.__tablename__
    assert LegalReleaseModel.__tablename__ == "legal_release_snapshots"
    assert LegalAuditReceiptModel.__tablename__ == "legal_audit_receipts"
    assert LegalApprovalAttestationModel.__tablename__ != LegalApprovalRevocationModel.__tablename__
    assert SourceDocumentModel.__tablename__ == "source_documents"
    assert SentenceBoundingBoxModel.__tablename__ == "sentence_bounding_boxes"
    assert DynamicRateModel.__tablename__ == "dynamic_rate_candidates"
