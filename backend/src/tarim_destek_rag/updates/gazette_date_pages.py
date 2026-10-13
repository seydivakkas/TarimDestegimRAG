"""Bounded official Gazette date-page discovery helpers (publication != crop year).

Official RG archive exposes dated issue pages at /DD.MM.YYYY. Only real links
present in those pages are fetched. No presumed PDF filename is constructed.
"""
from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from tarim_destek_rag.updates.discovery import OfficialPortal

MAX_DATE_WINDOW_DAYS = 14


def publication_window(
    start: str | None = None, end: str | None = None,
) -> tuple[list[OfficialPortal], dict[str, str | int]]:
    """Choose a bounded publication-date window for incremental/backfill scans.

    This is NOT a complete year coverage claim. An operator can explicitly
    request older historical windows in repeat operations.
    """
    today = datetime.now(ZoneInfo("Europe/Istanbul")).date()
    if (start is None) != (end is None):
        raise ValueError("Both from/to publication dates are needed")
    if start is None:
        stop = today
        begin = stop - timedelta(days=6)
    else:
        try:
            begin = date.fromisoformat(start)
            stop = date.fromisoformat(end)
        except (ValueError, TypeError):
            raise ValueError("Publication dates must be YYYY-MM-DD")
    days = (stop - begin).days + 1
    if (not 1 <= days <= MAX_DATE_WINDOW_DAYS
            or begin.year < 2020 or stop > today):
        raise ValueError("Choose a past 1–14-day publication range")
    portals = [
        OfficialPortal(
            source_id=f"RG_DAY_{d.strftime('%Y%m%d')}",
            index_url="https://resmigazete.gov.tr/" + d.strftime("%d.%m.%Y"),
            allowed_hosts=("resmigazete.gov.tr", "www.resmigazete.gov.tr"),
            max_documents=12,
        )
        for d in (begin + timedelta(days=n) for n in range(days))
    ]
    return portals, {
        "publication_from": begin.isoformat(),
        "publication_to": stop.isoformat(),
        "days_requested": days,
        "complete_annual_coverage_proven": False,
    }
