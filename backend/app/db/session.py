"""SQLAlchemy engine and session construction."""

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker


def create_database_engine(database_url: str) -> Engine:
    """Create an engine usable with SQLite now and PostgreSQL later."""
    if database_url.startswith("sqlite"):
        options = {"check_same_thread": False}
    elif database_url.startswith("postgresql"):
        # Bound initial connection failure below the device client's read timeout.
        options = {"connect_timeout": 5}
    else:
        options = {}
    return create_engine(database_url, connect_args=options, pool_pre_ping=True)


def create_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)
