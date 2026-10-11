"""P0-39: legacy generic source links must never imitate official passages."""
from __future__ import annotations

from tarim_destek_rag.citations.document_links import (
    format_citation_section_header,
    format_clickable_action,
    format_clickable_check,
    format_clickable_citation,
    format_highlighted_citation_card,
    get_article_preview,
    render_document_viewer_html,
    resolve_check_link,
)


def test_keyword_is_not_verified_article_reference() -> None:
    for text in ("ÇKS kaydı aktif", "367 TL", "Buğday", "MADDE 1"):
        loc = resolve_check_link(text)
        assert loc["url"] == ""
        assert loc["badge"] == "HOLD"


def test_rule_check_and_action_have_no_ungrounded_links() -> None:
    check = format_clickable_check("ÇKS kaydı aktif", "✅")
    assert "Kaynak pasajı: HOLD" in check
    assert "href=" not in check
    action = format_clickable_action("Başvuruyu inceleyin")
    assert "href=" not in action


def test_unverified_snippet_is_not_an_official_highlight() -> None:
    citation = {
        "title": "2026 Resmî Gazete",
        "section": "MADDE 1",
        "url": "https://www.resmigazete.gov.tr/eskiler/2024/08/20240829-1.pdf#page=1",
        "snippet": "BİREBİRİ DOĞRULANMAYAN SAHTE CÜMLE",
    }
    html = format_highlighted_citation_card(citation)
    assert "HOLD" in html
    assert "href=" not in html
    assert "SAHTE CÜMLE" not in html
    title, snip = format_clickable_citation(citation)
    assert "HOLD" in title and "href=" not in title
    assert "BİREBİRİ" in snip


def test_legacy_article_preview_is_not_a_fabricated_quote() -> None:
    for key in ("MADDE 1", "MADDE 2", "MADDE 4", "EK TABLO"):
        result = get_article_preview(key)
        assert result["status"] == "HOLD"
        assert result["text"] == ""
        assert result["url"] == ""


def test_legacy_viewer_cannot_guess_page() -> None:
    html = render_document_viewer_html("MADDE 1")
    assert "HOLD" in html
    assert "Doğrulanmış Mevzuat Metni" not in html


def test_generic_source_heading_claims_no_legal_approval() -> None:
    header = format_citation_section_header()
    assert "HOLD" in header
    assert "href=" not in header
