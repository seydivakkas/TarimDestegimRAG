"""Per-reason 'Neden?' evidence workbench: explicit claim -> normative source.

A verified original clause establishes that the text exists in that official
document; it does NOT prove a farmer fact, full amendment scope or payment.
No support-level citation is silently attached to a different rule check.
"""
from __future__ import annotations

import hashlib
import json
import os
from html import escape
from pathlib import Path
from typing import Any

from tarim_destek_rag.citations.claim_source_matrix import audit_claim_matrix

FIELDS = (
    ("passed_checks", "Sağlanan şart"),
    ("failed_checks", "Sağlanamayan şart"),
    ("missing_fields", "Eksik bilgi"),
)
_HOLD = (
    '<section style="padding:16px;border-left:5px solid #d97706;'
    'border-radius:9px;background:#fffbeb">'
    '<strong>HOLD — Birebir mevzuat kanıtı henüz tamamlanmadı.</strong>'
    '<p>Destek programının genel belge bağlantısı, bu tekil gerekçenin '
    'dayanağı değildir. Burada uydurma alıntı, sahte ekran görüntüsü '
    'veya tahmini sayfa bağlantısı üretilmez.</p></section>'
)


def _year(evaluation: dict[str, Any]) -> int | None:
    year = (evaluation.get("parcel") or {}).get("production_year")
    return year if type(year) is int else None


def _claims(evaluation: dict[str, Any] | None) -> list[dict[str, Any]]:
    """One shared rule-emitted identity for PC, report, FAQ and mobile."""
    from tarim_destek_rag.citations.check_identity import extracted_checks
    return extracted_checks(evaluation)


def claim_choices(evaluation: dict[str, Any] | None) -> list[tuple[str, str]]:
    """All displayed checks selectable, including every UNMAPPED reason."""
    rows = _claims(evaluation)
    return [
        (f"{i+1}. [{row['kind']}] {row['support_id']} "
         f"[{row.get('check_id') or 'LEGACY_HOLD'}]: {row['text'][:125]}",
         row["id"])
        for i, row in enumerate(rows)
    ]


def _paths() -> tuple[Path, Path, Path]:
    return (
        Path(os.getenv("TARIM_RAG_CLAIM_SOURCE_MATRIX",
                       "configs/p0_10_7_claim_source_matrix.json")),
        Path(os.getenv("TARIM_RAG_ORIGINAL_SOURCE_MANIFEST",
                       "configs/p0_10_3_original_source_manifest.json")),
        Path(os.getenv("TARIM_RAG_UPDATE_ARCHIVE", "data/legal_update_archive")),
    )


def claim_evidence_record(
    evaluation: dict[str, Any] | None, chosen_id: str | None,
) -> dict[str, Any]:
    """Return one source-bound normative claim or a fully explicit HOLD."""
    claims = _claims(evaluation)
    options = [row for row in claims if row["id"] == chosen_id]
    if len(options) != 1:
        return {"status": "HOLD", "reason": "NO_UNIQUE_SELECTED_CLAIM"}
    result: dict[str, Any] = {
        **options[0],
        "status": "HOLD",
        "source_location_status": "CLAIM_TO_SOURCE_SPAN_NOT_VERIFIED",
        "legal_year_approved": False,
        "farmer_fact_verified": False,
        "payment_approved": False,
        "source_passage": None,
    }
    if not isinstance(evaluation, dict):
        return result
    matrix_path, manifest_path, archive_root = _paths()
    try:
        matrix = json.loads(matrix_path.read_text(encoding="utf-8"))
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        audit = audit_claim_matrix(evaluation, matrix, manifest, archive_root)
        matching = [r for r in audit["claims"] if r["claim_id"] == chosen_id]
        if len(matching) != 1:
            result["reason"] = "CLAIM_AUDIT_NOT_UNIQUE"
            return result
        item = matching[0]
        span_id = item.get("candidate_span_id")
        proof = [
            p for p in audit["source_spans"]
            if p.get("span_id") == span_id and
            p.get("source_location_status") == "ORIGINAL_HTML_SPAN_LOCATED"
        ]
        source = [
            s for s in matrix["spans"] if s.get("span_id") == span_id
        ]
        if (len(proof) != 1 or len(source) != 1
                or proof[0].get("verified_quote") != source[0].get("exact_quote")
                or item.get("source_location_status") !=
                    "ORIGINAL_HTML_SPAN_LOCATED_NORMATIVE_ONLY"):
            result["reason"] = "ORIGINAL_SPAN_UNPROVEN"
            return result
        source_row = source[0]
        result.update({
            "source_location_status": "ORIGINAL_HTML_SPAN_LOCATED_NORMATIVE_ONLY",
            "source_passage": source_row["exact_quote"],
            "source_id": source_row["source_id"],
            "source_sha256": source_row["source_sha256"],
            "source_url": source_row["source_url"],
            "article": source_row["article"],
            "target_provision": source_row["target_provision"],
            "span_id": source_row["span_id"],
        })
    except (OSError, ValueError, KeyError, TypeError, ImportError) as exc:
        result["reason"] = type(exc).__name__
    return result


def render_claim_evidence(
    evaluation: dict[str, Any] | None, chosen_id: str | None,
) -> str:
    """Display only SHA-verified original excerpt; always mark legal claim HOLD."""
    if not chosen_id:
        return _HOLD
    record = claim_evidence_record(evaluation, chosen_id)
    text = record.get("text")
    if not isinstance(text, str):
        return _HOLD
    head = (
        '<section style="padding:15px;border:1px solid #cbd5e1;'
        'border-radius:10px;background:white">'
        f'<div><strong>İncelenen tekil gerekçe:</strong> {escape(text)}</div>'
        f'<p>Tür: {escape(str(record.get("kind") or ""))} · '
        f'Kural: <code>{escape(str(record.get("rule_id") or ""))}</code> · '
        f'Üretim yılı: {escape(str(record.get("year") or "BELİRSİZ"))}</p>'
    )
    quote = record.get("source_passage")
    if not isinstance(quote, str):
        return head + _HOLD + "</section>"
    url = escape(record["source_url"], quote=True)
    return (
        head
        + '<p style="border-left:5px solid #d97706;padding:8px;background:#fffbeb">'
        '<strong>HOLD — Normatif kaynak pasajının konumu bulundu.</strong> '
        'Bu, çiftçinin koşulu sağladığını, hükmün üretim yılı için hukukî '
        'geçerliliğini veya ödeme tutarını onaylamaz.</p>'
        f'<p><strong>Resmî kaynak:</strong> {escape(record["source_id"])} · '
        f'{escape(record["article"])} · '
        f'{escape(record["target_provision"])}</p>'
        '<p><strong>SHA doğrulanmış özgün HTML pasajı:</strong></p>'
        '<div style="line-height:1.9;padding:14px;border:1px solid #e2e8f0">'
        f'<mark style="background:#ffedd5;padding:3px">{escape(quote)}</mark>'
        '</div>'
        f'<p><a href="{url}" rel="noopener noreferrer" target="_blank">'
        'Özgün Resmî Gazete HTML belgesini aç ↗</a></p>'
        f'<p style="font-size:0.8rem">Özgün SHA-256: '
        f'<code>{escape(record["source_sha256"])}</code></p>'
        '<p>Geometrik PDF ekran görüntüsü bu HTML kanıtı için mevcut değil; '
        'kaynak türü HTML olduğundan sahte PDF sayfası oluşturulmaz.</p>'
        '</section>'
    )
