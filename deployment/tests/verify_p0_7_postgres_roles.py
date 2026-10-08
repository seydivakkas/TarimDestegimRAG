"""Temporary PostgreSQL integration preflight for P0-7 SQL grants.

CI uses fixture-only passwords, no real user identity. PostgreSQL service
does not have production TLS: this tests actual SQL privilege boundaries only,
NOT a real deployment, KMS, WORM or legal approval.
"""

import os
from pathlib import Path

import psycopg
from sqlalchemy import create_engine

from tarim_destek_rag.database.connection import Base
import tarim_destek_rag.database.models  # noqa: F401


def must(condition, explanation):
    if not condition:
        raise AssertionError(explanation)


def main():
    admin = os.environ["P0_7_CI_POSTGRES_URL"].replace(
        "postgresql://", "postgresql+psycopg://"
    )
    engine = create_engine(admin)
    Base.metadata.create_all(engine)
    engine.dispose()

    ddl = (Path(__file__).resolve().parents[1]
           / "sql/p0_7_legal_role_grants.sql").read_text(encoding="utf-8")
    native_url = os.environ["P0_7_CI_POSTGRES_URL"]
    with psycopg.connect(native_url, autocommit=True) as db:
        # No parameterized multi-statement prepared query; DDL is checked-in.
        db.execute(ddl, prepare=False)
        for suffix in ("reader", "writer"):
            login = f"tarim_legal_{suffix}_ci"
            db.execute(f"CREATE ROLE {login} LOGIN INHERIT PASSWORD 'ci-not-production'")
            db.execute(f"GRANT tarim_legal_{suffix} TO {login}")

    for role, expected_insert in (("reader", False), ("writer", True)):
        url = native_url.replace(
            "postgres:CI-only-postgres-not-production",
            f"tarim_legal_{role}_ci:ci-not-production",
        )
        with psycopg.connect(url) as db:
            name = db.execute("SELECT current_user").fetchone()[0]
            must(name == f"tarim_legal_{role}_ci", "Wrong actual legal PostgreSQL principal")
            for table in (
                "legal_approval_attestations", "legal_approval_revocations",
                "legal_audit_receipts",
            ):
                actions = {
                    a: db.execute(
                        "SELECT has_table_privilege(current_user, %s, %s)",
                        (table, a),
                    ).fetchone()[0]
                    for a in ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE")
                }
                must(actions["SELECT"] is True, f"{role} cannot read {table}")
                must(actions["INSERT"] is expected_insert, f"{role} INSERT mismatch {table}")
                must(
                    not any(actions[a] for a in ("UPDATE", "DELETE", "TRUNCATE")),
                    f"{role} has destructive privileges on {table}",
                )
            must(
                db.execute("SELECT has_table_privilege(current_user,%s,%s)",
                           ("verified_support_rates", "UPDATE")).fetchone()[0] is False,
                "Operator can change a source-derived legal monetary rate",
            )
            must(
                db.execute("SELECT has_table_privilege(current_user,%s,%s)",
                           ("reviewed_water_restriction_scopes", "UPDATE")).fetchone()[0] is False,
                "Operator can change an approved 2026 basin water restriction",
            )
            print(f"{role}: SELECT granted, INSERT={expected_insert}, UPDATE/DELETE denied")
    print("P0-7 REAL POSTGRESQL ROLE CONTRACT: PASS (CI only)")


if __name__ == "__main__":
    main()
