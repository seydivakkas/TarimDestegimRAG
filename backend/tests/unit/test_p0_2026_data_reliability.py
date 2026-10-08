"""P0 2026 katsayı ve kanıt güvenilirliği regresyon kontrolleri."""

from decimal import Decimal

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from frontend_pc.app import parse_irrigation_status
from tarim_destek_rag.citations.verifier import CitationVerifier
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.repository import SupportRepository
from tarim_destek_rag.explainer.template_explainer import CitationDetail
from tarim_destek_rag.models.farmer_parcel import FarmerProfile, IrrigationStatusEnum, Parcel
from tarim_destek_rag.models.source import AuthorityEnum, SourceDefinition
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.normalization.seed_data import seed_2026_support_data
from tarim_destek_rag.retrieval.hybrid import HybridRetriever
from tarim_destek_rag.retrieval.models import DocumentChunk
from tarim_destek_rag.rules.rules_impl import BasicSupportRule, WaterRestrictionRule
from tarim_destek_rag.scraper.registry import SourceRegistry


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        seed_2026_support_data(db)
        yield db
    engine.dispose()


@pytest.mark.parametrize(
    ("support_id", "crop", "expected"),
    [
        ("BASIC_SUPPORT_2026", "BUĞDAY", "477.10"),
        ("PLANNED_PRODUCTION_2026", "BUĞDAY", "477.10"),
        ("BASIC_SUPPORT_2026", "FINDIK", "550.50"),
        ("BASIC_SUPPORT_2026", "PAMUK", "825.75"),
        ("CERTIFIED_SEED_2026", "ARPA", "205.52"),
        ("CERTIFIED_SAPLING_2026", "FINDIK", "1835.00"),
        ("WATER_RESTRICTION_2026", "MERCİMEK", "293.60"),
    ],
)
def test_seed_2026_amended_unit_rates(session, support_id, crop, expected):
    amount = SupportRepository(session).get_amount(support_id, crop)
    assert amount is not None
    assert amount.unit_amount == Decimal(expected)
    assert amount.source_id == "TOB-2026-09-08"


@pytest.mark.parametrize(
    ("display", "expected"),
    [
        ("Sulu Tarım", "IRRIGATED"),
        ("Kuru Tarım", "DRY"),
        ("❓ Bilmiyorum / Emin Değilim", "UNKNOWN"),
        ("", "UNKNOWN"),
    ],
)
def test_irrigation_input_mapping(display, expected):
    assert parse_irrigation_status(display) == expected


def test_groundwater_extra_only_on_irrigated_land(session):
    farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    rule = WaterRestrictionRule()
    base = {"crop": "MERCİMEK", "area_da": Decimal("10"), "production_year": 2026}
    irrigated = rule.evaluate(farmer, Parcel(**base, irrigation=IrrigationStatusEnum.IRRIGATED), session)
    dry = rule.evaluate(farmer, Parcel(**base, irrigation=IrrigationStatusEnum.DRY), session)
    unknown = rule.evaluate(farmer, Parcel(**base, irrigation=IrrigationStatusEnum.UNKNOWN), session)
    assert irrigated.status == EligibilityStatusEnum.ELIGIBLE
    assert dry.status == EligibilityStatusEnum.NOT_ELIGIBLE
    assert unknown.status == EligibilityStatusEnum.REVIEW
    assert "irrigation" in unknown.missing_fields


def test_maize_is_not_granted_basic_support_in_restricted_basin(session):
    farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
    parcel = Parcel(crop="MISIR", area_da=Decimal("15.0"), production_year=2026)
    result = BasicSupportRule().evaluate(farmer, parcel, session)
    assert result.status == EligibilityStatusEnum.NOT_ELIGIBLE
    assert any("su kısıtı" in check for check in result.failed_checks)


def test_registered_source_is_not_accepted_as_passage_proof():
    registry = SourceRegistry()
    registry.register(
        SourceDefinition(
            id="RG-TEST",
            url="https://www.resmigazete.gov.tr",
            authority=AuthorityEnum.OFFICIAL_GAZETTE,
            title="Kayıtlı fakat pasajı kontrol edilmemiş kaynak",
            active=True,
        )
    )
    citation = CitationDetail(
        source_id="RG-TEST",
        title="Test",
        section="MADDE 1",
        year=2026,
        snippet="Gerçek kaynaktan doğrulanmamış özet",
    )
    result = CitationVerifier(registry).verify(citation)
    assert result.source_exists and result.source_active and result.year_valid
    assert result.is_valid is False
    assert result.status == "INSUFFICIENT_EVIDENCE"


def test_hybrid_reindex_is_idempotent_without_embedding_download():
    class DummyDense:
        def __init__(self):
            self.added = []

        def add_chunks(self, chunks):
            self.added.extend(chunks)

    class DummyBM25:
        def __init__(self):
            self._chunks = []

        def add_chunks(self, chunks):
            self._chunks.extend(chunks)

    dense, bm25 = DummyDense(), DummyBM25()
    hybrid = HybridRetriever(dense_store=dense, bm25_retriever=bm25)
    chunk = DocumentChunk(
        chunk_id="P0-ONE",
        source_id="P0",
        title="Kayıt",
        section="Bölüm",
        text="Örnek içerik",
        year=2026,
    )
    hybrid.add_chunks([chunk, chunk])
    hybrid.add_chunks([chunk])
    assert len(dense.added) == 1
    assert len(bm25._chunks) == 1
