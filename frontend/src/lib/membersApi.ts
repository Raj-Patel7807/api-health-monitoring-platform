/**
 * API functions for Team Members & RBAC (US-19 / Task F2).
 *
 * Implements:
 * - GET /api/v1/team/members: list members of the current team
 * - POST /api/v1/team/members: add an existing user to the team with a role
 * - PATCH /api/v1/team/members/{user_id}: update a member's role
 */

import { clearTokens, getAccessToken } from "./auth";
import { refreshAccessToken } from "./authApi";
import type {
    AddMemberPayload,
    MembersListResponse,
    Role,
    TeamMember,
} from "./members";

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

        if (record.error && typeof record.error === "object") {
            const errObj = record.error as Record<string, unknown>;
            if (typeof errObj.code === "string") code = errObj.code;
            if (typeof errObj.message === "string") message = cleanMsg(errObj.message);
        } else if (record.detail !== undefined) {
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
        if (status === 403) {
            message = "You don't have permission to perform this action.";
        } else if (status === 404) {
            message = "User not found.";
        } else if (status === 409) {
            message = "Cannot complete action due to a conflict.";
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
            null,
            {},
        );
    }

    if (response.status === 401) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
            const newToken = getAccessToken();
            try {
                response = await sendRequest(url, init, newToken);
            } catch {
                throw new ApiError(
                    "Could not reach the server after refreshing token.",
                    0,
                    null,
                    {},
                );
            }
            if (response.status === 401) {
                clearTokens();
                throw new ApiError(
                    "Session expired. Please log in again.",
                    401,
                    null,
                    {},
                );
            }
        } else {
            clearTokens();
            throw new ApiError(
                "Session expired. Please log in again.",
                401,
                null,
                {},
            );
        }
    }

    if (!response.ok) {
        throw await buildApiError(response);
    }

    return response.json() as Promise<T>;
}

export async function listMembers(): Promise<MembersListResponse> {
    return request<MembersListResponse>("/team/members");
}

export async function addMember(
    payload: AddMemberPayload,
): Promise<TeamMember> {
    return request<TeamMember>("/team/members", {
        method: "POST",
        body: JSON.stringify(payload),
    });
}

export async function changeMemberRole(
    userId: string,
    role: Role,
): Promise<TeamMember> {
    return request<TeamMember>(`/team/members/${encodeURIComponent(userId)}`, {
        method: "PATCH",
        body: JSON.stringify({ role }),
    });
}
