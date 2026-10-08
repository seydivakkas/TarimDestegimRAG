"""P0-7 preflight: real protocol, synthetic identities/Vault/S3 only.

No credential provisioning, public keys, retention policy or legal personnel
is ever invented as a real organizational authority by these tests.
"""

import base64
import io
import json
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import patch

import httpx
import jwt
import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session

from backend.tests.legal_approval_testkit import sign_subject, trust_pair
from backend.tests.unit.test_p0_2_verified_rates import add_rate
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.legal_audit import (
    _ensure_exact_locked_version, archive_signed_event, production_audit_valid,
)
from tarim_destek_rag.database.legal_approvals import two_person_approved
from tarim_destek_rag.database.legal_operator import (
    OFFICERS_ENV, OIDC_TRUST_ENV, VAULT_ADDR_ENV,
    authenticate_legal_officer, build_vault_signed_envelope,
)
from tarim_destek_rag.database.models import (
    LegalApprovalAttestationModel, LegalAuditReceiptModel,
    SourceModel, SupportProgramModel,
)


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as s:
        s.add_all([
            SupportProgramModel(
                id="BASIC_SUPPORT_2026", name="Test basic", year=2026, active=True
            ),
            SourceModel(
                source_id="SYNTHETIC-LEGAL-DOCUMENT",
                title="TEST ONLY", authority="OFFICIAL_GAZETTE",
                url="https://www.resmigazete.gov.tr/eskiler/2026/09/20260908-7.pdf",
                content_type="PDF", active=True,
            ),
        ])
        s.commit()
        yield s
    engine.dispose()


