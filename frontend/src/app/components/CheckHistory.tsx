import { useState } from "react";
import { useQuery } from "@tanstack/react-query";

import { getMonitorResults, ApiError } from "../../lib/monitorsApi";
import type {
    CheckResult,
    CheckResultStatus,
    TimeRange,
} from "../../lib/monitors";
import { MAX_CUSTOM_RANGE_DAYS } from "../../lib/monitors";

/* ── Helpers ─────────────────────────────────────────────────────────────── */

/** Formats an ISO timestamp in the user's local timezone. */
function formatLocalTime(iso: string): string {
    try {
        return new Intl.DateTimeFormat(undefined, {
            dateStyle: "medium",
            timeStyle: "medium",
        }).format(new Date(iso));
    } catch {
        return iso;
    }
}

/** Formats an ISO timestamp as UTC for the tooltip. */
function formatUtcTime(iso: string): string {
    try {
        return new Intl.DateTimeFormat("en-GB", {
            dateStyle: "medium",
            timeStyle: "long",
            timeZone: "UTC",
        }).format(new Date(iso));
    } catch {
        return iso;
    }
}

/** Returns `{from, to}` ISO strings for the selected preset range. */
function rangeToFromTo(range: TimeRange): { from: string; to: string } | null {
    if (range === "custom") return null;
    const now = new Date();
    const to = now.toISOString();
    const from = new Date(now);
    if (range === "1h") from.setHours(now.getHours() - 1);
    else if (range === "24h") from.setDate(now.getDate() - 1);
    else if (range === "7d") from.setDate(now.getDate() - 7);
    return { from: from.toISOString(), to };
}

/** Returns true if the span between two date strings exceeds MAX_CUSTOM_RANGE_DAYS. */
function customRangeExceedsLimit(from: string, to: string): boolean {
    try {
        const diffMs = new Date(to).getTime() - new Date(from).getTime();
        const diffDays = diffMs / (1000 * 60 * 60 * 24);
        return diffDays > MAX_CUSTOM_RANGE_DAYS;
    } catch {
        return false;
    }
}

/** Formats a local date-time string to an ISO 8601 string with UTC timezone for API. */
function toIsoWithTimezone(val: string): string | undefined {
    if (!val) return undefined;
    try {
        const d = new Date(val);
        if (isNaN(d.getTime())) return val;
        return d.toISOString();
    } catch {
        return val;
    }
}

/* ── Sub-components ──────────────────────────────────────────────────────── */

function StatusBadge({ status }: { status: CheckResultStatus }) {
    const cls =
        status === "healthy"
            ? "ch-badge ch-badge--ok"
            : "ch-badge ch-badge--fail";
    return <span className={cls}>{status}</span>;
}

/** A single expandable row for the response_body_excerpt. */
function ExcerptRow({
    excerpt,
    open,
    onToggle,
}: {
    excerpt: string;
    open: boolean;
    onToggle: () => void;
}) {
    return (
        <tr className="ch-excerpt-row">
            <td colSpan={5} className="ch-excerpt-cell">
                <button
                    type="button"
                    className="ch-excerpt-toggle"
                    onClick={onToggle}
                    aria-expanded={open}
                >
                    {open
                        ? "▲ Hide response excerpt"
                        : "▼ Show response excerpt"}
                </button>
                {open && <pre className="ch-excerpt-body">{excerpt}</pre>}
            </td>
        </tr>
    );
}

/** One data row in the results table (plus optional excerpt expansion). */
function ResultRow({ result }: { result: CheckResult }) {
    const [excerptOpen, setExcerptOpen] = useState(false);
    const hasExcerpt =
        result.status === "failing" &&
        result.response_body_excerpt != null &&
        result.response_body_excerpt.trim() !== "";

    return (
        <>
            <tr className="ch-row">
                {/* Timestamp */}
                <td className="ch-cell ch-cell--time">
                    <span
                        title={formatUtcTime(result.checked_at)}
                        className="ch-time"
                    >
                        {formatLocalTime(result.checked_at)}
                    </span>
                </td>

                {/* Status badge */}
                <td className="ch-cell">
                    <StatusBadge status={result.status} />
                </td>

                {/* HTTP status code */}
                <td className="ch-cell ch-cell--mono">
                    {result.http_status_code ?? "—"}
                </td>

                {/* Response time */}
                <td className="ch-cell ch-cell--mono">
                    {result.response_time_ms != null
                        ? `${result.response_time_ms} ms`
                        : "—"}
                </td>

                {/* Error message / expand toggle */}
                <td className="ch-cell ch-cell--error">
                    {hasExcerpt ? (
                        <button
                            type="button"
                            className="ch-expand-btn"
                            onClick={() => setExcerptOpen((o) => !o)}
                            aria-expanded={excerptOpen}
                            title="Toggle response excerpt"
                        >
                            {result.error_message ?? "—"}
                            <span className="ch-expand-icon" aria-hidden>
                                {excerptOpen ? " ▲" : " ▼"}
                            </span>
                        </button>
                    ) : (
                        <span className="ch-error-text">
                            {result.error_message ?? "—"}
                        </span>
                    )}
                </td>
            </tr>

            {/* Excerpt row (only rendered when there is an excerpt) */}
            {hasExcerpt && (
                <ExcerptRow
                    excerpt={result.response_body_excerpt!}
                    open={excerptOpen}
                    onToggle={() => setExcerptOpen((o) => !o)}
                />
            )}
        </>
    );
}

