"""Dashboard service layer for aggregated health metrics (US-13).

Provides single-query retrieval of all active monitors for a team with their
latest health check result (bounded by a freshness window) and active open incident.
"""

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.dashboard.schemas import (
    DashboardMonitorItem,
    DashboardResponse,
    DashboardSummary,
)
from app.modules.incidents.models import Incident
from app.modules.monitors.models import Monitor
from app.modules.results.models import HealthCheckResult

DEFAULT_FRESHNESS_HOURS = 24
STATUS_SORT_ORDER = {"failing": 0, "unknown": 1, "healthy": 2}


def derive_monitor_status(
    result_status: str | None,
    open_incident_id: UUID | None,
) -> str:
    """Derive health status for an active monitor on the dashboard.

    Status rules:
    - If no recent check result within the freshness window: 'unknown'
    - Else if an open incident exists or the latest check failed: 'failing'
    - Else: 'healthy'
    """
    if result_status is None:
        return "unknown"
    if open_incident_id is not None or result_status == "failing":
        return "failing"
    return "healthy"


async def get_dashboard(
    db: AsyncSession,
    team_id: UUID,
    freshness_window: timedelta | None = None,
) -> DashboardResponse:
    """Retrieve all active monitors for the team and aggregate their health status.

    Uses a single SQL query with a window function subquery to fetch the latest
    result per monitor within the freshness window, guaranteeing O(1) query count
    regardless of monitor count.
    """
    now = datetime.now(UTC)
    window = freshness_window or timedelta(hours=DEFAULT_FRESHNESS_HOURS)
    since = now - window

    # Subquery filtering active monitors for the team
    active_monitors_subq = select(Monitor.id).where(
        Monitor.team_id == team_id,
        Monitor.enabled.is_(True),
        Monitor.deleted_at.is_(None),
    )

    # Window function to number results per monitor descending by checked_at
    rn = (
        func.row_number()
        .over(
            partition_by=HealthCheckResult.monitor_id,
            order_by=HealthCheckResult.checked_at.desc(),
        )
        .label("rn")
    )

    # Subquery limited by time so PostgreSQL only scans recent monthly partitions
    latest_results_subq = (
        select(
            HealthCheckResult.monitor_id,
            HealthCheckResult.status.label("result_status"),
            HealthCheckResult.checked_at.label("last_checked_at"),
            HealthCheckResult.response_time_ms.label("last_response_time_ms"),
            rn,
        )
        .where(
            HealthCheckResult.monitor_id.in_(active_monitors_subq),
            HealthCheckResult.checked_at >= since,
        )
        .subquery()
    )

    # Main query joining active monitors, latest result (rn=1), and open incident
    stmt = (
        select(
            Monitor.id,
            Monitor.name,
            latest_results_subq.c.result_status,
            latest_results_subq.c.last_checked_at,
            latest_results_subq.c.last_response_time_ms,
            Incident.id.label("open_incident_id"),
        )
        .outerjoin(
            latest_results_subq,
            (latest_results_subq.c.monitor_id == Monitor.id) & (latest_results_subq.c.rn == 1),
        )
        .outerjoin(
            Incident,
            (Incident.monitor_id == Monitor.id) & (Incident.status == "open"),
        )
        .where(
            Monitor.team_id == team_id,
            Monitor.enabled.is_(True),
            Monitor.deleted_at.is_(None),
        )
    )

    result = await db.execute(stmt)
    rows = result.all()

    monitors: list[DashboardMonitorItem] = []
    healthy_count = 0
    failing_count = 0
    unknown_count = 0
    open_incidents_count = 0

    for row in rows:
        m_id, m_name, res_status, last_checked, last_rt, open_inc_id = row

        status = derive_monitor_status(res_status, open_inc_id)

        if status == "healthy":
            healthy_count += 1
        elif status == "failing":
            failing_count += 1
        else:
            unknown_count += 1

        if open_inc_id is not None:
            open_incidents_count += 1

        monitors.append(
            DashboardMonitorItem(
                id=m_id,
                name=m_name,
                status=status,
                last_checked_at=last_checked if res_status is not None else None,
                last_response_time_ms=last_rt if res_status is not None else None,
                open_incident_id=open_inc_id,
            )
        )

    # Failing monitors are listed first, then unknown, then healthy; tiebreak by name
    monitors.sort(
        key=lambda m: (
            STATUS_SORT_ORDER.get(m.status, 9),
            m.name.lower(),
        )
    )

    summary = DashboardSummary(
        total_monitors=len(monitors),
        healthy=healthy_count,
        failing=failing_count,
        unknown=unknown_count,
        open_incidents=open_incidents_count,
    )

    return DashboardResponse(monitors=monitors, summary=summary)
