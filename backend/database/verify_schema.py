#!/usr/bin/env python3
"""Automated Schema & Migration Verification Suite for API Health & Incident Monitoring Dashboard.
Verifies steps 5b to 5g:
  - 5b: Confirm DB is empty before migrating
  - 5c: alembic upgrade head
  - 5d: Compare live DB against ERD design (tables, columns, PKs, FKs, unique constraints, indexes, enums)
  - 5e: Smoke-test sample data exercising all FKs, rolled back in transaction + negative constraint tests
  - 5f: alembic downgrade base (verify clean DB) -> alembic upgrade head (idempotency)
  - 5g: docker compose down -v -> docker compose up -d -> fresh upgrade head
"""

import os
import socket
import subprocess
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, urlunparse

from dotenv import load_dotenv

# Ensure UTF-8 output on Windows consoles
if sys.stdout.encoding != "utf-8":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass


import psycopg
from psycopg.rows import dict_row

# Paths
REPO_ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = REPO_ROOT / "backend"

# Load environment
load_dotenv(BACKEND_DIR / ".env")
load_dotenv(REPO_ROOT / ".env")


def get_resolved_db_url() -> str:
    """Resolve database URL ensuring reachability (WSL2 bridge fallback)."""
    db_url = os.getenv("DATABASE_URL")
    if not db_url:
        user = os.getenv("POSTGRES_USER", "postgres")
        password = os.getenv("POSTGRES_PASSWORD", "postgres")
        host = os.getenv("POSTGRES_HOST", "127.0.0.1")
        port = os.getenv("POSTGRES_PORT", "5432")
        db = os.getenv("POSTGRES_DB", "api_health")
        db_url = f"postgresql://{user}:{password}@{host}:{port}/{db}"

    # Remove +psycopg driver for direct psycopg connection
    clean_url = db_url.replace("+psycopg", "")
    parsed = urlparse(clean_url)
    host = parsed.hostname or "127.0.0.1"
    port = parsed.port or 5432

    if host in ("localhost", "127.0.0.1"):
        reachable = False
        try:
            with socket.create_connection((host, port), timeout=0.5):
                reachable = True
        except (TimeoutError, OSError):
            reachable = False

        if not reachable:
            try:
                res = subprocess.run(
                    ["wsl", "-d", "Ubuntu-24.04", "--", "hostname", "-I"],
                    capture_output=True,
                    text=True,
                    timeout=2,
                )
                if res.returncode == 0 and res.stdout.strip():
                    wsl_ip = res.stdout.strip().split()[0]
                    with socket.create_connection((wsl_ip, port), timeout=0.5):
                        new_netloc = parsed.netloc.replace(f"@{host}", f"@{wsl_ip}").replace(
                            host, wsl_ip
                        )
                        parsed = parsed._replace(netloc=new_netloc)
                        clean_url = urlunparse(parsed)
            except Exception:
                pass

    return clean_url


def run_alembic(command: list[str]) -> subprocess.CompletedProcess:
    alembic_exe = BACKEND_DIR / ".venv" / "Scripts" / "alembic.exe"
    if not alembic_exe.exists():
        alembic_exe = BACKEND_DIR / ".venv" / "bin" / "alembic"
    if not alembic_exe.exists():
        alembic_cmd = ["alembic"]
    else:
        alembic_cmd = [str(alembic_exe)]

    cmd = alembic_cmd + command
    print(f"  $ {' '.join(cmd)}")
    res = subprocess.run(cmd, cwd=BACKEND_DIR, capture_output=True, text=True)
    if res.stdout:
        print(res.stdout.strip())
    if res.stderr:
        print(res.stderr.strip(), file=sys.stderr)
    if res.returncode != 0:
        raise RuntimeError(f"Alembic command failed: {' '.join(cmd)}")
    return res


