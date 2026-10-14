"""F07-F10 common, deliberately fail-closed evidence contract.

One stable JSON shape for PC, report, FAQ claim navigation, and future mobile
adapter. A source-located normative excerpt is NOT a legal-year or payout PASS.
An unrelated FAQ/RAG hit cannot inherit a claim's source identity.
"""
from __future__ import annotations

import hashlib
import json
import re
from html import escape
from typing import Any

from tarim_destek_rag.citations.claim_evidence_workbench import (
    _claims,
    _paths,
    claim_evidence_record,
)

CONTRACT_SCHEMA = 1
_SHA = re.compile(r"[0-9a-f]{64}\Z")
_CLAIM = re.compile(r"[0-9a-f]{24}\Z")


def _source_review_obligations(span_id: str, sha: str) -> list[str]:
    """List declared pending amendments, not an authoritative complete chain."""
    try:
        matrix_path, _, _ = _paths()
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        matches = [
            item for item in matrix.get("spans", [])
            if isinstance(item, dict) and item.get("span_id") == span_id
            and item.get("source_sha256") == sha
        ]
        if len(matches) != 1:
            return []
        obligations = matches[0].get("amendment_review_required")
        if not isinstance(obligations, list) or not all(
            isinstance(x, str) and 1 <= len(x) <= 70 for x in obligations
        ):
            return []
        return obligations
    except (OSError, ValueError, KeyError, TypeError):
        return []


