"""Fail-closed Ed25519 two-person legal approval validation (P0-5).

The independent trust store is configured OUTSIDE the database as
TARIM_RAG_LEGAL_TRUSTED_KEYS_JSON, e.g.
{"reviewer":{"role":"REVIEWER","public_key_b64":"..."},
 "approver":{"role":"APPROVER","public_key_b64":"..."}}

No private keys are created, shipped or stored by this application.
Merely setting review_status, approved_by or a 64-char SHA does not authorize
use of a legal amount or a district membership decision.
"""

from __future__ import annotations

import base64
import binascii
import hashlib
import json
import os
import re
from datetime import UTC, datetime
from decimal import Decimal
from typing import Literal
from urllib.parse import urlsplit

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from sqlalchemy import event, select
from sqlalchemy.orm import Session

from tarim_destek_rag.database.models import (
    LegalApprovalAttestationModel,
    LegalApprovalRevocationModel,
    ReviewedBasinSnapshotModel,
    ReviewedWaterRestrictionDistrictModel,
    VerifiedSupportRateModel,
)

Subject = (
    VerifiedSupportRateModel
    | ReviewedBasinSnapshotModel
    | ReviewedWaterRestrictionDistrictModel
)

CONTEXT = "TarimDestegimRAG/P0-5/legal-attestation/v1"
TRUST_ENV = "TARIM_RAG_LEGAL_TRUSTED_KEYS_JSON"


def _normalize(value):
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, datetime):
        return value.isoformat()
    return value


def _subject_kind(subject: Subject) -> Literal["RATE", "BASIN", "WATER"]:
    if isinstance(subject, VerifiedSupportRateModel):
        return "RATE"
    if isinstance(subject, ReviewedBasinSnapshotModel):
        return "BASIN"
    if isinstance(subject, ReviewedWaterRestrictionDistrictModel):
        return "WATER"
    raise TypeError("Unexpected legal approval subject")


def subject_payload(subject: Subject) -> dict:
    """Canonical immutable legal semantics, including the SOURCE DOCUMENT itself."""
    version = subject.source_version
    source = version.source if version is not None else None
    if version is None or source is None or subject.id is None:
        raise ValueError("A persisted legal record and source version are required")
    provenance = {
        "source_id": version.source_id,
        "source_url": source.url,
        "source_authority": source.authority,
        "source_active": source.active,
        "source_superseded": version.superseded,
        "source_sha256": version.content_hash,
        "source_effective_from": version.effective_from,
        "source_effective_to": version.effective_to,
        "document_version": version.version,
    }
    if isinstance(subject, VerifiedSupportRateModel):
        fields = {
            "program": subject.program_id,
            "crop": subject.crop_name,
            "year": subject.production_year,
            "province": subject.province,
            "district": subject.district,
            "unit_amount": subject.unit_amount,
            "unit": subject.unit,
            "effective_from": subject.effective_from.isoformat(),
            "effective_to": subject.effective_to.isoformat() if subject.effective_to else None,
            "legal_clause": subject.legal_clause,
            "review_status": subject.review_status,
            "approved_by": subject.approved_by,
            "approved_at": subject.approved_at,
            "review_reference": subject.review_reference,
        }
    elif isinstance(subject, ReviewedBasinSnapshotModel):
        fields = {
            "province": subject.province,
            "district": subject.district,
            "year": subject.production_year,
            "crop_codes": json.loads(subject.crop_codes_json),
            "drip_required_for_grain_maize": subject.drip_required_for_grain_maize,
            "document_page": subject.document_page,
            "review_status": subject.review_status,
            "coverage_complete": subject.coverage_complete,
            "reviewed_by": subject.reviewed_by,
            "reviewed_at": subject.reviewed_at,
            "review_reference": subject.review_reference,
        }
    else:
        fields = {
            "province": subject.province,
            "district": subject.district,
            "year": subject.production_year,
            "restriction_status": subject.restriction_status,
            "effective_from": subject.effective_from,
            "effective_to": subject.effective_to,
            "legal_clause": subject.legal_clause,
            "document_page": subject.document_page,
            "review_status": subject.review_status,
            "reviewed_by": subject.reviewed_by,
            "reviewed_at": subject.reviewed_at,
            "review_reference": subject.review_reference,
        }
    return {
        "context": CONTEXT,
        "kind": _subject_kind(subject),
        "record_id": subject.id,
        "provenance": provenance,
        "fields": {key: _normalize(value) for key, value in fields.items()},
    }