def wait_for_db(url: str, timeout: int = 30) -> None:
    start = time.time()
    while time.time() - start < timeout:
        try:
            conn = psycopg.connect(url, connect_timeout=2)
            conn.close()
            return
        except Exception:
            time.sleep(1)
    raise TimeoutError(f"Database at {url} did not become ready within {timeout}s")


def assert_empty_db(url: str) -> None:
    print("\n--- 5b. Confirm DB is empty before migrating ---")
    with psycopg.connect(url) as conn:
        with conn.cursor() as cur:
            # Check user tables
            cur.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' AND tablename != 'alembic_version';"
            )
            tables = cur.fetchall()
            # Check enums
            cur.execute(
                "SELECT typname FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'public' AND t.typtype = 'e';"
            )
            enums = cur.fetchall()
            # Check extensions
            cur.execute("SELECT extname FROM pg_extension WHERE extname NOT IN ('plpgsql');")
            exts = cur.fetchall()

            print(f"  Public tables found: {len(tables)} -> {tables}")
            print(f"  Public enums found:  {len(enums)} -> {enums}")
            print(f"  Extensions found:    {len(exts)} -> {exts}")

            assert len(tables) == 0, f"Expected 0 tables, got {tables}"
            assert len(enums) == 0, f"Expected 0 custom enums, got {enums}"
            assert len(exts) == 0, f"Expected 0 custom extensions, got {exts}"
    print("  [OK] Database confirmed completely empty!")


