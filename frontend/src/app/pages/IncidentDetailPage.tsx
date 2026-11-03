import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";

import {
    CHANNEL_TYPE_ICONS,
    CHANNEL_TYPE_LABELS,
    formatDateTime,
    formatDuration,
    formatIncidentDuration,
    type AlertDelivery,
    type AlertDeliveryListResponse,
    type IncidentDetail,
} from "../../lib/incidents";
import {
    getIncident,
    getIncidentDeliveries,
    ApiError,
} from "../../lib/incidentsApi";
import "./monitors.css";
import "./MonitorDetailPage.css";
import "./incidents.css";

export function IncidentDetailPage() {
    const { incidentId } = useParams<{ incidentId: string }>();
    const navigate = useNavigate();

    // Query incident details
    const {
        data: incident,
        isLoading: incidentLoading,
        isError: isIncidentError,
        error: incidentError,
        refetch: refetchIncident,
    } = useQuery({
        queryKey: ["incident", incidentId],
        queryFn: () => getIncident(incidentId!),
        enabled: Boolean(incidentId),
        refetchInterval: (query) => {
            const data = query.state.data as IncidentDetail | undefined;
            // Incident will also check pending deliveries via shouldPoll below
            return data?.status === "open" ? 20_000 : false;
        },
    });

    // Determine if incident is open or if any delivery is pending
    const isIncidentOpen = incident?.status === "open";

    // Query incident alert deliveries
    const {
        data: deliveriesData,
        isLoading: deliveriesLoading,
        isError: isDeliveriesError,
        error: deliveriesError,
        refetch: refetchDeliveries,
    } = useQuery({
        queryKey: ["incident-deliveries", incidentId],
        queryFn: () => getIncidentDeliveries(incidentId!),
        enabled: Boolean(incidentId),
        // Poll deliveries every 20 seconds while incident is open OR any delivery is pending
        refetchInterval: (query) => {
            const delivData = query.state.data as
                AlertDeliveryListResponse | undefined;
            const deliveries = delivData?.items ?? [];
            const hasPending = deliveries.some((d) => d.status === "pending");
            return isIncidentOpen || hasPending ? 20_000 : false;
        },
    });

    const deliveries: AlertDelivery[] = deliveriesData?.items ?? [];
    const hasPendingDelivery = deliveries.some((d) => d.status === "pending");
    const isActivelyPolling = isIncidentOpen || hasPendingDelivery;

    // Handle 401 unauthenticated
    useEffect(() => {
        if (incidentError instanceof ApiError && incidentError.status === 401) {
            navigate("/login", { replace: true });
        }
    }, [incidentError, navigate]);

    // Handle 404 Not Found (or incident from another team)
    const isNotFound =
        incidentError instanceof ApiError && incidentError.status === 404;

    if (isNotFound) {
        return (
            <main className="monitors-page">
                <Link to="/incidents" className="monitors-back-link">
                    ← Back to incidents
                </Link>
                <div className="monitors-card">
                    <div className="monitors-state-box" role="alert">
                        <h2>Incident not found</h2>
                        <p>
                            The requested incident does not exist or belongs to
                            another team.
                        </p>
                        <Link
                            to="/incidents"
                            className="monitors-button monitors-button--secondary"
                        >
                            Return to incidents list
                        </Link>
                    </div>
                </div>
            </main>
        );
    }

    if (incidentLoading) {
        return (
            <main className="monitors-page">
                <Link to="/incidents" className="monitors-back-link">
                    ← Back to incidents
                </Link>
                <div className="monitors-card">
                    <div
                        role="status"
                        className="monitors-state-box"
                        aria-live="polite"
                    >
                        <span className="spinner" aria-hidden="true" />
                        <p>Loading incident details...</p>
                    </div>
                </div>
            </main>
        );
    }

    if (isIncidentError || !incident) {
        return (
            <main className="monitors-page">
                <Link to="/incidents" className="monitors-back-link">
                    ← Back to incidents
                </Link>
                <div className="monitors-card">
                    <div role="alert" className="monitors-state-box">
                        <h2>Could not load incident</h2>
                        <p>
                            {incidentError instanceof Error
                                ? incidentError.message
                                : "Something went wrong."}
                        </p>
                        <button
                            type="button"
                            className="monitors-button monitors-button--secondary"
                            onClick={() => void refetchIncident()}
                        >
                            Try again
                        </button>
                    </div>
                </div>
            </main>
        );
    }

    const isOpen = incident.status === "open";

    return (
        <main className="monitors-page">
            <Link to="/incidents" className="monitors-back-link">
                ← Back to incidents
            </Link>

            <header className="monitors-header">
                <div className="monitors-header-text">
                    <h1>Incident for {incident.monitor_name}</h1>
                    <p className="monitors-subtitle">
                        Incident ID:{" "}
                        <code className="detail-value--mono">
                            {incident.id}
                        </code>
                    </p>
                </div>
                <div className="delivery-card-badges">
                    <span
                        className={`monitors-chip ${
                            isOpen
                                ? "monitors-chip--error"
                                : "monitors-chip--ok"
                        }`}
                        data-testid="incident-status-badge"
                    >
                        {isOpen ? "Open" : "Resolved"}
                    </span>
                    {isActivelyPolling && (
                        <div
                            className="incidents-polling-indicator"
                            title="Refreshing every 20 seconds while incident is open or delivery is pending"
                        >
                            <span
                                className="incidents-polling-dot"
                                aria-hidden="true"
                            />
                            <span>Live</span>
                        </div>
                    )}
                </div>
            </header>

            <div className="monitors-card">
                {/* ── Key Facts Grid ──────────────────────────────────────── */}
                <dl className="detail-grid">
                    <div className="detail-row">
                        <dt className="detail-label">Monitor Name</dt>
                        <dd className="detail-value">
                            <Link
                                to={`/monitors/${incident.monitor_id}`}
                                className="monitors-edit-link"
                            >
                                {incident.monitor_name}
                            </Link>
                        </dd>
                    </div>

                    <div className="detail-row">
                        <dt className="detail-label">Endpoint URL</dt>
                        <dd className="detail-value detail-value--mono">
                            {incident.monitor_url}
                        </dd>
                    </div>

                    <div className="detail-row">
                        <dt className="detail-label">Opened At</dt>
                        <dd className="detail-value">
                            {formatDateTime(incident.opened_at)}
                        </dd>
                    </div>

                    <div className="detail-row">
                        <dt className="detail-label">
                            {isOpen ? "Time Open" : "Resolved At / Duration"}
                        </dt>
                        <dd className="detail-value">
                            {isOpen ? (
                                <span className="incidents-duration-open">
                                    {formatIncidentDuration(incident)}
                                </span>
                            ) : (
                                <span>
                                    {formatDateTime(incident.resolved_at)}{" "}
                                    (duration:{" "}
                                    {formatDuration(
                                        incident.opened_at,
                                        incident.resolved_at,
                                    )}
                                    )
                                </span>
                            )}
                        </dd>
                    </div>

                    <div className="detail-row">
                        <dt className="detail-label">Failure Count</dt>
                        <dd className="detail-value">
                            <span className="incidents-failures-badge">
                                {incident.failure_count}
                            </span>
                        </dd>
                    </div>

                    <div className="detail-row">
                        <dt className="detail-label">Recovery Count</dt>
                        <dd className="detail-value">
                            <span className="incidents-recoveries-badge">
                                {incident.recovery_count}
                            </span>
                        </dd>
                    </div>
                </dl>

                {/* ── Alert Deliveries Panel ──────────────────────────────── */}
                <section
                    className="deliveries-section"
                    aria-labelledby="deliveries-heading"
                >
                    <div className="deliveries-section-header">
                        <h2
                            id="deliveries-heading"
                            className="deliveries-section-title"
                        >
                            Alert Deliveries
                        </h2>
                    </div>

                    {deliveriesLoading && (
                        <div
                            role="status"
                            className="monitors-state-box"
                            aria-live="polite"
                        >
                            <span className="spinner" aria-hidden="true" />
                            <p>Loading alert deliveries...</p>
                        </div>
                    )}

                    {isDeliveriesError && (
                        <div role="alert" className="monitors-state-box">
                            <p>
                                {deliveriesError instanceof Error
                                    ? deliveriesError.message
                                    : "Could not load alert deliveries."}
                            </p>
                            <button
                                type="button"
                                className="monitors-button monitors-button--secondary"
                                onClick={() => void refetchDeliveries()}
                            >
                                Retry
                            </button>
                        </div>
                    )}

                    {!deliveriesLoading &&
                        !isDeliveriesError &&
                        deliveries.length === 0 && (
                            <div className="monitors-state-box">
                                <p>
                                    No alert deliveries recorded for this
                                    incident.
                                </p>
                            </div>
                        )}

                    {!deliveriesLoading &&
                        !isDeliveriesError &&
                        deliveries.length > 0 && (
                            <div
                                className="deliveries-list"
                                data-testid="deliveries-list"
                            >
                                {deliveries.map((delivery) => {
                                    const typeIcon =
                                        CHANNEL_TYPE_ICONS[
                                            delivery.channel_type
                                        ] ?? "📣";
                                    const typeLabel =
                                        CHANNEL_TYPE_LABELS[
                                            delivery.channel_type
                                        ] ?? delivery.channel_type;

                                    return (
                                        <article
                                            key={delivery.id}
                                            className="delivery-card"
                                            data-testid={`delivery-card-${delivery.id}`}
                                        >
                                            <div className="delivery-card-top">
                                                <div className="delivery-card-channel">
                                                    <span aria-hidden="true">
                                                        {typeIcon}
                                                    </span>
                                                    <span>
                                                        {delivery.channel_name}
                                                    </span>
                                                    <span className="monitors-chip monitors-chip--method">
                                                        {typeLabel}
                                                    </span>
                                                </div>

                                                <div className="delivery-card-badges">
                                                    <span className="monitors-chip monitors-chip--method">
                                                        Event:{" "}
                                                        {delivery.event_type}
                                                    </span>
                                                    <span
                                                        className={`delivery-badge delivery-badge--${delivery.status}`}
                                                        data-testid={`delivery-status-${delivery.status}`}
                                                    >
                                                        {delivery.status}
                                                    </span>
                                                </div>
                                            </div>

                                            <div className="delivery-card-meta">
                                                <div className="delivery-card-meta-item">
                                                    <span>Attempts:</span>
                                                    <strong>
                                                        {delivery.attempt_count}
                                                    </strong>
                                                </div>
                                                <div className="delivery-card-meta-item">
                                                    <span>Sent At:</span>
                                                    <strong>
                                                        {delivery.sent_at
                                                            ? formatDateTime(
                                                                  delivery.sent_at,
                                                              )
                                                            : "—"}
                                                    </strong>
                                                </div>
                                            </div>

                                            {/* Error message for failed delivery */}
                                            {delivery.status === "failed" &&
                                                delivery.error_message && (
                                                    <div
                                                        className="delivery-error-box"
                                                        role="alert"
                                                        data-testid="delivery-error-box"
                                                    >
                                                        <span className="delivery-error-label">
                                                            Delivery Error
                                                        </span>
                                                        <span className="delivery-error-text">
                                                            {
                                                                delivery.error_message
                                                            }
                                                        </span>
                                                    </div>
                                                )}
                                        </article>
                                    );
                                })}
                            </div>
                        )}
                </section>
            </div>
        </main>
    );
}