def subject_digest(subject: Subject) -> str:
    raw = json.dumps(
        subject_payload(subject), sort_keys=True, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _trusted_public_keys() -> dict:
    """Missing or malformed external trust config always rejects authorization."""
    raw = os.getenv(TRUST_ENV)
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, dict):
            return {}
        keys = {}
        for principal, metadata in parsed.items():
            if not isinstance(principal, str) or not principal.strip():
                return {}
            if metadata.get("role") not in ("REVIEWER", "APPROVER"):
                return {}
            key = base64.b64decode(metadata["public_key_b64"], validate=True)
            if len(key) != 32:
                return {}
            keys[principal] = (metadata["role"], Ed25519PublicKey.from_public_bytes(key))
        return keys
    except (TypeError, ValueError, KeyError, AttributeError, binascii.Error):
        return {}


def attestation_message(
    *,
    kind: str,
    record_id: int,
    digest: str,
    source_sha256: str,
    role: str,
    principal_id: str,
    signed_at: str,
) -> bytes:
    payload = {
        "context": CONTEXT,
        "kind": kind,
        "record_id": record_id,
        "digest": digest,
        "source_sha256": source_sha256,
        "role": role,
        "principal_id": principal_id,
        "signed_at": signed_at,
    }
    return json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"),
    ).encode("utf-8")


def _validate_signature(
    signed: LegalApprovalAttestationModel,
    *,
    kind: str, record_id: int, digest: str, source_sha256: str, keys: dict,
) -> bool:
    configured = keys.get(signed.principal_id)
    if configured is None or configured[0] != signed.role:
        return False
    if (
        signed.subject_type != kind
        or signed.subject_id != record_id
        or signed.subject_digest != digest
        or signed.source_sha256 != source_sha256
    ):
        return False
    try:
        created = datetime.fromisoformat(signed.signed_at.replace("Z", "+00:00"))
        if created.tzinfo is None or created.astimezone(UTC) > datetime.now(UTC):
            return False
        signature = base64.b64decode(signed.signature_b64, validate=True)
        configured[1].verify(signature, attestation_message(
            kind=kind, record_id=record_id, digest=digest,
            source_sha256=source_sha256, role=signed.role,
            principal_id=signed.principal_id, signed_at=signed.signed_at,
        ))
        return True
    except (InvalidSignature, ValueError, TypeError, binascii.Error):
        return False


def two_person_approved(session: Session, subject: Subject) -> bool:
    """Independent signed reviewer+approver evidence, freshly checked every read."""
    keys = _trusted_public_keys()
    if len(keys) < 2:
        return False
    if getattr(subject, "review_status", None) != "VERIFIED":
        return False
    version = subject.source_version
    source = version.source if version is not None else None
    if version is None or source is None or not source.active or version.superseded:
        return False
    parsed = urlsplit(source.url)
    host = (parsed.hostname or "").lower()
    if (
        parsed.scheme != "https"
        or not (host == "resmigazete.gov.tr" or host.endswith(".resmigazete.gov.tr")
                or host == "tarimorman.gov.tr" or host.endswith(".tarimorman.gov.tr"))
        or source.authority not in ("OFFICIAL_GAZETTE", "MINISTRY_OF_AGRICULTURE")
        or not re.fullmatch(r"[0-9a-fA-F]{64}", version.content_hash or "")
    ):
        return False
    # Revocation is an append-only tombstone: even a source reactivation or a
    # second approval cannot silently restore authority for the same record ID.
    if session.scalars(select(LegalApprovalRevocationModel.id).where(
        LegalApprovalRevocationModel.subject_type == _subject_kind(subject),
        LegalApprovalRevocationModel.subject_id == subject.id,
    )).first() is not None:
        return False
    try:
        digest = subject_digest(subject)
        kind = _subject_kind(subject)
        source_hash = subject.source_version.content_hash
    except (ValueError, TypeError, KeyError, json.JSONDecodeError):
        return False
    rows = list(session.scalars(select(LegalApprovalAttestationModel).where(
        LegalApprovalAttestationModel.subject_type == kind,
        LegalApprovalAttestationModel.subject_id == subject.id,
    )).all())
    if len(rows) != 2 or {row.role for row in rows} != {"REVIEWER", "APPROVER"}:
        return False
    if rows[0].principal_id == rows[1].principal_id:
        return False
    return all(_validate_signature(
        row, kind=kind, record_id=subject.id, digest=digest,
        source_sha256=source_hash, keys=keys,
    ) for row in rows)


