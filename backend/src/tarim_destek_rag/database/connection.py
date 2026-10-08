from collections.abc import Generator
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
    """Tüm tabloları oluşturur."""
    import tarim_destek_rag.database.models  # noqa: F401

    eng = target_engine or engine
    Base.metadata.create_all(bind=eng)

