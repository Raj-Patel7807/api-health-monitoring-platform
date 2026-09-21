from pathlib import Path


def test_initial_migration_enables_pgvector() -> None:
    migration = Path("alembic/versions/0001_enable_pgvector.py").read_text(encoding="utf-8")

    assert "CREATE EXTENSION IF NOT EXISTS vector" in migration
