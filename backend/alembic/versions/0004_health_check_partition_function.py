"""Add monthly health check partition creation function.

Revision ID: 0004
Revises: 0003
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0004"
down_revision: str | Sequence[str] | None = "0003"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CREATE_PARTITION_FUNCTION = """
CREATE OR REPLACE FUNCTION create_health_check_partition(p_month DATE)
RETURNS VOID
LANGUAGE plpgsql
AS $$
DECLARE
    partition_start DATE := date_trunc('month', p_month)::date;
    partition_end DATE := (
        date_trunc('month', p_month) + INTERVAL '1 month'
    )::date;
    partition_name TEXT := (
        'health_check_results_' ||
        to_char(partition_start, 'YYYY_MM')
    );
BEGIN
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I
         PARTITION OF health_check_results
         FOR VALUES FROM (%L) TO (%L)',
        partition_name,
        partition_start::text || ' 00:00:00+00',
        partition_end::text || ' 00:00:00+00'
    );
END;
$$;
"""


def upgrade() -> None:
    # Create the reusable partition creation function.
    op.execute(sa.text(CREATE_PARTITION_FUNCTION))

    # Ensure the current month's partition exists.
    op.execute(sa.text("SELECT create_health_check_partition(CURRENT_DATE)"))

    # Create next month's partition in advance.
    op.execute(
        sa.text(
            """
            SELECT create_health_check_partition(
                (date_trunc('month', CURRENT_DATE) + INTERVAL '1 month')::date
            )
            """
        )
    )


def downgrade() -> None:
    # Keep existing partitions and their data.
    # Only remove the function created by this migration.
    op.execute(sa.text("DROP FUNCTION IF EXISTS create_health_check_partition(DATE)"))
