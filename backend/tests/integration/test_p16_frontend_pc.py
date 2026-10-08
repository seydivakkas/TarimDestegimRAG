"""TarımDestekRAG PC Frontend Entegrasyon Testleri.

FastAPI arka uç servisi ile Gradio arayüz bileşenlerinin
ve api_client katmanının doğrulanmasını kapsar.
"""

import pytest
from fastapi.testclient import TestClient
from tarim_destek_rag.api.main import app

from frontend_pc.api_client import ApiClient
from frontend_pc.app import (
    build_ui,
    evaluate_farmer_parcel,
    format_currency,
    generate_evaluation_report,
    parse_irrigation_status,
    load_benchmark_data,
)


@pytest.fixture(scope="module")
def client():
    """FastAPI test istemcisi (lifespan ile)."""
    with TestClient(app) as c:
        yield c


def test_api_client_with_testclient(client):
    """ApiClient sınıfının FastAPI test istemcisi üzerinden uçtan uca çalışması."""
    api = ApiClient(base_url="", client=client)

    # 1. Health
    h = api.check_health()
    assert h["status"] == "ok"
    assert "TarımDestekRAG" in h["service"]

    # 2. Supports
    supports = api.get_supports()
    assert len(supports) >= 5

    # 3. Sources
    sources = api.get_sources()
    assert len(sources) >= 1

    # 4. Evaluate
    farmer = {
        "farmer_id": "F-01",
        "province": "KONYA",
        "district": "KARATAY",
        "cks_status": True,
    }
    parcel = {
        "parcel_id": "P-01",
        "farmer_id": "F-01",
        "crop": "BUĞDAY",
        "area_da": 25.0,
        "production_year": 2026,
        "seed_certificate_available": True,
    }
    eval_res = api.evaluate_full(farmer, parcel)
    assert "rules" in eval_res
    assert eval_res["total_estimated_amount"] is None
    assert all(c["estimated_amount"] is None for c in eval_res["calculations"])

    # 5. Ask
    ask_res = api.ask("Konya buğday desteği", top_k=2)
    assert "summary_answer_tr" in ask_res
    assert len(ask_res["matched_chunks"]) > 0


def test_irrigation_selection_matches_parcel_enum():
    assert parse_irrigation_status("Sulu Tarım") == "IRRIGATED"
    assert parse_irrigation_status("Kuru Tarım") == "DRY"
    assert parse_irrigation_status("❓ Bilmiyorum / Emin Değilim") == "UNKNOWN"


def test_format_currency():
    """Para birimi biçimlendirici testi."""
    assert "1.000,50 ₺" in format_currency(1000.5)
    assert "0,00 ₺" in format_currency(0)
    assert format_currency(None) == "Hesaplanmadı"


def test_load_benchmark_data():
    """Vakaların DataFrame olarak yüklenmesi testi."""
    df = load_benchmark_data()
    assert not df.empty
    assert len(df) >= 50
    assert "Vaka ID" in df.columns
    assert "Hedef Destek" in df.columns


def test_evaluate_farmer_parcel_function(client):
    """Arayüzün evaluate_farmer_parcel fonksiyonu testi."""
    test_api = ApiClient(base_url="", client=client)

    kpi_html, cards_html, details_df, reasons_md, disclaimer_html, inline_html = evaluate_farmer_parcel(
        province="KONYA",
        district="KARATAY",
        cks_status=True,
        age_group="Genç Çiftçi (< 41 Yaş)",
        gender="Erkek",
        crop="BUĞDAY",
        area_da=25.0,
        irrigation_type="Kuru Tarım",
        seed_cert=True,
        sapling_cert=False,
        closed_orchard=False,
        client=test_api,
    )

    assert "Hesaplanabilen Tahmini Toplam" in kpi_html
    assert "Hesaplanmadı" in kpi_html
    assert "support-card" in cards_html
    assert not details_df.empty
    assert len(details_df) == 5
    assert "Kural Durum Kodları" in reasons_md
    assert "Yasal Uyarı" in disclaimer_html
    assert "inline-summary-box" in inline_html


def test_build_ui():
    """Gradio UI bloklarının hatasız derlenmesi testi."""
    app_blocks = build_ui()
    assert app_blocks is not None


