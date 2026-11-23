import { afterEach, describe, expect, it, vi } from "vitest";

import {
    clearTokens,
    getAccessToken,
    getRefreshToken,
    saveTokens,
    startSession,
} from "./auth";
import { getMe, login, signup } from "./authApi";

describe("authApi", () => {
    afterEach(() => {
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    it("posts signup to the versioned API and saves the returned tokens", async () => {
        const mockFetch = vi.fn().mockResolvedValue(
            new Response(
                JSON.stringify({
                    access_token: "access-token",
                    refresh_token: "refresh-token",
                }),
                {
                    status: 201,
                    headers: { "Content-Type": "application/json" },
                },
            ),
        );
        vi.stubGlobal("fetch", mockFetch);

        await signup(
            "Test User",
            "test@example.com",
            "password123",
            "Test Team",
        );

        expect(mockFetch).toHaveBeenCalledWith(
            "http://localhost:8000/api/v1/auth/signup",
            expect.objectContaining({ method: "POST" }),
        );
        expect(localStorage.getItem("access_token")).toBe("access-token");
        expect(localStorage.getItem("refresh_token")).toBe("refresh-token");
    });

    it("posts login to the versioned API", async () => {
        saveTokens("previous-access", "previous-refresh");
        const mockFetch = vi.fn().mockResolvedValue(
            new Response(JSON.stringify({ access_token: "access-token" }), {
                status: 200,
                headers: { "Content-Type": "application/json" },
            }),
        );
        vi.stubGlobal("fetch", mockFetch);

        await login("test@example.com", "password123");

        expect(mockFetch).toHaveBeenCalledWith(
            "http://localhost:8000/api/v1/auth/login",
            expect.objectContaining({ method: "POST" }),
        );
        expect(getRefreshToken()).toBeNull();
    });

    it.each(["offline", "503"])(
        "keeps the saved session when refresh fails with %s",
        async (reason) => {
            saveTokens("expired", "refresh");
            const fetchMock = vi
                .fn()
                .mockResolvedValueOnce(new Response(null, { status: 401 }));
            if (reason === "offline")
                fetchMock.mockRejectedValueOnce(new TypeError("offline"));
            else
                fetchMock.mockResolvedValueOnce(
                    new Response(null, { status: 503 }),
                );
            vi.stubGlobal("fetch", fetchMock);

            await expect(getMe()).rejects.toThrow();
            expect(getRefreshToken()).toBe("refresh");
            expect(getAccessToken()).toBe("expired");
        },
    );

    it("restores a refresh-only session once for simultaneous profile requests", async () => {
        localStorage.setItem("refresh_token", "refresh");
        const mockFetch = vi.fn(async (url: string, init: RequestInit) => {
            if (url.endsWith("/refresh"))
                return Response.json({
                    access_token: "renewed",
                    refresh_token: "next",
                });
            expect(new Headers(init.headers).get("Authorization")).toBe(
                "Bearer renewed",
            );
            return Response.json({ id: "user" });
        });
        vi.stubGlobal("fetch", mockFetch);
        await expect(Promise.all([getMe(), getMe()])).resolves.toEqual([
            { id: "user" },
            { id: "user" },
        ]);
        expect(
            mockFetch.mock.calls.filter(([url]) => url.endsWith("/refresh")),
        ).toHaveLength(1);
        expect(getRefreshToken()).toBe("next");
    });

    it.each(["logout", "switch"])(
        "ignores a late refresh after %s",
        async (action) => {
            localStorage.setItem("refresh_token", "old-refresh");
            let finish!: (response: Response) => void;
            const pendingResponse = new Promise<Response>((resolve) => {
                finish = resolve;
            });
            vi.stubGlobal("fetch", vi.fn().mockReturnValue(pendingResponse));
            const profile = getMe();
            clearTokens();
            if (action === "switch")
                startSession("other-access", "other-refresh");
            finish(
                Response.json({
                    access_token: "stale-access",
                    refresh_token: "stale-refresh",
                }),
            );
            await expect(profile).rejects.toThrow();
            expect(getAccessToken()).toBe(
                action === "switch" ? "other-access" : null,
            );
            expect(getRefreshToken()).toBe(
                action === "switch" ? "other-refresh" : null,
            );
        },
    );
});
