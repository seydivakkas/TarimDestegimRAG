"""G37: 2026 Basic Support registration chain, authentic-source gated.

Sources are NOT sufficient to infer that every farmer is eligible. In
particular, amendment 2025/42 MADDE 3 changes "ÇKS'ye" in original
2024/39 MADDE 5(1) to "ÇKS/ÖKS/KOBÜKS'e", effective 2026-01-01
(2025/42 MADDE 16). Detecting this change is distinct from legal
acceptance, complete amendment history, farmer status and payment.
"""
from __future__ import annotations

import json
import os
from html import escape
from pathlib import Path
from typing import Any

_PILOT_SPANS = (
    "BASE_2024_39_ART4_P1",
    "BASE_2024_39_ART5_P1",
    "AMEND_2025_42_ART3_BASE_ART5_P1",
    "AMEND_2025_42_ART16_EFFECTIVE_2026",
)


def _research_impact_rows() -> list[dict[str, Any]]:
    """Read historical impact RESEARCH, not normatively approved legal rules."""
    file = Path("configs/g37_2026_legal_impact_register.json")
    try:
        if not file.is_file() or file.stat().st_size > 250_000:
            return []
        data = json.loads(file.read_text(encoding="utf-8"))
        items = data.get("changes", [])
        if data.get("schema_version") != 1 or not isinstance(items, list):
            return []
        found: list[dict[str, Any]] = []
        seen: set[str] = set()
        for x in items:
            if not isinstance(x, dict):
                return []
            row_id = x.get("id")
            if (not isinstance(row_id, str) or len(row_id) > 70
                    or row_id in seen):
                return []
            seen.add(row_id)
            status = x.get("status")
            if status != "OFFICIAL_WEB_TEXT_RESEARCHED_ORIGINAL_SHA_PENDING_HOLD":
                # No external proposal can grant accepted-year legal status.
                return []
            found.append({
                "id": row_id,
                "reference": str(x.get("law") or "")[:32],
                "article": str(x.get("article") or "")[:80],
                "target": str(x.get("target") or "")[:120],
                "operation": str(x.get("operation") or "")[:100],
                "effective_rule": str(x.get("effective_rule") or "")[:250],
                "production_years_researched": x.get("production_years", []),
                "source_url": str(x.get("source_url") or "")[:240],
                "original_sha256": x.get("source_sha256"),
                "status": "SOURCE_RESEARCH_ONLY_LEGAL_HOLD",
                "independently_approved": False,
            })
        return found
    except (OSError, ValueError, TypeError, KeyError):
        return []


def source_chain_2026_cks() -> dict[str, Any]:
    """Recheck pinned original SHA/article/text for every pilot component."""
    from tarim_destek_rag.citations.claim_source_matrix import validate_source_span
    from tarim_destek_rag.citations.claim_evidence_workbench import _paths

    result: dict[str, Any] = {
        "schema_version": 1,
        "pilot_check_id": "BASIC_CKS_REGISTRATION",
        "production_year": 2026,
        "status": "G37_INDEPENDENT_VALIDITY_REVIEW_HOLD",
        "temporal_legal_status": "HOLD",
        "farmer_fact_status": "NOT_INDEPENDENTLY_VERIFIED",
        "payment_status": "HOLD",
        "general_registry_requirement": "2024/39 MADDE 4(1)",
        "basic_support_provision": "2024/39 MADDE 5(1)",
        "observed_amendment": "2025/42 MADDE 3 replaces ÇKS’ye with ÇKS/ÖKS/KOBÜKS’e",
        "effective_date_declared": "2026-01-01",
        "effective_date_source": "2025/42 MADDE 16",
        "sources": [],
        "other_updates": [
            {
                "reference": "2025/13",
                "provision": "2024/39 MADDE 5(3) (second crop soy)",
                "source_status": "EXTERNAL_RESEARCH_NOT_SHA_PINNED_HOLD",
                "affects_registry_phrase": False,
                "official_ministry_notice": "https://trabzon.tarimorman.gov.tr/Sayfalar/Detay.aspx?TermId=edd3ebad-7b98-490d-a10a-55785a9924e2&TermSetId=79f2f663-7aec-4bc1-b40a-56e75866bfb3&TermStoreId=368e785b-af33-487d-a98d-c11d5495130b&UrlSuffix=996%2F2025-2027-Yillarinda-Yapilacak-Bitkisel-Uretime-Yonelik-Desteklemeler-Ile-Diger-Bazi-Tarimsal-Desteklemelere-Odeme-Yapilmasina-Dair-Teblig",
            },
            {
                "reference": "11781",
                "provision": "8859 Cumhurbaşkanı Kararı 2026/2027 amendments",
                "source_status": "OFFICIAL_PDF_SHA_AND_APPLICABILITY_REVIEW_HOLD",
                "affects_registry_phrase": None,
                "official_url": "https://www.resmigazete.gov.tr/eskiler/2026/09/20260908-7.pdf",
            },
        ],
        "complete_source_chain": False,
        "independently_approved": False,
        "research_impact_changes": _research_impact_rows(),
    }
    try:
        matrix_path, manifest_path, archive = _paths()
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        spans = matrix.get("spans", [])
        by_id = {x.get("span_id"): x for x in spans if isinstance(x, dict)}
        if len(by_id) != len(spans):
            raise ValueError("Ambiguous source span IDs")
        for sid in _PILOT_SPANS:
            row = by_id.get(sid)
            if not isinstance(row, dict):
                result["sources"].append({
                    "span_id": sid, "status": "MISSING_SOURCE_RECORD_HOLD",
                    "verified_original": False,
                })
                continue
            proof = validate_source_span(row, manifest, archive)
            located = proof.get("source_location_status") == "ORIGINAL_HTML_SPAN_LOCATED"
            result["sources"].append({
                "span_id": sid,
                "document_id": row["source_id"],
                "source_sha256": row["source_sha256"],
                "source_url": row["source_url"],
                "article": row["article"],
                "target_provision": row["target_provision"],
                "source_location_status": proof.get("source_location_status", "HOLD"),
                "verified_original": located,
                "exact_quote": row["exact_quote"] if located else None,
                "unverified_quote_available": not located,
            })
        result["all_four_original_locations_verified"] = (
            len(result["sources"]) == len(_PILOT_SPANS)
            and all(x["verified_original"] for x in result["sources"])
        )
        # DO NOT lift legal HOLD based only on successful source matching.
    except (OSError, ValueError, KeyError, TypeError, RuntimeError, ImportError):
        result["sources"] = []
        result["all_four_original_locations_verified"] = False
    return result


