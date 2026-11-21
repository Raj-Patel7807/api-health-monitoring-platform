"""Add event_type, created_at columns and unique constraint to alert_deliveries.

Revision ID: 0005
Revises: 0004
"""

from collections.abc import Sequence

import sqlalchemy as sa

from alembic import op

revision: str = "0005"
down_revision: str | Sequence[str] | None = "0004"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Create the delivery_event_type enum type
    op.execute(sa.text("CREATE TYPE delivery_event_type AS ENUM ('opened', 'resolved')"))

    # Add event_type column
    op.add_column(
        "alert_deliveries",
        sa.Column(
            "event_type",
            sa.Enum("opened", "resolved", name="delivery_event_type", create_type=False),
            nullable=False,
            server_default="opened",
        ),
    )

    # Add created_at column
    op.add_column(
        "alert_deliveries",
        sa.Column(
            "created_at",
            sa.TIMESTAMP(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
    )

    # Add unique constraint on (incident_id, notification_channel_id, event_type)
    op.create_unique_constraint(
        "uq_alert_deliveries_incident_channel_event",
        "alert_deliveries",
        ["incident_id", "notification_channel_id", "event_type"],
    )


def downgrade() -> None:
    op.drop_constraint(
        "uq_alert_deliveries_incident_channel_event",
        "alert_deliveries",
        type_="unique",
    )
    op.drop_column("alert_deliveries", "created_at")
    op.drop_column("alert_deliveries", "event_type")
    op.execute(sa.text("DROP TYPE IF EXISTS delivery_event_type"))