def claim_contract(
    evaluation: dict[str, Any] | None, claim_id: str | None,
) -> dict[str, Any]:
    """Return only provenance positively established for this EXACT claim.

    Source fields are present only when SHA+article+literal HTML-node
    verification succeeded in the canonical claim_evidence_record verifier.
    No official URL is guessed for an unmapped claim. Legal/payment HOLD
    remains regardless of original passage location.
    """
    result: dict[str, Any] = {
        "schema_version": CONTRACT_SCHEMA,
        "contract_type": "SINGLE_CLAIM_EVIDENCE",
        "claim_id": claim_id if isinstance(claim_id, str)
        and _CLAIM.fullmatch(claim_id) else None,
        "evidence_id": None,
        "rule_id": None,
        "support_id": None,
        "check_id": None,
        "identity_status": "HOLD",
        "production_year": None,
        "claim_field": None,
        "claim_text": None,
        "source": None,
        "source_location_status": "HOLD",
        "amendment_chain": {"status": "NOT_PROVEN_COMPLETE", "review_required": []},
        "temporal_legal_status": "HOLD",
        "farmer_fact_status": "NOT_INDEPENDENTLY_VERIFIED",
        "payment_status": "HOLD",
        "final_acceptance": "HOLD",
        "navigation_available": False,
    }
    if not isinstance(evaluation, dict) or result["claim_id"] is None:
        return result
    candidates = [x for x in _claims(evaluation) if x["id"] == claim_id]
    if len(candidates) != 1:
        return result
    row = candidates[0]
    result.update({
        "rule_id": row["rule_id"],
        "support_id": row["support_id"],
        "check_id": row.get("check_id"),
        "identity_status": row.get("identity_status", "HOLD"),
        "production_year": row["year"],
        "claim_field": row["field"],
        "claim_text": row["text"],
    })
    located = claim_evidence_record(evaluation, claim_id)
    if located.get("source_location_status") != (
        "ORIGINAL_HTML_SPAN_LOCATED_NORMATIVE_ONLY"
    ):
        # A human-curated EXACT claim/year-to-native-PDF binding is the only
        # alternative. Never promote RAG/OCR similarity to normative proof.
        from tarim_destek_rag.citations.claim_pdf_exact_binding import (
            exact_pdf_binding,
        )

        pinned_pdf = exact_pdf_binding(evaluation, row)
        if pinned_pdf is None:
            return result
        sha = pinned_pdf["source_sha256"]
        original_quote = pinned_pdf["source_passage"]
        page = pinned_pdf["pdf_page"]
        source = {
            "document_id": pinned_pdf["source_id"],
            "source_sha256": sha,
            "original_url": pinned_pdf["source_url"],
            "format": "pdf",
            "article": pinned_pdf["target_provision"],
            "target_provision": pinned_pdf["target_provision"],
            "span_id": None,
            "exact_quote": original_quote,
            "pdf_page": page,
            "pixel_bbox": None,
            "pixel_boxes_180dpi": pinned_pdf["pixel_boxes_180dpi"],
            "visual_cell_status": "NATIVE_TEXT_LOCATION_UNREVIEWED",
        }
        token = hashlib.sha256(json.dumps(
            [claim_id, source["document_id"], sha, page, original_quote],
            ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")).hexdigest()[:32]
        result.update({
            "evidence_id": "TRAG-EV1-" + token,
            "source": source,
            "source_location_status": "ORIGINAL_PDF_NATIVE_QUOTE_LOCATED_ONLY",
            "amendment_chain": {
                "status": "NOT_PROVEN_COMPLETE", "review_required": [],
            },
            "navigation_available": True,
        })
        return result
    required = (
        "source_id", "source_sha256", "source_url", "article",
        "target_provision", "span_id", "source_passage",
    )
    if not all(isinstance(located.get(k), str) and located[k] for k in required):
        return result
    sha = located["source_sha256"]
    url = located["source_url"]
    if not _SHA.fullmatch(sha) or not url.startswith("https://"):
        return result
    source = {
        "document_id": located["source_id"],
        "source_sha256": sha,
        "original_url": url,
        "format": "html",
        "article": located["article"],
        "target_provision": located["target_provision"],
        "span_id": located["span_id"],
        "exact_quote": located["source_passage"],
        "pdf_page": None,
        "pixel_bbox": None,
        "visual_cell_status": "NOT_APPLICABLE_HTML",
    }
    token = hashlib.sha256(
        json.dumps(
            [claim_id, source["document_id"], sha, source["span_id"]],
            ensure_ascii=False, separators=(",", ":"),
        ).encode("utf-8")
    ).hexdigest()[:32]
    result.update({
        "evidence_id": "TRAG-EV1-" + token,
        "source": source,
        "source_location_status": "ORIGINAL_HTML_SPAN_LOCATED_NORMATIVE_ONLY",
        "amendment_chain": {
            "status": "NOT_PROVEN_COMPLETE",
            "review_required": _source_review_obligations(source["span_id"], sha),
        },
        "navigation_available": True,
    })
    return result


def evaluation_contract(evaluation: dict[str, Any] | None) -> dict[str, Any]:
    """Deterministic list; no farmer/parcel PII serialized to mobile or FAQ."""
    year = None
    if isinstance(evaluation, dict):
        raw_year = (evaluation.get("parcel") or {}).get("production_year")
        year = raw_year if type(raw_year) is int else None
    claims = _claims(evaluation) if isinstance(evaluation, dict) else []
    ordered: list[str] = []
    seen: set[str] = set()
    for row in claims:
        if row["id"] not in seen:
            ordered.append(row["id"])
            seen.add(row["id"])
    records = [claim_contract(evaluation, key) for key in ordered]
    return {
        "schema_version": CONTRACT_SCHEMA,
        "contract_type": "EVALUATION_EVIDENCE_INDEX",
        "production_year": year,
        "claims": records,
        "claim_count": len(claims),
        "unique_claim_count": len(records),
        "source_located_count": sum(x["navigation_available"] for x in records),
        "legal_approval": False,
        "payment_approval": False,
        "complete_coverage": False,
        "acceptance": "HOLD",
    }


def faq_contract(
    faq: dict[str, Any] | None, *,
    evaluation: dict[str, Any] | None = None,
    exact_claim_id: str | None = None,
) -> dict[str, Any]:
    """FAQ retrieval metadata alone is NEVER exact claim-to-source evidence."""
    result = {
        "schema_version": CONTRACT_SCHEMA,
        "contract_type": "FAQ_EVIDENCE",
        "faq_source_status": "FAQ_CITATION_NOT_VERIFIED",
        "claim": None,
        "acceptance": "HOLD",
    }
    # Only an explicitly chosen claim_id from the current evaluation can
    # inherit the exact same proof, never the FAQ title/snippet/keyword.
    if (not isinstance(faq, dict) or exact_claim_id is None
            or not isinstance(evaluation, dict)):
        return result
    contract = claim_contract(evaluation, exact_claim_id)
    result["claim"] = contract
    return result


def render_claim_contract_html(
    evaluation: dict[str, Any] | None, claim_id: str | None,
) -> str:
    """HTML used by claim navigator and FAQ explicit-claim inspector."""
    rec = claim_contract(evaluation, claim_id)
    if rec["claim_text"] is None:
        return "<p>HOLD — Seçilen gerekçenin tekil kimliği bulunamadı.</p>"
    parts = [
        '<section style="padding:12px;border:1px solid #cbd5e1;background:white">',
        f'<p><strong>Gerekçe:</strong> {escape(rec["claim_text"])}</p>',
        f'<p><strong>Claim ID:</strong> <code>{escape(rec["claim_id"])}</code> · '
        f'<strong>Yıl:</strong> {escape(str(rec["production_year"]))}</p>',
        f'<p><strong>Sabit check_id:</strong> '
        f'<code>{escape(str(rec["check_id"] or "LEGACY_HOLD"))}</code> · '
        f'<strong>Kimlik doğrulama:</strong> '
        f'{escape(rec["identity_status"])}</p>',
    ]
    source = rec["source"]
    if source is None:
        parts.append(
            '<p><strong>HOLD:</strong> Bu tekil gerekçeye ait SHA-bağlı '
            'birebir madde/fıkra/paragraf konumu yoktur. Bağlantı üretilmez.</p>'
        )
    else:
        parts.extend([
            f'<p><strong>Tekil kanıt ID:</strong> <code>{escape(rec["evidence_id"])}</code></p>',
            f'<p><strong>Özgün kaynak:</strong> {escape(source["document_id"])} · '
            f'{escape(source["target_provision"])}</p>',
            f'<p><strong>SHA-256:</strong> <code>{escape(source["source_sha256"])}</code></p>',
        ])
        if source["format"] == "html":
            from tarim_destek_rag.citations.original_html_navigator import (
                render_original_html_position,
            )
            parts.extend([
                '<p><strong>Birebir özgün HTML pasajı:</strong></p>',
                render_original_html_position(source),
            ])
        elif source["format"] == "pdf":
            from tarim_destek_rag.citations.claim_pdf_exact_binding import (
                render_pdf_claim_original,
            )
            parts.append(render_pdf_claim_original(source))
        else:
            parts.append("<p>HOLD — Bilinmeyen özgün kaynak formatı.</p>")
    parts.append(
        '<p><strong>Yıl/değişiklik zinciri:</strong> HOLD — '
        'bütün değişikliklerin etkisi bağımsız doğrulanmadı. '
        '<strong>Çiftçi olgusu:</strong> doğrulanmadı. '
        '<strong>Ödeme:</strong> HOLD.</p></section>'
    )
    return "".join(parts)



def render_claim_coverage_html(evaluation: dict[str, Any] | None) -> str:
    """Per-current-evaluation evidence location coverage; never legal coverage.

    An exact original-source span can be marked *located* while every
    temporal/farmer/payment gate still remains HOLD. Does not compute a
    misleading full-legal-approval percentage.
    """
    if not isinstance(evaluation, dict) or not evaluation.get("rules"):
        return "<p>HOLD — Önce bu parsel için bir değerlendirme oluşturun.</p>"
    audit = evaluation_contract(evaluation)
    total = audit["unique_claim_count"]
    verified = audit["source_located_count"]
    html_located = sum(
        row["source_location_status"] == "ORIGINAL_HTML_SPAN_LOCATED_NORMATIVE_ONLY"
        for row in audit["claims"]
    )
    pdf_located = sum(
        row["source_location_status"] == "ORIGINAL_PDF_NATIVE_QUOTE_LOCATED_ONLY"
        for row in audit["claims"]
    )
    unmapped = [row for row in audit["claims"]
                if not row.get("navigation_available")]
    from html import escape as safe
    return (
        '<section style="padding:12px;border:1px solid #cbd5e1;background:white">'
        "<strong>Tekil gerekçe → özgün kaynak konumu kapsamı</strong>"
        f"<p>Toplam tekil gerekçe: <b>{total}</b> · "
        f"Özgün kaynak metin konumu: <b>{verified}</b> "
        f"(HTML: {html_located}, native PDF: {pdf_located}) · "
        f"Eşleşmeyen/arşivi eksik/konumu doğrulanamayan: "
        f"<b>{len(unmapped)}</b></p>"
        "<p><strong>Hukukî yıl ve ödeme kabulü: HOLD.</strong> "
        "Bu sayılar kaç kez doğru hukukî sonuç verildiğini değil yalnız "
        "bu değerlendirmedeki kanıt-konum durumunu gösterir.</p>"
        + (
            "<details><summary>Eksik veya konumu doğrulanmamış gerekçeleri göster</summary>"
            "<ul>"
            + "".join(
                f"<li><code>{safe(str(row['claim_id']))}</code> · "
                f"{safe(str(row['rule_id']))} · "
                f"{safe(str(row['claim_text'])[:220])}</li>"
                for row in unmapped[:200]
            )
            + "</ul></details>"
            if unmapped else "<p>Bu değerlendirmede kaynak konumu açık kalan gerekçe yok; "
            "üretim yılı ve ödeme yine HOLD.</p>"
        )
        + "</section>"
    )
