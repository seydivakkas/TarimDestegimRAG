from collections.abc import Generator
import sqlite3
from pathlib import Path

from sqlalchemy import create_engine, event
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from tarim_destek_rag.config.settings import settings


class Base(DeclarativeBase):
    """Tüm veritabanı modellerinin türediği temel sınıf."""


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """SQLite için Foreign Key kısıtlarını zorunlu kıl."""
    # A PRAGMA on PostgreSQL/MySQL would prevent the DB driver from connecting.
    if isinstance(dbapi_connection, sqlite3.Connection):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()


def get_engine(db_url: str | None = None) -> Engine:
    """Veritabanı motorunu üretir."""
    url = db_url or settings.database_url
    # SQLite dosya dizininin varlığını garantiye al
    if url.startswith("sqlite:///"):
        file_path = url.replace("sqlite:///", "")
        if file_path != ":memory:":
            Path(file_path).parent.mkdir(parents=True, exist_ok=True)

    return create_engine(url, echo=False)


engine = get_engine()
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def get_db_session() -> Generator[Session, None, None]:
    """FastAPI dependency injection veya kod içi oturum üreteci."""
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


def init_db(target_engine: Engine | None = None) -> None:
    """Tüm tabloları oluşturur ve gerekli şema güncellemelerini uygular."""
    import tarim_destek_rag.database.models  # noqa: F401

    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)

    # Non-destructive compatibility for databases created before the extended
    # support_amounts and agricultural_faqs ORM models.
    if eng.dialect.name == "sqlite":
        support_ddl = {
            "production_year": "INTEGER DEFAULT 2026",
            "legal_decision_number": "VARCHAR(64)",
            "effective_from": "VARCHAR(10)",
            "effective_to": "VARCHAR(10)",
            "geographic_scope": "VARCHAR(64) DEFAULT 'GENEL'",
            "verification_status": "VARCHAR(32) DEFAULT 'DRAFT'",
        }
        faq_ddl = {
            "content_hash": "VARCHAR(64) DEFAULT NULL",
            "effective_date": "VARCHAR(32) DEFAULT NULL",
            "legal_span": "VARCHAR(256) DEFAULT NULL",
            "moderation_status": "VARCHAR(32) DEFAULT 'APPROVED'",
            "harvested_at": "VARCHAR(32) DEFAULT NULL",
            "source_domain": "VARCHAR(128) DEFAULT NULL",
            "version": "INTEGER DEFAULT 1",
        }
        with eng.begin() as connection:
            support_existing = {
                row[1]
                for row in connection.exec_driver_sql(
                    "PRAGMA table_info('support_amounts')"
                ).all()
            }
            if support_existing:
                for name, definition in support_ddl.items():
                    if name not in support_existing:
                        connection.exec_driver_sql(
                            f"ALTER TABLE support_amounts ADD COLUMN {name} {definition}"
                        )

            faq_existing = {
                row[1]
                for row in connection.exec_driver_sql(
                    "PRAGMA table_info('agricultural_faqs')"
                ).all()
            }
            if faq_existing:
                for name, definition in faq_ddl.items():
                    if name not in faq_existing:
                        connection.exec_driver_sql(
                            f"ALTER TABLE agricultural_faqs ADD COLUMN {name} {definition}"
                        )


