"""G09: proof-gated navigation to the actual SHA-pinned original HTML node.

This is a *reading location*, not a legal effectiveness or payment verdict.
The preview reproduces the actual original node text as escaped text, with the
exactly verified hit marked in the copy. Official HTML is never altered.
"""
from __future__ import annotations

import hashlib
import re
from html import escape
from typing import Any
from urllib.parse import quote, urlsplit

from bs4 import BeautifulSoup

from tarim_destek_rag.citations.claim_source_matrix import (
    _ARTICLE, _TRANSITION, _normalized_match,
)
from tarim_destek_rag.citations.claim_evidence_workbench import _paths

_ALLOWED_HOSTS = frozenset({
    "resmigazete.gov.tr", "www.resmigazete.gov.tr",
    "tarimorman.gov.tr", "www.tarimorman.gov.tr",
})
_SHA = re.compile(r"[0-9a-f]{64}\Z")


def locate_exact_html_node(source: dict[str, Any]) -> dict[str, Any]:
    """Locate the SINGLE verbatim source node in original, byte-checked HTML.

    Failure is explicit HOLD; no approximate textual search, made-up source
    paragraph number or mutated copy of the official original is produced.
    """
    result: dict[str, Any] = {
        "status": "HOLD", "original_url": None,
        "text_fragment_url": None, "original_node_marked_html": None,
        "source_sha256": None, "verified_article": None,
    }
    try:
        sha = source["source_sha256"]
        url = source["original_url"]
        article = source["article"]
        exact = source["exact_quote"]
        if (not isinstance(sha, str) or not _SHA.fullmatch(sha)
                or not isinstance(url, str)
                or not re.fullmatch(r"(?:GEÇİCİ )?MADDE \d+", article)
                or not isinstance(exact, str)):
            raise ValueError("Missing source identity")
        parsed = urlsplit(url)
        if (parsed.scheme != "https" or parsed.hostname not in _ALLOWED_HOSTS
                or parsed.username or parsed.password or parsed.fragment
                or parsed.port is not None):
            raise ValueError("Untrusted official HTML URI")
        _, manifest_path, archive_root = _paths()
        # Re-check actual manifest, even though the parent claim verifier
        # already did so, before publishing a deep link.
        import json
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        sources = [s for s in manifest.get("sources", [])
                   if isinstance(s, dict) and s.get("format") == "html"
                   and s.get("original_sha256") == sha
                   and s.get("url") == url]
        if len(sources) != 1:
            raise ValueError("HTML source identity is not in original manifest")
        path = archive_root / "originals" / (sha + ".html")
        if not path.is_file() or path.stat().st_size > 2_000_000:
            raise ValueError("Verified archive HTML is unavailable")
        raw = path.read_bytes()
        if not raw or hashlib.sha256(raw).hexdigest() != sha:
            raise ValueError("Original byte digest changed")
        doc = BeautifulSoup(raw, "html.parser")
        regex = _normalized_match(exact)
        heading = None
        matches: list[tuple[str, Any]] = []
        for node in doc.find_all(string=True):
            if node.parent and node.parent.name in {"script","style","title"}:
                continue
            original = str(node)
            transition = _TRANSITION.search(original)
            normal = _ARTICLE.search(original)
            if transition:
                heading = "GEÇİCİ MADDE " + transition.group(1)
            elif normal:
                heading = "MADDE " + normal.group(1)
            found = regex.search(original)
            if found and heading == article:
                matches.append((original, found))
        if len(matches) != 1:
            raise ValueError("No unique authentic HTML text node at article")
        original, hit = matches[0]
        # This is the escaped original text node, not an invented summary.
        # Preserve some real context so the reader can orient in the article.
        start = max(0, hit.start() - 220)
        end = min(len(original), hit.end() + 220)
        snippet = (
            ("… " if start else "")
            + original[start:hit.start()]
        )
        after = original[hit.end():end] + (" …" if end < len(original) else "")
        marked = (
            escape(snippet)
            + '<mark id="tarim-exact-original-node" '
            + 'style="background:#ffed52;padding:2px;outline:1px solid #a16207">'
            + escape(original[hit.start():hit.end()])
            + "</mark>"
            + escape(after)
        )
        # Chrome/Edge's Text Fragments may scroll to this text on the
        # official HTML. Browser compatibility and canonical whitespace can
        # prevent it; the in-app verified node is the deterministic fallback.
        external = url + "#:~:text=" + quote(exact, safe="")
        result.update({
            "status": "ORIGINAL_HTML_NODE_VERIFIED",
            "original_url": url,
            "text_fragment_url": external,
            "original_node_marked_html": marked,
            "source_sha256": sha,
            "verified_article": article,
        })
    except (OSError, ValueError, TypeError, KeyError, ImportError,
            UnicodeError, AttributeError):
        return result
    return result


def render_original_html_position(source: dict[str, Any]) -> str:
    """An anchored, escaped original node and optional browser deep link."""
    verified = locate_exact_html_node(source)
    if verified["status"] != "ORIGINAL_HTML_NODE_VERIFIED":
        return (
            "<p><strong>HOLD — Özgün HTML içinde birebir paragraf "
            "konumu açılamadı.</strong> Doğrulanmamış metne veya maddeye "
            "derin bağlantı üretilmez.</p>"
        )
    marked = verified["original_node_marked_html"]
    uri = escape(verified["text_fragment_url"], quote=True)
    return (
        '<section id="tarim-source-position" style="border:1px solid #cbd5e1;'
        'padding:12px;background:white">'
        "<strong>Özgün HTML içindeki gerçek metin düğümü "
        "(SHA-256 doğrulandı)</strong>"
        f'<p>Kaynak maddesi: {escape(verified["verified_article"])} · '
        f'SHA: <code>{escape(verified["source_sha256"])}</code></p>'
        f'<blockquote style="border-left:4px solid #64748b;padding-left:12px">'
        f'{marked}</blockquote>'
        f'<p><a href="{uri}" target="_blank" rel="noopener noreferrer">'
        'Resmî HTML’de birebir metne git (tarayıcı destekliyorsa) ↗</a></p>'
        "<small>Tarayıcı desteklemiyorsa resmî belge baştan açılabilir. "
        "Yukarıdaki pasaj özgün, hash-denetimli metin düğümünden üretildi; "
        "mevzuatın ilgili yılda yürürlükte olduğunu ve ödeme hakkını "
        "kanıtlamaz.</small></section>"
    )
