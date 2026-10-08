"""Controlled offline signing with OIDC officer proof + remote Vault Transit Ed25519.

No public HTTP endpoint; do NOT pass bearer tokens on command line or in
GitHub Actions. Provision short-lived secret files (0600) outside the repository.
Separate each officer's Vault ACL and OIDC identity; no local signing key.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

from tarim_destek_rag.database.legal_runtime import legal_session
from tarim_destek_rag.database.legal_audit import production_profile
from tarim_destek_rag.database.legal_approval_cli import _get_subject
from tarim_destek_rag.database.legal_operator import (
    authenticate_legal_officer, build_vault_signed_envelope,
    build_vault_revocation_envelope,
)


def _sensitive_file(path: Path) -> str:
    stat = path.stat()
    if os.name == "posix" and (stat.st_mode & 0o077):
        raise ValueError("Operator token file must be owner-only (chmod 600)")
    raw = path.read_text(encoding="utf-8").strip()
    if not raw:
        raise ValueError("Operator credential is empty")
    return raw


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True, choices=("RATE", "BASIN", "WATER"))
    parser.add_argument("--id", type=int, required=True)
    parser.add_argument("--role", required=True, choices=("REVIEWER", "APPROVER"))
    parser.add_argument("--action", choices=("approve", "revoke"), default="approve")
    parser.add_argument("--reason", help="Mandatory for revocation; included in Ed25519 signature")
    parser.add_argument("--oidc-token-file", type=Path, required=True)
    parser.add_argument("--vault-token-file", type=Path, required=True)
    parser.add_argument("--ack-subject-sha256", required=True)
    parser.add_argument("--out-file", type=Path, required=True)
    parser.add_argument("--sign", action="store_true",
                        help="Explicitly request a remote signing operation")
    args = parser.parse_args()
    if not args.sign:
        parser.error("Remote signature requires explicit --sign")
    if args.action == "revoke" and (args.role != "APPROVER" or not args.reason):
        parser.error("Revocation requires APPROVER role and --reason")
    if not production_profile():
        raise ValueError("Remote officer signing requires explicit production security profile")
    if not args.out_file.parent.is_dir():
        parser.error("Output parent directory must already exist")
    if args.out_file.exists():
        raise ValueError("Refusing to overwrite an existing signed envelope")
    officer = authenticate_legal_officer(
        _sensitive_file(args.oidc_token_file), args.role
    )
    with legal_session("reader") as session:
        subject = _get_subject(session, args.kind, args.id)
        if subject.review_status != "VERIFIED":
            raise ValueError("Subject is not a prepared, independently reviewed candidate")
        sign_function = (
            build_vault_revocation_envelope if args.action == "revoke"
            else build_vault_signed_envelope
        )
        kwargs = {"reason": args.reason} if args.action == "revoke" else {}
        envelope = sign_function(
            subject, officer,
            vault_token=_sensitive_file(args.vault_token_file),
            acknowledged_subject_digest=args.ack_subject_sha256,
            **kwargs,
        )
        # Fail if a read-only officer role has silently modified any records.
        session.rollback()
    output = json.dumps(envelope, ensure_ascii=False, indent=2) + "\n"
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY
    fd = os.open(args.out_file, flags, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8") as handle:
        handle.write(output)
    print(f"Detached {officer.role} signature recorded; no legal database change.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
