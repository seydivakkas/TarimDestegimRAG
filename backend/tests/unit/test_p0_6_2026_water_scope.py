"""2026/2025 amendment-safe water restriction scope tests.

Synthetic signatures prove code behavior, not real-government legal approval.
"""
import json
from datetime import UTC, datetime
from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.models import (
    ReviewedWaterRestrictionScopeModel,
    SourceModel,
    SourceVersionModel,
)
from tarim_destek_rag.database.repository import WaterRestrictionRepository
from tarim_destek_rag.models.farmer_parcel import FarmerProfile, IrrigationStatusEnum, Parcel
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.normalization.water_2026 import (
    AMENDMENT_ID,
    AMENDMENT_SHA256,
    AMENDMENT_URL,
    CATALOG,
    PINNED_DISTRICTS,
    PRIMARY_ID,
    PRIMARY_SHA256,
    PRIMARY_URL,
    load_water_catalog,
    stage_water_scope,
)
from tarim_destek_rag.rules.orchestrator import DecisionOrchestrator

from backend.tests.legal_approval_testkit import sign_subject


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        yield s
    engine.dispose()


def synthetic_scope(session, *, reviewed=True):
    sources = [
        SourceModel(
            source_id=PRIMARY_ID, url=PRIMARY_URL,
            authority="MINISTRY_OF_AGRICULTURE", title="Test referenced 2024/39",
            content_type="PDF", active=True,
        ),
        SourceModel(
            source_id=AMENDMENT_ID, url=AMENDMENT_URL,
            authority="OFFICIAL_GAZETTE", title="Test referenced 2025/42",
            content_type="HTML", active=True,
        ),
    ]
    session.add_all(sources)
    session.flush()
    versions = []
    for i, source in enumerate(sources):
        version = SourceVersionModel(
            source_id=source.source_id,
            content_hash=PRIMARY_SHA256 if i == 0 else AMENDMENT_SHA256,
            version=1, detected_at="2026-10-08T00:00:00+00:00",
            superseded=False, effective_from="2026-01-01", effective_to="2026-12-31",
        )
        session.add(version)
        versions.append(version)
    session.flush()
    scope = ReviewedWaterRestrictionScopeModel(
        production_year=2026,
        district_keys_json=json.dumps(sorted(PINNED_DISTRICTS), ensure_ascii=False),
        source_version_id=versions[0].id,
        amendment_source_version_id=versions[1].id,
        review_status="VERIFIED" if reviewed else "DRAFT",
        coverage_complete=reviewed,
        reviewed_by="SYNTHETIC_REVIEW" if reviewed else None,
        reviewed_at=datetime.now(UTC) if reviewed else None,
        review_reference="SYNTHETIC_NO_LEGAL_AUTHORITY" if reviewed else None,
    )
    session.add(scope)
    session.commit()
    return scope


def test_source_legal_52_is_explicit_2026_draft():
    data = load_water_catalog()
    assert data["district_count"] == 52
    assert data["province_count"] == 11
    assert len(PINNED_DISTRICTS) == 52
    assert data["exception_policies"]["2026_2024_39_ART_6_3_C"].startswith("REPEALED")
    assert data["exception_policies"]["2025_ALREADY_BEGUN_APPLICATIONS"] == "GRANDFATHER_PREVIOUS_2025_RULES_ONLY"
    assert "HATAY/KIRIKHAN" not in PINNED_DISTRICTS
    assert "MARDİN/NUSAYBİN" not in PINNED_DISTRICTS
    assert "KONYA/YALIHÜYÜK" not in PINNED_DISTRICTS
    assert "KONYA/KARATAY" in PINNED_DISTRICTS
    assert stage_water_scope(None) == 52