def register_detached_approval(
    session: Session,
    subject: Subject,
    envelope: dict,
) -> LegalApprovalAttestationModel:
    """Import a signature produced outside the API. Never signs or auto-promotes.

    Caller controls transaction. Privileged offline tooling must enforce its own
    operator authentication; this application exposes no public approval endpoint.
    """
    digest = subject_digest(subject)
    kind = _subject_kind(subject)
    source_hash = subject.source_version.content_hash
    row = LegalApprovalAttestationModel(
        subject_type=kind, subject_id=subject.id,
        role=envelope["role"], principal_id=envelope["principal_id"],
        subject_digest=envelope["subject_digest"],
        source_sha256=envelope["source_sha256"],
        signed_at=envelope["signed_at"],
        signature_b64=envelope["signature_b64"],
    )
    if not _validate_signature(
        row, kind=kind, record_id=subject.id, digest=digest,
        source_sha256=source_hash, keys=_trusted_public_keys(),
    ):
        raise ValueError("No authenticated, valid detached approval for this exact record")
    if session.scalars(select(LegalApprovalAttestationModel).where(
        LegalApprovalAttestationModel.subject_type == kind,
        LegalApprovalAttestationModel.subject_id == subject.id,
        LegalApprovalAttestationModel.role == row.role,
    )).first() is not None:
        raise ValueError("An attestation for this role already exists")
    session.add(row)
    session.flush()
    return row


@event.listens_for(LegalApprovalAttestationModel, "before_update")
def _reject_attestation_update(_mapper, _connection, _target):
    raise ValueError("Signed legal attestations cannot be updated; create new record versions")


@event.listens_for(LegalApprovalAttestationModel, "before_delete")
def _reject_attestation_delete(_mapper, _connection, _target):
    raise ValueError("Signed legal attestations cannot be deleted via the ORM")


def revocation_message(
    *,
    kind: str, record_id: int, digest: str, source_sha256: str,
    principal_id: str, signed_at: str, reason: str,
) -> bytes:
    return json.dumps({
        "context": CONTEXT + "/revoke/v1",
        "kind": kind, "record_id": record_id, "digest": digest,
        "source_sha256": source_sha256, "principal_id": principal_id,
        "signed_at": signed_at, "reason": reason,
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def register_detached_revocation(
    session: Session, subject: Subject, envelope: dict
) -> LegalApprovalRevocationModel:
    """Authenticated approver-signed, irreversible-for-this-ID deny event.

    A DB administrator can still bypass ORM protections; use append-only/WORM
    external audit archival in the production deployment.
    """
    kind = _subject_kind(subject)
    digest = subject_digest(subject)
    source_sha = subject.source_version.content_hash
    principal_id = envelope["principal_id"]
    keys = _trusted_public_keys()
    configured = keys.get(principal_id)
    if configured is None or configured[0] != "APPROVER":
        raise ValueError("A trusted independent approver must sign revocations")
    reason = envelope["reason"]
    signed_at = envelope["signed_at"]
    if (
        envelope["subject_digest"] != digest
        or envelope["source_sha256"] != source_sha
        or not isinstance(reason, str) or not reason.strip()
        or session.scalars(select(LegalApprovalRevocationModel.id).where(
            LegalApprovalRevocationModel.subject_type == kind,
            LegalApprovalRevocationModel.subject_id == subject.id,
        )).first() is not None
    ):
        raise ValueError("Revocation is duplicate or does not match the current subject")
    try:
        created = datetime.fromisoformat(signed_at.replace("Z", "+00:00"))
        if created.tzinfo is None or created.astimezone(UTC) > datetime.now(UTC):
            raise ValueError("Revocation timestamp is invalid")
        configured[1].verify(
            base64.b64decode(envelope["signature_b64"], validate=True),
            revocation_message(
                kind=kind, record_id=subject.id, digest=digest,
                source_sha256=source_sha, principal_id=principal_id,
                signed_at=signed_at, reason=reason,
            ),
        )
    except (InvalidSignature, ValueError, TypeError, binascii.Error) as exc:
        raise ValueError("Invalid authenticated revocation signature") from exc
    row = LegalApprovalRevocationModel(
        subject_type=kind, subject_id=subject.id, subject_digest=digest,
        source_sha256=source_sha, principal_id=principal_id,
        signed_at=signed_at, reason=reason,
        signature_b64=envelope["signature_b64"],
    )
    session.add(row)
    session.flush()
    return row


@event.listens_for(LegalApprovalRevocationModel, "before_update")
def _reject_revocation_update(_mapper, _connection, _target):
    raise ValueError("Signed revocations cannot be updated via the ORM")


@event.listens_for(LegalApprovalRevocationModel, "before_delete")
def _reject_revocation_delete(_mapper, _connection, _target):
    raise ValueError("Signed revocations cannot be deleted via the ORM")