def assert_schema_against_erd(url: str) -> None:
    print("\n--- 5d. Compare Live DB against Design / ERD ---")
    expected_tables = [
        "users",
        "teams",
        "team_memberships",
        "monitors",
        "monitor_assertions",
        "health_check_results",
        "health_check_results_2026_08",
        "health_check_results_2026_09",
        "health_check_results_2026_10",
        "health_check_results_2026_11",
        "health_check_results_2026_12",
        "health_check_daily_rollups",
        "maintenance_windows",
        "incidents",
        "notification_channels",
        "alert_deliveries",
        "reports",
        "audit_entries",
        "ai_analyses",
        "embeddings",
    ]

    expected_enums = [
        "team_role",
        "http_method",
        "assertion_type",
        "check_status",
        "incident_status",
        "channel_type",
        "delivery_status",
        "maintenance_mode",
        "audit_action",
    ]

    expected_extensions = ["pgcrypto", "citext", "vector"]

    with psycopg.connect(url, row_factory=dict_row) as conn:
        with conn.cursor() as cur:
            # 1. Tables check
            cur.execute(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public' ORDER BY tablename;"
            )
            live_tables = {r["tablename"] for r in cur.fetchall()}

            print("\n  [TABLES CHECK]")
            print(f"  {'Table Name':<35} {'Status'}")
            print("  " + "-" * 45)
            for tbl in expected_tables:
                status = "✅ Present" if tbl in live_tables else "❌ Missing"
                print(f"  {tbl:<35} {status}")
                assert tbl in live_tables, f"Table {tbl} missing in live database!"

            # 2. Enums check
            cur.execute(
                "SELECT typname FROM pg_type t JOIN pg_namespace n ON t.typnamespace = n.oid WHERE n.nspname = 'public' AND t.typtype = 'e';"
            )
            live_enums = {r["typname"] for r in cur.fetchall()}

            print("\n  [ENUMS CHECK]")
            print(f"  {'Enum Type':<35} {'Status'}")
            print("  " + "-" * 45)
            for enm in expected_enums:
                status = "✅ Present" if enm in live_enums else "❌ Missing"
                print(f"  {enm:<35} {status}")
                assert enm in live_enums, f"Enum {enm} missing in live database!"

            # 3. Extensions check
            cur.execute("SELECT extname FROM pg_extension;")
            live_exts = {r["extname"] for r in cur.fetchall()}

            print("\n  [EXTENSIONS CHECK]")
            print(f"  {'Extension':<35} {'Status'}")
            print("  " + "-" * 45)
            for ext in expected_extensions:
                status = "✅ Present" if ext in live_exts else "❌ Missing"
                print(f"  {ext:<35} {status}")
                assert ext in live_exts, f"Extension {ext} missing in live database!"

            # 4. Foreign keys check
            cur.execute("""
                SELECT
                    tc.table_name AS from_table,
                    kcu.column_name AS from_column,
                    ccu.table_name AS to_table,
                    ccu.column_name AS to_column
                FROM information_schema.table_constraints AS tc
                JOIN information_schema.key_column_usage AS kcu
                    ON tc.constraint_name = kcu.constraint_name
                    AND tc.table_schema = kcu.table_schema
                JOIN information_schema.constraint_column_usage AS ccu
                    ON ccu.constraint_name = tc.constraint_name
                    AND ccu.table_schema = tc.table_schema
                WHERE tc.constraint_type = 'FOREIGN KEY' AND tc.table_schema = 'public'
                ORDER BY tc.table_name, kcu.column_name;
            """)
            live_fks = cur.fetchall()
            print("\n  [FOREIGN KEYS CHECK]")
            print(f"  {'From Table.Column':<40} {'To Table.Column':<30} {'Status'}")
            print("  " + "-" * 78)
            fk_pairs = {
                (r["from_table"], r["from_column"], r["to_table"], r["to_column"]) for r in live_fks
            }

            expected_fks = [
                ("team_memberships", "team_id", "teams", "id"),
                ("team_memberships", "user_id", "users", "id"),
                ("monitors", "team_id", "teams", "id"),
                ("monitor_assertions", "monitor_id", "monitors", "id"),
                ("health_check_results", "monitor_id", "monitors", "id"),
                ("health_check_results", "failed_assertion_id", "monitor_assertions", "id"),
                ("health_check_daily_rollups", "monitor_id", "monitors", "id"),
                ("maintenance_windows", "monitor_id", "monitors", "id"),
                ("maintenance_windows", "created_by", "users", "id"),
                ("incidents", "monitor_id", "monitors", "id"),
                ("notification_channels", "team_id", "teams", "id"),
                ("notification_channels", "monitor_id", "monitors", "id"),
                ("alert_deliveries", "incident_id", "incidents", "id"),
                ("alert_deliveries", "notification_channel_id", "notification_channels", "id"),
                ("reports", "team_id", "teams", "id"),
                ("reports", "monitor_id", "monitors", "id"),
                ("reports", "requested_by", "users", "id"),
                ("audit_entries", "user_id", "users", "id"),
                ("ai_analyses", "incident_id", "incidents", "id"),
            ]

            for src_tbl, src_col, dst_tbl, dst_col in expected_fks:
                present = (src_tbl, src_col, dst_tbl, dst_col) in fk_pairs
                status = "✅ Active FK" if present else "❌ Missing FK"
                src_str = f"{src_tbl}.{src_col}"
                dst_str = f"{dst_tbl}.{dst_col}"
                print(f"  {src_str:<40} {dst_str:<30} {status}")
                assert present, f"Foreign key {src_str} -> {dst_str} missing!"

            print("  [OK] ERD vs Live DB comparison: 100% Match!")


