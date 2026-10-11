"""Mevzuat ve Kanıt Zinciri Tıklanabilir Belge Bağlantıları Modülü.

Kural motoru çıktılarındaki şart maddelerini (Sağlanan/Sağlanamayan) ve
atıf zincirlerini doğrudan Resmî Gazete, BÜGEM ve mevzuat portallarındaki
orijinal belge konumlarına bağlar.

Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
"""

from __future__ import annotations

import re
from typing import Any

# No hard-coded unofficial article/page/quotation maps.
DOCUMENT_LOCATIONS: dict[str, dict[str, str]] = {}
ARTICLE_PREVIEWS: dict[str, dict[str, str]] = {}


def resolve_check_link(check_text: str, support_id: str | None = None) -> dict[str, str]:
    """A rule/check keyword is NEVER proof of a Gazette article or page."""
    return {
        "title": "Kural açıklaması (resmî alıntı değil)",
        "section": "Madde ve pasaj bağımsız doğrulanmadı",
        "url": "",
        "badge": "HOLD",
    }


def format_clickable_check(
    check_text: str, status_icon: str = "✅",
    support_id: str | None = None,
) -> str:
    """Display rule/farmer condition without inventing a source hyperlink."""
    from html import escape

    css = "doc-fail" if status_icon in ("❌", "⚠️") else "doc-pass"
    return (
        f'<div class="doc-link-item {css}">'
        f'{escape(status_icon)} {escape(check_text)} '
        '<span class="doc-badge-tag">Kaynak pasajı: HOLD</span></div>'
    )


def format_clickable_action(action_text: str, support_id: str | None = None) -> str:
    """Actions are advisory; no guessed official source URLs."""
    from html import escape

    return (
        '<div class="doc-link-item doc-action">'
        + escape(action_text)
        + '<span class="doc-badge-tag">Kaynak pasajı: HOLD</span></div>'
    )


def format_citation_section_header(url: str | None = None) -> str:
    """Never assert a 'verified original quote' based on a generic document URL."""
    return '<strong>Kaynak pasajları — tekil doğrulama bekliyor (HOLD)</strong>'


def format_clickable_citation(
    citation: dict[str, Any],
    default_support_id: str | None = None,
) -> tuple[str, str]:
    """No law quotes from an unverified retrieval snippet or guessed page."""
    from html import escape

    title = escape(str(citation.get("title") or "Kaynak"))
    section = escape(str(citation.get("section") or "Madde bilinmiyor"))
    snippet = escape(str(citation.get("snippet") or ""))
    heading = (
        f'<span class="doc-citation-header-link">{title} — {section} '
        '(Birebir pasaj konumu: HOLD)</span>'
    )
    return heading, snippet


def get_article_preview(article_key: str) -> dict[str, str]:
    """Legacy arbitrary article previews are quarantined, not official quotes."""
    return {
        "title": "Özgün mevzuat sayfası arşiv incelemesi",
        "source": "SHA-256 doğrulanmış belge gerekir",
        "url": "",
        "text": "",
        "status": "HOLD",
    }


def highlight_legal_text(text: str, status: str | None = None) -> str:
    """HTML-escape unverified text; never label text as verified legal evidence."""
    from html import escape

    return escape(text or "")


def format_highlighted_citation_card(
    citation: dict[str, Any],
    status: str = "ELIGIBLE",
    support_id: str | None = None,
) -> str:
    """Only dedicated byte/span verifier may issue yellow original highlights."""
    from html import escape

    title = escape(str(citation.get("title") or "Kaynak notu"))
    section = escape(str(citation.get("section") or "Madde belirtilmemiş"))
    return (
        '<div class="legal-quote-card warn">'
        f'<strong>{title} — {section}</strong>'
        '<p>HOLD — Birebir resmî alıntı, sayfa, görsel vurgu ve yıl geçerliliği '
        'bu atıf için doğrulanmadı.</p>'
        '</div>'
    )


def render_document_viewer_html(article_key: str) -> str:
    """Never import RAG / guess a page for arbitrary article names."""
    if not isinstance(article_key, str) or not re.fullmatch(
        r"[A-Z][A-Z0-9_]+:[1-9][0-9]*", article_key,
    ):
        return (
            '<p>HOLD — Özgün PDF, birebir pasaj ve gerçek sayfa '
            'bağımsız olarak doğrulanmadı.</p>'
        )
    try:
        from tarim_destek_rag.citations.pdf_page_indexer import render_evidence_by_key

        return render_evidence_by_key(article_key)
    except (ImportError, OSError, ValueError):
        return '<p>HOLD — Gerçek kaynak arşivi kullanılamıyor.</p>'
