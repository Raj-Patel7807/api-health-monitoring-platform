const ACCESS_KEY = "access_token";
const REFRESH_KEY = "refresh_token";

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
    }
}

export function clearTokens() {
    localStorage.removeItem(ACCESS_KEY);
    localStorage.removeItem(REFRESH_KEY);
}

export function isLoggedIn(): boolean {
    return getAccessToken() !== null;
}
