/**
 * API functions and query hooks for Incidents & Alert Deliveries (US-09, US-10, US-11).
 *
 * All text from the API is rendered as plain text in the UI to prevent XSS.
 */

import { clearTokens, getAccessToken } from "./auth";
import { refreshAccessToken } from "./authApi";
import {
    sortIncidentsOpenFirst,
    type AlertDelivery,
    type AlertDeliveryListResponse,
    type Incident,
    type IncidentDetail,
    type IncidentFilterStatus,
    type IncidentListResponse,
} from "./incidents";

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

function cleanMsg(raw: unknown): string {
    if (typeof raw !== "string") return "";
    return raw.replace(/^Value error,\s*/, "");
}

function parseErrorResponse(status: number, data: unknown): ApiError {
    let message = "";
    let code: string | null = null;

    if (data && typeof data === "object") {
        const record = data as Record<string, unknown>;
        if (record.error && typeof record.error === "object") {
            const errObj = record.error as Record<string, unknown>;
            if (typeof errObj.code === "string") code = errObj.code;
            if (typeof errObj.message === "string")
                message = cleanMsg(errObj.message);
        } else if (record.detail !== undefined) {
            if (typeof record.detail === "string") {
                message = cleanMsg(record.detail);
            } else if (Array.isArray(record.detail)) {
                const first = record.detail[0] as { msg?: unknown } | undefined;
                if (first && typeof first.msg === "string") {
                    message = cleanMsg(first.msg);
                }
            }
        }
    }

    if (!message) {
        if (status === 403) message = "You don't have permission to do that.";
        else if (status === 404) message = "Incident not found.";
        else if (status >= 500)
            message = "Something went wrong on our side. Please try again.";
        else message = "Request failed.";
    }

    return new ApiError(message, status, code);
}

async function buildApiError(response: Response): Promise<ApiError> {
    let data: unknown = null;
    try {
        const text = await response.text();
        if (text) data = JSON.parse(text);
    } catch {
        data = null;
    }
    return parseErrorResponse(response.status, data);
}

async function sendRequest(
    url: string,
    init?: RequestInit,
    token?: string | null,
): Promise<Response> {
    const headers = new Headers(init?.headers);
    if (token) headers.set("Authorization", `Bearer ${token}`);
    if (init?.body && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
    }
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

export type ListIncidentsOptions = {
    page?: number;
    pageSize?: number;
    status?: IncidentFilterStatus;
    monitorId?: string;
};

/**
 * Fetch a paginated list of incidents with optional status and monitor filtering.
 * Shows open incidents first by default when unfiltered or filtered to all.
 */
export async function listIncidents(
    options: ListIncidentsOptions = {},
): Promise<IncidentListResponse> {
    const page = options.page ?? 1;
    const pageSize = options.pageSize ?? 20;
    const params = new URLSearchParams();

    params.set("page", String(page));
    params.set("page_size", String(pageSize));

    if (options.status && options.status !== "all") {
        params.set("status", options.status);
    }

    if (options.monitorId) {
        params.set("monitor_id", options.monitorId);
    }

    const res = await request<IncidentListResponse>(
        `/incidents?${params.toString()}`,
        {
            method: "GET",
        },
    );

    // Ensure open incidents are always listed first unless filtered specifically to resolved
    if (!options.status || options.status === "all") {
        return {
            ...res,
            items: sortIncidentsOpenFirst(res.items ?? []),
        };
    }

    return res;
}

/**
 * Fetch a single incident by ID with monitor_url.
 * Returns 404 ApiError if not found or belongs to another team.
 */
export async function getIncident(id: string): Promise<IncidentDetail> {
    return request<IncidentDetail>(`/incidents/${encodeURIComponent(id)}`, {
        method: "GET",
    });
}

/**
 * Fetch alert deliveries for an incident.
 */
export async function getIncidentDeliveries(
    incidentId: string,
): Promise<AlertDeliveryListResponse> {
    return request<AlertDeliveryListResponse>(
        `/incidents/${encodeURIComponent(incidentId)}/alert-deliveries`,
        { method: "GET" },
    );
}

// ---------------------------------------------------------------------------
// MSW handler stubs — used in Vitest tests
// ---------------------------------------------------------------------------

/**
 * Returns MSW request handlers for the incidents API.
 * Matching the pattern of channelHandlers in channelsApi.ts.
 */
export function incidentHandlers(
    incidents: Incident[] = [],
    deliveries: AlertDelivery[] = [],
) {
    return { incidents, deliveries };
}
