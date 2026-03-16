"""Database engine and session management."""

from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

DEFAULT_DB_PATH = Path("data/rr_records.db")


def get_engine(db_path: str | Path = DEFAULT_DB_PATH):
    """Create SQLite engine for the given database path."""
    return create_engine(f"sqlite:///{db_path}", echo=False)


def init_db(engine=None):
    """Create all tables. Uses default engine if none provided."""
    if engine is None:
        engine = get_engine()
    Base.metadata.create_all(engine)


def get_session_factory(engine=None):
    """Return a session factory bound to the engine."""
    if engine is None:
        engine = get_engine()
    return sessionmaker(bind=engine, class_=Session, expire_on_commit=False)


def get_session(engine=None) -> Session:
    """Return a new session. Caller is responsible for closing it."""
    factory = get_session_factory(engine)
    return factory()
