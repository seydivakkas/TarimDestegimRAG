"""Issue #6 Testleri: 5 Kullanıcı Görevi ve Ortak Değerlendirme Durumu (Shared State).

Gradio arayüzünün 5 ana kullanıcı görevine indirgendiğini, tek bir EvaluationResult
state'inin paylaşıldığını, gereksiz /evaluate çağrılarının önlendiğini ve geriye
dönük uyumluluğun korunduğunu doğrular.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import gradio as gr
import pytest
from fastapi.testclient import TestClient
from tarim_destek_rag.api.main import app

from frontend_pc.api_client import ApiClient
from frontend_pc.app import (
    build_ui,
    evaluate_farmer_parcel,
    generate_evaluation_report,
)
from frontend_pc.services.evaluation_service import (
    evaluate_for_ui,
)
from frontend_pc.state import EvaluationStateManager


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_build_ui_has_exactly_five_user_tasks():
    """Gradio bloklarında tam olarak 5 ana kullanıcı görevi (TabItem) olduğunu doğrular."""
    app_blocks = build_ui()
    assert app_blocks is not None

    # Bloklar içerisindeki TabItem bileşenlerini filtrele
    tab_items = [
        b for b in app_blocks.blocks.values()
        if isinstance(b, gr.TabItem)
    ]
    assert len(tab_items) == 5, f"Beklenen 5 sekme, bulunan: {len(tab_items)}"

    tab_labels = [t.label for t in tab_items]
    assert any("Çiftçi & Parsellerim" in lbl for lbl in tab_labels)
    assert any("Destek Analizi" in lbl for lbl in tab_labels)
    assert any("Mevzuat Asistanı" in lbl for lbl in tab_labels)
    assert any("Kaynaklar & Takvim" in lbl for lbl in tab_labels)
    assert any("Yönetim & Doğrulama" in lbl for lbl in tab_labels)


def test_evaluation_state_manager_caching():
    """EvaluationStateManager aynı girdiler için tekrar backend çağrısı yapmaz."""
    mock_api = MagicMock()
    mock_api.evaluate_full.return_value = {
        "status": "SUCCESS",
        "total_estimated_amount": 12500.0,
        "rules": [{"support_id": "BASE_SUPPORT", "status": "ELIGIBLE"}],
        "calculations": [{"support_id": "BASE_SUPPORT", "estimated_amount": 12500.0}],
    }

    state_mgr = EvaluationStateManager()
    farmer_data = {"province": "KONYA", "district": "KARATAY", "cks_status": True}
    parcel_data = {"crop": "BUĞDAY", "area_da": 25.0, "production_year": 2026}

    # 1. Çağrı: Önbellekte yok, backend çağrılır
    resp1, is_cached1 = state_mgr.get_or_evaluate(farmer_data, parcel_data, mock_api)
    assert is_cached1 is False
    assert mock_api.evaluate_full.call_count == 1
    assert resp1["total_estimated_amount"] == 12500.0

    # 2. Çağrı: Aynı girdiler, önbellekten dönülür (0 yeni API çağrısı)
    resp2, is_cached2 = state_mgr.get_or_evaluate(farmer_data, parcel_data, mock_api)
    assert is_cached2 is True
    assert mock_api.evaluate_full.call_count == 1  # Değişmedi!
    assert resp2 == resp1

    # 3. Çağrı: Alan değişti, yeni API çağrısı yapılır
    parcel_data_modified = {"crop": "BUĞDAY", "area_da": 50.0, "production_year": 2026}
    resp3, is_cached3 = state_mgr.get_or_evaluate(farmer_data, parcel_data_modified, mock_api)
    assert is_cached3 is False
    assert mock_api.evaluate_full.call_count == 2


def test_generate_report_uses_cached_state_without_backend_call():
    """Önceden hesaplanmış state verildiğinde generate_evaluation_report API çağrısı yapmaz."""
    mock_api = MagicMock()
    mock_cached_resp = {
        "status": "SUCCESS",
        "total_estimated_amount": 23850.0,
        "rules": [
            {
                "support_id": "BASE_SUPPORT",
                "support_name": "Temel Destek",
                "status": "ELIGIBLE",
            }
        ],
        "calculations": [
            {
                "support_id": "BASE_SUPPORT",
                "unit_amount": 465.0,
                "estimated_amount": 23850.0,
            }
        ],
        "explanations": [
            {
                "support_id": "BASE_SUPPORT",
                "summary_tr": "Temel destek şartları sağlandı.",
                "passed_checks": ["ÇKS kaydı aktif"],
            }
        ],
    }

    report_res = generate_evaluation_report(
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
        client=mock_api,
        cached_resp=mock_cached_resp,
    )

    # API'ye hiçbir evaluate_full çağrısı gitmediğini doğrula
    assert mock_api.evaluate_full.call_count == 0
    assert report_res["visible"] is True
    assert report_res["value"].endswith(".md")


def test_evaluate_for_ui_returns_shared_state_and_formatted_views(client):
    """evaluate_for_ui fonksiyonunun UI çıktılarını ve ortak state nesnesini ürettiğini doğrular."""
    test_api = ApiClient(base_url="", client=client)

    state_val, inline_html, kpi_html, cards_html, details_df, reasons_md, disclaimer_html = evaluate_for_ui(
        province="KONYA",
        district="KARATAY",
        cks_status="✅ Evet (ÇKS Kaydım Aktif)",
        age_group="Genç Çiftçi (< 41 Yaş)",
        gender="Erkek",
        crop="BUĞDAY",
        area_da=25.0,
        irrigation_type="Kuru Tarım",
        seed_cert="✅ Evet (Faturalı / Sertifikalı)",
        sapling_cert="❌ Hayır (Standart / Sertifikasız)",
        closed_orchard="Hayır (Münferit / Tarla)",
        client=test_api,
    )

    assert isinstance(state_val, dict)
    assert "total_estimated_amount" in state_val
    # P0-5 fail-closed kuralı: İncelemede olan destek varsa total_estimated_amount None (Hesaplanmadı) döner
    assert state_val["total_estimated_amount"] is None or float(state_val["total_estimated_amount"]) > 0
    assert "2026 Tarımsal Destek Ön Değerlendirmesi" in inline_html
    assert "Toplam Tahmini Hak Ediş" in kpi_html
    assert "support-card" in cards_html
    assert not details_df.empty
    assert "Kural Durum Kodları" in reasons_md
    assert "Yasal Uyarı" in disclaimer_html


def test_evaluate_farmer_parcel_backward_compatibility(client):
    """evaluate_farmer_parcel'in mevcut 6'lı tuple imzasını aynen koruduğunu doğrular."""
    test_api = ApiClient(base_url="", client=client)

    kpi, cards, df, reasons, discl, inline = evaluate_farmer_parcel(
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

    assert "Toplam Tahmini Hak Ediş" in kpi
    assert "support-card" in cards
    assert len(df) >= 5
    assert "MADDE" in reasons or "Kural Durum Kodları" in reasons
    assert "Yasal Uyarı" in discl
    assert "inline-summary-box" in inline
