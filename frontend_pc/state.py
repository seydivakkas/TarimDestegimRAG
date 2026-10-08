"""TarımDestekRAG PC Ortak Değerlendirme Durumu (Shared Evaluation State).

Çiftçi ve parsel bilgileri değişmedikçe tek bir /evaluate API çağrısı yapılmasını,
ekranlar arasında gezinildiğinde tutarların ve sonuçların korunmasını sağlar.
"""

from __future__ import annotations

import hashlib
import json
import logging
from typing import Any

from frontend_pc.api_client import ApiClient

logger = logging.getLogger("frontend_pc.state")


def compute_payload_hash(farmer_data: dict[str, Any], parcel_data: dict[str, Any]) -> str:
    """Çiftçi ve parsel girdilerini kanonik bir SHA-256 parmak izine dönüştürür."""
    canonical = {
        "farmer": {
            "province": str(farmer_data.get("province", "")).strip().upper(),
            "district": str(farmer_data.get("district", "")).strip().upper(),
            "cks_status": farmer_data.get("cks_status"),
            "age_group": str(farmer_data.get("age_group", "")),
            "gender": str(farmer_data.get("gender", "")),
        },
        "parcel": {
            "crop": str(parcel_data.get("crop", "")).strip().upper(),
            "area_da": float(parcel_data.get("area_da", 0.0)),
            "production_year": int(parcel_data.get("production_year", 2026)),
            "irrigation": str(parcel_data.get("irrigation", "UNKNOWN")),
            "seed_certificate_available": parcel_data.get("seed_certificate_available"),
            "sapling_certificate_available": parcel_data.get("sapling_certificate_available"),
            "is_closed_orchard": parcel_data.get("is_closed_orchard"),
        },
    }
    raw = json.dumps(canonical, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class EvaluationStateManager:
    """Tekil değerlendirme sonucunu önbelleğe alan ve durum sürekliliğini sağlayan yönetici."""

    def __init__(self) -> None:
        self._current_hash: str | None = None
        self._current_response: dict[str, Any] | None = None
        self._call_count: int = 0

    @property
    def call_count(self) -> int:
        """Yapılan gerçek backend /evaluate çağrısı adedi."""
        return self._call_count

    def get_current_response(self) -> dict[str, Any] | None:
        return self._current_response

    def clear(self) -> None:
        """Önbelleği temizler."""
        self._current_hash = None
        self._current_response = None

    def get_or_evaluate(
        self,
        farmer_data: dict[str, Any],
        parcel_data: dict[str, Any],
        client: ApiClient,
        force_refresh: bool = False,
    ) -> tuple[dict[str, Any], bool]:
        """Girdiler değişmemişse önbellekteki sonucu döner; değişmişse tek API çağrısı yapar.

        Returns:
            tuple[dict, bool]: (Değerlendirme yanıtı, Önbellekten mi geldi?)
        """
        payload_hash = compute_payload_hash(farmer_data, parcel_data)

        if not force_refresh and self._current_hash == payload_hash and self._current_response is not None:
            logger.debug("EvaluationState: Girdi değişmedi, önbellekten sonuç dönülüyor (hash=%s)", payload_hash[:8])
            return self._current_response, True

        logger.info("EvaluationState: Yeni girdi algılandı, backend /evaluate çağrılıyor (hash=%s)", payload_hash[:8])
        resp = client.evaluate_full(farmer_data, parcel_data)
        self._call_count += 1
        self._current_hash = payload_hash
        self._current_response = resp
        return resp, False


# Global tekil durum örneği
global_eval_state = EvaluationStateManager()
