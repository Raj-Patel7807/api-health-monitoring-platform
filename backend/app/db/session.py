"""Database session helpers.

- ``create_database_engine`` — synchronous engine used by Alembic migrations.
- ``get_db`` — async FastAPI dependency that yields an ``AsyncSession``.
"""

from collections.abc import AsyncGenerator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from app.core.config import get_settings


def create_database_engine() -> Engine:
    """Create the synchronous SQLAlchemy engine used by migrations."""
    return create_engine(get_settings().database_url, pool_pre_ping=True)


def _async_url(url: str) -> str:
    """Convert ``postgresql+psycopg://…`` to ``postgresql+psycopg_async://…``."""
    return url.replace("postgresql+psycopg://", "postgresql+psycopg_async://", 1)


def _make_async_session_factory() -> async_sessionmaker[AsyncSession]:
    engine = create_async_engine(
        _async_url(get_settings().database_url),
        pool_pre_ping=True,
    )
    return async_sessionmaker(engine, expire_on_commit=False)


# Module-level factory — created once on import.
_AsyncSessionFactory: async_sessionmaker[AsyncSession] | None = None


def get_async_session_factory() -> async_sessionmaker[AsyncSession]:
    """Return the module-level async session factory, creating it on first call."""
    global _AsyncSessionFactory
    if _AsyncSessionFactory is None:
        _AsyncSessionFactory = _make_async_session_factory()
    return _AsyncSessionFactory


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency: yield an async DB session and commit/rollback on exit."""
    factory = get_async_session_factory()
    async with factory() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise

