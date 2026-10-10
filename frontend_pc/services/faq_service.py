"""SSS ve Soru-Cevap Asistanı Servisi."""

from __future__ import annotations

import logging
from html import escape
from typing import Any

import pandas as pd

from frontend_pc.api_client import ApiClient
from tarim_destek_rag.citations.document_links import (
    format_highlighted_citation_card,
)

logger = logging.getLogger("frontend_pc.services.faq")


def get_faq_categories(client: ApiClient | None = None) -> list[str]:
    """Tüm benzersiz SSS kategorilerini listeler."""
    api = client or ApiClient()
    faqs = api.get_faqs()
    cats = sorted(list({f.get("category", "") for f in faqs if f.get("category")}))
    return ["Tümü"] + cats


def get_faq_banner_text(client: ApiClient | None = None) -> str:
    """SSS veritabanı istatistik özet metnini döner."""
    api = client or ApiClient()
    stats = api.get_faq_stats()
    total = stats.get("total_count", 0)
    verified = stats.get("verified_count", 0)
    cats = len(stats.get("category_counts", {}))
    if total > 0:
        return (
            f"📚 **Tarımsal Soru-Cevap Veritabanı:** Toplam **{total} adet** kayıt "
            f"({verified} doğrulanmış olarak işaretli, {cats} kategori). Bu kayıtların mevzuatla güncelliği ayrıca kontrol edilmelidir. "
            "Aşağıdaki tablodan soru seçebilir veya yukarıdaki sohbet alanına serbestçe yazabilirsiniz."
        )
    return (
        "📚 **Tarımsal Soru-Cevap Veritabanı:** Yürürlükteki mevzuat ve ziraî rehberler indekslenmiştir."
    )


def get_faq_table(
    category_filter: str = "Tümü",
    search_query: str = "",
    client: ApiClient | None = None,
) -> pd.DataFrame:
    """Kategori ve arama kriterine göre filtrelenmiş SSS tablosu döner."""
    api = client or ApiClient()
    cat_param = None if category_filter == "Tümü" else category_filter
    faqs = api.get_faqs(category=cat_param, search=search_query)
    rows = []
    for f in faqs:
        ans_short = f.get("answer", "")
        if len(ans_short) > 130:
            ans_short = ans_short[:127] + "..."
        citation = f.get("legal_citation") or f.get("citation") or "-"
        rows.append(
            {
                "Kategori": f.get("category", "-"),
                "Soru": f.get("question", "-"),
                "Özet Cevap": ans_short,
                "Resmî Yasal Dayanak": citation,
            }
        )
    return pd.DataFrame(rows)


def ask_assistant(
    user_message: str,
    chat_history: list[dict[str, str]],
    client: ApiClient | None = None,
) -> tuple[str, list[dict[str, str]]]:
    """Chatbot / Semantik Arama Asistanı (Sıfır LLM - Doğrulanmış Mevzuat)."""
    if not user_message or not user_message.strip():
        return "", chat_history

    api = client or ApiClient()
    resp = api.ask(user_message.strip(), top_k=3)
    answer = (
        resp.get("summary_answer_tr")
        or resp.get("answer")
        or "Sorunuza ilişkin mevzuatta doğrudan eşleşen madde bulunamadı."
    )
    chunks = resp.get("matched_chunks") or resp.get("citations", [])

    formatted_reply = f"{escape(str(answer))}\n\n"
    if chunks:
        formatted_reply += "---\n#### 📚 Aday kaynak metinleri (yalnız eşleşen pasajlar kanıttır):\n"
        for i, c in enumerate(chunks[:3], 1):
            if isinstance(c, dict):
                src = c.get("source_id", "RG")
                title = c.get("title", "Resmî Gazete")
                sec = c.get("section") or c.get("article_ref", "") or "Madde"
                raw_t = str(c.get("snippet") or c.get("text") or "")
                status = c.get("verification_status") or "UNVERIFIED_EXPLANATION"
                cit_dict = {
                    "title": f"[{i}] {title}",
                    "section": f"{sec} ({src})",
                    "year": c.get("year", 2026),
                    "snippet": raw_t if status != "UNVERIFIED_EXPLANATION"
                    else (raw_t if len(raw_t) <= 260 else raw_t[:260] + "..."),
                    "url": c.get("url"),
                    "verification_status": status,
                    "highlighted_pdf_url": c.get("highlighted_pdf_url"),
                    "document_sha256": c.get("document_sha256"),
                    "page_number": c.get("page_number"),
                }
                formatted_reply += f"{format_highlighted_citation_card(cit_dict, 'REVIEW')}\n\n"
            else:
                formatted_reply += (
                    f"\n**[{i}] Ön bilgi (resmî alıntı değildir):** {escape(str(c))}\n"
                )

    new_history = list(chat_history)
    new_history.append({"role": "user", "content": user_message})
    new_history.append({"role": "assistant", "content": formatted_reply})

    return "", new_history