def b64url(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def oidc_fixture(monkeypatch):
    signers = trust_pair(monkeypatch)
    signer = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    numbers = signer.public_key().public_numbers()
    jwk = {"kty": "RSA", "kid": "test-idp-key-1", "use": "sig",
           "n": b64url(numbers.n.to_bytes((numbers.n.bit_length() + 7)//8, "big")),
           "e": b64url(numbers.e.to_bytes((numbers.e.bit_length() + 7)//8, "big"))}
    monkeypatch.setenv(OIDC_TRUST_ENV, json.dumps({
        "issuer": "https://idp.example.invalid/tenant",
        "audience": "tarim-legal-officer-cli",
        "required_mfa_acr": ["urn:example:phishing-resistant-mfa"],
        "jwks": {"keys": [jwk]},
    }))
    monkeypatch.setenv(OFFICERS_ENV, json.dumps({
        "issuer-subject-reviewer": {
            "principal_id": "test-reviewer", "role": "REVIEWER", "vault_key": "legal-reviewer"
        },
        "issuer-subject-approver": {
            "principal_id": "test-approver", "role": "APPROVER", "vault_key": "legal-approver"
        },
    }))
    monkeypatch.setenv(VAULT_ADDR_ENV, "https://vault.example.invalid")
    return signer, signers


def id_token(key, *, sub="issuer-subject-reviewer", acr="urn:example:phishing-resistant-mfa",
             audience="tarim-legal-officer-cli", iat_offset=0, auth_offset=0, exp_offset=300):
    now = int(datetime.now(timezone.utc).timestamp())
    return jwt.encode({
        "iss": "https://idp.example.invalid/tenant", "aud": audience,
        "sub": sub, "acr": acr, "iat": now + iat_offset,
        "auth_time": now + auth_offset, "exp": now + exp_offset,
    }, key, algorithm="RS256", headers={"kid": "test-idp-key-1"})


def test_real_signature_protocol_with_pinned_oidc_subject_and_vault_transit(
    session, monkeypatch
):
    rsa_signer, signers = oidc_fixture(monkeypatch)
    officer = authenticate_legal_officer(id_token(rsa_signer), "REVIEWER")
    assert officer.principal_id == "test-reviewer"
    assert officer.vault_key == "legal-reviewer"
    rate = add_rate(session)
    from tarim_destek_rag.database.legal_approvals import attestation_message, subject_digest
    expected = subject_digest(rate)

    def vault_post(request):
        assert request.url.path == "/v1/transit/sign/legal-reviewer"
        assert request.headers["X-Vault-Token"] == "fake-secure-test-token-not-production"
        decoded = base64.b64decode(json.loads(request.content)["input"])
        signed = signers["REVIEWER"][1].sign(decoded)
        return httpx.Response(200, json={
            "data": {"signature": "vault:v1:" + base64.b64encode(signed).decode("ascii")}
        })

    client = httpx.Client(transport=httpx.MockTransport(vault_post))
    envelope = build_vault_signed_envelope(
        rate, officer, vault_token="fake-secure-test-token-not-production",
        acknowledged_subject_digest=expected, client=client,
    )
    assert envelope["role"] == "REVIEWER"
    assert envelope["subject_digest"] == expected
    assert len(base64.b64decode(envelope["signature_b64"])) == 64
    assert not any(k in envelope for k in ("vault_token", "oidc_jwt", "private_key"))
    client.close()


@pytest.mark.parametrize("change", [
    {"acr": "urn:example:password-only"},
    {"audience": "other-client"},
    {"iat_offset": -1000, "auth_offset": -1000},
    {"auth_offset": -2000},
    {"sub": "unregistered-account"},
    {"exp_offset": -10},
])
def test_reject_stale_unauthorized_or_non_mfa_identity(monkeypatch, change):
    signer, _ = oidc_fixture(monkeypatch)
    with pytest.raises(ValueError, match="OIDC officer"):
        authenticate_legal_officer(id_token(signer, **change), "REVIEWER")


def test_registered_reviewer_cannot_select_approver_role(monkeypatch):
    signer, _ = oidc_fixture(monkeypatch)
    with pytest.raises(ValueError, match="OIDC officer"):
        authenticate_legal_officer(id_token(signer), "APPROVER")


def test_reject_unsigned_jwt_and_jku_redirection(monkeypatch):
    _, _ = oidc_fixture(monkeypatch)
    forged = jwt.encode(
        {"sub": "issuer-subject-reviewer"}, key="", algorithm="none",
        headers={"kid": "test-idp-key-1", "jku": "https://evil.invalid/jwks.json"}
    )
    with pytest.raises(ValueError, match="OIDC officer"):
        authenticate_legal_officer(forged, "REVIEWER")


def test_wrong_digest_http_vault_and_invalid_signature_rejected(session, monkeypatch):
    signer, _ = oidc_fixture(monkeypatch)
    rate = add_rate(session)
    officer = authenticate_legal_officer(id_token(signer), "REVIEWER")
    with pytest.raises(ValueError, match="digest"):
        build_vault_signed_envelope(
            rate, officer, vault_token="fake-secure-test-token-not-production",
            acknowledged_subject_digest="0"*64,
        )
    from tarim_destek_rag.database.legal_approvals import subject_digest
    def broken_signature(_request):
        return httpx.Response(200, json={"data": {
            "signature": "vault:v1:" + base64.b64encode(b"x"*64).decode()
        }})
    with httpx.Client(transport=httpx.MockTransport(broken_signature)) as client:
        with pytest.raises(ValueError, match="pinned officer/key"):
            build_vault_signed_envelope(
                rate, officer, vault_token="fake-secure-test-token-not-production",
                acknowledged_subject_digest=subject_digest(rate), client=client,
            )
    monkeypatch.setenv(VAULT_ADDR_ENV, "http://127.0.0.1:8200")
    with pytest.raises(ValueError, match="HTTPS"):
        build_vault_signed_envelope(
            rate, officer, vault_token="fake-secure-test-token-not-production",
            acknowledged_subject_digest=subject_digest(rate),
        )


class FakeS3:
    def __init__(self):
        self.objects = {}
        self.mode = "COMPLIANCE"
        self.upload_version = True
        self.outage = False

    def put_object(self, **kwargs):
        key = kwargs["Key"]
        version = "fake-locked-version-1"
        self.objects[(kwargs["Bucket"], key, version)] = (
            kwargs["Body"], kwargs["ObjectLockRetainUntilDate"],
        )
        return {"VersionId": version} if self.upload_version else {}

    def get_object(self, **kwargs):
        if self.outage:
            raise RuntimeError("Independent audit storage is unreachable")
        raw, until = self.objects[
            (kwargs["Bucket"], kwargs["Key"], kwargs["VersionId"])
        ]
        return {"Body": io.BytesIO(raw), "VersionId": kwargs["VersionId"],
                "ObjectLockMode": self.mode, "ObjectLockRetainUntilDate": until}


class PostgresSessionProxy:
    """Wrap real SQLite test rows, simulate only PostgreSQL dialect guard.

    This is a UNIT contract test, not a substitute for live PostgreSQL/S3 IAM.
    """
    def __init__(self, sqlite_session):
        self.target = sqlite_session
        self.bind = SimpleNamespace(dialect=SimpleNamespace(name="postgresql"))
    def __getattr__(self, attr):
        return getattr(self.target, attr)


def test_worm_compliance_archive_readback_and_tamper_denial(
    session, monkeypatch
):
    rate = add_rate(session)
    sign_subject(session, rate, monkeypatch)
    proxy = PostgresSessionProxy(session)
    fake = FakeS3()
    monkeypatch.setenv("TARIM_RAG_LEGAL_SECURITY_PROFILE", "production")
    monkeypatch.setenv("TARIM_RAG_WORM_BUCKET", "legal-immutable-test-bucket")
    monkeypatch.setenv("TARIM_RAG_WORM_RETENTION_DAYS", "3650")
    from tarim_destek_rag.database import legal_audit
    monkeypatch.setattr(legal_audit, "_client", lambda: fake)
    events = list(session.scalars(select(LegalApprovalAttestationModel)).all())
    for event in events:
        archive_signed_event(
            proxy, "RATE", rate.id, event.role, event, s3=fake
        )
    session.commit()
    assert production_audit_valid(proxy, rate) is True
    receipt = session.scalars(select(LegalAuditReceiptModel)).first()
    assert _ensure_exact_locked_version(fake, receipt) is True
    fake.mode = "GOVERNANCE"
    assert production_audit_valid(proxy, rate) is False
    fake.mode = "COMPLIANCE"
    fake.outage = True
    assert production_audit_valid(proxy, rate) is False
    fake.outage = False
    stored_key = next(iter(fake.objects))
    raw, until = fake.objects[stored_key]
    fake.objects[stored_key] = (raw + b"tampered", until)
    assert production_audit_valid(proxy, rate) is False


def test_worm_refuses_missing_version_or_sqlite_production_activation(
    session, monkeypatch
):
    rate = add_rate(session)
    sign_subject(session, rate, monkeypatch)
    monkeypatch.setenv("TARIM_RAG_LEGAL_SECURITY_PROFILE", "production")
    monkeypatch.setenv("TARIM_RAG_WORM_BUCKET", "legal-immutable-test-bucket")
    monkeypatch.setenv("TARIM_RAG_WORM_RETENTION_DAYS", "365")
    assert two_person_approved(session, rate) is False
    fake = FakeS3()
    fake.upload_version = False
    event = session.scalars(select(LegalApprovalAttestationModel)).first()
    with pytest.raises(ValueError, match="VersionId"):
        archive_signed_event(
            PostgresSessionProxy(session), "RATE", rate.id, event.role,
            event, s3=fake,
        )


def test_production_flag_alone_does_not_activate_without_security_profile(
    session, monkeypatch
):
    rate = add_rate(session)
    sign_subject(session, rate, monkeypatch)
    assert two_person_approved(session, rate)
    monkeypatch.delenv("TARIM_RAG_LEGAL_SECURITY_PROFILE", raising=False)
    assert two_person_approved(session, rate) is False
