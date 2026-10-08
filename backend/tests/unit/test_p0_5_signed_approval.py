"""P0-5 cryptographic dual control, tamper resistance, revocation and key rotation.

Ephemeral Ed25519 keys in this test file are NEVER trusted production identities.
"""

import base64
import json
from datetime import datetime, timezone
from decimal import Decimal

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import Session

from backend.tests.legal_approval_testkit import (
    detached_envelope, sign_subject, trust_pair,
)
from backend.tests.unit.test_p0_2_verified_rates import add_rate
from tarim_destek_rag.database.connection import Base
from tarim_destek_rag.database.legal_approvals import (
    TRUST_ENV, register_detached_approval, register_detached_revocation,
    revocation_message, subject_digest, two_person_approved,
)
from tarim_destek_rag.database.models import (
    LegalApprovalAttestationModel, LegalApprovalRevocationModel,
    SourceModel, SupportProgramModel,
)
from tarim_destek_rag.database.repository import SupportRepository


@pytest.fixture
def session():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        db.add_all([
            SupportProgramModel(id="BASIC_SUPPORT_2026", name="Temel", year=2026, active=True),
            SourceModel(
                source_id="SYNTHETIC-LEGAL-DOCUMENT", title="TEST fixture only",
                url="https://www.resmigazete.gov.tr/eskiler/2026/09/20260908-7.pdf", authority="OFFICIAL_GAZETTE",
                content_type="PDF", active=True,
            ),
        ])
        db.commit()
        yield db
    engine.dispose()


def lookup(session):
    return SupportRepository(session).get_amount(
        "BASIC_SUPPORT_2026", "BUĞDAY",
        production_year=2026, province="KONYA", district="KARATAY",
    )


def test_status_and_metadata_alone_are_not_authorization(session, monkeypatch):
    monkeypatch.delenv(TRUST_ENV, raising=False)
    rate = add_rate(session)
    assert rate.review_status == "VERIFIED"
    assert rate.approved_by and rate.review_reference
    assert lookup(session) is None
    assert two_person_approved(session, rate) is False


def test_missing_or_malformed_external_trust_store_fails_closed(session, monkeypatch):
    rate = add_rate(session)
    sign_subject(session, rate, monkeypatch)
    assert lookup(session) is not None
    monkeypatch.setenv(TRUST_ENV, '{"unsafe":"not a key"}')
    assert lookup(session) is None
    monkeypatch.setenv(TRUST_ENV, '{"unsafe":{"role":"REVIEWER","public_key_b64":"***"}}')
    assert lookup(session) is None


def test_only_one_review_signature_is_inadequate(session, monkeypatch):
    rate = add_rate(session)
    keys = trust_pair(monkeypatch)
    register_detached_approval(session, rate, detached_envelope(rate, "REVIEWER", keys))
    session.commit()
    assert lookup(session) is None
    register_detached_approval(session, rate, detached_envelope(rate, "APPROVER", keys))
    session.commit()
    assert lookup(session) is not None


def test_duplicate_role_cannot_masquerade_as_second_signer(session, monkeypatch):
    rate = add_rate(session)
    keys = trust_pair(monkeypatch)
    envelope = detached_envelope(rate, "REVIEWER", keys)
    register_detached_approval(session, rate, envelope)
    session.commit()
    with pytest.raises(ValueError, match="already exists"):
        register_detached_approval(session, rate, envelope)
    assert lookup(session) is None


def test_forged_signature_and_role_impersonation_rejected(session, monkeypatch):
    rate = add_rate(session)
    keys = trust_pair(monkeypatch)
    original = detached_envelope(rate, "REVIEWER", keys)
    original["signature_b64"] = base64.b64encode(b"\x00" * 64).decode("ascii")
    with pytest.raises(ValueError, match="valid detached approval"):
        register_detached_approval(session, rate, original)
    original = detached_envelope(rate, "REVIEWER", keys)
    original["role"] = "APPROVER"
    with pytest.raises(ValueError, match="valid detached approval"):
        register_detached_approval(session, rate, original)
    assert lookup(session) is None


def test_signed_record_amount_change_invalidates_both_approvals(session, monkeypatch):
    rate = add_rate(session)
    sign_subject(session, rate, monkeypatch)
    assert lookup(session) is not None
    rate.unit_amount = Decimal("999.99")
    session.commit()
    assert lookup(session) is None


def test_source_version_sha_change_invalidates_both_approvals(session, monkeypatch):
    rate = add_rate(session)
    sign_subject(session, rate, monkeypatch)
    rate.source_version.content_hash = "b" * 64
    session.commit()
    assert lookup(session) is None


def test_source_url_change_invalidates_approvals(session, monkeypatch):
    rate = add_rate(session)
    sign_subject(session, rate, monkeypatch)
    source = session.get(SourceModel, "SYNTHETIC-LEGAL-DOCUMENT")
    source.url = "https://evil.invalid/modified-source"
    session.commit()
    assert lookup(session) is None


