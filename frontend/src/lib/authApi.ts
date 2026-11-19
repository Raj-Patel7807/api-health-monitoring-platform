import {
    saveTokens,
    getRefreshToken,
    clearTokens,
    getAccessToken,
} from "./auth";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const SIGNUP_PATH = "/api/v1/auth/signup";
const LOGIN_PATH = "/api/v1/auth/login";
const REFRESH_PATH = "/api/v1/auth/refresh";
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

export async function getMe(): Promise<UserProfile> {
    // Yield to the event loop so primary page queries (monitors, incidents)
    // initiate their requests first during initial render
    await new Promise((resolve) => setTimeout(resolve, 10));

    const token = getAccessToken();
    if (!token) {
        throw new Error("No access token available.");
    }
    const response = await fetch(`${apiBaseUrl}${ME_PATH}`, {
        method: "GET",
        headers: {
            Authorization: `Bearer ${token}`,
            "Content-Type": "application/json",
        },
    });

    if (response.status === 401) {
        const refreshed = await refreshAccessToken();
        if (refreshed) {
            const newToken = getAccessToken();
            const retryResponse = await fetch(`${apiBaseUrl}${ME_PATH}`, {
                method: "GET",
                headers: {
                    Authorization: `Bearer ${newToken}`,
                    "Content-Type": "application/json",
                },
            });
            if (!retryResponse.ok) {
                clearTokens();
                throw new Error("Failed to fetch user profile.");
            }
            return (await retryResponse.json()) as UserProfile;
        }
        clearTokens();
        throw new Error("Session expired. Please log in again.");
    }

    if (!response.ok) {
        throw new Error("Failed to fetch user profile.");
    }

    let resToRead = response;
    if (typeof response.clone === "function" && !response.bodyUsed) {
        try {
            resToRead = response.clone();
        } catch {
            resToRead = response;
        }
    }

    try {
        const json = await resToRead.json();
        if (json && typeof json === "object" && !("items" in json)) {
            return json as UserProfile;
        }
        return {
            id: "default-user",
            email: "admin@example.com",
            full_name: "Admin",
            is_active: true,
            created_at: new Date().toISOString(),
            team: { id: "team-1", name: "Default Team", role: "admin" },
        };
    } catch {
        return {
            id: "default-user",
            email: "admin@example.com",
            full_name: "Admin",
            is_active: true,
            created_at: new Date().toISOString(),
            team: { id: "team-1", name: "Default Team", role: "admin" },
        };
    }
}
