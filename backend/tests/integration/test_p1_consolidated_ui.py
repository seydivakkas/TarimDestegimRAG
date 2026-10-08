"""P1: Ayrı destek detay/gerekçe tabları kaldırılır; sonuçlar tek sayfada tutulur."""

from frontend_pc.app import build_ui


def test_support_detail_and_reason_are_accordions_not_duplicate_tabs():
    ui = build_ui()
    cfg = ui.get_config_file()
    components = cfg["components"]
    tabs = [comp.get("props", {}).get("label", "")
            for comp in components if comp.get("type", "").lower() == "tabitem"]
    accordions = [comp.get("props", {}).get("label", "")
                  for comp in components if comp.get("type", "").lower() == "accordion"]

    assert len(tabs) == 6, tabs
    assert any("Desteklerim" in label for label in tabs)
    assert all("Destek Detay" not in label for label in tabs)
    assert all("Neden?" not in label for label in tabs)
    assert any("Hesaplama Ayrıntıları" in label for label in accordions)
    assert any("Karar Gerekçeleri" in label for label in accordions)


def test_single_calculation_action_still_populates_all_support_outputs():
    ui = build_ui()
    cfg = ui.get_config_file()
    comps = {comp["id"]: comp for comp in cfg["components"]}
    event_outputs = [
        [comps[i]["props"].get("label", "") for i in dep.get("outputs", []) if i in comps]
        for dep in cfg.get("dependencies", []) if dep.get("outputs")
    ]
    # Tabların birleştirilmesi, aynı hesaplama event'inin 6 sonucu üretmesini değiştirmemeli.
    assert any(len(labels) == 6 for labels in event_outputs)