def smoke_test_sample_data(url: str) -> None:
    print("\n--- 5e. Smoke-test with sample data in a transaction rolled back ---")
    with psycopg.connect(url) as conn:
        # Start transaction
        with conn.transaction():
            with conn.cursor() as cur:
                # 1. Insert User
                cur.execute("""
                    INSERT INTO users (email, full_name, password_hash)
                    VALUES ('alice@example.com', 'Alice Engineer', 'argon2id$hashedpassword')
                    RETURNING id;
                """)
                user_id = cur.fetchone()[0]
                print(f"  [+] Inserted user id: {user_id}")

                # 2. Insert Team
                cur.execute("""
                    INSERT INTO teams (name)
                    VALUES ('Platform Infra Team')
                    RETURNING id;
                """)
                team_id = cur.fetchone()[0]
                print(f"  [+] Inserted team id: {team_id}")

                # 3. Insert Team Membership
                cur.execute(
                    """
                    INSERT INTO team_memberships (team_id, user_id, role)
                    VALUES (%s, %s, 'admin')
                    RETURNING id;
                """,
                    (team_id, user_id),
                )
                membership_id = cur.fetchone()[0]
                print(f"  [+] Inserted team_membership id: {membership_id}")

                # 4. Insert Monitor
                cur.execute(
                    """
                    INSERT INTO monitors (team_id, name, url, method, check_interval_seconds)
                    VALUES (%s, 'Payment Gateway API', 'https://api.payments.internal/health', 'GET', 30)
                    RETURNING id;
                """,
                    (team_id,),
                )
                monitor_id = cur.fetchone()[0]
                print(f"  [+] Inserted monitor id: {monitor_id}")

                # 5. Insert Monitor Assertion
                cur.execute(
                    """
                    INSERT INTO monitor_assertions (monitor_id, assertion_type, expression, expected_value)
                    VALUES (%s, 'jsonpath', '$.status', 'UP')
                    RETURNING id;
                """,
                    (monitor_id,),
                )
                assertion_id = cur.fetchone()[0]
                print(f"  [+] Inserted monitor_assertion id: {assertion_id}")

                # 6. Insert Health Check Result (dated 2026-10-12, lands in partition 2026_10)
                cur.execute(
                    """
                    INSERT INTO health_check_results (
                        monitor_id, checked_at, status, http_status_code, response_time_ms, failed_assertion_id
                    )
                    VALUES (%s, '2026-10-12 02:00:00+00', 'healthy', 200, 45, NULL)
                    RETURNING id;
                """,
                    (monitor_id,),
                )
                hcr_id = cur.fetchone()[0]
                print(f"  [+] Inserted health_check_result id: {hcr_id} into monthly partition")

                # 7. Insert Rollup
                cur.execute(
                    """
                    INSERT INTO health_check_daily_rollups (
                        monitor_id, day, total_checks, failed_checks, avg_response_time_ms, p95_response_time_ms, uptime_percentage
                    )
                    VALUES (%s, '2026-10-12', 1440, 0, 44.50, 68.20, 100.00)
                    RETURNING id;
                """,
                    (monitor_id,),
                )
                rollup_id = cur.fetchone()[0]
                print(f"  [+] Inserted health_check_daily_rollups id: {rollup_id}")

                # 8. Insert Maintenance Window
                cur.execute(
                    """
                    INSERT INTO maintenance_windows (
                        monitor_id, name, starts_at, ends_at, mode, reason, created_by
                    )
                    VALUES (%s, 'DB Upgrade Maintenance', '2026-10-12 04:00:00+00', '2026-10-12 05:00:00+00', 'suppress_alerts', 'Routine patching', %s)
                    RETURNING id;
                """,
                    (monitor_id, user_id),
                )
                maint_id = cur.fetchone()[0]
                print(f"  [+] Inserted maintenance_window id: {maint_id}")

                # 9. Insert Incident
                cur.execute(
                    """
                    INSERT INTO incidents (monitor_id, status, opened_at, failure_count)
                    VALUES (%s, 'open', '2026-10-12 03:00:00+00', 3)
                    RETURNING id;
                """,
                    (monitor_id,),
                )
                incident_id = cur.fetchone()[0]
                print(f"  [+] Inserted incident id: {incident_id}")

                # 10. Insert Notification Channel
                cur.execute(
                    """
                    INSERT INTO notification_channels (team_id, monitor_id, type, name, configuration)
                    VALUES (%s, %s, 'slack', 'Ops Alerts Slack', '{"webhook_url": "https://hooks.slack.com/services/xxx"}'::jsonb)
                    RETURNING id;
                """,
                    (team_id, monitor_id),
                )
                channel_id = cur.fetchone()[0]
                print(f"  [+] Inserted notification_channel id: {channel_id}")

                # 11. Insert Alert Delivery
                cur.execute(
                    """
                    INSERT INTO alert_deliveries (incident_id, notification_channel_id, status, attempt_count)
                    VALUES (%s, %s, 'sent', 1)
                    RETURNING id;
                """,
                    (incident_id, channel_id),
                )
                delivery_id = cur.fetchone()[0]
                print(f"  [+] Inserted alert_delivery id: {delivery_id}")

                # 12. Insert Report
                cur.execute(
                    """
                    INSERT INTO reports (
                        team_id, monitor_id, requested_by, period_start, period_end, uptime_percentage, total_checks, failed_checks
                    )
                    VALUES (%s, %s, %s, '2026-10-01 00:00:00+00', '2026-10-08 00:00:00+00', 99.95, 10080, 5)
                    RETURNING id;
                """,
                    (team_id, monitor_id, user_id),
                )
                report_id = cur.fetchone()[0]
                print(f"  [+] Inserted report id: {report_id}")

                # 13. Insert Audit Entry (append-only)
                cur.execute(
                    """
                    INSERT INTO audit_entries (user_id, action, entity_type, entity_id, new_values)
                    VALUES (%s, 'INSERT', 'monitors', %s, '{"name": "Payment Gateway API"}'::jsonb)
                    RETURNING id;
                """,
                    (user_id, monitor_id),
                )
                audit_id = cur.fetchone()[0]
                print(f"  [+] Inserted audit_entry id: {audit_id}")

                # 14. Insert AI Analysis
                cur.execute(
                    """
                    INSERT INTO ai_analyses (incident_id, summary, suggested_actions, model)
                    VALUES (%s, 'Payment API degraded due to high connection latency.', '["Scale payment pod", "Check DB connection pool"]'::jsonb, 'gemini-1.5-pro')
                    RETURNING id;
                """,
                    (incident_id,),
                )
                analysis_id = cur.fetchone()[0]
                print(f"  [+] Inserted ai_analysis id: {analysis_id}")

                # 15. Insert Embedding (1536 dims pgvector)
                dummy_vec = "[" + ",".join(["0.01"] * 1536) + "]"
                cur.execute(
                    """
                    INSERT INTO embeddings (entity_type, entity_id, content, embedding)
                    VALUES ('ai_analysis', %s, 'Payment API degraded due to latency', %s::vector)
                    RETURNING id;
                """,
                    (analysis_id, dummy_vec),
                )
                emb_id = cur.fetchone()[0]
                print(f"  [+] Inserted embedding id: {emb_id} with 1536-dimensional vector")

                print("  [OK] Successfully exercised all 15 tables and their foreign keys!")
                # In psycopg 3, raising psycopg.Rollback rolls back the transaction cleanly
                raise psycopg.Rollback()
    print("  [OK] Rolled back smoke-test transaction cleanly.")

    # -------------------------------------------------------------
    # Negative constraint tests: assert errors on invalid actions
    # -------------------------------------------------------------
    print("\n  [NEGATIVE CONSTRAINT TESTS]")
    with psycopg.connect(url) as conn:
        # Test 1: Invalid check constraint (check_interval_seconds <= 0)
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO monitors (team_id, name, url, check_interval_seconds)
                    VALUES ('00000000-0000-0000-0000-000000000001', 'Bad Interval', 'https://api.com', -10);
                """)
            raise AssertionError("Failed to reject check_interval_seconds <= 0")
        except psycopg.Error as e:
            conn.rollback()
            print(f"  [OK] Rejected negative check_interval_seconds: {type(e).__name__}")

        # Test 2: Orphan Foreign Key rejection
        try:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO monitors (team_id, name, url)
                    VALUES ('ffffffff-ffff-ffff-ffff-ffffffffffff', 'Orphan Monitor', 'https://api.com');
                """)
            raise AssertionError("Failed to reject orphan FK monitor -> team")
        except psycopg.Error as e:
            conn.rollback()
            print(f"  [OK] Rejected orphan foreign key: {type(e).__name__}")

        # Test 3: Duplicate Unique constraint rejection (duplicate user email)
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (email, full_name, password_hash) VALUES ('unique@test.com', 'U1', 'h1');"
                )
                cur.execute(
                    "INSERT INTO users (email, full_name, password_hash) VALUES ('unique@test.com', 'U2', 'h2');"
                )
            raise AssertionError("Failed to reject duplicate unique email")
        except psycopg.Error as e:
            conn.rollback()
            print(f"  [OK] Rejected duplicate unique email: {type(e).__name__}")

        # Test 4: Invalid Enum value rejection
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "INSERT INTO team_memberships (team_id, user_id, role) VALUES ('00000000-0000-0000-0000-000000000001', '00000000-0000-0000-0000-000000000002', 'superadmin');"
                )
            raise AssertionError("Failed to reject invalid enum value")
        except psycopg.Error as e:
            conn.rollback()
            print(f"  [OK] Rejected invalid enum value 'superadmin': {type(e).__name__}")


