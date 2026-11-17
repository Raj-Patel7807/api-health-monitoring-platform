import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { renderHook, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import React from "react";

import { useCurrentRole } from "./useCurrentRole";

function createWrapper() {
    const queryClient = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return ({ children }: { children: React.ReactNode }) => (
        <QueryClientProvider client={queryClient}>
            {children}
        </QueryClientProvider>
    );
}

describe("useCurrentRole", () => {
    beforeEach(() => {
        localStorage.setItem("access_token", "test-token");
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    it("returns admin role and flags when /auth/me returns admin", async () => {
        const mockProfile = {
            id: "u-1",
            email: "admin@example.com",
            full_name: "Admin User",
            is_active: true,
            created_at: "2026-10-01T10:00:00Z",
            team: {
                id: "t-1",
                name: "Engineering",
                role: "admin",
            },
        };

        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue(
                new Response(JSON.stringify(mockProfile), {
                    status: 200,
                    headers: { "Content-Type": "application/json" },
                }),
            ),
        );

        const { result } = renderHook(() => useCurrentRole(), {
            wrapper: createWrapper(),
        });

        await waitFor(() => expect(result.current.isLoading).toBe(false));

        expect(result.current.role).toBe("admin");
        expect(result.current.isAdmin).toBe(true);
        expect(result.current.isOperator).toBe(false);
        expect(result.current.isReadOnly).toBe(false);
    });

    it("returns operator role and flags when /auth/me returns operator", async () => {
        const mockProfile = {
            id: "u-2",
            email: "operator@example.com",
            full_name: "Ops User",
            is_active: true,
            created_at: "2026-10-01T10:00:00Z",
            team: {
                id: "t-1",
                name: "Engineering",
                role: "operator",
            },
        };

        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue(
                new Response(JSON.stringify(mockProfile), {
                    status: 200,
                    headers: { "Content-Type": "application/json" },
                }),
            ),
        );

        const { result } = renderHook(() => useCurrentRole(), {
            wrapper: createWrapper(),
        });

        await waitFor(() => expect(result.current.role).toBe("operator"));

        expect(result.current.role).toBe("operator");
        expect(result.current.isAdmin).toBe(false);
        expect(result.current.isOperator).toBe(true);
        expect(result.current.isReadOnly).toBe(false);
    });

    it("returns read_only role and flags when /auth/me returns read_only", async () => {
        const mockProfile = {
            id: "u-3",
            email: "viewer@example.com",
            full_name: "Viewer User",
            is_active: true,
            created_at: "2026-10-01T10:00:00Z",
            team: {
                id: "t-1",
                name: "Engineering",
                role: "read_only",
            },
        };

        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue(
                new Response(JSON.stringify(mockProfile), {
                    status: 200,
                    headers: { "Content-Type": "application/json" },
                }),
            ),
        );

        const { result } = renderHook(() => useCurrentRole(), {
            wrapper: createWrapper(),
        });

        await waitFor(() => expect(result.current.role).toBe("read_only"));

        expect(result.current.role).toBe("read_only");
        expect(result.current.isAdmin).toBe(false);
        expect(result.current.isOperator).toBe(false);
        expect(result.current.isReadOnly).toBe(true);
    });

    it("defaults to admin if not logged in", () => {
        localStorage.clear();

        const { result } = renderHook(() => useCurrentRole(), {
            wrapper: createWrapper(),
        });

        expect(result.current.role).toBe("admin");
        expect(result.current.isAdmin).toBe(true);
        expect(result.current.isReadOnly).toBe(false);
        expect(result.current.isLoading).toBe(false);
    });
});
