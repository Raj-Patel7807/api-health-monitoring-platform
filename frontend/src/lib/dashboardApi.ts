/**
 * API functions for the Dashboard page (US-13 / S4-F1).
 *
 * The dashboard does not have a dedicated backend endpoint yet; it is composed
 * client-side from two existing endpoints:
 *   - GET /monitors          → all monitors (up to 500 for realistic teams)
 *   - GET /incidents?status=open → open incident per monitor
 *
 * Both responses are already typed and tested in monitorsApi / incidentsApi.
 */

import { clearTokens, getAccessToken } from "./auth";
import { refreshAccessToken } from "./authApi";
import type { DashboardMonitorRow, DashboardSummary } from "./dashboard";
import type { MonitorListResponse } from "./monitors";
import type { IncidentListResponse } from "./incidents";

export { type DashboardMonitorRow, type DashboardSummary };

export class ApiError extends Error {
    readonly status: number;
    readonly code: string | null;

    constructor(message: string, status: number, code: string | null = null) {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.code = code;
    }
}

function parseErrorMessage(status: number, data: unknown): string {
    if (data && typeof data === "object") {
        const rec = data as Record<string, unknown>;
        if (rec.error && typeof rec.error === "object") {
            const e = rec.error as Record<string, unknown>;
            if (typeof e.message === "string") return e.message;
        }
        if (typeof rec.detail === "string") return rec.detail;
    }
    if (status >= 500) return "Something went wrong on our side. Please try again.";
    if (status === 401) return "Session expired. Please log in again.";
    if (status === 403) return "You don't have permission to view this.";
    return "Request failed.";
}

async function buildApiError(response: Response): Promise<ApiError> {
    let data: unknown = null;
    try {
        const text = await response.text();
        if (text) data = JSON.parse(text);
    } catch {
        data = null;
    }
    return new ApiError(
        parseErrorMessage(response.status, data),
        response.status,
    );
}

async function sendRequest(
    url: string,
    init?: RequestInit,
    token?: string | null,
): Promise<Response> {
    const headers = new Headers(init?.headers);
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return fetch(url, { ...init, headers });
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
    const apiBase =
        (import.meta.env.VITE_API_BASE_URL as string | undefined) ??
        "http://localhost:8000";
    const url = `${apiBase}/api/v1${path}`;
    const token = getAccessToken();

    let response: Response;
    try {
        response = await sendRequest(url, init, token);
    } catch {
        throw new ApiError(
            "Could not reach the server. Check your connection and try again.",
            0,
        );
    }

    if (response.status === 401) {
        let refreshed = false;
        try {
            refreshed = await refreshAccessToken();
        } catch {
            refreshed = false;
        }
        if (refreshed) {
            const newToken = getAccessToken();
            try {
                response = await sendRequest(url, init, newToken);
            } catch {
                throw new ApiError(
                    "Could not reach the server. Check your connection and try again.",
                    0,
                );
            }
        } else {
            clearTokens();
            throw await buildApiError(response);
        }
    }

    if (!response.ok) throw await buildApiError(response);
    if (response.status === 204) return undefined as T;

    const text = await response.text();
    if (!text) return undefined as T;
    return JSON.parse(text) as T;
}

/** Classify a monitor's health based on consecutive_failures field. */
function classifyHealth(monitor: {
    enabled: boolean;
    consecutive_failures?: number;
}): "healthy" | "failing" | "unknown" {
    if (!monitor.enabled) return "unknown";
    if ((monitor.consecutive_failures ?? 0) > 0) return "failing";
    return "healthy";
}

export type DashboardData = {
    summary: DashboardSummary;
    rows: DashboardMonitorRow[];
};

/**
 * Fetch dashboard data by composing two API calls in parallel:
 * - GET /monitors (page_size=500 to get all monitors)
 * - GET /incidents?status=open (page_size=500 to find open incidents per monitor)
 */
export async function getDashboardData(): Promise<DashboardData> {
    const [monitorsRes, incidentsRes] = await Promise.all([
        request<MonitorListResponse>("/monitors?page=1&page_size=500", {
            method: "GET",
        }),
        request<IncidentListResponse>("/incidents?status=open&page=1&page_size=500", {
            method: "GET",
        }),
    ]);

    const monitors = monitorsRes.items ?? [];
    const openIncidents = incidentsRes.items ?? [];

    // Build a map: monitorId → incidentId for open incidents
    const openIncidentByMonitor = new Map<string, string>();
    for (const incident of openIncidents) {
        if (!openIncidentByMonitor.has(incident.monitor_id)) {
            openIncidentByMonitor.set(incident.monitor_id, incident.id);
        }
    }

    // Build dashboard rows
    const rows: DashboardMonitorRow[] = monitors.map((m) => ({
        id: m.id,
        name: m.name,
        url: m.url,
        health: classifyHealth(m),
        lastCheckedAt: m.next_check_at ?? null,
        lastResponseTimeMs: null, // Not in monitor response — would require /results
        openIncidentId: openIncidentByMonitor.get(m.id) ?? null,
    }));

    // Sort: failing first, then unknown, then healthy
    rows.sort((a, b) => {
        const rank = { failing: 0, unknown: 1, healthy: 2 };
        return rank[a.health] - rank[b.health];
    });

    // Summary counts
    const summary: DashboardSummary = {
        total: monitors.length,
        healthy: rows.filter((r) => r.health === "healthy").length,
        failing: rows.filter((r) => r.health === "failing").length,
        unknown: rows.filter((r) => r.health === "unknown").length,
        openIncidents: openIncidents.length,
    };

    return { summary, rows };
}
