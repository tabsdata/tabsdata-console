from __future__ import annotations

import os
from pathlib import Path
from typing import Optional, Tuple

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from tdconsole.db.models import Base
DEFAULT_DB_URL = os.environ.get(
    "TDCONSOLE_DB_URL",
    f"sqlite:///{(Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'tdconsole' / 'tdconsole.db').resolve()}",
)

_engine: Engine | None = None
_SessionLocal: sessionmaker | None = None


def _ensure_sqlite_dir(db_url: str) -> None:
    """Create parent directory for SQLite files if needed."""
    if db_url.startswith("sqlite:///"):
        db_path = Path(db_url.replace("sqlite:///", "", 1)).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)


def get_engine(db_url: Optional[str] = None) -> Engine:
    """Return a shared SQLAlchemy engine for the provided URL."""
    global _engine, _SessionLocal
    url = db_url or DEFAULT_DB_URL
    if _engine is not None and str(_engine.url) == url:
        return _engine

    _ensure_sqlite_dir(url)
    _engine = create_engine(url, echo=False, future=True)
    _SessionLocal = sessionmaker(bind=_engine, future=True)
    return _engine


def get_sessionmaker(db_url: Optional[str] = None) -> sessionmaker:
    """Return the configured session factory, creating it if necessary."""
    engine = get_engine(db_url)
    if _SessionLocal is None:
        return sessionmaker(bind=engine, future=True)
    return _SessionLocal


def start_session(db_url: Optional[str] = None) -> Tuple[Session, Base]:
    """
    Build a Session bound to the configured engine.

    db_url:
        Optional SQLAlchemy database URL. Falls back to env var TDCONSOLE_DB_URL
        or ~/.local/share/tdconsole/tdconsole.db for persistence.
    """
    engine = get_engine(db_url)
    Base.metadata.create_all(engine)
    SessionLocal = get_sessionmaker(db_url)
    session = SessionLocal()

    # Import here to avoid circular import at module load time
    from tdconsole.core.find_instances import sync_filesystem_instances_to_db

    sync_filesystem_instances_to_db(session=session)
    return session, Base
