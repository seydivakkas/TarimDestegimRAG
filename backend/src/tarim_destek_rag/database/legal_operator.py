"""P0-7 offline legal officer authentication + Vault Transit Ed25519 sign adaptor.

NO personal identity records, key material, KMS token or cloud credentials are
shipped. Enrollment is an independent organization/IdP administrator action.
Production signing must occur in a separate, access-controlled operator job.

Trusted files MUST be provisioned by immutable configuration management, not
edited by a reviewer. JWTs are validated from pinned RS256 JWKS, not from
untrusted JWT jku/x5u/kid links. Vault private keys never leave the service.
"""

from __future__ import annotations

import base64
import binascii
import json
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlsplit

import httpx
import jwt
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

from tarim_destek_rag.database.legal_approvals import (
    TRUST_ENV, _trusted_public_keys, attestation_message, subject_digest,
    subject_payload,
)

SAFE_VAULT_KEY = re.compile(r"^[a-zA-Z0-9_-]{1,96}$")
SAFE_PRINCIPAL = re.compile(r"^[a-zA-Z0-9_.:@/-]{3,180}$")
OIDC_TRUST_ENV = "TARIM_RAG_LEGAL_IDP_TRUST_JSON"
OFFICERS_ENV = "TARIM_RAG_LEGAL_OFFICERS_JSON"
VAULT_ADDR_ENV = "TARIM_RAG_VAULT_ADDR"


@dataclass(frozen=True)
class LegalOfficer:
    principal_id: str
    role: str
    vault_key: str
    oidc_subject: str


def _configured_json(name: str) -> dict:
    try:
        value = json.loads(os.environ[name])
        if not isinstance(value, dict):
            raise ValueError("Expected JSON object")
        return value
    except (KeyError, ValueError, TypeError) as exc:
        raise ValueError(f"Missing or invalid trusted deployment policy: {name}") from exc


def authenticate_legal_officer(id_token: str, expected_role: str) -> LegalOfficer:
    """Resolve OIDC *subject*, not an untrusted role claim or user-supplied name."""
    if expected_role not in ("REVIEWER", "APPROVER"):
        raise ValueError("Unsupported legal role")
    cfg = _configured_json(OIDC_TRUST_ENV)
    officers = _configured_json(OFFICERS_ENV)
    try:
        issuer = cfg["issuer"]
        audience = cfg["audience"]
        keys = cfg["jwks"]["keys"]
        if not isinstance(issuer, str) or not issuer.startswith("https://"):
            raise ValueError("Invalid OIDC issuer")
        if not isinstance(audience, str) or not audience:
            raise ValueError("Missing OIDC audience")
        header = jwt.get_unverified_header(id_token)
        if header.get("alg") != "RS256" or not isinstance(header.get("kid"), str):
            raise ValueError("Unsupported ID token signature algorithm")
        candidates = [k for k in keys if k.get("kid") == header["kid"]
                      and k.get("kty") == "RSA" and k.get("use", "sig") == "sig"]
        if len(candidates) != 1:
            raise ValueError("OIDC signing key is not uniquely pinned")
        public = jwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(candidates[0]))
        claims = jwt.decode(
            id_token, key=public, algorithms=["RS256"],
            issuer=issuer, audience=audience, leeway=15,
            options={"require": ["iss", "aud", "sub", "iat", "exp", "auth_time"]},
        )
        now = datetime.now(timezone.utc).timestamp()
        if (
            not isinstance(claims.get("sub"), str)
            or not isinstance(claims.get("iat"), (int, float))
            or now - claims["iat"] > 300  # short-lived operator identity
            or not isinstance(claims.get("auth_time"), (int, float))
            or now - claims["auth_time"] > 900  # recent interactive authentication
            or claims["iat"] > now + 15
            or claims["auth_time"] > now + 15
        ):
            raise ValueError("Operator authentication is stale or not interactive")
        subject = claims["sub"]
        registration = officers.get(subject)
        if not isinstance(registration, dict) or registration.get("role") != expected_role:
            raise ValueError("Subject is not registered for the requested independent role")
        principal = registration["principal_id"]
        key_name = registration["vault_key"]
        if not SAFE_PRINCIPAL.fullmatch(principal) or not SAFE_VAULT_KEY.fullmatch(key_name):
            raise ValueError("Registered operator identity/key is malformed")
        trusted = _trusted_public_keys()
        if principal not in trusted or trusted[principal][0] != expected_role:
            raise ValueError("Operator is not in independent Ed25519 verification store")
        return LegalOfficer(principal, expected_role, key_name, subject)
    except (jwt.PyJWTError, KeyError, IndexError, TypeError, ValueError) as exc:
        raise ValueError("OIDC officer identity or authorization verification failed") from exc


