"""Çiftçi ve Parsel Hak Ediş Değerlendirme Servisi."""

from __future__ import annotations

import logging
import time
import uuid
from pathlib import Path
from typing import Any

import gradio as gr
import pandas as pd

from frontend_pc.api_client import ApiClient
from frontend_pc.formatters import (
    generate_report_markdown,
    parse_irrigation_status,
    parse_tri_state,
    render_details_dataframe,
    render_disclaimer_html,
    render_inline_summary_html,
    render_kpi_html,
    render_reasons_markdown,
    render_support_cards_html,
)
from frontend_pc.state import EvaluationStateManager, global_eval_state

logger = logging.getLogger("frontend_pc.services.evaluation")


def build_farmer_and_parcel_dicts(
    province: str,
    district: str,
    cks_status: str | bool | None,
    age_group: str,
    gender: str,
    crop: str,
    area_da: float,
    irrigation_type: str,
    seed_cert: str | bool | None,
    sapling_cert: str | bool | None,
    closed_orchard: str | bool | None,
    farmer_id: str = "FARMER-DEMO-001",
    parcel_id: str = "PARCEL-DEMO-001",
) -> tuple[dict[str, Any], dict[str, Any]]:
    """Girdileri FastAPI Pydantic şemasına uygun sözlüklere dönüştürür."""
    parsed_cks = parse_tri_state(cks_status)
    parsed_seed = parse_tri_state(seed_cert)
    parsed_sapling = parse_tri_state(sapling_cert)
    parsed_orchard = parse_tri_state(closed_orchard)

    farmer_data = {
        "farmer_id": farmer_id,
        "province": province.strip().upper(),
        "district": district.strip().upper(),
        "cks_status": parsed_cks,
        "age_group": "<41" if "Genç" in age_group else "STANDARD",
        "gender": "KADIN" if "Kadın" in gender else "ERKEK",
    }

    parcel_data = {
        "parcel_id": parcel_id,
        "farmer_id": farmer_id,
        "crop": crop.strip().upper(),
        "area_da": float(area_da),
        "production_year": 2026,
        "irrigation": parse_irrigation_status(irrigation_type),
        "seed_certificate_available": parsed_seed,
        "sapling_certificate_available": parsed_sapling,
        "is_closed_orchard": parsed_orchard,
    }

    return farmer_data, parcel_data


def evaluate_farmer_parcel(
    province: str,
    district: str,
    cks_status: str | bool | None,
    age_group: str,
    gender: str,
    crop: str,
    area_da: float,
    irrigation_type: str,
    seed_cert: str | bool | None,
    sapling_cert: str | bool | None,
    closed_orchard: str | bool | None,
    client: ApiClient | None = None,
    state_mgr: EvaluationStateManager | None = None,
) -> tuple[str, str, pd.DataFrame, str, str, str]:
    """Geriye dönük uyumlu değerlendirme fonksiyonu.

    6'lı tuple döner: (kpi_html, cards_html, details_df, reasons_markdown, disclaimer_html, inline_html).
    """
    active_client = client or ApiClient()
    mgr = state_mgr or global_eval_state

    farmer_data, parcel_data = build_farmer_and_parcel_dicts(
        province=province,
        district=district,
        cks_status=cks_status,
        age_group=age_group,
        gender=gender,
        crop=crop,
        area_da=area_da,
        irrigation_type=irrigation_type,
        seed_cert=seed_cert,
        sapling_cert=sapling_cert,
        closed_orchard=closed_orchard,
    )

    resp, _ = mgr.get_or_evaluate(farmer_data, parcel_data, active_client)

    if "error" in resp:
        err_msg = f"<div class='disclaimer-box'>⚠️ <b>Hata:</b> {resp['error']}</div>"
        return err_msg, "", pd.DataFrame(), "", "", err_msg

    inline_html = render_inline_summary_html(
        resp, float(area_da), crop, province, district
    )
    kpi_html = render_kpi_html(resp)
    cards_html = render_support_cards_html(resp)
    details_df = render_details_dataframe(resp, float(area_da))
    reasons_md = render_reasons_markdown(resp)
    disclaimer_html = render_disclaimer_html()

    return kpi_html, cards_html, details_df, reasons_md, disclaimer_html, inline_html


