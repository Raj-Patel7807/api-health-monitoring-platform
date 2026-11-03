import { useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { AppNav } from "../components/AppNav";
import {
    formatDateTime,
    formatIncidentDuration,
    type Incident,
    type IncidentFilterStatus,
    type IncidentListResponse,
} from "../../lib/incidents";
import { listIncidents, ApiError } from "../../lib/incidentsApi";
import { listMonitors } from "../../lib/monitorsApi";
import "./monitors.css";
import "./incidents.css";

export function IncidentsPage() {
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();

    const rawPage = parseInt(searchParams.get("page") ?? "1", 10);
    const page = Number.isInteger(rawPage) && rawPage >= 1 ? rawPage : 1;

    const rawStatus = searchParams.get("status");
    const statusFilter: IncidentFilterStatus =
        rawStatus === "open" || rawStatus === "resolved" ? rawStatus : "all";

    const monitorIdFilter = searchParams.get("monitor_id") ?? "";

    // Load monitors list for the monitor filter dropdown
    const { data: monitorsData } = useQuery({
        queryKey: ["monitors-filter-options"],
        queryFn: () => listMonitors(1, 100),
    });
    const monitors = monitorsData?.items ?? [];

    // Query incidents with status and monitor filters
    const { data, isLoading, isError, error, refetch } = useQuery({
        queryKey: [
            "incidents",
            { page, status: statusFilter, monitorId: monitorIdFilter },
        ],
        queryFn: () =>
            listIncidents({
                page,
                pageSize: 20,
                status: statusFilter,
                monitorId: monitorIdFilter || undefined,
            }),
        placeholderData: keepPreviousData,
        // Refresh every 20 seconds while any incident in the list is open
        refetchInterval: (query) => {
            const listData = query.state.data as
                IncidentListResponse | undefined;
            const hasOpenIncident = listData?.items?.some(
                (i) => i.status === "open",
            );
            return hasOpenIncident ? 20_000 : false;
        },
    });

    useEffect(() => {
        if (error instanceof ApiError && error.status === 401) {
            navigate("/login", { replace: true });
        }
    }, [error, navigate]);

    function handleStatusChange(nextStatus: IncidentFilterStatus) {
        setSearchParams((prev) => {
            const copy = new URLSearchParams(prev);
            if (nextStatus === "all") {
                copy.delete("status");
            } else {
                copy.set("status", nextStatus);
            }
            copy.set("page", "1");
            return copy;
        });
    }

    function handleMonitorChange(nextMonitorId: string) {
        setSearchParams((prev) => {
            const copy = new URLSearchParams(prev);
            if (!nextMonitorId) {
                copy.delete("monitor_id");
            } else {
                copy.set("monitor_id", nextMonitorId);
            }
            copy.set("page", "1");
            return copy;
        });
    }

    function handlePageChange(nextPage: number) {
        setSearchParams((prev) => {
            const copy = new URLSearchParams(prev);
            copy.set("page", String(nextPage));
            return copy;
        });
    }

    const total = data?.total ?? 0;
    const pageSize = data?.page_size ?? 20;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    const items: Incident[] = data?.items ?? [];
    const isEmpty = !isLoading && !isError && items.length === 0;
    const hasOpenIncidents = items.some((i) => i.status === "open");

    return (
        <main className="monitors-page">
            <AppNav />

            <header className="monitors-header">
                <div className="monitors-header-text">
                    <h1>Incidents</h1>
                    <p className="monitors-subtitle">
                        Track outages, confirmed failures, and recovery status
                        across your services.
                    </p>
                </div>
                {hasOpenIncidents && (
                    <div
                        className="incidents-polling-indicator"
                        title="Refreshing every 20 seconds"
                    >
                        <span
                            className="incidents-polling-dot"
                            aria-hidden="true"
                        />
                        <span>Live updates</span>
                    </div>
                )}
            </header>

            <section className="monitors-card">
                {/* ── Filters Bar ─────────────────────────────────────────── */}
                <div className="incidents-filter-bar">
                    <div className="incidents-filter-group">
                        <label
                            htmlFor="status-filter"
                            className="incidents-filter-label"
                        >
                            Status:
                        </label>
                        <select
                            id="status-filter"
                            aria-label="Filter by status"
                            className="incidents-select"
                            value={statusFilter}
                            onChange={(e) =>
                                handleStatusChange(
                                    e.target.value as IncidentFilterStatus,
                                )
                            }
                        >
                            <option value="all">All statuses</option>
                            <option value="open">Open</option>
                            <option value="resolved">Resolved</option>
                        </select>
                    </div>

                    <div className="incidents-filter-group">
                        <label
                            htmlFor="monitor-filter"
                            className="incidents-filter-label"
                        >
                            Monitor:
                        </label>
                        <select
                            id="monitor-filter"
                            aria-label="Filter by monitor"
                            className="incidents-select"
                            value={monitorIdFilter}
                            onChange={(e) =>
                                handleMonitorChange(e.target.value)
                            }
                        >
                            <option value="">All monitors</option>
                            {monitors.map((m) => (
                                <option key={m.id} value={m.id}>
                                    {m.name}
                                </option>
                            ))}
                        </select>
                    </div>
                </div>

                {/* ── Loading State ───────────────────────────────────────── */}
                {isLoading && (
                    <div
                        role="status"
                        className="monitors-state-box"
                        aria-live="polite"
                    >
                        <span className="spinner" aria-hidden="true" />
                        <p>Loading incidents...</p>
                    </div>
                )}

                {/* ── Error State ─────────────────────────────────────────── */}
                {isError && (
                    <div role="alert" className="monitors-state-box">
                        <h2>Could not load incidents</h2>
                        <p>
                            {error instanceof Error
                                ? error.message
                                : "Something went wrong."}
                        </p>
                        <button
                            type="button"
                            className="monitors-button monitors-button--secondary"
                            onClick={() => void refetch()}
                        >
                            Try again
                        </button>
                    </div>
                )}

                {/* ── Empty State ─────────────────────────────────────────── */}
                {isEmpty && (
                    <div className="monitors-state-box">
                        <h2>No incidents found</h2>
                        <p>
                            {statusFilter === "open"
                                ? "Great news! There are currently no open incidents."
                                : "No incidents match your selected filters."}
                        </p>
                        {(statusFilter !== "all" || monitorIdFilter !== "") && (
                            <button
                                type="button"
                                className="monitors-button monitors-button--secondary"
                                onClick={() => {
                                    handleStatusChange("all");
                                    handleMonitorChange("");
                                }}
                            >
                                Clear filters
                            </button>
                        )}
                    </div>
                )}

                {/* ── Incidents Table ─────────────────────────────────────── */}
                {!isLoading && !isError && !isEmpty && (
                    <>
                        <div className="monitors-table-container">
                            <table className="monitors-table">
                                <caption className="monitors-sr-only">
                                    Incidents list
                                </caption>
                                <thead>
                                    <tr>
                                        <th scope="col">Monitor</th>
                                        <th scope="col">Status</th>
                                        <th scope="col">Opened</th>
                                        <th scope="col">Duration</th>
                                        <th scope="col">Failures</th>
                                        <th scope="col">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {items.map((incident) => {
                                        const isOpen =
                                            incident.status === "open";
                                        return (
                                            <tr
                                                key={incident.id}
                                                data-testid={`incident-row-${incident.id}`}
                                            >
                                                <td>
                                                    <div className="monitors-cell-name">
                                                        <Link
                                                            to={`/incidents/${incident.id}`}
                                                            data-testid={`incident-link-${incident.id}`}
                                                        >
                                                            {
                                                                incident.monitor_name
                                                            }
                                                        </Link>
                                                    </div>
                                                </td>
                                                <td>
                                                    <span
                                                        className={`monitors-chip ${
                                                            isOpen
                                                                ? "monitors-chip--error"
                                                                : "monitors-chip--ok"
                                                        }`}
                                                    >
                                                        {isOpen
                                                            ? "Open"
                                                            : "Resolved"}
                                                    </span>
                                                </td>
                                                <td>
                                                    {formatDateTime(
                                                        incident.opened_at,
                                                    )}
                                                </td>
                                                <td>
                                                    <span
                                                        className={
                                                            isOpen
                                                                ? "incidents-duration-open"
                                                                : "incidents-duration-resolved"
                                                        }
                                                    >
                                                        {formatIncidentDuration(
                                                            incident,
                                                        )}
                                                    </span>
                                                </td>
                                                <td>
                                                    <span className="incidents-failures-badge">
                                                        {incident.failure_count}
                                                    </span>
                                                </td>
                                                <td>
                                                    <div className="monitors-actions-cell">
                                                        <Link
                                                            to={`/incidents/${incident.id}`}
                                                            className="monitors-edit-link"
                                                        >
                                                            View
                                                        </Link>
                                                    </div>
                                                </td>
                                            </tr>
                                        );
                                    })}
                                </tbody>
                            </table>
                        </div>

                        {/* ── Pagination ──────────────────────────────────── */}
                        {totalPages > 1 && (
                            <nav
                                className="monitors-pagination"
                                aria-label="Incidents pagination"
                            >
                                <span className="monitors-pagination-info">
                                    Page {page} of {totalPages} ({total}{" "}
                                    incidents)
                                </span>
                                <div className="monitors-pagination-actions">
                                    <button
                                        type="button"
                                        className="monitors-button monitors-button--secondary"
                                        disabled={page <= 1}
                                        onClick={() =>
                                            handlePageChange(page - 1)
                                        }
                                        aria-label="Previous page"
                                    >
                                        Previous
                                    </button>
                                    <button
                                        type="button"
                                        className="monitors-button monitors-button--secondary"
                                        disabled={page >= totalPages}
                                        onClick={() =>
                                            handlePageChange(page + 1)
                                        }
                                        aria-label="Next page"
                                    >
                                        Next
                                    </button>
                                </div>
                            </nav>
                        )}
                    </>
                )}
            </section>
        </main>
    );
}
