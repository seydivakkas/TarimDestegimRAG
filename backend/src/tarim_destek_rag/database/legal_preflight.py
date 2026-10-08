"""Read-only production acceptance preflight. NO provisioning, no key creation.

It must run in an organization-controlled environment that has real OIDC
policy, official officers, PostgreSQL TLS credentials, and S3 IAM credentials.
Missing controls => raises and returns nonzero; never enables the payout flag.
"""

from __future__ import annotations

import os

from sqlalchemy import text

from tarim_destek_rag.database.legal_audit import (
    _bucket,
    _retention,
    production_profile,
)
from tarim_destek_rag.database.legal_operator import (
    OFFICERS_ENV,
    OIDC_TRUST_ENV,
    SAFE_VAULT_KEY,
    _configured_json,
    _trusted_public_keys,
    _vault_url,
)
from tarim_destek_rag.database.legal_runtime import legal_session

PROTECTED = (
    "legal_approval_attestations",
    "legal_approval_revocations",
    "legal_audit_receipts",
)
RESTRICTED_SOURCE = (
    "verified_support_rates",
    "reviewed_basin_snapshots",
    "reviewed_water_restriction_scopes",
    "legal_release_snapshots",
)


def check_operator_policy() -> None:
    idp = _configured_json(OIDC_TRUST_ENV)
    officers = _configured_json(OFFICERS_ENV)
    trusted = _trusted_public_keys()
    if (
        not idp.get("issuer", "").startswith("https://")
        or not isinstance(idp.get("audience"), str)
        or not isinstance(idp.get("required_mfa_acr"), list)
        or not idp["required_mfa_acr"]
        or not isinstance(idp.get("jwks"), dict)
        or len(idp["jwks"].get("keys", [])) < 1
    ):
        raise ValueError("OIDC pinned trust, MFA policy or signing key missing")
    if len(officers) < 2 or len(trusted) < 2:
        raise ValueError("Two independently assigned legal officers are required")
    keys = set()
    people = set()
    roles = set()
    for sub, member in officers.items():
        if not isinstance(sub, str) or not isinstance(member, dict):
            raise ValueError("Malformed officer role enrollment")
        principal = member.get("principal_id")
        role = member.get("role")
        key = member.get("vault_key", "")
        if (
            not isinstance(principal, str) or principal not in trusted
            or trusted[principal][0] != role or not SAFE_VAULT_KEY.fullmatch(key)
        ):
            raise ValueError("Officer/Vault key does not match independent Ed25519 registry")
        people.add(principal)
        keys.add(key)
        roles.add(role)
    if len(people) < 2 or len(keys) < 2 or roles != {"REVIEWER", "APPROVER"}:
        raise ValueError("Separate natural persons and separate signing keys required")
    _vault_url()


def check_postgres_permissions() -> None:
    role_names = set()
    for role in ("reader", "writer"):
        with legal_session(role) as session:
            principal = session.execute(text("SELECT current_user")).scalar_one()
            role_names.add(principal)
            is_super = session.execute(text(
                "SELECT rolsuper FROM pg_roles WHERE rolname=current_user"
            )).scalar_one()
            if is_super:
                raise ValueError("No operator may be database superuser")
            for table in PROTECTED:
                for privilege in ("UPDATE", "DELETE", "TRUNCATE"):
                    has_it = session.execute(text(
                        "SELECT has_table_privilege(current_user, :table, :priv)"
                    ), {"table": table, "priv": privilege}).scalar_one()
                    if has_it:
                        raise ValueError(f"{role} has destructive {privilege} on {table}")
                insert = session.execute(text(
                    "SELECT has_table_privilege(current_user, :table, 'INSERT')"
                ), {"table": table}).scalar_one()
                if insert != (role == "writer"):
                    raise ValueError(f"{role} INSERT privilege mismatch for {table}")
            for table in RESTRICTED_SOURCE:
                modified = session.execute(text(
                    "SELECT has_table_privilege(current_user, :table, 'UPDATE')"
                ), {"table": table}).scalar_one()
                if modified:
                    raise ValueError(f"{role} may silently alter an approved legal source")
    if len(role_names) != 2:
        raise ValueError("Legal reader and writer must use distinct database principals")


def check_s3_object_lock(s3) -> None:
    bucket = _bucket()
    days = int(os.environ["TARIM_RAG_WORM_RETENTION_DAYS"])
    _retention()
    versioning = s3.get_bucket_versioning(Bucket=bucket)
    if versioning.get("Status") != "Enabled":
        raise ValueError("S3 Object Lock bucket versioning disabled")
    lock = s3.get_object_lock_configuration(Bucket=bucket)
    config = lock.get("ObjectLockConfiguration", {})
    retention = config.get("Rule", {}).get("DefaultRetention", {})
    if (
        config.get("ObjectLockEnabled") != "Enabled"
        or retention.get("Mode") != "COMPLIANCE"
        or not isinstance(retention.get("Days"), int)
        or retention.get("Days") < days
    ):
        raise ValueError("S3 bucket default COMPLIANCE Object Lock is not strong enough")
    public = s3.get_public_access_block(Bucket=bucket).get("PublicAccessBlockConfiguration", {})
    if not all(public.get(flag) is True for flag in (
        "BlockPublicAcls", "IgnorePublicAcls",
        "BlockPublicPolicy", "RestrictPublicBuckets",
    )):
        raise ValueError("Immutable legal audit bucket could be publicly accessible")
    encrypted = s3.get_bucket_encryption(Bucket=bucket)
    rules = encrypted["ServerSideEncryptionConfiguration"]["Rules"]
    if not any(
        x["ApplyServerSideEncryptionByDefault"].get("SSEAlgorithm") == "aws:kms"
        for x in rules
    ):
        raise ValueError("Legal WORM bucket lacks managed KMS server encryption")


def run_live_preflight() -> None:
    if not production_profile():
        raise ValueError("Live legal preflight requires production security profile")
    if os.environ.get("TARIM_RAG_LEGAL_ACTIVATION_ENABLED") == "true":
        raise ValueError("Run this preflight with payment activation switched OFF")
    check_operator_policy()
    check_postgres_permissions()
    import boto3
    check_s3_object_lock(boto3.client("s3"))
    # No production activation here: real reviewer signatures and WORM
    # canary + independent change control remain separate mandatory gates.
    print("P0-7 READ-ONLY live configuration checks passed; activation STILL OFF")


if __name__ == "__main__":
    run_live_preflight()
