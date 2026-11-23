import { startSession } from "./auth";
import { authenticatedFetch } from "./authenticatedFetch";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const SIGNUP_PATH = "/api/v1/auth/signup";
const LOGIN_PATH = "/api/v1/auth/login";
const ME_PATH = "/api/v1/auth/me";

export type Role = "admin" | "operator" | "read_only";

export type UserTeam = {
    id: string;
    name: string;
    role: Role;
};

export type UserProfile = {
    id: string;
    email: string;
    full_name: string;
    is_active: boolean;
    created_at: string;
    team?: UserTeam | null;
};

type TokenResponse = {
    access_token: string;
    refresh_token?: string;
};

async function postJson(path: string, body: unknown): Promise<Response> {
    return fetch(`${apiBaseUrl}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
    });
}

export async function signup(
    fullName: string,
    email: string,
    password: string,
    teamName?: string,
): Promise<void> {
    const response = await postJson(SIGNUP_PATH, {
        full_name: fullName,
        email,
        password,
        team_name: teamName,
    });
    if (!response.ok) {
        throw new Error("Signup failed. Please check your details.");
    }
    // API.md: 201 returns { user, team, access_token, refresh_token }
    try {
        const data = (await response.json()) as TokenResponse & {
            user?: unknown;
            team?: unknown;
        };
        if (data.access_token) {
            startSession(data.access_token, data.refresh_token ?? null);
        }
    } catch {
        // If the body isn't JSON (e.g. mock server), silently continue
    }
}

export async function login(email: string, password: string): Promise<void> {
    const response = await postJson(LOGIN_PATH, { email, password });
    if (!response.ok) {
        throw new Error("Invalid email or password.");
    }
    const data = (await response.json()) as TokenResponse;
    startSession(data.access_token, data.refresh_token ?? null);
}

export async function getMe(): Promise<UserProfile> {
    const response = await authenticatedFetch(`${apiBaseUrl}${ME_PATH}`, {
        method: "GET",
    });
    if (!response.ok) {
        throw new Error(
            response.status === 401
                ? "Session expired. Please log in again."
                : "Failed to fetch user profile.",
        );
    }
    return (await response.json()) as UserProfile;
}
