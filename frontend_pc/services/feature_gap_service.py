"""Read-only feature gap register view for the admin tab.

A project work plan, never a test pass or legal/payment verdict.
"""
from __future__ import annotations

import json
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[2]
_REGISTER = _ROOT / "configs" / "feature_gap_register.json"


def gap_register_view() -> tuple[str, list[list[str]]]:
    """Read and display all tracked work items from the canonical file."""
    try:
        if not _REGISTER.is_file() or _REGISTER.stat().st_size > 150_000:
            raise ValueError("Feature register not found or too large")
        data = json.loads(_REGISTER.read_text(encoding="utf-8"))
        if (data.get("schema_version") != 1
                or not isinstance(data.get("features"), list)
                or not isinstance(data.get("work_items"), list)):
            raise ValueError("Feature register has unknown schema")
        features, items = data["features"], data["work_items"]
        if (len(features) != 14 or len(items) > 300
                or len({x["gap_id"] for x in items}) != len(items)
                or len({x["id"] for x in features}) != 14):
            raise ValueError("Feature register is ambiguous")
        open_items = [x for x in items if x.get("status") != "CLOSED_IMPLEMENTED"]
        blocked = sum(x.get("status") == "BLOCKED_EXTERNAL" for x in items)
        deferred = sum(x.get("status") == "DEFERRED_F14" for x in items)
        p0 = sum(x.get("priority") == "P0" for x in open_items)
        summary = (
            "### Proje iş takibi — kayıtlı eksikler\n"
            f"**Açık iş kalemi:** {len(open_items)} · "
            f"**P0:** {p0} · **Dış girdi bekleyen:** {blocked} · "
            f"**F14'e ertelenen:** {deferred}  \n"
            f"**Kayıt tarihi:** {data.get('last_reviewed', 'BELİRSİZ')} · "
            "**PR #41:** DRAFT iş planı.  \n"
            "Bu tablo kod/görev envanteridir, test başarı yüzdesi veya "
            "hukukî/ödeme kararı değildir. EK-20 için 48 koordinat ve 96 "
            "gerçek inceleme ayrıca açık kalabilir."
        )
        rows: list[list[str]] = []
        for item in sorted(open_items, key=lambda x: (
            {"P0": 0, "P1": 1, "P2": 2, "P3": 3}.get(x["priority"], 4),
            x["gap_id"],
        )):
            rows.append([
                str(item["gap_id"]),
                str(item["feature_id"]),
                str(item["priority"]),
                str(item["status"]),
                str(item["title"]),
                str(item["solution"]),
                str(item["definition_of_done"]),
            ])
        return summary, rows
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError):
        return (
            "**HOLD — İş kayıt dosyası okunamadı.** "
            "Yerel configs/feature_gap_register.json kontrol edilmeli.",
            [],
        )
