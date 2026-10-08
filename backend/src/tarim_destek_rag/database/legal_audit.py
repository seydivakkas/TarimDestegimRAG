"""P0-7 immutable external audit: S3 Object Lock COMPLIANCE mode.

A SQL UPDATE/DELETE restriction is not WORM. Production authorization only
becomes valid after each signed event has a locked S3 version, a matching
DB receipt, and an independent live read-back. Outage -> REVIEW/null.
Neither a simulated S3 object nor a local directory is production evidence.
"""

from __future__ import annotations

import hashlib
import json
import os
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import event, select
from sqlalchemy.orm import Session

from tarim_destek_rag.database.models import (
    LegalApprovalAttestationModel,
    LegalAuditReceiptModel,
)

AUDIT_BUCKET_ENV = "TARIM_RAG_WORM_BUCKET"
AUDIT_DAYS_ENV = "TARIM_RAG_WORM_RETENTION_DAYS"
SECURITY_PROFILE_ENV = "TARIM_RAG_LEGAL_SECURITY_PROFILE"
CONTEXT = "TarimDestegimRAG/P0-7/worm-audit/v1"


def production_profile() -> bool:
    return os.environ.get(SECURITY_PROFILE_ENV) == "production"


def _bucket() -> str:
    bucket = os.getenv(AUDIT_BUCKET_ENV, "")
    if not bucket or "/" in bucket or "://" in bucket or len(bucket) < 3:
        raise ValueError("Explicitly configured WORM bucket is required")
    return bucket


def _retention() -> datetime:
    try:
        days = int(os.environ[AUDIT_DAYS_ENV])
    except (KeyError, ValueError) as exc:
        raise ValueError("WORM retention days are missing") from exc
    if not (365 <= days <= 36500):
        raise ValueError("WORM retention must be configured between 365 and 36500 days")
    return datetime.now(UTC) + timedelta(days=days)


def _client():
    import boto3
    # IAM roles/short-lived credentials are supplied by the deployment, never
    # by this code. S3 bucket policies forbid bypass and non-COMPLIANCE writes.
    return boto3.client("s3")


def _event_dict(kind: str, record_id: int, role: str, event) -> dict:
    if role in ("REVIEWER", "APPROVER"):
        if event.subject_type != kind or event.subject_id != record_id or event.role != role:
            raise ValueError("Audit event identity mismatch")
        payload = {
            "principal_id": event.principal_id,
            "signed_at": event.signed_at,
            "subject_digest": event.subject_digest,
            "source_sha256": event.source_sha256,
            "signature_b64": event.signature_b64,
        }
    elif role == "REVOCATION":
        if event.subject_type != kind or event.subject_id != record_id:
            raise ValueError("Revocation audit identity mismatch")
        payload = {
            "principal_id": event.principal_id, "signed_at": event.signed_at,
            "subject_digest": event.subject_digest,
            "source_sha256": event.source_sha256,
            "reason": event.reason,
            "signature_b64": event.signature_b64,
        }
    else:
        raise ValueError("Unknown audit event role")
    return {
        "context": CONTEXT,
        "subject_type": kind,
        "subject_id": record_id,
        "event_role": role,
        "signed_event": payload,
    }


def _canonical_bytes(payload: dict) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":")).encode("utf-8")


def _ensure_exact_locked_version(s3, receipt: LegalAuditReceiptModel,
                                 canonical: bytes | None = None) -> bool:
    try:
        if receipt.object_bucket != _bucket() or not receipt.object_version:
            return False
        obj = s3.get_object(
            Bucket=receipt.object_bucket,
            Key=receipt.object_key,
            VersionId=receipt.object_version,
        )
        raw = obj["Body"].read()
        if (
            hashlib.sha256(raw).hexdigest() != receipt.payload_sha256
            or (canonical is not None and raw != canonical)
            or obj.get("VersionId") != receipt.object_version
            or obj.get("ObjectLockMode") != "COMPLIANCE"
        ):
            return False
        protected_until = obj.get("ObjectLockRetainUntilDate")
        if protected_until is None or protected_until.astimezone(UTC) < datetime.now(UTC):
            return False
        if not receipt.retain_until or protected_until < receipt.retain_until:
            return False
        return True
    except (Exception,):  # Operational S3 failure is ALWAYS a deny, never an allowance.
        return False


