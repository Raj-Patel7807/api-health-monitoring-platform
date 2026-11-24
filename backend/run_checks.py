"""Run immediate health checks on all active monitors and display results."""

from __future__ import annotations

import sys
from app.db.session import get_db_session
from app.modules.monitors.checker import check_monitor_by_id
from app.modules.monitors.models import Monitor


def main() -> None:
    print("\n🔍 Running health checks on active monitors...\n")

    with get_db_session() as session:
        monitors = (
            session.query(Monitor)
            .filter(Monitor.enabled.is_(True), Monitor.deleted_at.is_(None))
            .order_by(Monitor.created_at.desc())
            .all()
        )

        if not monitors:
            print("No active monitors found in the database.")
            return

        healthy_count = 0
        failing_count = 0

        for m in monitors:
            result = check_monitor_by_id(str(m.id), db_session=session)
            status_str = str(result.status).upper() if result else "UNKNOWN"
            code = getattr(result, "http_status_code", None)
            latency = getattr(result, "response_time_ms", None)
            err = getattr(result, "error_message", None)

            if status_str == "HEALTHY":
                healthy_count += 1
                icon = "✅"
            else:
                failing_count += 1
                icon = "❌"

            code_info = f"HTTP {code}" if code is not None else "No Response"
            latency_info = f"{latency}ms" if latency is not None else ""
            err_info = f"({err})" if err and status_str != "HEALTHY" else ""

            print(f"{icon} [{status_str:<7}] {m.name} ({m.url})")
            print(f"   ↳ {code_info} {latency_info} {err_info}".strip())
            print()

        print("-" * 60)
        print(
            f"Summary: {len(monitors)} checked | {healthy_count} Healthy | {failing_count} Failing\n"
        )


if __name__ == "__main__":
    main()