def _vault_url() -> str:
    addr = os.environ.get(VAULT_ADDR_ENV, "")
    parsed = urlsplit(addr)
    # No private/local HTTP fallback, URL userinfo, query or arbitrary path.
    if (
        parsed.scheme != "https" or not parsed.hostname or parsed.username
        or parsed.password or parsed.query or parsed.fragment or parsed.path not in ("", "/")
    ):
        raise ValueError("Vault requires explicitly trusted HTTPS endpoint")
    return addr.rstrip("/")


def build_vault_signed_envelope(
    subject,
    officer: LegalOfficer,
    *,
    vault_token: str,
    acknowledged_subject_digest: str,
    client: httpx.Client | None = None,
    signed_at: str | None = None,
) -> dict:
    """Call designated role-scoped Transit key; verify returned Ed25519 bytes locally.

    A Vault ACL must restrict each officer's token to their own transit/sign key.
    Operator must inspect canonical subject payload and acknowledge its full digest.
    """
    digest = subject_digest(subject)
    if acknowledged_subject_digest != digest:
        raise ValueError("Exact canonical subject digest was not acknowledged")
    if len(vault_token) < 20 or "\n" in vault_token:
        raise ValueError("Vault operator credential missing or malformed")
    if not SAFE_VAULT_KEY.fullmatch(officer.vault_key):
        raise ValueError("Unsafe signing key name")
    trusted = _trusted_public_keys().get(officer.principal_id)
    if trusted is None or trusted[0] != officer.role:
        raise ValueError("Trusted public key does not match officer identity")
    kind = subject_payload(subject)["kind"]
    timestamp = signed_at or datetime.now(timezone.utc).isoformat(timespec="seconds")
    message = attestation_message(
        kind=kind, record_id=subject.id, digest=digest,
        source_sha256=subject.source_version.content_hash,
        role=officer.role, principal_id=officer.principal_id,
        signed_at=timestamp,
    )
    url = f"{_vault_url()}/v1/transit/sign/{officer.vault_key}"
    created_client = client is None
    remote = client if client is not None else httpx.Client(
        timeout=10, follow_redirects=False, trust_env=False,
    )
    try:
        response = remote.post(
            url,
            headers={"X-Vault-Token": vault_token},
            json={"input": base64.b64encode(message).decode("ascii"), "prehashed": False},
        )
        response.raise_for_status()
        signature_text = response.json()["data"]["signature"]
        match = re.fullmatch(r"vault:v([1-9][0-9]*):([A-Za-z0-9+/]+={0,2})", signature_text)
        if match is None:
            raise ValueError("Transit response is not a supported versioned signature")
        signature = base64.b64decode(match.group(2), validate=True)
        if len(signature) != 64:
            raise ValueError("Invalid Ed25519 signature length")
        trusted[1].verify(signature, message)
    except (httpx.HTTPError, KeyError, TypeError, json.JSONDecodeError,
            InvalidSignature, binascii.Error, ValueError) as exc:
        raise ValueError("Vault transit failed to prove signature for pinned officer/key") from exc
    finally:
        if created_client:
            remote.close()
    return {
        "role": officer.role,
        "principal_id": officer.principal_id,
        "subject_digest": digest,
        "source_sha256": subject.source_version.content_hash,
        "signed_at": timestamp,
        "signature_b64": base64.b64encode(signature).decode("ascii"),
    }