/* ── Main Component ──────────────────────────────────────────────────────── */

export function CheckHistory({ monitorId }: { monitorId: string }) {
    /* ── Filter state ── */
    const [timeRange, setTimeRange] = useState<TimeRange>("24h");
    const [customFrom, setCustomFrom] = useState("");
    const [customTo, setCustomTo] = useState("");
    const [statusFilter, setStatusFilter] = useState<CheckResultStatus | "">(
        "",
    );
    const [page, setPage] = useState(1);

    /* ── Derived range params ── */
    const isCustom = timeRange === "custom";
    const customRangeError =
        isCustom && customFrom && customTo
            ? customRangeExceedsLimit(customFrom, customTo)
                ? `Custom range cannot exceed ${MAX_CUSTOM_RANGE_DAYS} days.`
                : null
            : null;

    const presetFromTo = isCustom ? null : rangeToFromTo(timeRange);

    const fromParam = isCustom
        ? toIsoWithTimezone(customFrom)
        : presetFromTo?.from;
    const toParam = isCustom ? toIsoWithTimezone(customTo) : presetFromTo?.to;

    /* Block the query when a custom range error exists or range is incomplete */
    const queryEnabled =
        !customRangeError && !(isCustom && (!customFrom || !customTo));

    /* ── Query ── */
    const { data, isLoading, isError, error, refetch } = useQuery({
        queryKey: [
            "monitor-results",
            monitorId,
            timeRange,
            customFrom,
            customTo,
            statusFilter,
            page,
        ],
        queryFn: () =>
            getMonitorResults(monitorId, {
                page,
                page_size: 20,
                from: fromParam,
                to: toParam,
                status: statusFilter || undefined,
            }),
        enabled: Boolean(monitorId) && queryEnabled,
    });

    /* ── Filter change helpers (reset pagination to page 1) ── */
    function handleTimeRangeChange(value: TimeRange) {
        setTimeRange(value);
        setPage(1);
    }

    function handleStatusChange(value: CheckResultStatus | "") {
        setStatusFilter(value);
        setPage(1);
    }

    function handleCustomFromChange(value: string) {
        setCustomFrom(value);
        setPage(1);
    }

    function handleCustomToChange(value: string) {
        setCustomTo(value);
        setPage(1);
    }

    /* ── Pagination ── */
    const totalPages = data
        ? Math.max(1, Math.ceil(data.total / (data.page_size || 20)))
        : 1;

    /* ── Render ── */
    return (
        <section
            className="ch-section monitors-card"
            aria-labelledby="check-history-heading"
        >
            {/* ── Section header ── */}
            <div className="ch-header">
                <h2 id="check-history-heading" className="detail-card-title">
                    Check history
                </h2>

                {/* ── Controls row ── */}
                <div className="ch-controls">
                    {/* Time-range selector */}
                    <div
                        className="ch-control-group"
                        role="group"
                        aria-label="Time range"
                    >
                        {(
                            [
                                { value: "1h", label: "Last hour" },
                                { value: "24h", label: "24 hours" },
                                { value: "7d", label: "7 days" },
                                { value: "custom", label: "Custom" },
                            ] as { value: TimeRange; label: string }[]
                        ).map(({ value, label }) => (
                            <button
                                key={value}
                                type="button"
                                className={`ch-range-btn${timeRange === value ? " ch-range-btn--active" : ""}`}
                                onClick={() => handleTimeRangeChange(value)}
                                aria-pressed={timeRange === value}
                            >
                                {label}
                            </button>
                        ))}
                    </div>

                    {/* Status filter */}
                    <label className="ch-select-label">
                        <span className="ch-select-text">Status</span>
                        <select
                            className="ch-select"
                            value={statusFilter}
                            onChange={(e) =>
                                handleStatusChange(
                                    e.target.value as CheckResultStatus | "",
                                )
                            }
                        >
                            <option value="">All</option>
                            <option value="healthy">Healthy</option>
                            <option value="failing">Failing</option>
                        </select>
                    </label>
                </div>

                {/* Custom date pickers (only shown when timeRange === "custom") */}
                {isCustom && (
                    <div
                        className="ch-custom-range"
                        role="group"
                        aria-label="Custom date range"
                    >
                        <label className="ch-date-label">
                            <span className="ch-select-text">From</span>
                            <input
                                type="datetime-local"
                                className="ch-date-input"
                                value={customFrom}
                                onChange={(e) =>
                                    handleCustomFromChange(e.target.value)
                                }
                            />
                        </label>
                        <label className="ch-date-label">
                            <span className="ch-select-text">To</span>
                            <input
                                type="datetime-local"
                                className="ch-date-input"
                                value={customTo}
                                onChange={(e) =>
                                    handleCustomToChange(e.target.value)
                                }
                            />
                        </label>
                    </div>
                )}

                {/* Custom range error message */}
                {customRangeError && (
                    <p role="alert" className="ch-range-error">
                        {customRangeError}
                    </p>
                )}
            </div>

            {/* ── Table body states ── */}

            {/* Loading */}
            {isLoading && (
                <div
                    role="status"
                    className="monitors-state-box"
                    aria-live="polite"
                >
                    <span className="spinner" aria-hidden="true" />
                    <p>Loading check history…</p>
                </div>
            )}

            {/* API error (includes 422 for out-of-range) */}
            {isError && !isLoading && (
                <div role="alert" className="monitors-state-box ch-error-state">
                    <p className="ch-state-msg">
                        {error instanceof ApiError
                            ? error.message
                            : "Could not load check history."}
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

            {/* Custom range — waiting for user input */}
            {!isLoading &&
                !isError &&
                isCustom &&
                (!customFrom || !customTo) && (
                    <div className="monitors-state-box ch-empty-state">
                        <p className="ch-state-msg">
                            Select a From and To date above to load results.
                        </p>
                    </div>
                )}

            {/* Results table */}
            {!isLoading && !isError && data && (
                <>
                    {data.items.length === 0 ? (
                        /* Empty state */
                        <div
                            className="monitors-state-box ch-empty-state"
                            data-testid="ch-empty"
                        >
                            <p className="ch-state-msg">
                                No checks found for this time range and filter.
                            </p>
                        </div>
                    ) : (
                        <div className="ch-table-wrapper">
                            <table className="ch-table" data-testid="ch-table">
                                <thead>
                                    <tr className="ch-head-row">
                                        <th className="ch-th" scope="col">
                                            Time
                                        </th>
                                        <th className="ch-th" scope="col">
                                            Status
                                        </th>
                                        <th className="ch-th" scope="col">
                                            HTTP code
                                        </th>
                                        <th className="ch-th" scope="col">
                                            Response time
                                        </th>
                                        <th className="ch-th" scope="col">
                                            Error
                                        </th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.items.map((result) => (
                                        <ResultRow
                                            key={result.id}
                                            result={result}
                                        />
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}

                    {/* Pagination */}
                    {data.total > 0 && (
                        <div
                            className="ch-pagination"
                            role="navigation"
                            aria-label="Check history pagination"
                        >
                            <button
                                type="button"
                                className="monitors-button monitors-button--secondary ch-page-btn"
                                disabled={page <= 1}
                                onClick={() => setPage((p) => p - 1)}
                                aria-label="Previous page"
                            >
                                ← Prev
                            </button>
                            <span className="ch-page-info">
                                Page {page} of {totalPages}
                                <span className="ch-page-total">
                                    {" "}
                                    ({data.total} total)
                                </span>
                            </span>
                            <button
                                type="button"
                                className="monitors-button monitors-button--secondary ch-page-btn"
                                disabled={page >= totalPages}
                                onClick={() => setPage((p) => p + 1)}
                                aria-label="Next page"
                            >
                                Next →
                            </button>
                        </div>
                    )}
                </>
            )}
        </section>
    );
}