def archive_signed_event(
    session: Session, kind: str, subject_id: int, event_role: str,
    signed_event, *, s3=None,
) -> LegalAuditReceiptModel:
    """WORM write + read-back first, DB receipt second. DB commit remains caller's.

    An orphan locked object after DB rollback is acceptable; DB without WORM
    receipt is never an approved legal decision.
    """
    if not production_profile():
        raise ValueError("WORM archive writes require an explicit production security profile")
    if session.bind is None or session.bind.dialect.name != "postgresql":
        raise ValueError("Production legal audit writes require PostgreSQL")
    existing = session.scalars(select(LegalAuditReceiptModel).where(
        LegalAuditReceiptModel.subject_type == kind,
        LegalAuditReceiptModel.subject_id == subject_id,
        LegalAuditReceiptModel.event_role == event_role,
    )).first()
    if existing is not None:
        raise ValueError("An immutable event receipt already exists")
    payload = _canonical_bytes(_event_dict(kind, subject_id, event_role, signed_event))
    digest = hashlib.sha256(payload).hexdigest()
    bucket = _bucket()
    retain_until = _retention()
    key = f"legal/v1/{kind}/{subject_id}/{event_role}/{uuid4().hex}.json"
    remote = s3 or _client()
    response = remote.put_object(
        Bucket=bucket, Key=key, Body=payload, ContentType="application/json",
        Metadata={"sha256": digest},
        ObjectLockMode="COMPLIANCE",
        ObjectLockRetainUntilDate=retain_until,
    )
    version_id = response.get("VersionId")
    if not version_id:
        raise ValueError("S3 Object Lock bucket did not return an immutable VersionId")
    receipt = LegalAuditReceiptModel(
        subject_type=kind, subject_id=subject_id, event_role=event_role,
        object_bucket=bucket, object_key=key, object_version=version_id,
        payload_sha256=digest, retain_until=retain_until,
    )
    if not _ensure_exact_locked_version(remote, receipt, canonical=payload):
        raise ValueError("S3 WORM audit write cannot be independently verified")
    session.add(receipt)
    session.flush()
    return receipt


def production_audit_valid(session: Session, subject) -> bool:
    """Every decision independently re-reads both WORM evidence objects.

    If S3 goes down, approvals fail closed rather than relying on mutable DB
    receipt strings. No S3 access (or SQLite) is an implicit authorization.
    """
    if not production_profile():
        return True  # existing isolated synthetic testing profile only
    if session.bind is None or session.bind.dialect.name != "postgresql":
        return False
    from tarim_destek_rag.database.legal_approvals import _subject_kind
    kind = _subject_kind(subject)
    events = list(session.scalars(select(LegalApprovalAttestationModel).where(
        LegalApprovalAttestationModel.subject_type == kind,
        LegalApprovalAttestationModel.subject_id == subject.id,
    )).all())
    receipts = list(session.scalars(select(LegalAuditReceiptModel).where(
        LegalAuditReceiptModel.subject_type == kind,
        LegalAuditReceiptModel.subject_id == subject.id,
    )).all())
    if (
        len(events) != 2 or len(receipts) != 2
        or {x.event_role for x in receipts} != {"REVIEWER", "APPROVER"}
    ):
        return False
    by_role = {x.role: x for x in events}
    try:
        s3 = _client()
    except Exception:
        return False
    for receipt in receipts:
        event = by_role.get(receipt.event_role)
        if event is None:
            return False
        expected = _canonical_bytes(_event_dict(kind, subject.id, receipt.event_role, event))
        if not _ensure_exact_locked_version(s3, receipt, canonical=expected):
            return False
    return True


@event.listens_for(LegalAuditReceiptModel, "before_update")
def _deny_receipt_mutation(_mapper, _connection, _row):
    raise ValueError("Immutable S3 audit receipts cannot be modified via the ORM")


@event.listens_for(LegalAuditReceiptModel, "before_delete")
def _deny_receipt_deletion(_mapper, _connection, _row):
    raise ValueError("Immutable S3 audit receipts cannot be removed via the ORM")
