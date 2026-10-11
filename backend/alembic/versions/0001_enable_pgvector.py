"""initial schema mvp

Revision ID: 0001
Revises: 
Create Date: 2026-10-12 00:00:00.000000

"""
from pathlib import Path
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _load_statements_from_sql(sql_file_path: Path) -> list[str]:
    """Parse raw SQL file into separate statements, safely handling comments,
    quoted strings, and skipping explicit transaction blocks (BEGIN/COMMIT).
    """
    sql_text = sql_file_path.read_text(encoding="utf-8")
    statements: list[str] = []
    current: list[str] = []
    in_single_quote = False
    in_double_quote = False

    for line in sql_text.splitlines():
        stripped = line.strip()
        # Omit standalone transaction boundaries because Alembic manages the migration transaction
        if stripped.upper() in ("BEGIN;", "COMMIT;", "BEGIN", "COMMIT"):
            continue

        i = 0
        while i < len(line):
            ch = line[i]
            # Detect single line comment -- outside quoted literals
            if not in_single_quote and not in_double_quote and ch == "-" and i + 1 < len(line) and line[i + 1] == "-":
                current.append(line[i:])
                break

            if ch == "'" and not in_double_quote:
                # Handle escaped single quote ''
                if in_single_quote and i + 1 < len(line) and line[i + 1] == "'":
                    current.append("''")
                    i += 2
                    continue
                in_single_quote = not in_single_quote
            elif ch == '"' and not in_single_quote:
                in_double_quote = not in_double_quote
            elif ch == ";" and not in_single_quote and not in_double_quote:
                stmt = "".join(current).strip()
                if stmt:
                    statements.append(stmt)
                current = []
                i += 1
                continue

            current.append(ch)
            i += 1
        current.append("\n")

    trailing = "".join(current).strip()
    if trailing and trailing.upper() not in ("BEGIN;", "COMMIT;", "BEGIN", "COMMIT"):
        statements.append(trailing)

    return statements


def upgrade() -> None:
    """Apply initial schema MVP from schema_mvp.sql."""
    current_dir = Path(__file__).resolve().parent
    candidates = [
        current_dir.parent.parent / "database" / "schema_mvp.sql",
        current_dir.parent.parent / "database" / "schema.sql",
        current_dir.parent.parent / "schema_mvp.sql",
        current_dir.parent.parent / "schema.sql",
        current_dir.parent.parent.parent / "database" / "schema_mvp.sql",
        current_dir.parent.parent.parent / "database" / "schema.sql",
        current_dir.parent.parent.parent / "schema_mvp.sql",
        current_dir.parent.parent.parent / "schema.sql",
        current_dir.parent / "schema_mvp.sql",
        current_dir / "schema_mvp.sql",
        Path("/app/database/schema_mvp.sql"),
        Path("/app/database/schema.sql"),
        Path("/app/schema_mvp.sql"),
    ]

    sql_path = next((p for p in candidates if p.exists()), None)
    if not sql_path:
        raise FileNotFoundError(
            f"Source schema SQL file not found in any expected location: {[str(p) for p in candidates[:4]]}"
        )


    statements = _load_statements_from_sql(sql_path)
    for statement in statements:
        op.execute(sa.text(statement))


def downgrade() -> None:
    """Tear down initial schema MVP in reverse dependency order."""
    # 1. Drop tables in reverse foreign-key dependency order
    tables = [
        "embeddings",
        "ai_analyses",
        "audit_entries",
        "reports",
        "alert_deliveries",
        "notification_channels",
        "incidents",
        "maintenance_windows",
        "health_check_daily_rollups",
        "health_check_results_2026_12",
        "health_check_results_2026_11",
        "health_check_results_2026_10",
        "health_check_results_2026_09",
        "health_check_results_2026_08",
        "health_check_results",
        "monitor_assertions",
        "monitors",
        "team_memberships",
        "teams",
        "users",
    ]
    for table in tables:
        op.execute(sa.text(f"DROP TABLE IF EXISTS {table} CASCADE;"))

    # 2. Drop custom enum types in reverse dependency order
    enums = [
        "audit_action",
        "maintenance_mode",
        "delivery_status",
        "channel_type",
        "incident_status",
        "check_status",
        "assertion_type",
        "http_method",
        "team_role",
    ]
    for enum_type in enums:
        op.execute(sa.text(f"DROP TYPE IF EXISTS {enum_type} CASCADE;"))

    # 3. Drop extensions created by this migration
    extensions = [
        "vector",
        "citext",
        "pgcrypto",
    ]
    for ext in extensions:
        op.execute(sa.text(f"DROP EXTENSION IF EXISTS {ext} CASCADE;"))
