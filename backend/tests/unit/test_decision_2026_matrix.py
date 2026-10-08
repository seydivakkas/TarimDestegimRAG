"""P0-3 decision matrix: every source-derived component remains in REVIEW without approval.

Unlike historical golden cases, this suite cannot silently turn demo seeds into
ELIGIBLE or 0 TL amounts.
"""

from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tarim_destek_rag.calculator.calculator import SupportCalculator
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.models import SupportProgramModel
from tarim_destek_rag.models.farmer_parcel import (
    FarmerProfile,
    IrrigationStatusEnum,
    Parcel,
)
from tarim_destek_rag.normalization.legal_components_2026 import (
    PROGRAMS,
    load_component_catalog,
    stage_component_rates,
)
from tarim_destek_rag.normalization.normalizer import EligibilityStatusEnum
from tarim_destek_rag.rules.orchestrator import DecisionOrchestrator


def test_all_56_2026_components_do_not_trigger_unapproved_eligibility_or_payment():
    data = load_component_catalog()
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        session.add_all([
            SupportProgramModel(id=p, name=p, year=2026, active=True)
            for p in sorted(PROGRAMS)
        ])
        session.flush()
        assert stage_component_rates(session, apply=True) == 56
        session.commit()

        farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=True)
        orch = DecisionOrchestrator()
        for crop in sorted({row["crop_name"] for row in data["components"]}):
            parcel = Parcel(
                crop=crop, area_da=Decimal("12.4"), production_year=2026,
                irrigation=IrrigationStatusEnum.IRRIGATED,
                seed_certificate_available=True,
                sapling_certificate_available=True,
                is_closed_orchard=True,
            )
            decisions = orch.evaluate_all(farmer, parcel, session)
            assert len(decisions) == 5, crop
            assert not any(x.status == EligibilityStatusEnum.ELIGIBLE for x in decisions), crop
            for decision in decisions:
                assert decision.status in (
                    EligibilityStatusEnum.REVIEW,
                    EligibilityStatusEnum.NOT_ELIGIBLE,
                )
                calc = SupportCalculator.calculate(decision, parcel.area_da, None)
                assert calc.estimated_amount is None, (crop, decision.support_id)
    engine.dispose()


def test_hard_denial_is_not_confused_with_missing_legal_price():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        farmer = FarmerProfile(province="KONYA", district="KARATAY", cks_status=False)
        parcel = Parcel(crop="BUĞDAY", area_da=Decimal("12.4"), production_year=2026)
        result = DecisionOrchestrator().evaluate_all(farmer, parcel, session)
        basic = next(x for x in result if x.support_id == "BASIC_SUPPORT_2026")
        assert basic.status == EligibilityStatusEnum.NOT_ELIGIBLE
        assert SupportCalculator.calculate(basic, parcel.area_da, None).estimated_amount is None
    engine.dispose()
