import { afterEach, describe, expect, it, vi } from "vitest";

import {
    clearTokens,
    getAccessToken,
    getRefreshToken,
    saveTokens,
    startSession,
} from "./auth";
import { getMe, login, signup, updateMe } from "./authApi";

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

    it("surfaces API error detail on signup failure with string detail", async () => {
        const mockFetch = vi.fn().mockResolvedValue(
            new Response(
                JSON.stringify({
                    detail: "An account with this email address already exists.",
                }),
                {
                    status: 409,
                    headers: { "Content-Type": "application/json" },
                },
            ),
        );
        vi.stubGlobal("fetch", mockFetch);

        await expect(
            signup("Test User", "dup@example.com", "password123"),
        ).rejects.toThrow("An account with this email address already exists.");
    });

    it("surfaces validation error msgs on signup failure with array detail", async () => {
        const mockFetch = vi.fn().mockResolvedValue(
            new Response(
                JSON.stringify({
                    detail: [
                        { msg: "String should have at least 8 characters" },
                    ],
                }),
                {
                    status: 422,
                    headers: { "Content-Type": "application/json" },
                },
            ),
        );
        vi.stubGlobal("fetch", mockFetch);

        await expect(
            signup("Test User", "test@example.com", "short"),
        ).rejects.toThrow("String should have at least 8 characters");
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

    it("sends PATCH to /api/v1/auth/me and returns updated profile", async () => {
        saveTokens("my-token", "my-refresh");
        const mockFetch = vi.fn().mockResolvedValue(
            new Response(
                JSON.stringify({
                    id: "user-123",
                    email: "updated@example.com",
                    full_name: "Updated Name",
                    is_active: true,
                    created_at: "2026-01-01T00:00:00Z",
                    team: { id: "team-1", name: "Alpha", role: "admin" },
                }),
                {
                    status: 200,
                    headers: { "Content-Type": "application/json" },
                },
            ),
        );
        vi.stubGlobal("fetch", mockFetch);

        const result = await updateMe({
            full_name: "Updated Name",
            email: "updated@example.com",
        });

        expect(result.full_name).toBe("Updated Name");
        expect(result.email).toBe("updated@example.com");
        expect(mockFetch).toHaveBeenCalledWith(
            "http://localhost:8000/api/v1/auth/me",
            expect.objectContaining({
                method: "PATCH",
                body: JSON.stringify({
                    full_name: "Updated Name",
                    email: "updated@example.com",
                }),
            }),
        );
    });

    it("surfaces error detail on updateMe failure", async () => {
        saveTokens("my-token", "my-refresh");
        const mockFetch = vi.fn().mockResolvedValue(
            new Response(
                JSON.stringify({
                    detail: "Incorrect current password.",
                }),
                {
                    status: 400,
                    headers: { "Content-Type": "application/json" },
                },
            ),
        );
        vi.stubGlobal("fetch", mockFetch);

        await expect(
            updateMe({
                current_password: "wrong",
                new_password: "newsecret456",
            }),
        ).rejects.toThrow("Incorrect current password.");
    });
});
