/**
 * DashboardPage — S4-F1 (US-13)
 *
 * Shows:
 *  - 5 summary cards: total monitors, healthy, failing, unknown, open incidents
 *  - A table of all monitors sorted failing-first with:
 *      • name + URL (links to /monitors/:id)
 *      • status badge (Healthy / Failing / Unknown — color + text label)
 *      • last-checked time in local time with UTC tooltip; "—" when missing
 *      • open incident link to /incidents/:id when applicable
 *  - Loading skeleton, empty state, and error state with retry
 *  - Background refresh every 30 seconds (refetchInterval)
 */

import { useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { getDashboardData, ApiError } from "../../lib/dashboardApi";
import type { DashboardMonitorRow, DashboardSummary } from "../../lib/dashboardApi";
import type { MonitorHealthStatus } from "../../lib/dashboard";
import { AppNav } from "../components/AppNav";
import "./dashboard.css";

// ── Helpers ─────────────────────────────────────────────────────────────────

function formatLocalTime(iso: string | null): { local: string; utc: string } | null {
    if (!iso) return null;
    try {
        const date = new Date(iso);
        const local = new Intl.DateTimeFormat(undefined, {
            dateStyle: "short",
            timeStyle: "short",
        }).format(date);
        const utc = new Intl.DateTimeFormat("en-US", {
            timeZone: "UTC",
            dateStyle: "short",
            timeStyle: "short",
        }).format(date);
        return { local, utc };
    } catch {
        return null;
    }
}

// ── Sub-components ───────────────────────────────────────────────────────────

type SummaryCardProps = {
    label: string;
    value: number;
    icon: string;
    variant?: "healthy" | "failing" | "incidents" | "default";
    animationDelay?: number;
};

function SummaryCard({ label, value, icon, variant = "default", animationDelay = 0 }: SummaryCardProps) {
    return (
        <div
            className={`dashboard-summary-card${variant !== "default" ? ` dashboard-summary-card--${variant}` : ""}`}
            style={{ animationDelay: `${animationDelay}ms` }}
            data-testid={`summary-card-${label.toLowerCase().replace(/\s+/g, "-")}`}
        >
            <span className="dashboard-card-icon" aria-hidden="true">
                {icon}
            </span>
            <p className="dashboard-card-label">{label}</p>
            <p
                className={`dashboard-card-value${variant !== "default" ? ` dashboard-card-value--${variant}` : ""}`}
                aria-label={`${label}: ${value}`}
            >
                {value}
            </p>
        </div>
    );
}

type StatusBadgeProps = {
    health: MonitorHealthStatus;
};

const BADGE_LABELS: Record<MonitorHealthStatus, string> = {
    healthy: "Healthy",
    failing: "Failing",
    unknown: "Unknown",
};

function StatusBadge({ health }: StatusBadgeProps) {
    return (
        <span
            className={`dashboard-badge dashboard-badge--${health}`}
            aria-label={`Status: ${BADGE_LABELS[health]}`}
        >
            <span className="dashboard-badge-dot" aria-hidden="true" />
            {BADGE_LABELS[health]}
        </span>
    );
}

type LastCheckedCellProps = {
    iso: string | null;
};

function LastCheckedCell({ iso }: LastCheckedCellProps) {
    const formatted = formatLocalTime(iso);

    if (!formatted) {
        return (
            <span className="dashboard-cell-time-dash" aria-label="Last checked: not yet">
                —
            </span>
        );
    }

    return (
        <time
            className="dashboard-cell-time"
            dateTime={iso!}
            title={`UTC: ${formatted.utc}`}
        >
            {formatted.local}
        </time>
    );
}

// ── Summary skeleton (loading) ───────────────────────────────────────────────

function SummarySkeleton() {
    return (
        <div className="dashboard-skeleton-cards" aria-hidden="true">
            {Array.from({ length: 5 }).map((_, i) => (
                <div key={i} className="dashboard-skeleton-card" />
            ))}
        </div>
    );
}

// ── Summary cards ────────────────────────────────────────────────────────────

type SummaryCardsProps = { summary: DashboardSummary };

function SummaryCards({ summary }: SummaryCardsProps) {
    return (
        <section
            className="dashboard-summary-grid"
            aria-label="Health summary"
            data-testid="summary-cards"
        >
            <SummaryCard
                label="Total Monitors"
                value={summary.total}
                icon="📡"
                variant="default"
                animationDelay={0}
            />
            <SummaryCard
                label="Healthy"
                value={summary.healthy}
                icon="✅"
                variant="healthy"
                animationDelay={60}
            />
            <SummaryCard
                label="Failing"
                value={summary.failing}
                icon="🔴"
                variant="failing"
                animationDelay={120}
            />
            <SummaryCard
                label="Unknown"
                value={summary.unknown}
                icon="⚪"
                variant="default"
                animationDelay={180}
            />
            <SummaryCard
                label="Open Incidents"
                value={summary.openIncidents}
                icon="🚨"
                variant="incidents"
                animationDelay={240}
            />
        </section>
    );
}

// ── Monitor table ─────────────────────────────────────────────────────────────

type MonitorTableProps = { rows: DashboardMonitorRow[] };

function MonitorTable({ rows }: MonitorTableProps) {
    if (rows.length === 0) {
        return (
            <div className="dashboard-state-box" data-testid="empty-state">
                <span className="dashboard-state-icon" aria-hidden="true">📡</span>
                <h2>No monitors yet</h2>
                <p>
                    Start tracking your endpoints to see their health here.
                </p>
                <Link
                    to="/monitors/new"
                    className="dashboard-button dashboard-button--primary"
                    data-testid="add-first-monitor-link"
                >
                    Add your first monitor
                </Link>
            </div>
        );
    }

    return (
        <div className="dashboard-table-container">
            <table className="dashboard-table">
                <caption className="dashboard-sr-only">Monitor health overview</caption>
                <thead>
                    <tr>
                        <th scope="col">Monitor</th>
                        <th scope="col">Status</th>
                        <th scope="col">Last Checked</th>
                        <th scope="col">Response</th>
                        <th scope="col">Incident</th>
                    </tr>
                </thead>
                <tbody>
                    {rows.map((row) => (
                        <tr key={row.id} data-testid={`monitor-row-${row.id}`}>
                            {/* Name + URL */}
                            <td>
                                <div className="dashboard-cell-name">
                                    <Link
                                        to={`/monitors/${row.id}`}
                                        className="dashboard-cell-name-link"
                                        aria-label={`View monitor ${row.name}`}
                                    >
                                        {row.name}
                                    </Link>
                                    <span className="dashboard-cell-url">
                                        {row.url}
                                    </span>
                                </div>
                            </td>

                            {/* Health badge — color + text label (not color-only) */}
                            <td>
                                <StatusBadge health={row.health} />
                            </td>

                            {/* Last checked — local time with UTC tooltip; "—" if null */}
                            <td>
                                <LastCheckedCell iso={row.lastCheckedAt} />
                            </td>

                            {/* Response time */}
                            <td>
                                {row.lastResponseTimeMs !== null ? (
                                    <span className="dashboard-cell-rt">
                                        {row.lastResponseTimeMs} ms
                                    </span>
                                ) : (
                                    <span className="dashboard-cell-time-dash" aria-label="Response time: not available">
                                        —
                                    </span>
                                )}
                            </td>

                            {/* Open incident link */}
                            <td>
                                {row.openIncidentId ? (
                                    <Link
                                        to={`/incidents/${row.openIncidentId}`}
                                        className="dashboard-incident-link"
                                        aria-label={`View open incident for ${row.name}`}
                                    >
                                        🚨 Open incident
                                    </Link>
                                ) : (
                                    <span className="dashboard-no-incident">—</span>
                                )}
                            </td>
                        </tr>
                    ))}
                </tbody>
            </table>
        </div>
    );
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export function DashboardPage() {
    const navigate = useNavigate();

    const { data, isLoading, isError, error, refetch } = useQuery({
        queryKey: ["dashboard"],
        queryFn: getDashboardData,
        // Refresh every 30 seconds in the background without flicker
        refetchInterval: 30_000,
        refetchIntervalInBackground: false,
        // Keep previous data visible during refresh to avoid flicker
        placeholderData: keepPreviousData,
    });

    // Redirect to login on 401
    useEffect(() => {
        if (error instanceof ApiError && error.status === 401) {
            navigate("/login", { replace: true });
        }
    }, [error, navigate]);

    return (
        <main className="dashboard-page">
            <AppNav />

            {/* Page header */}
            <header className="dashboard-header">
                <div className="dashboard-header-text">
                    <h1>Dashboard</h1>
                    <p className="dashboard-subtitle">
                        Real-time health overview of all your monitored endpoints.
                    </p>
                </div>
                <div className="dashboard-refresh-info" aria-live="polite">
                    <span className="dashboard-refresh-dot" aria-hidden="true" />
                    Auto-refreshes every 30s
                </div>
            </header>

            {/* Loading skeleton for summary cards */}
            {isLoading && !data && <SummarySkeleton />}

            {/* Summary cards (shown once data is available; kept during background refresh) */}
            {data && <SummaryCards summary={data.summary} />}

            {/* Error state */}
            {isError && !data && (
                <div
                    role="alert"
                    className="dashboard-monitors-card"
                    data-testid="error-state"
                >
                    <div className="dashboard-state-box">
                        <span className="dashboard-state-icon" aria-hidden="true">⚠️</span>
                        <h2>Could not load dashboard</h2>
                        <p>
                            {error instanceof Error
                                ? error.message
                                : "Something went wrong."}
                        </p>
                        <button
                            type="button"
                            className="dashboard-button dashboard-button--secondary"
                            onClick={() => void refetch()}
                            data-testid="retry-btn"
                        >
                            Try again
                        </button>
                    </div>
                </div>
            )}

            {/* Monitor table */}
            <section className="dashboard-monitors-card" aria-labelledby="monitors-heading">
                <div className="dashboard-monitors-card-header">
                    <h2 id="monitors-heading">All Monitors</h2>
                    <Link
                        to="/monitors"
                        className="dashboard-monitors-card-link"
                        aria-label="Go to full monitors list"
                    >
                        Manage monitors →
                    </Link>
                </div>

                {/* Loading spinner inside table area */}
                {isLoading && !data && (
                    <div
                        role="status"
                        className="dashboard-state-box"
                        aria-live="polite"
                        data-testid="loading-state"
                    >
                        <span className="spinner" aria-hidden="true" />
                        <p>Loading monitors…</p>
                    </div>
                )}

                {/* Table — also renders during background refresh keeping previous data */}
                {data && (
                    <MonitorTable rows={data.rows} />
                )}

                {/* Error inside table area (only if no previous data) */}
                {isError && !data && null /* already handled above */}
            </section>
        </main>
    );
}
