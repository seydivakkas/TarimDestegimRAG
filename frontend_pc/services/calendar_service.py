"""Başvuru Takvimi ve Pencereleri Servisi."""

from __future__ import annotations

import logging
import pandas as pd

from frontend_pc.api_client import ApiClient
from frontend_pc.formatters import calculate_window_status

logger = logging.getLogger("frontend_pc.services.calendar")


def get_application_windows_table(client: ApiClient | None = None) -> pd.DataFrame:
    """2026 Destekleme Programları ve Başvuru Takvimini dinamik getirir."""
    api = client or ApiClient()
    supports = api.get_supports()
    rows = []
    for s in supports:
        start_str = s.get("application_start")
        end_str = s.get("application_end")
        active = s.get("active", True)
        s_disp, e_disp, status_disp = calculate_window_status(start_str, end_str, active)
        rows.append(
            {
                "Destek Programı": s.get("name", s.get("id")),
                "Başlangıç Tarihi": (
                    s_disp
                    if s_disp != "Doğrulanmadı"
                    else (s.get("application_start") or "Kaynak doğrulaması gerekli")
                ),
                "Bitiş Tarihi": (
                    e_disp
                    if e_disp != "Doğrulanmadı"
                    else (s.get("application_end") or "Kaynak doğrulaması gerekli")
                ),
                "Durum": status_disp,
                "Açıklama": s.get("description", "-"),
            }
        )
    return pd.DataFrame(rows)