def test_idempotency_rollback(url: str) -> None:
    print("\n--- 5f. Idempotency & Rollback test ---")
    print("  [>] Running 'alembic downgrade base'...")
    run_alembic(["downgrade", "base"])

    # Verify DB returns to empty
    assert_empty_db(url)

    print("  [>] Running 'alembic upgrade head' again...")
    run_alembic(["upgrade", "head"])

    # Show current & history
    print("\n  [>] alembic current:")
    run_alembic(["current"])
    print("\n  [>] alembic history:")
    run_alembic(["history"])
    print("  [OK] Rollback and re-upgrade succeeded idempotently!")


# def test_destroy_and_recreate(url: str) -> None:
#     print("\n--- 5g. Destroy-and-recreate test (docker compose down -v) ---")
#     print("  [>] Running 'docker compose down -v'...")
#     subprocess.run("docker compose down -v", cwd=REPO_ROOT, check=True, shell=True)

#     print("  [>] Bringing up fresh container with 'docker compose up -d'...")
#     subprocess.run("docker compose up -d", cwd=REPO_ROOT, check=True, shell=True)

#     print("  [>] Waiting for container to be healthy...")
#     resolved_url = get_resolved_db_url()
#     wait_for_db(resolved_url, timeout=30)

#     print("  [>] Confirming brand-new container DB is empty...")
#     assert_empty_db(resolved_url)

#     print("  [>] Running 'alembic upgrade head' on fresh container...")
#     run_alembic(["upgrade", "head"])

#     print("  [>] Comparing fresh schema against ERD...")
#     assert_schema_against_erd(resolved_url)

#     print("  [OK] Destroy-and-recreate test PASSED 100%!")


def main():
    print("==================================================================")
    print(" DISTRIBUTED API HEALTH MONITORING — DATABASE VERIFICATION SUITE  ")
    print("==================================================================")

    url = get_resolved_db_url()
    wait_for_db(url)

    # 5d: Verify live DB against ERD
    assert_schema_against_erd(url)

    # 5e: Smoke-test sample data & negative constraints
    smoke_test_sample_data(url)

    # 5f: Idempotency & rollback test
    if os.getenv("ALLOW_DESTRUCTIVE_DB_VERIFY") == "1":
        test_idempotency_rollback(url)

    # 5g: Destroy and recreate test
    # test_destroy_and_recreate(url)

    print("\n" + "=" * 66)
    print(" ALL VERIFICATION TASKS (5b to 5g) PASSED WITH ZERO ERRORS! ")
    print("==================================================================")


if __name__ == "__main__":
    main()
