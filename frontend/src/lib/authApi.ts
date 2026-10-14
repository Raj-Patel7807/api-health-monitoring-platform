import { saveTokens, getRefreshToken, clearTokens } from "./auth";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const SIGNUP_PATH = "/api/v1/auth/signup";
const LOGIN_PATH = "/api/v1/auth/login";
const REFRESH_PATH = "/api/v1/auth/refresh";

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
    teamName: string = "My Team",
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
            saveTokens(data.access_token, data.refresh_token ?? null);
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
    saveTokens(data.access_token, data.refresh_token ?? null);
}

export async function refreshAccessToken(): Promise<boolean> {
    const refreshToken = getRefreshToken();
    if (!refreshToken) {
        return false;
    }
    const response = await postJson(REFRESH_PATH, {
        refresh_token: refreshToken,
    });
    if (!response.ok) {
        clearTokens();
        return false;
    }
    const data = (await response.json()) as TokenResponse;
    saveTokens(data.access_token, data.refresh_token ?? refreshToken);
    return true;
}
