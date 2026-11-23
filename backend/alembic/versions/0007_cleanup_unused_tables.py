"""Clean up unused tables and enhance ai_analyses schema.

Revision ID: 0007
Revises: 0006
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0007"
down_revision: str | Sequence[str] | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Drop foreign key constraint, index, and column on health_check_results
    op.execute(
        sa.text(
            "ALTER TABLE health_check_results "
            "DROP CONSTRAINT IF EXISTS health_check_results_failed_assertion_id_fkey CASCADE"
        )
    )
    op.execute(sa.text("DROP INDEX IF EXISTS idx_hcr_failed_assertion CASCADE"))
    op.execute(
        sa.text(
            "ALTER TABLE health_check_results DROP COLUMN IF EXISTS failed_assertion_id CASCADE"
        )
    )

    # 2. Drop unused tables that have no models, services, or APIs
    op.execute(sa.text("DROP TABLE IF EXISTS embeddings CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS audit_entries CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS reports CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS maintenance_windows CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS health_check_daily_rollups CASCADE"))
    op.execute(sa.text("DROP TABLE IF EXISTS monitor_assertions CASCADE"))

    # 3. Drop unused enum types
    op.execute(sa.text("DROP TYPE IF EXISTS assertion_type CASCADE"))
    op.execute(sa.text("DROP TYPE IF EXISTS maintenance_mode CASCADE"))
    op.execute(sa.text("DROP TYPE IF EXISTS audit_action CASCADE"))

    # 4. Enhance ai_analyses table for AI incident assistance (US-16 / Section 6)
    op.execute(
        sa.text(
            "ALTER TABLE ai_analyses "
            "ADD COLUMN IF NOT EXISTS status VARCHAR(50) NOT NULL DEFAULT 'completed'"
        )
    )
    op.execute(sa.text("ALTER TABLE ai_analyses ADD COLUMN IF NOT EXISTS root_cause TEXT"))
    op.execute(
        sa.text(
            "ALTER TABLE ai_analyses "
            "ADD COLUMN IF NOT EXISTS investigation_steps JSONB NOT NULL DEFAULT '[]'::jsonb"
        )
    )
    op.execute(
        sa.text(
            "ALTER TABLE ai_analyses "
            "ADD COLUMN IF NOT EXISTS prevention_steps JSONB NOT NULL DEFAULT '[]'::jsonb"
        )
    )
    op.execute(sa.text("ALTER TABLE ai_analyses ADD COLUMN IF NOT EXISTS error_message TEXT"))


def downgrade() -> None:
    # Downgrade ai_analyses extra columns
    op.execute(sa.text("ALTER TABLE ai_analyses DROP COLUMN IF EXISTS error_message"))
    op.execute(sa.text("ALTER TABLE ai_analyses DROP COLUMN IF EXISTS prevention_steps"))
    op.execute(sa.text("ALTER TABLE ai_analyses DROP COLUMN IF EXISTS investigation_steps"))
    op.execute(sa.text("ALTER TABLE ai_analyses DROP COLUMN IF EXISTS root_cause"))
    op.execute(sa.text("ALTER TABLE ai_analyses DROP COLUMN IF EXISTS status"))
