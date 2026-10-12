"""Verify the migrated database state, not exact migration source text."""

import os

from sqlalchemy import create_engine, text


def test_pgvector_extension_exists_in_database() -> None:
    """Integration CI runs Alembic before this test and provides DATABASE_URL."""
    database_url = os.environ["DATABASE_URL"]
    engine = create_engine(database_url)
    try:
        with engine.connect() as conn:
            installed = conn.scalar(
                text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            )
            assert installed is True
            assert conn.scalar(text("SELECT COUNT(*) FROM alembic_version")) == 1
    finally:
        engine.dispose()