@pytest.mark.parametrize("tamper", [
    lambda d: d["districts"].append(dict(d["districts"][0])),
    lambda d: d["districts"][0].update(district="KIRIKHAN"),
    lambda d: d["districts"][0].update(review_status="VERIFIED"),
    lambda d: d["legal_basis"][1].update(effective_from="2027-01-01"),
    lambda d: d["exception_policies"].update({"2026_2024_39_ART_6_3_C": "DRIP_EXCEPTION_ACTIVE"}),
    lambda d: d["constraints"].update(coverage_complete=True),
    lambda d: d["legal_basis"][1].update(content_sha256="f" * 64),
])
def test_source_tampering_is_rejected(tmp_path, tamper):
    d = json.loads(CATALOG.read_text(encoding="utf-8"))
    tamper(d)
    p = tmp_path / "tampered.json"
    p.write_text(json.dumps(d, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(ValueError):
        load_water_catalog(p)


def test_draft_and_seed_cannot_grant_or_deny_water_scope(session, monkeypatch):
    synthetic_scope(session, reviewed=False)
    assessment = WaterRestrictionRepository(session).assess_2026("KONYA", "KARATAY", 2026)
    assert assessment.outcome == "UNKNOWN"
    assert WaterRestrictionRepository(session).assess_2026(
        "HATAY", "KIRIKHAN", 2026
    ).outcome == "UNKNOWN"


def test_complete_double_signed_national_scope_has_positive_and_negative(session, monkeypatch):
    scope = synthetic_scope(session)
    assert WaterRestrictionRepository(session).assess_2026(
        "KONYA", "KARATAY", 2026
    ).outcome == "UNKNOWN"
    sign_subject(session, scope, monkeypatch)
    repo = WaterRestrictionRepository(session)
    assert repo.assess_2026("KONYA", "KARATAY", 2026).outcome == "RESTRICTED"
    for province, district in (
        ("HATAY", "KIRIKHAN"), ("HATAY", "HASSA"),
        ("HATAY", "PAYAS"), ("MARDİN", "NUSAYBİN"),
        ("KONYA", "YALIHÜYÜK"),
    ):
        assert repo.assess_2026(province, district, 2026).outcome == "NOT_RESTRICTED"
    assert repo.assess_2026("KONYA", "KARATAY", 2025).outcome == "UNKNOWN"
    assert repo.assess_2026("KONYA", "KARATAY", 2027).outcome == "UNKNOWN"


@pytest.mark.parametrize("crop,drip", [
    ("MISIR_DANE", True), ("MISIR_DANE", False), ("MISIR_DANE", None),
    ("PATATES", None),
])
def test_2026_maize_potato_deny_all_five_supports_even_with_drip(
    session, monkeypatch, crop, drip,
):
    sign_subject(session, synthetic_scope(session), monkeypatch)
    farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    parcel = Parcel(
        crop=crop, area_da=Decimal("12.4"), production_year=2026,
        irrigation=IrrigationStatusEnum.IRRIGATED, drip_irrigation=drip,
    )
    results = DecisionOrchestrator().evaluate_all(farmer, parcel, session)
    assert len(results) == 5
    for r in results:
        assert r.status == EligibilityStatusEnum.NOT_ELIGIBLE
        assert any("2025/42" in reason for reason in r.failed_checks)


def test_outside_signed_scope_does_not_automatically_pay(session, monkeypatch):
    sign_subject(session, synthetic_scope(session), monkeypatch)
    farmer = FarmerProfile(province="HATAY", district="KIRIKHAN", cks_status=True)
    parcel = Parcel(crop="PATATES", area_da=Decimal("8"), production_year=2026)
    results = DecisionOrchestrator().evaluate_all(farmer, parcel, session)
    assert all(r.status != EligibilityStatusEnum.ELIGIBLE for r in results)
    assert all("verified_support_rate" in r.missing_fields for r in results)


def test_unsigned_sources_or_amendment_changes_reject_scope(session, monkeypatch):
    scope = synthetic_scope(session)
    sign_subject(session, scope, monkeypatch)
    repo = WaterRestrictionRepository(session)
    assert repo.assess_2026("KONYA", "KARATAY", 2026).outcome == "RESTRICTED"
    scope.amendment_source_version.content_hash = "a" * 64
    session.commit()
    assert repo.assess_2026("KONYA", "KARATAY", 2026).outcome == "UNKNOWN"


def test_reread_requires_valid_original_pdf_and_amendment(session, tmp_path):
    pdf = tmp_path / "2024.pdf"
    amendment = tmp_path / "2025.htm"
    with pytest.raises(ValueError, match="Explicit original PDF"):
        stage_water_scope(session, apply=True)
    pdf.write_bytes(b"not-a-pdf")
    amendment.write_bytes(b"2025/42 MADDE 16")
    with pytest.raises(ValueError, match="Original legal source"):
        stage_water_scope(
            session, apply=True, original_pdf_path=pdf, amendment_html_path=amendment
        )
