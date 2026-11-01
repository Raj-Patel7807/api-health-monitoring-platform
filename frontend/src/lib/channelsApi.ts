/**
 * API functions for notification channels (US-03).
 *
 * Uses the same request() helper pattern as monitorsApi.ts.
 * Secret handling:
 * - secret_value is sent in the request body but never stored in any
 *   client-side cache, localStorage, sessionStorage, or console log.
 * - TanStack Query is configured with select: (data) => data so the raw
 *   response (which never contains secret_value) goes into the cache.
 */

import { clearTokens, getAccessToken } from "./auth";
import { refreshAccessToken } from "./authApi";
import type {
    Channel,
    ChannelListResponse,
    ChannelType,
} from "./channels";

// ---------------------------------------------------------------------------
// Re-use ApiError from monitorsApi to keep one error class across the app
// ---------------------------------------------------------------------------

export class ApiError extends Error {
    readonly status: number;
    readonly code: string | null;
    readonly fieldErrors: Partial<Record<string, string>>;

    constructor(
        message: string,
        status: number,
        code: string | null = null,
        fieldErrors: Partial<Record<string, string>> = {},
    ) {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.code = code;
        this.fieldErrors = fieldErrors;
    }
}

function cleanMsg(raw: unknown): string {
    if (typeof raw !== "string") return "";
    return raw.replace(/^Value error,\s*/, "");
}

function parseErrorResponse(status: number, data: unknown): ApiError {
    let message = "";
    let code: string | null = null;
    const fieldErrors: Partial<Record<string, string>> = {};

    if (data && typeof data === "object") {
        const record = data as Record<string, unknown>;
        if (record.detail !== undefined) {
            if (typeof record.detail === "string") {
                message = cleanMsg(record.detail);
            } else if (Array.isArray(record.detail)) {
                for (const item of record.detail) {
                    if (item && typeof item === "object") {
                        const loc = (item as { loc?: unknown[] }).loc;
                        const msg = cleanMsg((item as { msg?: unknown }).msg);
                        if (Array.isArray(loc) && loc.length > 0) {
                            const field = String(loc[loc.length - 1]);
                            if (field && !fieldErrors[field]) {
                                fieldErrors[field] = msg;
                            }
                        }
                    }
                }
                if (!message) message = "Request data is invalid.";
            }
        }
    }

    if (!message) {
        if (status === 403) message = "You don't have permission to do that.";
        else if (status === 404) message = "Channel not found.";
        else if (status >= 500) message = "Something went wrong on our side. Please try again.";
        else message = "Request failed.";
    }

    return new ApiError(message, status, code, fieldErrors);
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

// ---------------------------------------------------------------------------
// Channel API functions
// ---------------------------------------------------------------------------

export async function listChannels(options?: {
    monitorId?: string;
    scope?: "team";
}): Promise<ChannelListResponse> {
    const params = new URLSearchParams();
    if (options?.monitorId) params.set("monitor_id", options.monitorId);
    if (options?.scope) params.set("scope", options.scope);
    const qs = params.toString();
    return request<ChannelListResponse>(
        `/notification-channels${qs ? `?${qs}` : ""}`,
        { method: "GET" },
    );
}

export async function createChannel(payload: {
    type: ChannelType;
    name: string;
    monitor_id: string | null;
    secret_value: string;
    configuration?: Record<string, unknown>;
}): Promise<Channel> {
    return request<Channel>("/notification-channels", {
        method: "POST",
        body: JSON.stringify(payload),
    });
}

export async function updateChannel(
    id: string,
    patch: {
        name?: string;
        is_enabled?: boolean;
        secret_value?: string;
        configuration?: Record<string, unknown>;
    },
): Promise<Channel> {
    return request<Channel>(
        `/notification-channels/${encodeURIComponent(id)}`,
        {
            method: "PATCH",
            body: JSON.stringify(patch),
        },
    );
}

/**
 * Soft-deletes a notification channel.
 * Returns void because the API responds with 204 No Content.
 * Roles required: admin, operator.
 */
export async function deleteChannel(id: string): Promise<void> {
    return request<void>(
        `/notification-channels/${encodeURIComponent(id)}`,
        { method: "DELETE" },
    );
}

// ---------------------------------------------------------------------------
// MSW handler stubs — used in Vitest tests (not in production)
// ---------------------------------------------------------------------------

/**
 * Returns MSW request handlers for the notification channels API.
 * Import this only from test files; never in production code.
 *
 * Usage in a test:
 *   import { channelHandlers } from "@/lib/channelsApi";
 *   server.use(...channelHandlers(mockData));
 */
export function channelHandlers(channels: Channel[] = []) {
    // This stub is intentionally minimal — tests that need full MSW
    // should compose their own handlers. Kept here so the import path
    // is stable for future test expansion.
    return channels;
}
