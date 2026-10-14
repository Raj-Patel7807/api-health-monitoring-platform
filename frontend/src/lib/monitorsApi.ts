import { clearTokens, getAccessToken } from "./auth";
import { refreshAccessToken } from "./authApi";
import type {
    Monitor,
    MonitorField,
    MonitorListResponse,
    MonitorPayload,
} from "./monitors";

export class ApiError extends Error {
    readonly status: number;
    readonly code: string | null;
    readonly fieldErrors: Partial<Record<MonitorField, string>>;

    constructor(
        message: string,
        status: number,
        code: string | null = null,
        fieldErrors: Partial<Record<MonitorField, string>> = {},
    ) {
        super(message);
        this.name = "ApiError";
        this.status = status;
        this.code = code;
        this.fieldErrors = fieldErrors;
    }
}

function cleanMsg(raw: unknown): string {
    if (typeof raw !== "string") {
        return "";
    }
    return raw.replace(/^Value error,\s*/, "");
}

function parseErrorResponse(status: number, data: unknown): ApiError {
    let message = "";
    let code: string | null = null;
    const fieldErrors: Partial<Record<MonitorField, string>> = {};

    if (data && typeof data === "object") {
        const record = data as Record<string, unknown>;

        // Shape 1 & 2: { error: { code, message, details } }
        if (record.error && typeof record.error === "object") {
            const errObj = record.error as Record<string, unknown>;
            if (typeof errObj.code === "string") {
                code = errObj.code;
            }
            if (typeof errObj.message === "string") {
                message = cleanMsg(errObj.message);
            }

            if (Array.isArray(errObj.details)) {
                for (const item of errObj.details) {
                    if (item && typeof item === "object") {
                        const loc = (item as { loc?: unknown[] }).loc;
                        const msg = cleanMsg((item as { msg?: unknown }).msg);
                        if (Array.isArray(loc) && loc.length > 0) {
                            const field = String(loc[loc.length - 1]);
                            if (field && !fieldErrors[field as MonitorField]) {
                                fieldErrors[field as MonitorField] = msg;
                            }
                        }
                    }
                }
            } else if (errObj.details && typeof errObj.details === "object") {
                for (const [k, v] of Object.entries(
                    errObj.details as Record<string, unknown>,
                )) {
                    const msg = cleanMsg(v);
                    if (msg && !fieldErrors[k as MonitorField]) {
                        fieldErrors[k as MonitorField] = msg;
                    }
                }
            }
        }
        // Shape 3: FastAPI default { detail: "text" | [ { loc, msg } ] }
        else if (record.detail !== undefined) {
            if (typeof record.detail === "string") {
                message = cleanMsg(record.detail);
            } else if (Array.isArray(record.detail)) {
                for (const item of record.detail) {
                    if (item && typeof item === "object") {
                        const loc = (item as { loc?: unknown[] }).loc;
                        const msg = cleanMsg((item as { msg?: unknown }).msg);
                        if (Array.isArray(loc) && loc.length > 0) {
                            const field = String(loc[loc.length - 1]);
                            if (field && !fieldErrors[field as MonitorField]) {
                                fieldErrors[field as MonitorField] = msg;
                            }
                        }
                    }
                }
                if (!message) {
                    message = "Request data is invalid.";
                }
            }
        }
    }

    if (!message) {
        if (status === 403) {
            message = "You don't have permission to do that.";
        } else if (status === 404) {
            message = "Monitor not found.";
        } else if (status >= 500 && status < 600) {
            message = "Something went wrong on our side. Please try again.";
        } else {
            message = "Request failed.";
        }
    }

    return new ApiError(message, status, code, fieldErrors);
}

async function buildApiError(response: Response): Promise<ApiError> {
    let data: unknown = null;
    try {
        const text = await response.text();
        if (text) {
            data = JSON.parse(text);
        }
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
    if (token) {
        headers.set("Authorization", `Bearer ${token}`);
    }
    if (init?.body && !headers.has("Content-Type")) {
        headers.set("Content-Type", "application/json");
    }

    return fetch(url, {
        ...init,
        headers,
    });
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
            null,
            {},
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
                    null,
                    {},
                );
            }
        } else {
            clearTokens();
            throw await buildApiError(response);
        }
    }

    if (!response.ok) {
        throw await buildApiError(response);
    }

    if (response.status === 204) {
        return undefined as T;
    }

    const text = await response.text();
    if (!text) {
        return undefined as T;
    }

    return JSON.parse(text) as T;
}

export async function listMonitors(
    page: number = 1,
    pageSize: number = 20,
): Promise<MonitorListResponse> {
    return request<MonitorListResponse>(
        `/monitors?page=${page}&page_size=${pageSize}`,
        { method: "GET" },
    );
}

export async function getMonitor(id: string): Promise<Monitor> {
    return request<Monitor>(`/monitors/${encodeURIComponent(id)}`, {
        method: "GET",
    });
}

export async function createMonitor(payload: MonitorPayload): Promise<Monitor> {
    return request<Monitor>("/monitors", {
        method: "POST",
        body: JSON.stringify(payload),
    });
}

export async function updateMonitor(
    id: string,
    partialPayload: Partial<MonitorPayload>,
): Promise<Monitor> {
    return request<Monitor>(`/monitors/${encodeURIComponent(id)}`, {
        method: "PATCH",
        body: JSON.stringify(partialPayload),
    });
}

/**
 * Soft-deletes a monitor (sets deleted_at on the backend).
 * Returns void because the API responds with 204 No Content.
 * Role required: admin.
 */
export async function deleteMonitor(id: string): Promise<void> {
    return request<void>(`/monitors/${encodeURIComponent(id)}`, {
        method: "DELETE",
    });
}