def render_cks_source_chain() -> str:
    """Render only verified original quotes, no "effective 2026 PASS" banner."""
    state = source_chain_2026_cks()
    parts = [
        '<section style="border:1px solid #cbd5e1;padding:12px">',
        "<h3>2026 Temel Destek kayıt şartı — değişiklik zinciri</h3>",
        "<p><strong>Genel kayıt hükmü:</strong> 2024/39 MADDE 4(1). "
        "<strong>Temel destek:</strong> MADDE 5(1). "
        "<strong>Metin değişikliği:</strong> 2025/42 MADDE 3. "
        "<strong>Yürürlük kaydı:</strong> 2025/42 MADDE 16 (1 Ocak 2026).</p>",
        "<p><strong>HOLD:</strong> Bu kaynak konumlarını doğrulamak "
        "yürürlük/ilga zincirinin veya çiftçinin resmî kayıt bilgilerinin "
        "bağımsız hukukî doğrulanması yerine geçmez.</p>",
    ]
    for item in state["sources"]:
        sid = escape(item["span_id"])
        if not item.get("verified_original"):
            parts.append(
                f"<p><code>{sid}</code> — özgün HTML baytları, SHA veya "
                "gerçek madde pasajı bu ortamda doğrulanamadı: HOLD.</p>"
            )
            continue
        url = escape(item["source_url"], quote=True)
        q = escape(item["exact_quote"])
        parts.append(
            f'<p><code>{sid}</code> · '
            f'{escape(item["target_provision"])} · '
            f'SHA: <code>{escape(item["source_sha256"])}</code> · '
            f'<a href="{url}" target="_blank" rel="noopener noreferrer">'
            "Özgün Resmî Gazete HTML aç ↗</a></p>"
            '<blockquote style="border-left:3px solid #d97706;padding:8px">'
            '<mark style="background:#ffedd5">' + q + "</mark></blockquote>"
        )
    parts.append(
        "<h4>2025/13 ve 11781 — ayrı yürürlük ve konu etkileri</h4>"
        "<p><strong>HOLD:</strong> Bu araştırma kayıtları özgün PDF/HTML'nin "
        "SHA ve bağımsız hukukî kabulü yerine geçmez.</p>"
    )
    for change in state.get("research_impact_changes", []):
        parts.append(
            '<p><code>' + escape(change["id"]) + '</code> · '
            '<strong>' + escape(change["reference"]) + ' '
            + escape(change["article"]) + '</strong> · '
            + escape(change["target"]) + '<br>'
            + escape(change["effective_rule"]) +
            ' · <strong>LEGAL HOLD</strong></p>'
        )
    return "".join(parts) + "</section>"
