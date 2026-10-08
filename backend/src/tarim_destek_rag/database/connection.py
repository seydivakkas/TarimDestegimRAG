from collections.abc import Generator
from pathlib import Path

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from tarim_destek_rag.config.settings import settings


class Base(DeclarativeBase):
    """Tüm veritabanı modellerinin türediği temel sınıf."""


@event.listens_for(Engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    """SQLite için Foreign Key kısıtlarını zorunlu kıl."""
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

    # SQLite hafif şema göçü (production_year ve diğer kolonlar yoksa otomatik ekle)
    with eng.connect() as conn:
        try:
            cursor = conn.execute(text("PRAGMA table_info(support_amounts)"))
            columns = [row[1] for row in cursor.fetchall()]
            if columns and "production_year" not in columns:
                conn.execute(text("ALTER TABLE support_amounts ADD COLUMN production_year INTEGER DEFAULT 2026"))
            if columns and "legal_decision_number" not in columns:
                conn.execute(text("ALTER TABLE support_amounts ADD COLUMN legal_decision_number VARCHAR(64) DEFAULT '11781'"))
            if columns and "effective_from" not in columns:
                conn.execute(text("ALTER TABLE support_amounts ADD COLUMN effective_from VARCHAR(10) DEFAULT '2026-09-08'"))
            if columns and "effective_to" not in columns:
                conn.execute(text("ALTER TABLE support_amounts ADD COLUMN effective_to VARCHAR(10) DEFAULT NULL"))
            if columns and "geographic_scope" not in columns:
                conn.execute(text("ALTER TABLE support_amounts ADD COLUMN geographic_scope VARCHAR(64) DEFAULT 'GENEL'"))
            if columns and "verification_status" not in columns:
                conn.execute(text("ALTER TABLE support_amounts ADD COLUMN verification_status VARCHAR(32) DEFAULT 'VERIFIED'"))
            conn.commit()
        except Exception:
            pass

