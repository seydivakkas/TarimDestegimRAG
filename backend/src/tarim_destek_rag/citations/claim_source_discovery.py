"""G33 support-reason research, deliberately separate from certified claim provenance.

EVERY selected rule check can be researched in the indexed real documents.
Search hits are *potential sources*, never proof that a law applies to that
specific reason, production year, or farmer. Only curated exact bindings from
canonical_evidence_contract.py may assert a verified normative source link.
"""
from __future__ import annotations

import re
from html import escape
from typing import Any

from tarim_destek_rag.citations.claim_evidence_workbench import _claims

_HEX_SHA = re.compile(r"[a-f0-9]{64}\Z")
_HEX_CHUNK = re.compile(r"[a-f0-9]{24}\Z")


def selected_claim(evaluation: dict[str, Any] | None,
                   claim_id: str | None) -> dict[str, Any] | None:
    if not isinstance(evaluation, dict) or not isinstance(claim_id, str):
        return None
    matches = [x for x in _claims(evaluation) if x["id"] == claim_id]
    return matches[0] if len(matches) == 1 else None


def source_candidates(
    evaluation: dict[str, Any] | None, claim_id: str | None, *,
    limit: int = 6,
) -> dict[str, Any]:
    """Return candidates from actual indexed documents, scoped to ONE claim.

    A result does not become normative evidence; do not write it to the claim
    binding matrix, legal-year engine, EK-20 reviews or payment calculations.
    """
    claim = selected_claim(evaluation, claim_id)
    response: dict[str, Any] = {
        "schema_version": 1,
        "claim_id": claim_id if claim else None,
        "status": "HOLD",
        "candidate_status": "RESEARCH_ONLY_NOT_CLAIM_PROOF",
        "claim_text": claim["text"] if claim else None,
        "production_year": claim["year"] if claim else None,
        "hits": [],
        "legal_status": "HOLD",
        "payment_status": "HOLD",
    }
    if claim is None or not 1 <= limit <= 10:
        return response
    try:
        from tarim_destek_rag.retrieval.document_rag import get_document_rag
        # Retrieval is only exploration. It MUST NOT match a regulation to a
        # production year, or infer a legal claim from a semantic similarity.
        engine = get_document_rag()
        hits = engine.search(claim["text"], top_k=min(limit + 4, 10))
        seen = set()
        for item in hits:
            if not isinstance(item, dict):
                continue
            sid = item.get("source_id")
            sha = item.get("source_sha256")
            chunk = item.get("chunk_id")
            page = item.get("page_number")
            if (not isinstance(sid, str) or sid.startswith("USER_")
                    or not isinstance(sha, str) or not _HEX_SHA.fullmatch(sha)
                    or not isinstance(chunk, str)
                    or not _HEX_CHUNK.fullmatch(chunk)
                    or (page is not None and (
                        type(page) is not int or not 1 <= page <= 2000))):
                continue
            unique = (sha, chunk)
            if unique in seen:
                continue
            seen.add(unique)
            response["hits"].append({
                "proof_key": sha + ":" + chunk,
                "source_id": sid,
                "source_sha256": sha,
                "chunk_id": chunk,
                "page_number": page,
                "format": item.get("format"),
                "title": str(item.get("title") or sid)[:180],
                "excerpt": str(item.get("text") or "")[:340],
                "status": "SEARCH_CANDIDATE_NOT_NORMATIVE_PROOF",
            })
            if len(response["hits"]) == limit:
                break
        response["status"] = (
            "SOURCE_RESEARCH_CANDIDATES_HOLD" if response["hits"]
            else "NO_DOCUMENT_CANDIDATES_HOLD"
        )
    except (OSError, ValueError, KeyError, TypeError, ImportError,
            RuntimeError, AttributeError):
        response["status"] = "SOURCE_RESEARCH_UNAVAILABLE_HOLD"
    return response


def candidate_choices(evaluation: dict[str, Any] | None, claim_id: str | None
                      ) -> tuple[str, list[tuple[str, str]], dict[str, Any]]:
    """Gradio helper; only expose scoped SHA+chunk keys from this retrieval."""
    result = source_candidates(evaluation, claim_id)
    hits = result["hits"]
    if result["claim_id"] is None:
        return ("**HOLD:** Önce mevcut değerlendirmeden tekil gerekçe seçin.",
                [], {"claim_id": None, "candidates": []})
    title = (
        f"**{len(hits)} kaynak araştırma adayı.** "
        "Bunlar arama eşleşmeleridir; ilgili şartın hukukî dayanağı "
        "oldukları, yürürlük yılları veya ödeme uygunluğu **doğrulanmadı**. "
        "Seçilen aday özgün dosyada tekrar SHA ile denetlenir."
    )
    options = [
        (
            f"{i+1}. {h['title']} · "
            + (f"PDF sayfa {h['page_number']}" if h["page_number"] else "HTML")
            + f" · SHA {h['source_sha256'][:12]} · ARAŞTIRMA ADAYI",
            h["proof_key"],
        )
        for i, h in enumerate(hits)
    ]
    return (title, options, {
        "claim_id": result["claim_id"],
        "candidates": [h["proof_key"] for h in hits],
    })


def candidate_original_html(evaluation: dict[str, Any] | None,
                            claim_id: str | None, proof_key: str | None,
                            whitelist: dict[str, Any] | None) -> str:
    """One selected original source, never silently attributed to claim."""
    if (selected_claim(evaluation, claim_id) is None
            or not isinstance(whitelist, dict)
            or whitelist.get("claim_id") != claim_id
            or not isinstance(whitelist.get("candidates"), list)
            or not isinstance(proof_key, str)
            or proof_key not in whitelist["candidates"]
            or not re.fullmatch(r"[a-f0-9]{64}:[a-f0-9]{24}", proof_key)):
        return "<p>HOLD — Seçilen kaynak bu tekil gerekçeye ait arama sonucunda yok.</p>"
    sha, chunk = proof_key.split(":")
    try:
        from tarim_destek_rag.citations.rag_exact_location import (
            render_rag_citation_proof,
        )
        html = render_rag_citation_proof(sha, chunk)
        # The renderer is trusted code; it HTML-escapes original document
        # text, checks bytes, and uses original pixels for any candidate ROI.
        match = re.search(r"<body>(.*)</body>", html, flags=re.DOTALL)
        if match is None:
            raise ValueError("Original page did not render")
        return (
            '<section style="border:2px solid #d97706;padding:10px">'
            '<p><strong>ARAŞTIRMA ADAYI — BU GEREKÇENİN '
            'MEVZUAT DAYANAĞI OLARAK ONAYLANMADI.</strong> '
            'Üretim yılı, değişiklik zinciri ve ödeme HOLD. '
            'Turuncu eşleşme sadece dosya içindeki alıntı konumudur.</p>'
            + match.group(1) + "</section>"
        )
    except (OSError, ValueError, KeyError, TypeError, RuntimeError,
            ImportError, AttributeError):
        return (
            "<p>HOLD — Orijinal kaynak baytları ya da aynı "
            "alıntının konumu artık doğrulanamıyor.</p>"
        )
