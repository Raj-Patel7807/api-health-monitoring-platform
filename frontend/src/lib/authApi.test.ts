import { afterEach, describe, expect, it, vi } from "vitest";

import { login, signup } from "./authApi";

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
    });
});
