"""Source-bound read-only proof-route contract used by UI and reports.

This is only a safe link contract: the backend endpoint independently checks
pinned original bytes, source SHA, and the actual sentence/cell location.
"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import parse_qs, urlsplit

_SHA = re.compile(r"[a-f0-9]{64}\Z")


def verified_highlight_path(evidence: dict[str, Any], support_id: str | None = None) -> str | None:
    """Only accept complete, internally consistent proof URLs. Never infer a clause."""
    status = evidence.get("verification_status")
    sha = evidence.get("source_sha256") if status == (
        "ORIGINAL_PDF_ROW_AND_CROP_LOCATED_DRAFT_REVIEW"
    ) else evidence.get("document_sha256")
    path = evidence.get("highlighted_pdf_url")
    if not isinstance(sha, str) or not _SHA.fullmatch(sha):
        return None
    if not isinstance(path, str) or not path.startswith("/evidence/highlight/"):
        return None
    try:
        route = urlsplit(path)
        pairs = parse_qs(route.query, keep_blank_values=True)
    except ValueError:
        return None
    if (route.scheme or route.netloc or route.path.startswith("//")
        or any(len(values) != 1 for values in pairs.values())):
        return None
    params = {key: values[0] for key, values in pairs.items()}
    page = evidence.get("page_number")
    if status == "EXACT_PDF_MATCH_PENDING_LEGAL_REVIEW":
        quote = evidence.get("snippet")
        if (type(page) is not int or not 1 <= page <= 2000
            or route.path != f"/evidence/highlight/{sha}"
            or set(params) != {"page", "quote"} or route.fragment
            or params["page"] != str(page) or not isinstance(quote, str)
            or not quote or params["quote"] != quote):
            return None
    elif status == "VISUAL_SOURCE_LOCATED_PENDING_SECOND_REVIEW":
        sid = params.get("support_id")
        if (type(page) is not int or not 1 <= page <= 2000
            or route.path != f"/evidence/highlight/visual/{sha}"
            or set(params) != {"support_id"} or route.fragment != f"page={page}"
            or not sid or (support_id is not None and sid != support_id)):
            return None
    elif status == "ORIGINAL_HTML_TEXT_LOCATED_PENDING_LEGAL_REVIEW":
        sid = params.get("support_id")
        if (route.path != f"/evidence/highlight/html/{sha}"
            or set(params) != {"support_id"}
            or route.fragment != "tarim-evidence-highlight"
            or not sid or (support_id is not None and sid != support_id)):
            return None
    elif status == "ORIGINAL_PDF_ROW_AND_CROP_LOCATED_DRAFT_REVIEW":
        year = evidence.get("production_year")
        required = {
            "province": evidence.get("province"),
            "district": evidence.get("district"),
            "crop": evidence.get("crop_code"),
            "production_year": str(year),
        }
        if (type(page) is not int or not 1 <= page <= 2000
            or type(year) is not int or year not in (2026, 2027)
            or any(not isinstance(required[k], str) or not required[k]
                   for k in ("province", "district", "crop"))
            or route.path != f"/evidence/highlight/basin/{sha}"
            or set(params) != set(required) or params != required
            or route.fragment != f"page={page}"
            or evidence.get("eligible") is not None
            or evidence.get("approved_rate") is not None):
            return None
    else:
        return None
    return path
