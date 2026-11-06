"""Helper script to insert realistic sample check history for testing the UI."""
from datetime import datetime, timedelta, timezone
import uuid
from sqlalchemy import select
from app.db.session import get_db_session
from app.modules.monitors.models import Monitor
from app.modules.results.models import HealthCheckResult

def seed():
    with get_db_session() as session:
        # Find the first monitor (e.g. example1)
        stmt = select(Monitor).order_by(Monitor.created_at.desc()).limit(1)
        monitor = session.execute(stmt).scalar_one_or_none()

        if not monitor:
            print("No monitor found in database. Please create a monitor on http://localhost:5173/monitors first.")
            return

        print(f"Adding 25 sample check history rows for monitor: '{monitor.name}' ({monitor.id})")
        now = datetime.now(timezone.utc)

        # Generate 25 records over the past few hours
        results = []
        for i in range(25):
            t = now - timedelta(minutes=i * 5)
            # Make some failing, some healthy
            if i in (2, 5, 6):
                results.append(HealthCheckResult(
                    id=uuid.uuid4(),
                    monitor_id=monitor.id,
                    checked_at=t,
                    status="failing",
                    http_status_code=500,
                    response_time_ms=850 + i * 10,
                    timeout=False,
                    connection_error=False,
                    ssl_error=False,
                    error_message="Internal Server Error: Database pool exhausted",
                    response_body_excerpt='{"error": "InternalServerError", "message": "Failed to connect to database replica", "code": 5001}',
                    created_at=t,
                ))
            elif i == 8:
                results.append(HealthCheckResult(
                    id=uuid.uuid4(),
                    monitor_id=monitor.id,
                    checked_at=t,
                    status="failing",
                    http_status_code=None,
                    response_time_ms=None,
                    timeout=True,
                    connection_error=False,
                    ssl_error=False,
                    error_message="Request timed out after 10 seconds",
                    response_body_excerpt=None,
                    created_at=t,
                ))
            else:
                results.append(HealthCheckResult(
                    id=uuid.uuid4(),
                    monitor_id=monitor.id,
                    checked_at=t,
                    status="healthy",
                    http_status_code=200,
                    response_time_ms=115 + (i * 7) % 80,
                    timeout=False,
                    connection_error=False,
                    ssl_error=False,
                    error_message=None,
                    response_body_excerpt=None,
                    created_at=t,
                ))

        session.add_all(results)

        # Also update the monitor's live counter (Failure & recovery card)
        monitor.consecutive_successes = 2
        monitor.consecutive_failures = 0

        session.commit()
        print(f"Successfully inserted {len(results)} check results!")
        print("Updated monitor's consecutive_successes to 2!")
        print("Refresh your browser on http://localhost:5173 to see the table, pagination, badges, and expandable rows!")

if __name__ == "__main__":
    seed()
