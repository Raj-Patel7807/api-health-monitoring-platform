import { useQuery } from "@tanstack/react-query";
import { getHealth } from "../../lib/api";

/** Polls /health every 30 s and displays a live backend status indicator. */
export function HealthStatus() {
    const apiBase =
        (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
        "http://localhost:8000";

    const { data, isLoading, isError } = useQuery({
        queryKey: ["health"],
        queryFn: getHealth,
        // Retry twice with a 3-second gap before showing an error state.
        retry: 2,
        retryDelay: 3_000,
        // Re-fetch silently in the background every 30 seconds.
        refetchInterval: 30_000,
        refetchIntervalInBackground: false,
    });

    const statusClass = isLoading
        ? "status--loading"
        : isError
          ? "status--error"
          : "status--ok";

    const statusText = isLoading ? "checking…" : isError ? "unavailable" : data?.status ?? "ok";

    return (
        <div className="status-banner">
            <div className={`status-card ${statusClass}`} role="status" aria-live="polite">
                <div className="status-indicator">
                    {isLoading ? (
                        <span className="spinner" aria-hidden="true" />
                    ) : (
                        <span className="status-dot" aria-hidden="true" />
                    )}
                    <span className="status-label">Backend API</span>
                    <span className="status-value">{statusText}</span>
                </div>
                <div className="status-divider" aria-hidden="true" />
                <span className="status-endpoint" aria-label={`Endpoint: ${apiBase}/health`}>
                    {apiBase}/health
                </span>
            </div>
        </div>
    );
}
