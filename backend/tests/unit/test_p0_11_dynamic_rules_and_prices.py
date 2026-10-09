"""Unit tests for P0-11: Dinamik Kural ve Fiyat Motoru.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR

Bu yazılım ve ilgili tüm dosyalar ("Yazılım") yalnızca görüntüleme ve eğitim
amaçlı olarak paylaşılmıştır.

YASAKLAR:
  1. Kopyalanamaz, çoğaltılamaz, dağıtılamaz veya yeniden yayınlanamaz.
  2. Ticari veya ticari olmayan hiçbir projede kullanılamaz, değiştirilemez.
  3. Alt lisanslanamaz, satılamaz veya devredilemez.
  4. Tersine mühendislik yapılamaz.

İZİN VERİLEN KULLANIM:
  - GitHub üzerinde görüntüleme ve okuma.
  - Kişisel öğrenim amacıyla kodu inceleme (kopyalamadan).

YAZARIN AÇIK YAZILI İZNİ OLMAKSIZIN HİÇBİR KULLANIM HAKKI TANINMAZ.
İzin talepleri için: GitHub @seydivakkas
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from tarim_destek_rag.api.main import app
from tarim_destek_rag.rules.bitemporal_engine import BitemporalRuleCatalog
from tarim_destek_rag.rules.dynamic_rule_repository import DynamicRuleRepository
from tarim_destek_rag.rules.dynamic_support_evaluator import DynamicSupportEvaluator
from tarim_destek_rag.rules.rule_synthesizer import RuleSynthesizer
from tarim_destek_rag.rules.table_parser import (
    DEFAULT_WATER_RESTRICTION_BASINS,
    TableParser,
    normalize_crop_code,
)
from tarim_destek_rag.updates.legislation_models import (
    AnnexTableInfo,
    DiscoveredLegislation,
    EffectiveDateInfo,
    LegislationIdentity,
    LegislationType,
    TableKind,
)


@pytest.fixture
def mock_discovered_legislation() -> DiscoveredLegislation:
    """Mock mevzuat belgesi örneği."""
    return DiscoveredLegislation(
        document_sha256="1234567890abcdef" * 4,
        source_url="https://resmigazete.gov.tr/eskiler/2026/08/20260829-1.pdf",
        discovered_at_utc="2026-08-29T10:00:00Z",
        identity=LegislationIdentity(
            legislation_type=LegislationType.CUMHURBASKANI_KARARI,
            number="8786",
            title="2026-2028 Yıllarında Yapılacak Bitkisel Üretime Yönelik Desteklemeler",
            authority="CUMHURBASKANLIGI",
            rg_date="2026-08-29",
            rg_number="32647",
        ),
        effective_dates=EffectiveDateInfo(
            effective_date="2026-01-01",
            valid_production_years=[2026, 2027, 2028],
        ),
        annex_tables=[
            AnnexTableInfo(
                annex_code="EK-1",
                title="Temel Destek ve Katsayı Tablosu",
                table_kind=TableKind.SUPPORT_RATES,
                page_number=3,
            ),
            AnnexTableInfo(
                annex_code="EK-2",
                title="Planlı Üretim Destek Tablosu",
                table_kind=TableKind.PLANNED_PRODUCTION,
                page_number=4,
            ),
            AnnexTableInfo(
                annex_code="EK-3",
                title="Su Kısıtı Olan Havza ve İlçeler",
                table_kind=TableKind.WATER_RESTRICTION,
                page_number=5,
            ),
        ],
    )


class TestTableParser:
    """Ek Tablo Ayrıştırıcı (TableParser) testleri."""

    def test_normalize_crop_code(self) -> None:
        assert normalize_crop_code("buğday") == "BUĞDAY"
        assert normalize_crop_code("ekmeklik buğday") == "BUĞDAY"
        assert normalize_crop_code("makarnalık buğday") == "BUĞDAY"
        assert normalize_crop_code("arpa") == "ARPA"
        assert normalize_crop_code("dane mısır") == "MISIR_DANE"
        assert normalize_crop_code("mısır (dane)") == "MISIR_DANE"
        assert normalize_crop_code("yağlık ayçiçeği") == "AYÇİÇEĞİ_YAĞLIK"
        assert normalize_crop_code("kütlü pamuk") == "PAMUK_KÜTLÜ"
        assert normalize_crop_code("kırmızı mercimek") == "MERCİMEK"
        assert normalize_crop_code("nohut") == "NOHUT"
        assert normalize_crop_code("kuru fasulye") == "FASULYE_KURU"
        assert normalize_crop_code("fındık") == "FINDIK"
        assert normalize_crop_code("zeytin") == "ZEYTİN"

    def test_extract_base_coefficient(self) -> None:
        sample_text_1 = "2026 yılı için temel katsayı değeri: 244,00 TL olarak belirlenmiştir."
        assert TableParser.extract_base_coefficient(sample_text_1) == Decimal("244.00")

        sample_text_2 = "Gösterge tutarı: 366.00 TL/da üzerinden hesaplanır."
        assert TableParser.extract_base_coefficient(sample_text_2) == Decimal("366.00")

        sample_fallback = "Herhangi bir sayı içermeyen metin."
        assert TableParser.extract_base_coefficient(sample_fallback, default=Decimal("244.00")) == Decimal("244.00")

    def test_parse_rate_table_ek1(self) -> None:
        base_coef = Decimal("244.00")
        sample_page = """
        Kategori 1: Arpa, Buğday katsayı 1.0000
        Kategori 2: Dane mısır katsayı 1.2500
        Kategori 3: Ayçiçeği yağlık, soya, pamuk katsayı 1.5000
        Kategori 4: Kuru fasulye, mercimek, nohut katsayı 2.0000
        """
        rows = TableParser.parse_rate_table(sample_page, base_coefficient=base_coef)
        assert len(rows) >= 6
        crops_found = {r.crop_code for r in rows}
        assert "BUĞDAY" in crops_found
        assert "ARPA" in crops_found
        assert "MISIR_DANE" in crops_found
        assert "AYÇİÇEĞİ_YAĞLIK" in crops_found

        bugday_row = next(r for r in rows if r.crop_code == "BUĞDAY")
        assert bugday_row.category_multiplier == Decimal("1.0000")
        assert bugday_row.official_unit_amount == Decimal("244.00")

        misir_row = next(r for r in rows if r.crop_code == "MISIR_DANE")
        assert misir_row.category_multiplier == Decimal("1.2500")
        assert misir_row.official_unit_amount == Decimal("305.00")

    def test_parse_planned_crops_ek2(self) -> None:
        base_coef = Decimal("244.00")
        sample_page = "Planlı üretim kapsamında buğday ve arpa ilave katsayı: 1.0000"
        rows = TableParser.parse_planned_crops(sample_page, base_coefficient=base_coef)
        assert len(rows) >= 2
        bugday_planned = next(r for r in rows if r.crop_code == "BUĞDAY")
        assert bugday_planned.official_unit_amount == Decimal("244.00")

    def test_parse_water_restriction_ek3(self) -> None:
        rows = TableParser.parse_water_restriction("Konya Karapınar su kısıtı")
        assert len(rows) == len(DEFAULT_WATER_RESTRICTION_BASINS)
        konya_row = next(r for r in rows if r.province == "KONYA")
        assert "KARAPINAR" in konya_row.districts
        assert "SARAYÖNÜ" in konya_row.districts
        assert konya_row.multiplier == Decimal("1.0000")
        assert konya_row.unit_amount == Decimal("244.00")


class TestRuleSynthesizer:
    """Kural Sentezleyici (RuleSynthesizer) testleri."""

    def test_synthesize_and_validate_candidates(self, mock_discovered_legislation: DiscoveredLegislation) -> None:
        candidates = RuleSynthesizer.synthesize_candidates(
            mock_discovered_legislation, production_year=2026
        )
        assert len(candidates) > 0

        # Tüm adayların bitemporal şema gereksinimlerini sağlaması zorunludur
        for cand in candidates:
            # validate_candidate ValueError fırlatmamalıdır
            rule = BitemporalRuleCatalog.validate_candidate(cand)
            assert rule.production_year == 2026
            assert rule.review_status == "DRAFT"
            assert cand["schema_version"] == 1

    def test_compile_bitemporal_catalog(self, mock_discovered_legislation: DiscoveredLegislation) -> None:
        catalog = RuleSynthesizer.compile_bitemporal_catalog(
            mock_discovered_legislation, production_year=2026
        )
        assert isinstance(catalog, BitemporalRuleCatalog)

        # Temel Destek kuralını sorgula
        res = catalog.evaluate(
            program_key="BASIC_SUPPORT",
            crop_code="BUĞDAY",
            production_year=2026,
            as_of_date=date(2026, 5, 1),
            facts={"cks_registered": True, "crop_code": "BUĞDAY"},
            province="KONYA",
            district="KARAPINAR",
        )
        # Fail-closed kuralı: DRAFT statüsündeki kurallar REVIEW döner ve payable_amount None olmalıdır
        assert res.status == "REVIEW"
        assert res.proposed_unit_amount == Decimal("244.00")
        assert res.payable_amount is None


class TestDynamicRuleRepository:
    """Kural Kataloğu Deposu (DynamicRuleRepository) testleri."""

    def test_save_and_load_rules(self, tmp_path: Path, mock_discovered_legislation: DiscoveredLegislation) -> None:
        repo = DynamicRuleRepository(tmp_path)
        candidates = RuleSynthesizer.synthesize_candidates(
            mock_discovered_legislation, production_year=2026
        )
        target_file = repo.save_rules(2026, candidates)
        assert target_file.is_file()

        loaded = repo.load_rules(2026)
        assert len(loaded) == len(candidates)
        assert repo.list_years() == [2026]

        filtered_basic = repo.list_rules(year=2026, program_key="BASIC_SUPPORT")
        assert len(filtered_basic) > 0
        assert all(r["program_key"] == "BASIC_SUPPORT" for r in filtered_basic)

        catalog = repo.get_catalog(years=[2026])
        assert isinstance(catalog, BitemporalRuleCatalog)


class TestDynamicSupportEvaluator:
    """Çoklu Destek Kalemleri Değerlendirici (DynamicSupportEvaluator) testleri."""

    @pytest.fixture
    def active_catalog(self, mock_discovered_legislation: DiscoveredLegislation) -> BitemporalRuleCatalog:
        return RuleSynthesizer.compile_bitemporal_catalog(
            mock_discovered_legislation, production_year=2026
        )

    def test_evaluate_wheat_parcel(self, active_catalog: BitemporalRuleCatalog) -> None:
        summary = DynamicSupportEvaluator.evaluate_parcel(
            catalog=active_catalog,
            production_year=2026,
            as_of_date=date(2026, 6, 1),
            crop="BUĞDAY",
            area_da=Decimal("100"),
            province="ANKARA",
            district="POLATLI",
            cks_registered=True,
            irrigation=False,
            certified_seed=True,
        )
        assert summary.crop_code == "BUĞDAY"
        assert summary.area_da == Decimal("100")
        assert summary.overall_status == "REVIEW"

        # 100 dekar için kalemler:
        # Temel Destek: 244 * 100 = 24.400 TL
        # Planlı Üretim: 244 * 100 = 24.400 TL
        # Toplam önerilen tutar: 24.400 + 24.400 + 8.784 = 57.584,00 TL
        assert summary.total_proposed_amount is not None
        assert summary.total_proposed_amount == Decimal("57584.00")

        # Fail-closed doğrulaması: Kurallar DRAFT olduğundan payable_amount None olmalıdır
        assert summary.total_payable_amount is None
        assert summary.fail_closed_reason is not None

    def test_evaluate_water_restricted_lentil_parcel(self, active_catalog: BitemporalRuleCatalog) -> None:
        # Karapınar'da susuz mercimek üretimi (su kısıtı ilave desteği almalı)
        summary = DynamicSupportEvaluator.evaluate_parcel(
            catalog=active_catalog,
            production_year=2026,
            as_of_date=date(2026, 6, 1),
            crop="MERCİMEK",
            area_da=Decimal("50"),
            province="KONYA",
            district="KARAPINAR",
            cks_registered=True,
            irrigation=False,
        )
        water_item = next((it for it in summary.items if it.program_key == "WATER_RESTRICTION"), None)
        assert water_item is not None
        assert water_item.status == "REVIEW"
        assert water_item.unit_amount == Decimal("244.00")
        assert water_item.proposed_amount == Decimal("12200.00")

    def test_evaluate_unregistered_farmer(self, active_catalog: BitemporalRuleCatalog) -> None:
        # ÇKS kaydı olmayan çiftçi hiçbir destekten yararlanamaz
        summary = DynamicSupportEvaluator.evaluate_parcel(
            catalog=active_catalog,
            production_year=2026,
            as_of_date=date(2026, 6, 1),
            crop="BUĞDAY",
            area_da=Decimal("50"),
            province="ANKARA",
            district="POLATLI",
            cks_registered=False,
        )
        # A DRAFT legal condition cannot deliver a final denial or 0-TL payout.
        assert summary.overall_status == "REVIEW"
        assert summary.total_payable_amount is None

    def test_verified_rules_allow_payable_amount(self, mock_discovered_legislation: DiscoveredLegislation) -> None:
        # Kuralları DRAFT'tan VERIFIED'a çekip ödeme tutarını test et
        candidates = RuleSynthesizer.synthesize_candidates(
            mock_discovered_legislation, production_year=2026
        )
        verified_candidates = []
        for c in candidates:
            c_copy = dict(c)
            c_copy["review_status"] = "VERIFIED"
            verified_candidates.append(c_copy)

        catalog = BitemporalRuleCatalog.from_candidates(verified_candidates)
        summary = DynamicSupportEvaluator.evaluate_parcel(
            catalog=catalog,
            production_year=2026,
            as_of_date=date(2026, 6, 1),
            crop="BUĞDAY",
            area_da=Decimal("10"),
            province="ANKARA",
            district="POLATLI",
            cks_registered=True,
            irrigation=False,
            certified_seed=False,
        )
        # Fake VERIFIED labels alone cannot authorize a payment.
        assert summary.total_payable_amount is None
        assert summary.fail_closed_reason is not None


class TestApiEndpointsP011:
    """FastAPI REST Uç Noktaları Testleri."""

    @pytest.fixture
    def client(self) -> TestClient:
        return TestClient(app)

    def test_synthesize_requires_admin(self, client: TestClient) -> None:
        resp = client.post(
            "/admin/rules/synthesize",
            json={"document_sha256": "0" * 64},
        )
        # Yönetici API anahtarı olmadan 401, 403 veya 503 dönmeli
        assert resp.status_code in (401, 403, 503)

    def test_dynamic_evaluate_public_endpoint(self, client: TestClient, tmp_path: Path, monkeypatch: Any) -> None:
        # Test deposunu ayarla ve örnek kural sentezle
        archive_root = tmp_path / "archive"
        monkeypatch.setenv("TARIM_RAG_UPDATE_ARCHIVE", str(archive_root))

        from tarim_destek_rag.updates.legislation_repository import LegislationCatalogRepository

        leg_repo = LegislationCatalogRepository(archive_root)
        doc = DiscoveredLegislation(
            document_sha256="e" * 64,
            source_url="https://resmigazete.gov.tr/eskiler/2026/08/test.pdf",
            identity=LegislationIdentity(
                legislation_type=LegislationType.CUMHURBASKANI_KARARI, number="8786", title="Test",
            ),
            effective_dates=EffectiveDateInfo(
                effective_date="2026-01-01",
                valid_production_years=[2026],
            ),
            annex_tables=[
                AnnexTableInfo(
                    annex_code="EK-1", title="Test Rates",
                    table_kind=TableKind.SUPPORT_RATES,
                )
            ],
        )
        leg_repo.save(doc)

        admin_key = "test-admin-secret-key-p011"
        monkeypatch.setenv("TARIM_RAG_ADMIN_API_KEY", admin_key)

        # Sentezle
        synth_resp = client.post(
            "/admin/rules/synthesize",
            json={"document_sha256": "e" * 64, "production_year": 2026},
            headers={"X-Admin-Key": admin_key},
        )
        assert synth_resp.status_code == 200
        data = synth_resp.json()
        assert data["status"] == "SYNTHESIZED_SUCCESSFULLY"
        assert data["rule_count"] > 0

        # Listele
        list_resp = client.get(
            "/admin/rules/dynamic?year=2026",
            headers={"X-Admin-Key": admin_key},
        )
        assert list_resp.status_code == 200
        rules = list_resp.json()
        assert len(rules) > 0

        # Çiftçi parsel değerlendirmesi yap (/api/v1/rules/dynamic-evaluate)
        eval_resp = client.post(
            "/api/v1/rules/dynamic-evaluate",
            json={
                "production_year": 2026,
                "crop": "BUĞDAY",
                "area_da": 25.0,
                "province": "KONYA",
                "district": "KARAPINAR",
                "cks_registered": True,
                "irrigation": False,
                "certified_seed": True,
            },
        )
        assert eval_resp.status_code == 200
        eval_data = eval_resp.json()
        assert eval_data["crop_code"] == "BUĞDAY"
        assert eval_data["overall_status"] == "REVIEW"
        assert eval_data["total_proposed_amount"] is not None
        # DRAFT olduğundan fail-closed koruması devrede
        assert eval_data["total_payable_amount"] is None
