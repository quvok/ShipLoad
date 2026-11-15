"""Database configuration. No implicit in-memory or local fallback database."""
from collections.abc import Generator
import os

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def configure_database(database_url: str | None = None) -> None:
    """Configure the database from an explicit URL (primarily useful for tests)."""
    global _engine, _session_factory
    url = database_url or os.getenv("DATABASE_URL")
    if not url:
        _engine = None
        _session_factory = None
        return
    _engine = create_engine(url, pool_pre_ping=True)
    _session_factory = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def get_session() -> Generator[Session, None, None]:
    if _session_factory is None:
        raise HTTPException(
            status_code=503,
            detail="База данных не настроена. Задайте DATABASE_URL.",
        )
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database is not configured; set DATABASE_URL.")
    return _engine


configure_database()
