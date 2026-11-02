"""Add deleted_at and secret_display_hint to notification_channels (US-03).

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-01 00:00:00.000000

The DELETE endpoint for notification_channels cannot hard-delete rows that have
alert_deliveries (FK constraint). This migration adds a soft-delete column so
the application can set deleted_at instead, and the list endpoint hides them
while the alert dispatcher skips them (see API.md note).

secret_display_hint stores a safe, truncated preview of the secret shown to
users after creation (e.g. "hooks.slack.com/…/X7Q"). The raw secret is never
persisted in any column.
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0003"
down_revision: str | Sequence[str] | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notification_channels",
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.add_column(
        "notification_channels",
        sa.Column("secret_display_hint", sa.Text(), nullable=True),
    )
    # Index so list queries that filter WHERE deleted_at IS NULL stay fast.
    op.create_index(
        "idx_notification_channels_active",
        "notification_channels",
        ["team_id"],
        postgresql_where=sa.text("deleted_at IS NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_notification_channels_active",
        table_name="notification_channels",
    )
    op.drop_column("notification_channels", "secret_display_hint")
    op.drop_column("notification_channels", "deleted_at")
