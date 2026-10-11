"""P0-01–P0-05 regression: untrusted labels, missing scope and signer fallbacks.

ÖZEL LİSANS — TÜM HAKLAR SAKLIDIR
Telif Hakkı (c) 2026 Seydi Eryılmaz (@seydivakkas)
"""
from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from tarim_destek_rag.api.main import app
from tarim_destek_rag.rules.bitemporal_engine import BitemporalRuleCatalog
from tarim_destek_rag.rules.dynamic_support_evaluator import DynamicSupportEvaluator
from tarim_destek_rag.rules.legal_activation import (
    RuleActivationPipeline,
    TrustedKeyMismatchError,
)
from tarim_destek_rag.security.kms_provider import (
    HashiCorpVaultProvider,
    PKCS11HsmProvider,
    get_kms_provider,
)


def _candidate(status: str) -> dict:
    return {
        "schema_version": 1,
        "rule_id": "RULE-2030-BASE",
        "program_key": "BASIC_SUPPORT",
        "crop_code": "BUĞDAY",
        "production_year": 2030,
        "province": "*",
        "district": "*",
        "base_coefficient": "510.00",
        "category_multiplier": "1.0000",
        "official_unit_amount": "510.00",
        "unit": "TRY/da",
        "effective_from": "2030-01-01",
        "effective_to": "2030-12-31",
        "published_at": "2029-12-15T00:00:00+00:00",
        "discovered_at": "2029-12-16T00:00:00+00:00",
        "source_document_sha256": "a" * 64,
        "source_sentence_id": 5,
        "conditions": {"all_of": [{"field": "cks_registered", "op": "eq", "value": True}]},
        "review_status": status,
    }


@pytest.mark.parametrize("status", ["DRAFT", "VERIFIED", "REVOKED", "HOLD"])
@pytest.mark.parametrize("registered", [True, False])
def test_untrusted_legal_label_cannot_pay_or_deny(status: str, registered: bool) -> None:
    catalog = BitemporalRuleCatalog.from_candidates([_candidate(status)])
    result = catalog.evaluate(
        program_key="BASIC_SUPPORT", crop_code="BUĞDAY",
        production_year=2030, as_of_date=date(2030, 6, 1),
        facts={"cks_registered": registered},
    )
    assert result.status == "REVIEW"
    assert result.payable_amount is None


def test_known_missing_future_year_never_falls_back_or_becomes_zero() -> None:
    catalog = BitemporalRuleCatalog.from_candidates([_candidate("VERIFIED")])
    summary = DynamicSupportEvaluator.evaluate_parcel(
        catalog=catalog, production_year=2031,
        as_of_date=date(2031, 6, 1), crop="BUĞDAY",
        area_da=Decimal("10"), province="KONYA", district="KARATAY",
    )
    assert summary.overall_status == "UNKNOWN"
    assert summary.total_payable_amount is None
    assert all(item.payable_amount is None for item in summary.items)


def test_fake_verified_label_is_not_external_approval() -> None:
    catalog = BitemporalRuleCatalog.from_candidates([_candidate("VERIFIED")])
    summary = DynamicSupportEvaluator.evaluate_parcel(
        catalog=catalog, production_year=2030,
        as_of_date=date(2030, 6, 1), crop="BUĞDAY",
        area_da=Decimal("10"), province="KONYA", district="KARATAY",
    )
    assert summary.total_payable_amount is None
    assert summary.overall_status in ("REVIEW", "UNKNOWN")


def test_activation_rejects_request_supplied_trust_root(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TARIM_RAG_LEGAL_SECURITY_PROFILE", "production")
    pipeline = RuleActivationPipeline(tmp_path)
    with pytest.raises(TrustedKeyMismatchError, match="Request-supplied"):
        pipeline._load_trusted_store({"reviewer": {"public_key_b64": "self-issued"}})


def test_missing_manifest_and_missing_trusted_keys_never_authorize(tmp_path, monkeypatch) -> None:
    monkeypatch.setenv("TARIM_RAG_LEGAL_SECURITY_PROFILE", "production")
    monkeypatch.setenv("TARIM_RAG_LEGAL_ACTIVATION_ENABLED", "true")
    monkeypatch.delenv("TARIM_RAG_LEGAL_TRUSTED_KEYS_JSON", raising=False)
    assert not RuleActivationPipeline(tmp_path).active_release_is_verified(2030)


def test_production_http_private_key_signing_blocked(monkeypatch) -> None:
    monkeypatch.setenv("TARIM_RAG_LEGAL_SECURITY_PROFILE", "production")
    monkeypatch.setenv("TARIM_RAG_ADMIN_API_KEY", "test-p0-secret")
    client = TestClient(app)
    response = client.post(
        "/admin/rules/attestation",
        headers={"X-Admin-Key": "test-p0-secret"},
        json={
            "production_year": 2030,
            "actor_id": "UNTRUSTED",
            "role": "LEGAL_REVIEWER",
            "private_key_b64": "AA==",
            "source_document_sha256": "a" * 64,
        },
    )
    assert response.status_code == 403


def test_unavailable_kms_never_silently_signs_in_software(monkeypatch) -> None:
    vault = HashiCorpVaultProvider(vault_url="https://vault.example.org", token="test-token")
    assert vault.health_check()["status"] == "UNAVAILABLE"
    assert vault.verify_signature("key", b"data", "sig") is False
    with pytest.raises(RuntimeError, match="Vault Transit"):
        vault.sign_payload("key", b"data")

    hsm = PKCS11HsmProvider(slot_id=1)
    assert hsm.health_check()["hardware_token_present"] is False
    with pytest.raises(RuntimeError, match="HSM PKCS11"):
        hsm.sign_payload("key", b"data")

    monkeypatch.setenv("TARIM_RAG_LEGAL_SECURITY_PROFILE", "production")
    with pytest.raises(RuntimeError, match="Software KMS"):
        get_kms_provider("software")
