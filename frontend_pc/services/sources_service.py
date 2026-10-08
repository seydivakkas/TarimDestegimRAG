"""Resmî Mevzuat Kaynakları Servisi."""

from __future__ import annotations

import logging
import pandas as pd

from frontend_pc.api_client import ApiClient

logger = logging.getLogger("frontend_pc.services.sources")


def get_sources_table(client: ApiClient | None = None) -> pd.DataFrame:
    """Kayıtlı mevzuat kaynakları listesini getirir."""
    api = client or ApiClient()
    sources = api.get_sources()
    rows = []
    for s in sources:
        rows.append(
            {
                "Kaynak Kodu": s.get("id") or s.get("source_id"),
                "Otorite": s.get("authority"),
                "Başlık": s.get("title"),
                "Format": s.get("content_type"),
                "Öncelik": s.get("priority", 0),
                "URL / Erişim": s.get("url"),
            }
        )
    return pd.DataFrame(rows)
