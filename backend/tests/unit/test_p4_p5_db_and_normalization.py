from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.repository import (
    BasinRepository,
    SupportRepository,
    WaterRestrictionRepository,
)
from tarim_destek_rag.normalization.normalizer import (
    normalize_crop_name,
    normalize_turkish_currency,
    normalize_turkish_date,
)
from tarim_destek_rag.normalization.seed_data import seed_2026_support_data


def test_normalization_functions():
    """Tarih, para ve ürün adı dönüştürücüleri."""
    assert normalize_turkish_date("31 Temmuz 2026") == "2026-07-31"
    assert normalize_turkish_date("15.08.2026") == "2026-08-15"
    assert normalize_turkish_date("2026-01-01") == "2026-01-01"

    assert normalize_turkish_currency("465 TL") == Decimal("465")
    assert normalize_turkish_currency("1.250,50 TL") == Decimal("1250.50")

    assert normalize_crop_name("findik") == "FINDIK"
    assert normalize_crop_name("buğday") == "BUĞDAY"
    assert normalize_crop_name("mısır") == "MISIR"


def test_db_seeding_and_repositories():
    """SQLite in-memory veritabanında tohumlama ve repo sorgulamaları."""
    engine = create_engine("sqlite:///:memory:", echo=False)
    Base.metadata.create_all(bind=engine)

    with Session(engine) as session:
        seed_2026_support_data(session)

        # 1. Destek repository testi
        support_repo = SupportRepository(session)
        prog = support_repo.get_program("BASIC_SUPPORT_2026")
        assert prog is not None
        assert prog.name == "Temel Destek"

        amt = support_repo.get_legacy_amount("BASIC_SUPPORT_2026", "BUĞDAY")
        assert amt is not None
        assert amt.unit_amount == Decimal("465.00")
        assert support_repo.get_amount(
            "BASIC_SUPPORT_2026", "BUĞDAY",
            production_year=2026, province="KONYA", district="KARATAY",
        ) is None

        window = support_repo.get_window("BASIC_SUPPORT_2026", 2026)
        assert window is not None
        assert window.start_date == "2026-09-01"

        # 2. Havza repository testi
        basin_repo = BasinRepository(session)
        assert basin_repo.is_crop_supported_in_basin("KONYA", "KARATAY", "BUĞDAY", 2026) is True
        assert basin_repo.is_crop_supported_in_basin("KONYA", "KARATAY", "PAMUK", 2026) is False

        # 3. Su kısıtı repository testi
        water_repo = WaterRestrictionRepository(session)
        res = water_repo.get_restriction("KONYA", "KARATAY", 2026)
        assert res is not None
        assert res.is_water_restricted is True
        assert water_repo.get_restriction("İSTANBUL", "KADIKÖY", 2026) is None
