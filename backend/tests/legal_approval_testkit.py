"""TEST-ONLY Ed25519 keys. Never use these randomized test signers in production."""

import base64
import json
from datetime import datetime, timezone

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey

from tarim_destek_rag.database.legal_approvals import (
    TRUST_ENV, _subject_kind, attestation_message, register_detached_approval, subject_digest,
)
from tarim_destek_rag.database.models import (
    ReviewedBasinSnapshotModel, ReviewedWaterRestrictionDistrictModel,
    VerifiedSupportRateModel,
)


def trust_pair(monkeypatch):
    signers = {}
    config = {}
    for principal, role in (("test-reviewer", "REVIEWER"), ("test-approver", "APPROVER")):
        private = Ed25519PrivateKey.generate()
        signers[role] = (principal, private)
        public = private.public_key().public_bytes(
            encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw
        )
        config[principal] = {
            "role": role, "public_key_b64": base64.b64encode(public).decode("ascii"),
        }
    monkeypatch.setenv(TRUST_ENV, json.dumps(config))
    return signers


def detached_envelope(subject, role, signers):
    principal, key = signers[role]
    kind = _subject_kind(subject)
    digest = subject_digest(subject)
    sha = subject.source_version.content_hash
    now = datetime.now(timezone.utc).isoformat(timespec="seconds")
    signature = key.sign(attestation_message(
        kind=kind, record_id=subject.id, digest=digest,
        source_sha256=sha, principal_id=principal, role=role, signed_at=now,
    ))
    return {
        "role": role, "principal_id": principal, "subject_digest": digest,
        "source_sha256": sha, "signed_at": now,
        "signature_b64": base64.b64encode(signature).decode("ascii"),
    }


def sign_subject(session, subject, monkeypatch, signers=None):
    if signers is None:
        signers = trust_pair(monkeypatch)
    for role in ("REVIEWER", "APPROVER"):
        register_detached_approval(session, subject, detached_envelope(subject, role, signers))
    session.commit()
    return signers
