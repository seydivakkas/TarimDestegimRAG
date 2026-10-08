"""Separate PostgreSQL database identities for legal read and write operations.

Production identities and passwords are externally provisioned. The runtime
process must not receive legal_writer connection secrets; the isolated
operator import process must not receive the public API credentials.
"""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator, Literal

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

from tarim_destek_rag.database.connection import SessionLocal, init_db
from tarim_destek_rag.database.legal_audit import production_profile

ConnectionRole = Literal["reader", "writer"]


@contextmanager
def legal_session(role: ConnectionRole) -> Iterator[Session]:
    if role not in ("reader", "writer"):
        raise ValueError("Invalid legal database role")
    if not production_profile():
        # Offline-only legacy sqlite DB. The two-person authorizer still
        # requires the isolated pytest profile to return successful decisions.
        init_db()
        with SessionLocal() as session:
            yield session
        return
    prefix = "TARIM_RAG_LEGAL_DB_READER" if role == "reader" else "TARIM_RAG_LEGAL_DB_WRITER"
    secret_url = os.getenv(prefix + "_URL", "")
    expected_user = os.getenv(prefix + "_ROLE", "")
    if not secret_url or not expected_user or not expected_user.startswith("tarim_legal_"):
        raise ValueError("Production legal database credentials/role mapping are missing")
    parsed = make_url(secret_url)
    if parsed.get_backend_name() != "postgresql" or parsed.get_driver_name() != "psycopg":
        raise ValueError("Production approval storage requires psycopg PostgreSQL")
    # Strict TLS hostname verification for the separately managed operator DB.
    # Deployment must mount the trusted PostgreSQL CA certificate.
    engine = create_engine(secret_url, connect_args={"sslmode": "verify-full"})
    try:
        with Session(engine) as session:
            actual = session.execute(text("SELECT current_user")).scalar_one()
            if actual != expected_user:
                raise ValueError("Authenticated DB principal does not match expected legal role")
            yield session
    finally:
        engine.dispose()
