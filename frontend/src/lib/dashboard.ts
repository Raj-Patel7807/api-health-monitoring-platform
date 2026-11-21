/**
 * Types for the Dashboard page (US-13 / S4-F1).
 *
 * The dashboard aggregates:
 *   - GET /monitors (all monitors with their current status)
 *   - GET /incidents?status=open (count of open incidents + per-monitor incident id)
 */

export type MonitorHealthStatus = "healthy" | "failing" | "unknown";

/**
 * One row in the dashboard monitor table.
 * Derived client-side from Monitor + latest CheckResult + open Incident (if any).
 */
export type DashboardMonitorRow = {
    id: string;
    name: string;
    url: string;
    health: MonitorHealthStatus;
    lastCheckedAt: string | null; // ISO 8601 or null
    lastResponseTimeMs: number | null;
    openIncidentId: string | null;
};

/**
 * Summary card counts shown at the top of the dashboard.
 */
export type DashboardSummary = {
    total: number;
    healthy: number;
    failing: number;
    unknown: number;
    openIncidents: number;
};
