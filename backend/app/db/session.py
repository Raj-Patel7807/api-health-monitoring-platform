from collections.abc import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def create_database_engine() -> Engine:
    """Create the synchronous SQLAlchemy engine used by migrations and repositories."""

    return create_engine(get_settings().database_url, pool_pre_ping=True)


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Return a session factory bound to the provided or default engine."""
    target_engine = engine or create_database_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=target_engine)


@contextmanager
def get_db_session(engine: Engine | None = None) -> Generator[Session, None, None]:
    """Provide a transactional database session scope for workers and services."""
    factory = get_session_factory(engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