def test_key_rotation_invalidates_historic_approval(session, monkeypatch):
    rate = add_rate(session)
    sign_subject(session, rate, monkeypatch)
    assert lookup(session) is not None
    trust_pair(monkeypatch)  # New public keys at the same identity/role labels.
    assert lookup(session) is None


def test_signed_revocation_cannot_be_reversed_by_status_toggle(session, monkeypatch):
    rate = add_rate(session)
    keys = sign_subject(session, rate, monkeypatch)
    assert lookup(session) is not None
    principal, signer = keys["APPROVER"]
    reason = "Document clause superseded; controlled test revocation"
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    digest = subject_digest(rate)
    sha = rate.source_version.content_hash
    signed = signer.sign(revocation_message(
        kind="RATE", record_id=rate.id, digest=digest, source_sha256=sha,
        principal_id=principal, signed_at=created, reason=reason,
    ))
    envelope = {
        "principal_id": principal, "reason": reason, "signed_at": created,
        "subject_digest": digest, "source_sha256": sha,
        "signature_b64": base64.b64encode(signed).decode("ascii"),
    }
    register_detached_revocation(session, rate, envelope)
    session.commit()
    assert lookup(session) is None
    with pytest.raises(ValueError, match="duplicate"):
        register_detached_revocation(session, rate, envelope)
    assert lookup(session) is None


def test_untrusted_revocation_signature_cannot_be_registered(session, monkeypatch):
    rate = add_rate(session)
    keys = trust_pair(monkeypatch)
    principal, signer = keys["REVIEWER"]
    created = datetime.now(timezone.utc).isoformat(timespec="seconds")
    digest = subject_digest(rate)
    sha = rate.source_version.content_hash
    signature = signer.sign(revocation_message(
        kind="RATE", record_id=rate.id, digest=digest, source_sha256=sha,
        principal_id=principal, signed_at=created, reason="Test",
    ))
    with pytest.raises(ValueError, match="trusted independent approver"):
        register_detached_revocation(session, rate, {
            "principal_id": principal, "reason": "Test", "signed_at": created,
            "subject_digest": digest, "source_sha256": sha,
            "signature_b64": base64.b64encode(signature).decode("ascii"),
        })


def test_append_only_approval_and_revocation_reject_orm_mutations(session, monkeypatch):
    rate = add_rate(session)
    keys = sign_subject(session, rate, monkeypatch)
    approval = session.scalars(select(LegalApprovalAttestationModel)).first()
    approval.signature_b64 = "tampered"
    with pytest.raises(ValueError, match="cannot be updated"):
        session.flush()
    session.rollback()
    assert lookup(session) is not None
    approval = session.scalars(select(LegalApprovalAttestationModel)).first()
    session.delete(approval)
    with pytest.raises(ValueError, match="cannot be deleted"):
        session.flush()
    session.rollback()
    assert lookup(session) is not None


def test_attestation_db_signature_tampering_detected_even_if_orm_guard_bypassed(
    session, monkeypatch
):
    rate = add_rate(session)
    sign_subject(session, rate, monkeypatch)
    assert lookup(session) is not None
    # Simulate compromised privileged SQL client: proof must fail validation.
    session.execute(text(
        "UPDATE legal_approval_attestations SET signature_b64=:sig WHERE role='REVIEWER'"
    ), {"sig": base64.b64encode(b"f" * 64).decode("ascii")})
    session.commit()
    assert lookup(session) is None


def test_unofficial_host_or_publisher_must_not_activate(session, monkeypatch):
    rate = add_rate(session)
    sign_subject(session, rate, monkeypatch)
    assert lookup(session) is not None
    source = session.get(SourceModel, "SYNTHETIC-LEGAL-DOCUMENT")
    source.url = "https://not-resmigazete.gov.tr.example.invalid/document.pdf"
    session.commit()
    assert lookup(session) is None
    source.url = "https://www.resmigazete.gov.tr/eskiler/2026/09/20260908-7.pdf"
    source.authority = "TEST_ONLY"
    session.commit()
    assert lookup(session) is None


def test_inactive_source_denied_even_with_two_signatures(session, monkeypatch):
    rate = add_rate(session)
    sign_subject(session, rate, monkeypatch)
    assert lookup(session) is not None
    source = session.get(SourceModel, "SYNTHETIC-LEGAL-DOCUMENT")
    source.active = False
    session.commit()
    assert lookup(session) is None


def test_global_activation_switch_defaults_off_even_with_two_valid_signatures(
    session, monkeypatch
):
    rate = add_rate(session)
    sign_subject(session, rate, monkeypatch)
    assert lookup(session) is not None  # Only inside ephemeral test activation.
    monkeypatch.delenv("TARIM_RAG_LEGAL_ACTIVATION_ENABLED", raising=False)
    assert lookup(session) is None
    monkeypatch.setenv("TARIM_RAG_LEGAL_ACTIVATION_ENABLED", "TRUE")
    assert lookup(session) is None
