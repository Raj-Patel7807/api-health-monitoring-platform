import { useState, useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getMonitor, deleteMonitor, ApiError } from "../../lib/monitorsApi";
import type { Monitor } from "../../lib/monitors";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { ToastContainer } from "../components/Toast";
import { useToast } from "../components/useToast";
import "./monitors.css";
import "./MonitorDetailPage.css";

/* ── Helpers ──────────────────────────────────────────────────────────────── */

function formatDateTime(iso: string | null | undefined): string {
    if (!iso) return "—";
    try {
        return new Intl.DateTimeFormat(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
        }).format(new Date(iso));
    } catch {
        return iso;
    }
}

function formatRelative(iso: string | null | undefined): string {
    if (!iso) return "";
    try {
        const diff = new Date(iso).getTime() - Date.now();
        const abs = Math.abs(diff);
        const secs = Math.round(abs / 1000);
        if (secs < 60) return `${secs}s`;
        const mins = Math.round(secs / 60);
        if (mins < 60) return `${mins}m`;
        const hrs = Math.round(mins / 60);
        return `${hrs}h`;
    } catch {
        return "";
    }
}

function statusClass(monitor: Monitor): string {
    if (!monitor.enabled) return "monitors-chip--warning";
    if (monitor.backoff_until && new Date(monitor.backoff_until) > new Date()) {
        return "monitors-chip--error";
    }
    if ((monitor.consecutive_failures ?? 0) > 0) return "monitors-chip--error";
    return "monitors-chip--ok";
}

function statusLabel(monitor: Monitor): string {
    if (!monitor.enabled) return "Paused";
    if (monitor.backoff_until && new Date(monitor.backoff_until) > new Date()) {
        return "Backing off";
    }
    if ((monitor.consecutive_failures ?? 0) > 0) return "Failing";
    return "Healthy";
}

/* ── Detail row helper ───────────────────────────────────────────────────── */
function DetailRow({
    label,
    value,
    mono = false,
}: {
    label: string;
    value: React.ReactNode;
    mono?: boolean;
}) {
    return (
        <div className="detail-row">
            <dt className="detail-label">{label}</dt>
            <dd className={`detail-value${mono ? " detail-value--mono" : ""}`}>
                {value}
            </dd>
        </div>
    );
}

