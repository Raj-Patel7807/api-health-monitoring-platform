"""Track scheduled check and alert delivery claims."""

import sqlalchemy as sa

from alembic import op

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("monitors", sa.Column("pending_check_id", sa.Uuid(), nullable=True))
    op.add_column("alert_deliveries", sa.Column("attempt_started_at", sa.DateTime(timezone=True)))
    for field in ("check_interval_seconds", "current_interval_seconds"):
        op.alter_column("monitors", field, server_default="30")


def downgrade() -> None:
    for field in ("check_interval_seconds", "current_interval_seconds"):
        op.alter_column("monitors", field, server_default="60")
    op.drop_column("alert_deliveries", "attempt_started_at")
    op.drop_column("monitors", "pending_check_id")