def test_generate_evaluation_report(client):
    """Resmî ön değerlendirme raporu dosyasının üretilmesi testi."""
    test_api = ApiClient(base_url="", client=client)
    res = generate_evaluation_report(
        province="KONYA",
        district="KARATAY",
        cks_status=True,
        age_group="Genç Çiftçi (< 41 Yaş)",
        gender="Erkek",
        crop="BUĞDAY",
        area_da=25.0,
        irrigation_type="Kuru Tarım",
        seed_cert=True,
        sapling_cert=False,
        closed_orchard=False,
        client=test_api,
    )
    assert res is not None
    assert "value" in res
    assert res["visible"] is True
    assert res["value"].endswith(".md")
    from pathlib import Path
    document = Path(res["value"]).read_text(encoding="utf-8")
    assert "Bağımsız Yazılım Raporu" in document
    assert "resmî bir belge değildir" in document
    assert "# T.C. TARIM VE ORMAN BAKANLIĞI" not in document


def test_evaluate_farmer_parcel_with_unknown_options(client):
    """'Bilmiyorum / Emin Değilim' seçiminin REVIEW durumunu ve eksik alanları üretmesi testi."""
    test_api = ApiClient(base_url="", client=client)

    kpi_html, cards_html, details_df, reasons_md, disclaimer_html, inline_html = evaluate_farmer_parcel(
        province="KONYA",
        district="KARATAY",
        cks_status="❓ Bilmiyorum / Emin Değilim",
        age_group="Standart (41+ Yaş)",
        gender="Erkek",
        crop="BUĞDAY",
        area_da=25.0,
        irrigation_type="❓ Bilmiyorum / Emin Değilim",
        seed_cert="❓ Bilmiyorum / Emin Değilim",
        sapling_cert="❌ Hayır (Standart / Sertifikasız)",
        closed_orchard="Hayır (Münferit / Tarla)",
        client=test_api,
    )

    assert "İnceleme" in kpi_html
    assert "badge-review" in inline_html
    assert "Eksik" in reasons_md or "cks_status" in reasons_md


def test_turkey_provinces_turkish_alphabet_sorting():
    """81 ilin Türkçe alfabe kurallarına göre A'dan Z'ye sıralı olduğunu doğrular."""
    from frontend_pc.geo_data import TURKEY_DISTRICTS, TURKEY_PROVINCES

    assert len(TURKEY_PROVINCES) == 81
    assert len(TURKEY_DISTRICTS) == 81

    # Başlangıç ve bitiş kontrolü
    assert TURKEY_PROVINCES[0] == "ADANA"
    assert TURKEY_PROVINCES[-1] == "ZONGULDAK"

    # Ç harfinin C ile D arasında olduğunu doğrula
    assert TURKEY_PROVINCES.index("BURSA") < TURKEY_PROVINCES.index("ÇANAKKALE")
    assert TURKEY_PROVINCES.index("ÇANAKKALE") < TURKEY_PROVINCES.index("ÇANKIRI")
    assert TURKEY_PROVINCES.index("ÇANKIRI") < TURKEY_PROVINCES.index("ÇORUM")
    assert TURKEY_PROVINCES.index("ÇORUM") < TURKEY_PROVINCES.index("DENİZLİ")

    # I ve İ harflerinin H ile K arasında olduğunu doğrula
    assert TURKEY_PROVINCES.index("HATAY") < TURKEY_PROVINCES.index("IĞDIR")
    assert TURKEY_PROVINCES.index("IĞDIR") < TURKEY_PROVINCES.index("ISPARTA")
    assert TURKEY_PROVINCES.index("ISPARTA") < TURKEY_PROVINCES.index("İSTANBUL")
    assert TURKEY_PROVINCES.index("İSTANBUL") < TURKEY_PROVINCES.index("İZMİR")
    assert TURKEY_PROVINCES.index("İZMİR") < TURKEY_PROVINCES.index("KAHRAMANMARAŞ")

    # Ş harfinin S ile T arasında olduğunu doğrula
    assert TURKEY_PROVINCES.index("SİVAS") < TURKEY_PROVINCES.index("ŞANLIURFA")
    assert TURKEY_PROVINCES.index("ŞANLIURFA") < TURKEY_PROVINCES.index("ŞIRNAK")
    assert TURKEY_PROVINCES.index("ŞIRNAK") < TURKEY_PROVINCES.index("TEKİRDAĞ")

