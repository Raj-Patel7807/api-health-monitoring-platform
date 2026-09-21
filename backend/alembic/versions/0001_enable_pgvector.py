"""enable pgvector extension

Revision ID: 0001_enable_pgvector
Revises:
Create Date: 2026-09-22
"""

from alembic import op

revision = "0001_enable_pgvector"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")


def downgrade() -> None:
    # Keep extension removal explicit because future tables may depend on it.
    op.execute("DROP EXTENSION IF EXISTS vector")
