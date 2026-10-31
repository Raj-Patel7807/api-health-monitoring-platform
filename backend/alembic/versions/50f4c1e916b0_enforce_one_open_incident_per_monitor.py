"""enforce_one_open_incident_per_monitor

Revision ID: 50f4c1e916b0
Revises: 0001
Create Date: 2026-11-01 04:58:25.548165
"""

from alembic import op

revision = "50f4c1e916b0"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Replace non-unique idx_incidents_open with unique index to guarantee at most
    # one open incident per monitor at database level (AC-10.1 / US-09 / Issue #49).
    op.execute("DROP INDEX IF EXISTS idx_incidents_open")
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_incident_one_open_per_monitor "
        "ON incidents (monitor_id) WHERE status = 'open'"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ux_incident_one_open_per_monitor")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_incidents_open "
        "ON incidents (monitor_id) WHERE status = 'open'"
    )
