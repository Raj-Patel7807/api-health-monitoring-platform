import { useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { keepPreviousData, useQuery } from "@tanstack/react-query";

import { listMonitors, ApiError } from "../../lib/monitorsApi";
import type { Monitor } from "../../lib/monitors";
import "./monitors.css";

function formatDateTime(isoString: string): string {
    try {
        return new Intl.DateTimeFormat(undefined, {
            dateStyle: "short",
            timeStyle: "short",
        }).format(new Date(isoString));
    } catch {
        return isoString;
    }
}

export function MonitorsPage() {
    const navigate = useNavigate();
    const [searchParams, setSearchParams] = useSearchParams();

    const rawPage = parseInt(searchParams.get("page") ?? "1", 10);
    const page = Number.isInteger(rawPage) && rawPage >= 1 ? rawPage : 1;

    const { data, isLoading, isError, error, refetch } = useQuery({
        queryKey: ["monitors", { page }],
        queryFn: () => listMonitors(page, 20),
        placeholderData: keepPreviousData,
    });

    useEffect(() => {
        if (error instanceof ApiError && error.status === 401) {
            navigate("/login", { replace: true });
        }
    }, [error, navigate]);

    const total = data?.total ?? 0;
    const pageSize = data?.page_size ?? 20;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    const items: Monitor[] = data?.items ?? [];
    const isEmpty = !isLoading && !isError && page === 1 && items.length === 0;

    return (
        <main className="monitors-page">
            <header className="monitors-header">
                <div className="monitors-header-text">
                    <h1>Monitors</h1>
                    <p className="monitors-subtitle">
                        The endpoints your team keeps an eye on.
                    </p>
                </div>
                <Link
                    to="/monitors/new"
                    className="monitors-button monitors-button--primary"
                >
                    Add monitor
                </Link>
            </header>

            <section className="monitors-card">
                {isLoading && (
                    <div
                        role="status"
                        className="monitors-state-box"
                        aria-live="polite"
                    >
                        <span className="spinner" aria-hidden="true" />
                        <p>Loading monitors...</p>
                    </div>
                )}

                {isError && (
                    <div role="alert" className="monitors-state-box">
                        <h2>Could not load monitors</h2>
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

                {isEmpty && (
                    <div className="monitors-state-box">
                        <h2>No monitors yet</h2>
                        <p>
                            Start tracking your endpoints to detect downtime and
                            incidents early.
                        </p>
                        <Link
                            to="/monitors/new"
                            className="monitors-button monitors-button--primary"
                        >
                            Add your first monitor
                        </Link>
                    </div>
                )}

                {!isLoading && !isError && !isEmpty && (
                    <>
                        <div className="monitors-table-container">
                            <table className="monitors-table">
                                <caption className="monitors-sr-only">
                                    Monitors
                                </caption>
                                <thead>
                                    <tr>
                                        <th scope="col">Name</th>
                                        <th scope="col">Method</th>
                                        <th scope="col">Status</th>
                                        <th scope="col">Interval</th>
                                        <th scope="col">Expected</th>
                                        <th scope="col">Created</th>
                                        <th scope="col">Actions</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {items.map((monitor) => (
                                        <tr key={monitor.id}>
                                            <td>
                                                <div className="monitors-cell-name">
                                                    <Link
                                                        to={`/monitors/${monitor.id}`}
                                                    >
                                                        {monitor.name}
                                                    </Link>
                                                    <span className="monitors-url">
                                                        {monitor.url}
                                                    </span>
                                                </div>
                                            </td>
                                            <td>
                                                <span className="monitors-chip monitors-chip--method">
                                                    {monitor.method}
                                                </span>
                                            </td>
                                            <td>
                                                <span
                                                    className={`monitors-chip ${
                                                        monitor.enabled
                                                            ? "monitors-chip--ok"
                                                            : "monitors-chip--warning"
                                                    }`}
                                                >
                                                    {monitor.enabled
                                                        ? "Enabled"
                                                        : "Paused"}
                                                </span>
                                            </td>
                                            <td>
                                                Every{" "}
                                                {monitor.check_interval_seconds}
                                                s
                                            </td>
                                            <td>
                                                {monitor.expected_status_code}
                                            </td>
                                            <td>
                                                {formatDateTime(
                                                    monitor.created_at,
                                                )}
                                            </td>
                                            <td>
                                                <Link
                                                    to={`/monitors/${monitor.id}/edit`}
                                                    className="monitors-edit-link"
                                                    aria-label={`Edit ${monitor.name}`}
                                                >
                                                    Edit
                                                </Link>
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>

                        <nav
                            aria-label="Pagination"
                            className="monitors-pagination"
                        >
                            <span className="monitors-pagination-info">
                                Page {page} of {totalPages} · {total} monitors
                            </span>
                            <div className="monitors-pagination-actions">
                                <button
                                    type="button"
                                    className="monitors-button monitors-button--secondary"
                                    disabled={page <= 1}
                                    onClick={() =>
                                        setSearchParams({
                                            page: String(page - 1),
                                        })
                                    }
                                >
                                    Previous
                                </button>
                                <button
                                    type="button"
                                    className="monitors-button monitors-button--secondary"
                                    disabled={page >= totalPages}
                                    onClick={() =>
                                        setSearchParams({
                                            page: String(page + 1),
                                        })
                                    }
                                >
                                    Next
                                </button>
                            </div>
                        </nav>
                    </>
                )}
            </section>
        </main>
    );
}
