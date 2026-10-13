"""SSS ve Soru-Cevap Asistanı Servisi."""

from __future__ import annotations

import logging
from typing import Any

import pandas as pd

from frontend_pc.api_client import ApiClient

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
            f"📚 **SSS Kütüphanesi:** Toplam **{total} adet** kayıt "
            f"({verified} doğrulanmış olarak işaretli, {cats} kategori). Bu kayıtların mevzuatla güncelliği ayrıca kontrol edilmelidir. "
            "Aşağıdaki tablodan soru seçebilir veya yukarıdaki sohbet alanına serbestçe yazabilirsiniz."
        )
    return (
        "📚 **Doğrulanmış Tarımsal Çözüm Veritabanı:** SSS kayıtları mevcut olabilir; özgün kaynaklar için belge analiz asistanını kullanın."
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
                "Kaynak notu (doğrulanmamış pasaj)": citation,
            }
        )
    return pd.DataFrame(rows)


def ask_assistant(
    user_message: str,
    chat_history: list[dict[str, str]] | None,
    client: ApiClient | None = None,
) -> tuple[str, list[dict[str, str]]]:
    """Backward-compatible default unfiltered document RAG chat."""
    return ask_assistant_filtered(user_message, chat_history, None, client=client)


def ask_assistant_filtered(
    user_message: str,
    chat_history: list[dict[str, str]] | None,
    source_id: str | None = None,
    *,
    client: ApiClient | None = None,
) -> tuple[str, list[dict[str, str]]]:
    """Optional exact source filter, never a guessed document reference."""
    if not user_message or not user_message.strip():
        return "", list(chat_history or [])

    api = client or ApiClient()
    result = api.ask_documents(
        user_message.strip(), top_k=4,
        source_id=source_id if source_id else None,
    )
    answer = str(result.get("answer") or "Belgelerden cevap üretilemedi.")
    citations = result.get("citations") or []
    lines = [answer]
    if citations:
        lines.extend(["", "---", "#### İnceleyebileceğiniz özgün kaynaklar"])
        for index, item in enumerate(citations[:6], 1):
            if not isinstance(item, dict):
                continue
            from urllib.parse import urlsplit
            url = item.get("url")
            document_sha = str(item.get("source_sha256") or "")
            label = str(item.get("title") or item.get("source_id") or "Belge")
            page = item.get("page_number")
            section = str(item.get("section") or "")
            method = str(item.get("extraction_method") or "UNKNOWN")
            if isinstance(url, str):
                origin = urlsplit(url)
                is_local_page = (
                    url.startswith("/documents/view/")
                    and ".." not in url and "//" not in url
                )
                if is_local_page or (
                    origin.scheme == "https" and origin.hostname in {
                    "resmigazete.gov.tr", "www.resmigazete.gov.tr",
                    "tarimorman.gov.tr", "www.tarimorman.gov.tr",
                }
                ):
                    if is_local_page:
                        url = api.base_url.rstrip("/") + url
                    # No guessed HTML page number; PDF link page is in
                    # original indexed metadata, not from a topic guess.
                    loc = f"PDF sayfa {page}" if type(page) is int else section
                    lines.append(
                        f"{index}. [{label} — {loc}]({url}) "
                        f"(okuma: {method}, kaynak SHA: `{document_sha[:16]}…`)"
                    )
                    if (
                        type(page) is int
                        and len(document_sha) == 64
                        and all(ch in "0123456789abcdef" for ch in document_sha)
                    ):
                        source_id = str(item.get("source_id") or "")
                        if is_local_page:
                            screenshot_url = url
                        elif source_id == (
                            "RG_DISCOVERED_" + document_sha[:16].upper()
                        ):
                            screenshot_url = (
                                f"{api.base_url.rstrip('/')}"
                                f"/documents/annual-original-page/{document_sha}/page/{page}"
                            )
                        else:
                            screenshot_url = (
                                f"{api.base_url.rstrip('/')}"
                                f"/documents/original-page/{document_sha}/page/{page}"
                            )
                        lines.append(
                            f"   · [Gerçek sayfa ekran görüntüsü]({screenshot_url})"
                        )
                    if method in ("OCR_DRAFT", "OCR_UNREVIEWED"):
                        lines.append("   · OCR ön okuması; rakam ve sözcükleri görüntüyle karşılaştırın.")
    else:
        lines.append(
            "\n**Not:** Kaynak bulunamadığında belge dışından açıklama "
            "uydurulmadı. Eksik OCR sayfaları için özgün sayfayı açabilirsiniz."
        )

    history = list(chat_history or [])
    history.append({"role": "user", "content": user_message.strip()})
    history.append({"role": "assistant", "content": "\n".join(lines)})
    return "", history
