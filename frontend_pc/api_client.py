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

    def synthesize_dynamic_rules(
        self,
        document_sha256: str,
        production_year: int | None = None,
        default_base_coef: str | None = None,
    ) -> dict[str, Any]:
        """Synthesize and persist declarative dynamic rules from discovered legislation."""
        try:
            body: dict[str, Any] = {"document_sha256": document_sha256}
            if production_year:
                body["production_year"] = production_year
            if default_base_coef:
                body["default_base_coefficient"] = default_base_coef
            response = self._request("POST", "/admin/rules/synthesize", json=body)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def list_dynamic_rules(
        self,
        year: int | None = None,
        program_key: str | None = None,
        crop_code: str | None = None,
    ) -> list[dict[str, Any]]:
        """List and filter dynamic rules stored in repository."""
        try:
            params: dict[str, Any] = {}
            if year:
                params["year"] = year
            if program_key:
                params["program_key"] = program_key
            if crop_code:
                params["crop_code"] = crop_code
            response = self._request("GET", "/admin/rules/dynamic", params=params)
            response.raise_for_status()
            return response.json()
        except Exception:
            return []

    def dynamic_evaluate(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Evaluate a farmer parcel across all dynamic support programs."""
        try:
            response = self._request("POST", "/api/v1/rules/dynamic-evaluate", json=payload)
            response.raise_for_status()
            return response.json()
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def create_attestation(
        self,
        production_year: int,
        actor_id: str,
        role: str,
        private_key_b64: str,
        source_document_sha256: str | None = None,
        statement: str | None = None,
        notes: str = "",
    ) -> dict[str, Any]:
        """Sign and generate an official Ed25519 legal attestation for dynamic rules."""
        key = os.getenv("TARIM_RAG_ADMIN_API_KEY")
        headers = {"X-Admin-Key": key} if key else {}
        try:
            body: dict[str, Any] = {
                "production_year": production_year,
                "actor_id": actor_id,
                "role": role,
                "private_key_b64": private_key_b64,
                "notes": notes,
            }
            if source_document_sha256:
                body["source_document_sha256"] = source_document_sha256
            if statement:
                body["statement"] = statement
            resp = self._request("POST", "/admin/rules/attestation", json=body, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            return {"status": "ERROR", "message": f"HTTP {exc.response.status_code}: {exc.response.text}"}
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def activate_rules(
        self,
        production_year: int,
        source_document_sha256: str,
        reviewer_attestation: dict[str, Any],
        approver_attestation: dict[str, Any],
        trusted_keys: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Submit dual legal attestations to elevate rules from DRAFT to VERIFIED in WORM audit."""
        key = os.getenv("TARIM_RAG_ADMIN_API_KEY")
        headers = {"X-Admin-Key": key} if key else {}
        try:
            body = {
                "production_year": production_year,
                "source_document_sha256": source_document_sha256,
                "reviewer_attestation": reviewer_attestation,
                "approver_attestation": approver_attestation,
                "trusted_keys": trusted_keys,
            }
            resp = self._request("POST", "/admin/rules/activate", json=body, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            return {"status": "ERROR", "message": f"HTTP {exc.response.status_code}: {exc.response.text}"}
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def get_activation_status(self, year: int = 2026) -> dict[str, Any]:
        """Get rule activation state, manifest info, and WORM chain integrity status."""
        key = os.getenv("TARIM_RAG_ADMIN_API_KEY")
        headers = {"X-Admin-Key": key} if key else {}
        try:
            resp = self._request("GET", "/admin/rules/activation-status", params={"year": year}, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def revoke_rules(
        self,
        production_year: int,
        actor_id: str,
        reason: str,
        signature_b64: str | None = None,
    ) -> dict[str, Any]:
        """Instantly revoke rule activation (fail-closed) and append revocation event to WORM log."""
        key = os.getenv("TARIM_RAG_ADMIN_API_KEY")
        headers = {"X-Admin-Key": key} if key else {}
        try:
            body = {
                "production_year": production_year,
                "actor_id": actor_id,
                "reason": reason,
                "signature_b64": signature_b64,
            }
            resp = self._request("POST", "/admin/rules/revoke", json=body, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except httpx.HTTPStatusError as exc:
            return {"status": "ERROR", "message": f"HTTP {exc.response.status_code}: {exc.response.text}"}
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def get_worm_audit_log(
        self,
        year: int | None = None,
        event_type: str | None = None,
        limit: int = 50,
    ) -> dict[str, Any]:
        """Retrieve WORM immutable audit log blocks and chain integrity verification."""
        key = os.getenv("TARIM_RAG_ADMIN_API_KEY")
        headers = {"X-Admin-Key": key} if key else {}
        try:
            params: dict[str, Any] = {"limit": limit}
            if year:
                params["year"] = year
            if event_type:
                params["event_type"] = event_type
            resp = self._request("GET", "/admin/rules/worm-audit", params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc), "history": []}

    # -----------------------------------------------------------------------
    # P0-13: Gerçek Kurumsal Onay, HSM/KMS ve Güvenli Yayın İstemci Yöntemleri
    # -----------------------------------------------------------------------

    def get_kms_status(self) -> dict[str, Any]:
        """Fetch KMS / HSM provider status and registered keys."""
        key = os.getenv("TARIM_RAG_ADMIN_API_KEY")
        headers = {"X-Admin-Key": key} if key else {}
        try:
            resp = self._request("GET", "/admin/enterprise/kms/status", headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc), "keys": []}

    def audit_database_roles(self) -> dict[str, Any]:
        """Audit PostgreSQL enterprise roles, grants, and RLS policies."""
        key = os.getenv("TARIM_RAG_ADMIN_API_KEY")
        headers = {"X-Admin-Key": key} if key else {}
        try:
            resp = self._request("GET", "/admin/enterprise/db-roles/audit", headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def build_secure_release(
        self,
        production_year: int = 2026,
        key_alias: str = "release-master",
        enforce_verified_only: bool = True,
    ) -> dict[str, Any]:
        """Build cryptographically sealed release bundle via KMS."""
        key = os.getenv("TARIM_RAG_ADMIN_API_KEY")
        headers = {"X-Admin-Key": key} if key else {}
        try:
            body = {
                "production_year": production_year,
                "key_alias": key_alias,
                "enforce_verified_only": enforce_verified_only,
            }
            resp = self._request("POST", "/admin/enterprise/release/build", json=body, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def verify_secure_release(
        self,
        package_path: str,
        expected_key_alias: str = "release-master",
    ) -> dict[str, Any]:
        """Verify cryptographic integrity and KMS seal of a release package."""
        key = os.getenv("TARIM_RAG_ADMIN_API_KEY")
        headers = {"X-Admin-Key": key} if key else {}
        try:
            body = {
                "package_path": package_path,
                "expected_key_alias": expected_key_alias,
            }
            resp = self._request("POST", "/admin/enterprise/release/verify", json=body, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def enterprise_revoke(
        self,
        rule_id: str,
        reason_code: str,
        legal_reference: str,
        authorized_officer: str,
        notes: str = "",
        key_alias: str = "legal-approver",
    ) -> dict[str, Any]:
        """Execute enterprise rule revocation with reason taxonomy and KMS certificate."""
        key = os.getenv("TARIM_RAG_ADMIN_API_KEY")
        headers = {"X-Admin-Key": key} if key else {}
        try:
            body = {
                "rule_id": rule_id,
                "reason_code": reason_code,
                "legal_reference": legal_reference,
                "authorized_officer": authorized_officer,
                "notes": notes,
                "key_alias": key_alias,
            }
            resp = self._request("POST", "/admin/enterprise/revoke/enterprise", json=body, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}

    def export_evidence_vault(
        self,
        production_year: int = 2026,
        signer_officer: str = "ChiefLegalAuditor",
        key_alias: str = "legal-approver",
    ) -> dict[str, Any]:
        """Export signed, court-admissible legal evidence vault (ZIP)."""
        key = os.getenv("TARIM_RAG_ADMIN_API_KEY")
        headers = {"X-Admin-Key": key} if key else {}
        try:
            params = {
                "production_year": production_year,
                "signer_officer": signer_officer,
                "key_alias": key_alias,
            }
            resp = self._request("GET", "/admin/enterprise/evidence-vault/export", params=params, headers=headers)
            resp.raise_for_status()
            return resp.json()
        except Exception as exc:
            return {"status": "ERROR", "message": str(exc)}





