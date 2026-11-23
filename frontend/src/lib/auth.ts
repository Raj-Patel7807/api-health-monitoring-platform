const ACCESS_KEY = "access_token";
const REFRESH_KEY = "refresh_token";
const SESSION_KEY = "login_session";
const SESSION_EVENT = "auth-session-changed";

export function getAccessToken(): string | null {
    return localStorage.getItem(ACCESS_KEY);
}

export function getRefreshToken(): string | null {
    return localStorage.getItem(REFRESH_KEY);
}

export function saveTokens(accessToken: string, refreshToken: string | null) {
    localStorage.setItem(ACCESS_KEY, accessToken);
    if (refreshToken) {
        localStorage.setItem(REFRESH_KEY, refreshToken);
    } else {
        localStorage.removeItem(REFRESH_KEY);
    }
}

export function startSession(accessToken: string, refreshToken: string | null) {
    saveTokens(accessToken, refreshToken);
    localStorage.setItem(SESSION_KEY, crypto.randomUUID());
    window.dispatchEvent(new Event(SESSION_EVENT));
}

export function clearTokens() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
    localStorage.removeItem(SESSION_KEY);
    window.dispatchEvent(new Event(SESSION_EVENT));
}

export function getSessionId(): string | null {
    if (!getAccessToken() && !getRefreshToken()) return null;
    // Existing logins predate the identifier. They can still renew normally.
    return localStorage.getItem(SESSION_KEY) ?? "legacy";
}

export function subscribeSession(listener: () => void) {
    const onStorage = (event: StorageEvent) => {
        if (event.storageArea === localStorage) listener();
    };
    window.addEventListener("storage", onStorage);
    window.addEventListener(SESSION_EVENT, listener);
    return () => {
        window.removeEventListener("storage", onStorage);
        window.removeEventListener(SESSION_EVENT, listener);
    };
}
