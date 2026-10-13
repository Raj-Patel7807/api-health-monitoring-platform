"""Database session helpers.

- ``create_database_engine`` — synchronous engine used by Alembic migrations.
- ``get_db`` — async FastAPI dependency that yields an ``AsyncSession``.
- ``get_db_session`` — synchronous session context manager for workers/services.
"""

from collections.abc import AsyncGenerator, Generator
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import Session, sessionmaker

from app.core.config import get_settings


def create_database_engine() -> Engine:
    """Create the synchronous SQLAlchemy engine used by migrations."""
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def _async_url(url: str) -> str:
    """Convert the synchronous PostgreSQL URL to its async equivalent."""
    return url.replace("postgresql+psycopg://", "postgresql+psycopg_async://", 1)


def _make_async_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(
        _async_url(get_settings().database_url),
        pool_pre_ping=True,
    )
    return async_sessionmaker(engine, expire_on_commit=False)


# Module-level factory — created once on first use.
_AsyncSessionFactory: async_sessionmaker[AsyncSession] | None = None


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the module-level async session factory, creating it on first call."""
    global _AsyncSessionFactory
    if _AsyncSessionFactory is None:
        _AsyncSessionFactory = _make_async_session_factory()
    return _AsyncSessionFactory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield an async DB session and commit or roll back on exit."""
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise


def get_session_factory(engine: Engine | None = None) -> sessionmaker[Session]:
    """Return a session factory bound to the provided or default engine."""
    target_engine = engine or create_database_engine()
    return sessionmaker(autocommit=False, autoflush=False, bind=target_engine)


@contextmanager
def get_db_session(engine: Engine | None = None) -> Generator[Session, None, None]:
    """Provide a database session scope for workers and services."""
    factory = get_session_factory(engine)
    session = factory()
    try:
        yield session
    finally:
        session.close()