/* ── Page ────────────────────────────────────────────────────────────────── */
export function MonitorDetailPage() {
    const { monitorId } = useParams<{ monitorId: string }>();
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { toasts, addToast, dismissToast } = useToast();

    const [deleteOpen, setDeleteOpen] = useState(false);

    const { data: monitor, isLoading, isError, error, refetch } = useQuery({
        queryKey: ["monitor", monitorId],
        queryFn: () => getMonitor(monitorId!),
        enabled: Boolean(monitorId),
        refetchInterval: 30_000, // poll every 30 s to keep status fresh
    });

    // Redirect to login on 401
    useEffect(() => {
        if (error instanceof ApiError && error.status === 401) {
            navigate("/login", { replace: true });
        }
    }, [error, navigate]);

    const deleteMutation = useMutation({
        mutationFn: () => deleteMonitor(monitorId!),
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ["monitors"] });
            queryClient.removeQueries({ queryKey: ["monitor", monitorId] });
            navigate("/monitors", { replace: true });
        },
        onError: (err) => {
            setDeleteOpen(false);
            addToast(
                err instanceof ApiError
                    ? err.message
                    : "Could not delete monitor. Please try again.",
                "error",
            );
        },
    });

    /* ── Loading state ── */
    if (isLoading) {
        return (
            <main className="monitors-page monitors-page--detail">
                <Link to="/monitors" className="monitors-back-link">
                    ← Back to monitors
                </Link>
                <div className="monitors-card detail-card">
                    <div
                        role="status"
                        className="monitors-state-box"
                        aria-live="polite"
                    >
                        <span className="spinner" aria-hidden="true" />
                        <p>Loading monitor…</p>
                    </div>
                </div>
            </main>
        );
    }

    /* ── Error state ── */
    if (isError) {
        const is404 = error instanceof ApiError && error.status === 404;
        return (
            <main className="monitors-page monitors-page--detail">
                <Link to="/monitors" className="monitors-back-link">
                    ← Back to monitors
                </Link>
                <div className="monitors-card detail-card">
                    <div
                        role="alert"
                        className="monitors-state-box"
                    >
                        <h2>
                            {is404
                                ? "Monitor not found"
                                : "Could not load monitor"}
                        </h2>
                        <p>
                            {is404
                                ? "This monitor may have been deleted."
                                : (error instanceof Error
                                      ? error.message
                                      : "Something went wrong.")}
                        </p>
                        {is404 ? (
                            <Link
                                to="/monitors"
                                className="monitors-button monitors-button--secondary"
                            >
                                Back to monitors
                            </Link>
                        ) : (
                            <button
                                type="button"
                                className="monitors-button monitors-button--secondary"
                                onClick={() => void refetch()}
                            >
                                Try again
                            </button>
                        )}
                    </div>
                </div>
            </main>
        );
    }

    if (!monitor) return null;

    const nextCheckAt = monitor.next_check_at;
    const backoffUntil = monitor.backoff_until;
    const isInBackoff =
        Boolean(backoffUntil) && new Date(backoffUntil!) > new Date();

    const nextCheckRelative = nextCheckAt ? formatRelative(nextCheckAt) : null;
    const backoffRelative = isInBackoff ? formatRelative(backoffUntil) : null;

    return (
        <>
            <main className="monitors-page monitors-page--detail">
                {/* ── Header ── */}
                <div className="detail-page-header">
                    <Link to="/monitors" className="monitors-back-link">
                        ← Back to monitors
                    </Link>
                    <div className="detail-header-row">
                        <div>
                            <h1 className="detail-title">{monitor.name}</h1>
                            <p className="detail-url monitors-url">
                                {monitor.url}
                            </p>
                        </div>
                        <div className="detail-header-actions">
                            <Link
                                to={`/monitors/${monitor.id}/edit`}
                                className="monitors-button monitors-button--secondary"
                                aria-label={`Edit ${monitor.name}`}
                            >
                                Edit
                            </Link>
                            <button
                                type="button"
                                className="monitors-button monitors-button--danger"
                                aria-label={`Delete ${monitor.name}`}
                                onClick={() => setDeleteOpen(true)}
                                data-testid="delete-monitor-btn"
                            >
                                Delete
                            </button>
                        </div>
                    </div>
                </div>

                {/* ── Status banner ── */}
                <div className="detail-status-banner">
                    <span
                        className={`monitors-chip ${statusClass(monitor)} detail-status-chip`}
                    >
                        {statusLabel(monitor)}
                    </span>
                    <span className="monitors-chip monitors-chip--method">
                        {monitor.method}
                    </span>
                    <span className="detail-status-text">
                        Expected {monitor.expected_status_code}
                    </span>
                    <span className="detail-status-text">
                        Every {monitor.check_interval_seconds}s
                    </span>
                </div>

                {/* ── Detail cards grid ── */}
                <div className="detail-grid">
                    {/* Runtime card */}
                    <section
                        className="monitors-card detail-card"
                        aria-labelledby="runtime-heading"
                    >
                        <h2 id="runtime-heading" className="detail-card-title">
                            Runtime status
                        </h2>
                        <dl className="detail-list">
                            <DetailRow
                                label="Next check"
                                value={
                                    nextCheckAt ? (
                                        <span>
                                            {formatDateTime(nextCheckAt)}
                                            {nextCheckRelative && (
                                                <span className="detail-relative">
                                                    {" "}
                                                    (in {nextCheckRelative})
                                                </span>
                                            )}
                                        </span>
                                    ) : (
                                        <span className="detail-muted">
                                            Not scheduled
                                        </span>
                                    )
                                }
                            />
                            <DetailRow
                                label="Backoff until"
                                value={
                                    isInBackoff && backoffUntil ? (
                                        <span className="detail-value--alert">
                                            {formatDateTime(backoffUntil)}
                                            {backoffRelative && (
                                                <span className="detail-relative">
                                                    {" "}
                                                    (~{backoffRelative} left)
                                                </span>
                                            )}
                                        </span>
                                    ) : (
                                        <span className="detail-muted">—</span>
                                    )
                                }
                            />
                        </dl>
                    </section>

                    {/* Failure / recovery counters */}
                    <section
                        className="monitors-card detail-card"
                        aria-labelledby="counters-heading"
                    >
                        <h2
                            id="counters-heading"
                            className="detail-card-title"
                        >
                            Failure &amp; recovery
                        </h2>
                        <div className="detail-counters">
                            <div
                                className={`detail-counter ${
                                    (monitor.consecutive_failures ?? 0) > 0
                                        ? "detail-counter--fail"
                                        : ""
                                }`}
                                aria-label="Consecutive failures"
                            >
                                <span
                                    className="detail-counter-value"
                                    data-testid="consecutive-failures"
                                >
                                    {monitor.consecutive_failures ?? 0}
                                </span>
                                <span className="detail-counter-label">
                                    Consecutive failures
                                </span>
                                <span className="detail-counter-sub">
                                    threshold: {monitor.failure_threshold ?? 3}
                                </span>
                            </div>
                            <div
                                className={`detail-counter ${
                                    (monitor.consecutive_successes ?? 0) > 0
                                        ? "detail-counter--ok"
                                        : ""
                                }`}
                                aria-label="Consecutive successes"
                            >
                                <span
                                    className="detail-counter-value"
                                    data-testid="consecutive-successes"
                                >
                                    {monitor.consecutive_successes ?? 0}
                                </span>
                                <span className="detail-counter-label">
                                    Consecutive successes
                                </span>
                                <span className="detail-counter-sub">
                                    threshold:{" "}
                                    {monitor.recovery_threshold ?? 2}
                                </span>
                            </div>
                        </div>
                    </section>

                    {/* Configuration card */}
                    <section
                        className="monitors-card detail-card"
                        aria-labelledby="config-heading"
                    >
                        <h2 id="config-heading" className="detail-card-title">
                            Configuration
                        </h2>
                        <dl className="detail-list">
                            <DetailRow
                                label="Timeout"
                                value={`${monitor.timeout_seconds ?? 10}s`}
                                mono
                            />
                            <DetailRow
                                label="Check interval"
                                value={`${monitor.check_interval_seconds}s`}
                                mono
                            />
                            <DetailRow
                                label="Expected status"
                                value={String(monitor.expected_status_code)}
                                mono
                            />
                            <DetailRow
                                label="Failure threshold"
                                value={String(monitor.failure_threshold ?? 3)}
                                mono
                            />
                            <DetailRow
                                label="Recovery threshold"
                                value={String(monitor.recovery_threshold ?? 2)}
                                mono
                            />
                            <DetailRow
                                label="Created"
                                value={formatDateTime(monitor.created_at)}
                            />
                        </dl>
                    </section>
                </div>
            </main>

            {/* ── Delete confirmation ── */}
            <ConfirmDialog
                open={deleteOpen}
                title="Delete monitor?"
                description={`"${monitor.name}" and all its history will be permanently removed. This cannot be undone.`}
                confirmLabel="Delete monitor"
                confirmingLabel="Deleting…"
                isConfirming={deleteMutation.isPending}
                onConfirm={() => void deleteMutation.mutateAsync()}
                onCancel={() => setDeleteOpen(false)}
            />

            {/* ── Toast notifications ── */}
            <ToastContainer toasts={toasts} onDismiss={dismissToast} />
        </>
    );
}
