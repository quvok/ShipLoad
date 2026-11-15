"""Database configuration with a persistent local SQLite default."""
from collections.abc import Generator
import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException
from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

load_dotenv()

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None
_DEFAULT_DATABASE = Path(__file__).resolve().parents[1] / "data" / "shipload.db"


def default_database_url() -> str:
    """Return the stable local SQLite path used for development."""
    _DEFAULT_DATABASE.parent.mkdir(parents=True, exist_ok=True)
    return f"sqlite:///{_DEFAULT_DATABASE.as_posix()}"


def configure_database(database_url: str | None = None) -> None:
    """Configure DATABASE_URL or fall back to the persistent local SQLite file."""
    global _engine, _session_factory
    url = database_url or os.getenv("DATABASE_URL") or default_database_url()
    connect_args = {"check_same_thread": False} if url.startswith("sqlite:") else {}
    _engine = create_engine(url, pool_pre_ping=True, connect_args=connect_args)
    _session_factory = sessionmaker(bind=_engine, autoflush=False, autocommit=False)


def get_session() -> Generator[Session, None, None]:
    if _session_factory is None:
        raise HTTPException(status_code=503, detail="База данных не настроена.")
    session = _session_factory()
    try:
        yield session
    finally:
        session.close()


def get_engine() -> Engine:
    if _engine is None:
        raise RuntimeError("Database is not configured.")
    return _engine


configure_database()
