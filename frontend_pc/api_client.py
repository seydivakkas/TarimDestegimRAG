"""TarımDestekRAG PC Frontend API İstemcisi.

FastAPI arka uç servisi ile iletişim kurar. Tüm veri alışverişi HTTP REST API
üzerinden gerçekleştirilir; Gradio arayüzünde iş mantığı (business logic) tutulmaz.
"""

from __future__ import annotations

import os
from typing import Any

import httpx

API_BASE_URL = os.getenv("API_BASE_URL", "http://127.0.0.1:8000")


class ApiClient:
    """TarımDestekRAG FastAPI REST istemcisi."""

    def __init__(
        self,
        base_url: str = API_BASE_URL,
        client: httpx.Client | None = None,
        timeout: float = 30.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._custom_client = client
        self.timeout = timeout

    def _request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        """İsteği özel istemci veya yeni istemci üzerinden yürütür."""
        url = f"{self.base_url}{path}" if self.base_url else path
        if self._custom_client is not None:
            return self._custom_client.request(method, url, **kwargs)
        with httpx.Client(timeout=self.timeout) as client:
            return client.request(method, url, **kwargs)

    def check_health(self) -> dict[str, Any]:
        """Arka uç servisinin sağlık durumunu kontrol eder."""
        try:
            resp = self._request("GET", "/health")
            if resp.status_code == 200:
                return resp.json()
            return {"status": "error", "code": resp.status_code, "message": resp.text}
        except Exception as e:
            return {"status": "unreachable", "message": str(e)}

    def is_online(self) -> bool:
        """Sunucu ayakta mı?"""
        res = self.check_health()
        return res.get("status") == "ok"

    def get_supports(self) -> list[dict[str, Any]]:
        """Mevcut 2026 destek programları listesini çeker."""
        try:
            resp = self._request("GET", "/supports")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return [{"id": "ERROR", "name": f"Bağlantı Hatası: {e}", "year": 2026, "active": False}]

    def get_sources(self) -> list[dict[str, Any]]:
        """Kayıtlı resmî mevzuat kaynaklarını çeker."""
        try:
            resp = self._request("GET", "/sources")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return [{"id": "ERROR", "title": f"Kaynaklar alınamadı: {e}", "authority": "UNKNOWN"}]

    def evaluate_full(
        self,
        farmer_payload: dict[str, Any],
        parcel_payload: dict[str, Any],
    ) -> dict[str, Any]:
        """Çiftçi ve parsel için tam uygunluk, hesaplama ve açıklama değerlendirmesi."""
        try:
            resp = self._request(
                "POST",
                "/evaluate",
                json={"farmer": farmer_payload, "parcel": parcel_payload},
            )
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as e:
            return {"error": f"HTTP Hatası {e.response.status_code}: {e.response.text}"}
        except Exception as e:
            return {"error": f"Sunucuya ulaşılamadı: {e}"}

    def ask(self, query: str, top_k: int = 5) -> dict[str, Any]:
        """Mevzuat içi semantik arama ve soru-cevap sorgusu (Sıfır LLM)."""
        try:
            resp = self._request(
                "POST",
                "/ask",
                json={"question": query, "top_k": top_k},
            )
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {
                "question": query,
                "summary_answer_tr": f"Arama servisine ulaşılamadı: {e}",
                "matched_chunks": [],
                "source_titles": [],
            }

    def get_faqs(self, category: str | None = None, search: str | None = None) -> list[dict[str, Any]]:
        """2026 Resmî Çiftçi Sıkça Sorulan Sorular (SSS) kütüphanesini getirir."""
        try:
            params: dict[str, str] = {}
            if category and category != "Tümü":
                params["category"] = category
            if search and search.strip():
                params["search"] = search.strip()
            resp = self._request("GET", "/faqs", params=params)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            try:
                from tarim_destek_rag.retrieval.knowledge_base import FARMER_FAQ_LIST
                res = FARMER_FAQ_LIST
                if category and category != "Tümü":
                    res = [f for f in res if category.lower() in f.get("category", "").lower()]
                if search and search.strip():
                    sq = search.strip().lower()
                    res = [f for f in res if sq in f.get("question", "").lower() or sq in f.get("answer", "").lower()]
                return res
            except Exception:
                return []

    def get_faq_stats(self) -> dict[str, Any]:
        """Tarımsal SSS veritabanı istatistiklerini getirir."""
        try:
            resp = self._request("GET", "/faqs/stats")
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return {"total_count": 0, "verified_count": 0, "category_counts": {}}

    def harvest_faqs(self) -> dict[str, Any]:
        """İnternet ve resmî portallardan soru-cevap veri tabanını günceller / senkronize eder."""
        try:
            resp = self._request("POST", "/faqs/harvest")
            resp.raise_for_status()
            return resp.json()
        except Exception as e:
            return {"status": "ERROR", "message": f"Bağlantı hatası: {e}"}

    def scan_legal_updates(self, production_year: int) -> dict[str, Any]:
        """One-click discovery; never publish unreviewed legislative changes."""
        key = os.getenv("TARIM_RAG_ADMIN_API_KEY")
        if not key:
            return {
                "status": "ADMIN_NOT_CONFIGURED",
                "message": "Güncelleme taraması yönetici anahtarı olmadan kapalıdır.",
            }
        try:
            response = self._request(
                "POST", "/admin/legal-updates/scan",
                params={"year": int(production_year)},
                headers={"X-Admin-Key": key}, timeout=120,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            return {"status": "ERROR", "message": f"Resmî kaynak taraması başarısız: {exc}"}

    def get_grounding_evidence(self, sentence_id: int, year: int) -> dict[str, Any]:
        """Read authenticated-by-source, but unapproved, exact PDF citation details."""
        try:
            response = self._request(
                "GET", f"/api/v1/grounding/evidence/{sentence_id}",
                params={"year": year},
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def get_grounding_page_bytes(
        self, sentence_id: int, page: int, year: int,
    ) -> bytes | None:
        """Fetch visible yellow-marked actual page; no user-supplied coordinates."""
        try:
            response = self._request(
                "GET",
                f"/api/v1/grounding/image/{sentence_id}/page/{page}",
                params={"year": year, "fmt": "png"},
            )
            response.raise_for_status()
            if response.headers.get("content-type", "").split(";")[0] != "image/png":
                return None
            return response.content
        except Exception:
            return None

    def get_grounding_by_program(
        self, program_key: str, year: int, crop_code: str | None = None,
    ) -> dict[str, Any]:
        """Fetch exact verified PDF clause by program key and year."""
        try:
            params: dict[str, Any] = {"year": year}
            if crop_code:
                params["crop_code"] = crop_code
            response = self._request(
                "GET", f"/api/v1/grounding/program/{program_key}",
                params=params,
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def list_discovered_legislation(
        self, year: int | None = None, legislation_type: str | None = None,
    ) -> list[dict[str, Any]]:
        """Fetch list of structural official legislation discovered from portals."""
        try:
            params: dict[str, Any] = {}
            if year:
                params["year"] = year
            if legislation_type:
                params["legislation_type"] = legislation_type
            response = self._request(
                "GET", "/admin/legal-updates/legislation", params=params,
            )
            response.raise_for_status()
            return response.json()
        except Exception:
            return []

    def get_discovered_legislation_detail(self, document_sha256: str) -> dict[str, Any]:
        """Fetch detailed structural info (articles, annexes, dates) for legislation."""
        try:
            response = self._request(
                "GET", f"/admin/legal-updates/legislation/{document_sha256}",
            )
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}