def evaluate_for_ui(
    province: str,
    district: str,
    cks_status: str | bool | None,
    age_group: str,
    gender: str,
    crop: str,
    area_da: float,
    irrigation_type: str,
    seed_cert: str | bool | None,
    sapling_cert: str | bool | None,
    closed_orchard: str | bool | None,
    client: ApiClient | None = None,
    state_mgr: EvaluationStateManager | None = None,
) -> tuple[dict[str, Any], str, str, str, pd.DataFrame, str, str]:
    """Gradio UI için evaluation state nesnesini de içeren 7'li tuple döner.

    Returns:
        (resp_state, inline_html, kpi_html, cards_html, details_df, reasons_md, disclaimer_html)
    """
    active_client = client or ApiClient()
    mgr = state_mgr or global_eval_state

    farmer_data, parcel_data = build_farmer_and_parcel_dicts(
        province=province,
        district=district,
        cks_status=cks_status,
        age_group=age_group,
        gender=gender,
        crop=crop,
        area_da=area_da,
        irrigation_type=irrigation_type,
        seed_cert=seed_cert,
        sapling_cert=sapling_cert,
        closed_orchard=closed_orchard,
    )

    resp, _ = mgr.get_or_evaluate(farmer_data, parcel_data, active_client)

    if "error" in resp:
        err_msg = f"<div class='disclaimer-box'>⚠️ <b>Hata:</b> {resp['error']}</div>"
        return resp, err_msg, err_msg, "", pd.DataFrame(), "", err_msg

    inline_html = render_inline_summary_html(
        resp, float(area_da), crop, province, district
    )
    kpi_html = render_kpi_html(resp)
    cards_html = render_support_cards_html(resp)
    details_df = render_details_dataframe(resp, float(area_da))
    reasons_md = render_reasons_markdown(resp)
    disclaimer_html = render_disclaimer_html()

    return resp, inline_html, kpi_html, cards_html, details_df, reasons_md, disclaimer_html


def generate_evaluation_report(
    province: str,
    district: str,
    cks_status: str | bool | None,
    age_group: str,
    gender: str,
    crop: str,
    area_da: float,
    irrigation_type: str,
    seed_cert: str | bool | None,
    sapling_cert: str | bool | None,
    closed_orchard: str | bool | None,
    client: ApiClient | None = None,
    cached_resp: dict[str, Any] | None = None,
    state_mgr: EvaluationStateManager | None = None,
) -> dict:
    """Bağımsız yazılımın resmî olmayan ön değerlendirme raporunu hazırlar.

    cached_resp veya state_mgr'daki önbellek mevcutsa ikinci bir /evaluate API çağrısı YAPMAZ!
    """
    farmer_data, parcel_data = build_farmer_and_parcel_dicts(
        province=province,
        district=district,
        cks_status=cks_status,
        age_group=age_group,
        gender=gender,
        crop=crop,
        area_da=area_da,
        irrigation_type=irrigation_type,
        seed_cert=seed_cert,
        sapling_cert=sapling_cert,
        closed_orchard=closed_orchard,
        farmer_id="FARMER-REPORT-001",
        parcel_id="PARCEL-REPORT-001",
    )

    resp: dict[str, Any] | None = cached_resp
    if resp is None:
        mgr = state_mgr or global_eval_state
        active_client = client or ApiClient()
        resp, _ = mgr.get_or_evaluate(farmer_data, parcel_data, active_client)

    if not resp or "error" in resp:
        return gr.update(value=None, visible=False)

    report_content = generate_report_markdown(resp, farmer_data, parcel_data)

    out_dir = Path("data") / "reports"
    out_dir.mkdir(parents=True, exist_ok=True)
    report_file = (
        out_dir
        / f"tarim_destek_on_degerlendirme_raporu_{int(time.time())}_{uuid.uuid4().hex[:8]}.md"
    )
    with open(report_file, "w", encoding="utf-8") as f:
        f.write(report_content)

    return gr.update(value=str(report_file.resolve()), visible=True)
