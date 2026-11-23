import {
    clearTokens,
    getAccessToken,
    getRefreshToken,
    getSessionId,
    saveTokens,
} from "./auth";

const apiBase = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const pendingRefreshes = new Map<string, Promise<Response | null>>();

async function renewSession(refreshToken: string, sessionId: string) {
    const response = await fetch(`${apiBase}/api/v1/auth/refresh`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ refresh_token: refreshToken }),
    });
    const tokens = response.ok ? await response.json() : null;
    // Logout, another login, or a renewal in another tab can win this race.
    if (getSessionId() !== sessionId || getRefreshToken() !== refreshToken) {
        return null;
    }
    if (!response.ok) {
        if (response.status === 401) clearTokens();
        return response;
    }
    if (typeof tokens?.access_token !== "string" || !tokens.access_token) {
        throw new Error("The server returned an incomplete session.");
    }
    saveTokens(tokens.access_token, tokens.refresh_token ?? refreshToken);
    return null;
}

function refreshOnce(refreshToken: string, sessionId: string) {
    let pending = pendingRefreshes.get(refreshToken);
    if (!pending) {
        pending = renewSession(refreshToken, sessionId).finally(() => {
            pendingRefreshes.delete(refreshToken);
        });
        pendingRefreshes.set(refreshToken, pending);
    }
    return pending;
}

export async function authenticatedFetch(
    url: string,
    init?: RequestInit,
): Promise<Response> {
    const send = (token: string | null) => {
        const headers = new Headers(init?.headers);
        if (token) headers.set("Authorization", `Bearer ${token}`);
        if (init?.body && !headers.has("Content-Type")) {
            headers.set("Content-Type", "application/json");
        }
        return fetch(url, { ...init, headers });
    };

    const sessionId = getSessionId();
    const firstToken = getAccessToken();
    if (firstToken || !sessionId) {
        const response = await send(firstToken);
        if (
            response.status !== 401 ||
            !sessionId ||
            getSessionId() !== sessionId
        )
            return response;
        if (!getRefreshToken()) {
            clearTokens();
            return response;
        }
    }

    const refreshToken = getRefreshToken();
    if (refreshToken && getAccessToken() === firstToken) {
        const failure = await refreshOnce(refreshToken, sessionId);
        if (failure) return failure.clone();
    }
    const token = getAccessToken();
    if (!token || getSessionId() !== sessionId)
        return new Response(null, { status: 401 });

    const response = await send(token);
    if (
        response.status === 401 &&
        getSessionId() === sessionId &&
        getAccessToken() === token
    ) {
        clearTokens();
    }
    return response;
}
