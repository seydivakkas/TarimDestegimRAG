"""Regression: five-task modular Gradio UI has one shared calculation action.

P0 structural merge protection: do not resurrect 6 duplicate screens from
older prototype or silently drop the single result-state calculation.
"""
from frontend_pc.app import build_ui


def test_support_detail_and_reason_are_not_duplicate_top_level_tabs():
    ui = build_ui()
    cfg = ui.get_config_file()
    comps = cfg["components"]
    tabs = [
        comp.get("props", {}).get("label", "")
        for comp in comps
        if comp.get("type", "").lower() == "tabitem"
        and str(comp.get("props", {}).get("id") or "").startswith("tab_")
    ]
    assert len(tabs) == 5, tabs
    assert any("Çiftçi & Parsellerim" in label for label in tabs)
    assert any("Destek Analizi" in label for label in tabs)
    assert any("Yönetim & Doğrulama" in label for label in tabs)
    assert all("Destek Detay" not in label for label in tabs)
    assert all("Neden?" not in label for label in tabs)


def test_single_calculation_action_still_populates_shared_state_and_support_outputs():
    ui = build_ui()
    cfg = ui.get_config_file()
    comps = {comp["id"]: comp for comp in cfg["components"]}
    events = [
        [comps[i] for i in dep.get("outputs", []) if i in comps]
        for dep in cfg.get("dependencies", []) if dep.get("outputs")
    ]
    # Shared evaluation state, inline summary and five support-analysis views
    # are produced atomically by the existing on_calculate_click callback.
    assert any(
        len(outputs) == 7
        and any(c["type"].lower() == "state" for c in outputs)
        for outputs in events
    )
