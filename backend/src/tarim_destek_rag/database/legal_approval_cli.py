"""Offline application of independently signed legal approvals (never a public API).

Security: the operator must use DB-level least-privilege access and a separately
managed identity process. Only the TEST suite generates private signing keys.
Live keys belong in an external KMS/HSM/signing service, not this repository.
"""

import argparse
import json
from pathlib import Path

from sqlalchemy.orm import Session

from tarim_destek_rag.database.connection import SessionLocal, init_db
from tarim_destek_rag.database.legal_approvals import (
    register_detached_approval, register_detached_revocation,
    subject_digest, subject_payload, two_person_approved,
)
from tarim_destek_rag.database.models import (
    ReviewedBasinSnapshotModel, VerifiedSupportRateModel,
    ReviewedWaterRestrictionScopeModel,
)


def _get_subject(session: Session, kind: str, record_id: int):
    table = {"RATE": VerifiedSupportRateModel, "BASIN": ReviewedBasinSnapshotModel,
             "WATER": ReviewedWaterRestrictionScopeModel}[kind]
    obj = session.get(table, record_id)
    if obj is None:
        raise ValueError("Unknown legal record; no approval was submitted")
    return obj


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=("inspect", "apply-attestations", "revoke"))
    parser.add_argument("--kind", required=True, choices=("RATE", "BASIN", "WATER"))
    parser.add_argument("--id", required=True, type=int)
    parser.add_argument("--bundle", type=Path, help="Externally signed JSON envelopes")
    parser.add_argument("--commit", action="store_true",
                        help="Write atomically; otherwise validate and rollback")
    args = parser.parse_args()

    init_db()
    with SessionLocal() as session:
        subject = _get_subject(session, args.kind, args.id)
        if args.action == "inspect":
            print(json.dumps({
                "payload": subject_payload(subject),
                "subject_digest": subject_digest(subject),
                "source_sha256": subject.source_version.content_hash,
                "approval_status": two_person_approved(session, subject),
            }, sort_keys=True, ensure_ascii=False, indent=2, default=str))
            return 0

        if args.bundle is None:
            parser.error("--bundle required to import a signed record")
        document = json.loads(args.bundle.read_text(encoding="utf-8"))
        if document.get("kind") != args.kind or document.get("record_id") != args.id:
            raise ValueError("Signed bundle is scoped to another legal record")
        try:
            if args.action == "apply-attestations":
                envelopes = document.get("attestations")
                if not isinstance(envelopes, list) or len(envelopes) != 2:
                    raise ValueError("Exactly two independent detached signatures required")
                for envelope in envelopes:
                    register_detached_approval(session, subject, envelope)
                if not two_person_approved(session, subject):
                    raise ValueError("The two-party legal approval gate still rejects this record")
            else:
                register_detached_revocation(session, subject, document["revocation"])
                if two_person_approved(session, subject):
                    raise ValueError("Revocation did not close the entitlement gate")
            if args.commit:
                session.commit()
                print("Externally signed evidence stored atomically; no private keys used.")
            else:
                session.rollback()
                print("DRY RUN: detached signatures valid; nothing written.")
        except Exception:
            session.rollback()
            raise
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
