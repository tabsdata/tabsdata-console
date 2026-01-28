import os
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from tdconsole.core.find_instances import sync_filesystem_instances_to_db
from tdconsole.core.models import Base  # your ORM models

DEFAULT_DB_URL = os.environ.get(
    "TDCONSOLE_DB_URL",
    f"sqlite:///{(Path(os.environ.get('XDG_DATA_HOME', Path.home() / '.local' / 'share')) / 'tdconsole' / 'tdconsole.db').resolve()}",
)


def _ensure_sqlite_dir(db_url: str) -> None:
    """Create parent directory for SQLite files if needed."""
    if db_url.startswith("sqlite:///"):
        db_path = Path(db_url.replace("sqlite:///", "", 1)).expanduser()
        db_path.parent.mkdir(parents=True, exist_ok=True)


def start_session(db_url: str | None = None):
    url = db_url or DEFAULT_DB_URL
    _ensure_sqlite_dir(url)
    engine = create_engine(url, echo=False, future=True)
    SessionLocal = sessionmaker(bind=engine, future=True)
    session = SessionLocal()
    Base.metadata.create_all(engine)
    sync_filesystem_instances_to_db(session=session)
    # Base.metadata.drop_all(engine)
    # Base.metadata.create_all(engine)
    return session, Base


# session = start_session()[0]
# x = query_session(session=session, model=Instance, status="Not Running")
# for inst in x:
#     print({c.name: getattr(inst, c.name) for c in inst.__table__.columns})
