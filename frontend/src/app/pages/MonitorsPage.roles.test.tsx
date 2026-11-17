import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { MonitorsPage } from "./MonitorsPage";
import * as roleHook from "../hooks/useCurrentRole";

function renderMonitorsPage() {
    const client = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return render(
        <QueryClientProvider client={client}>
            <MemoryRouter initialEntries={["/monitors"]}>
                <MonitorsPage />
            </MemoryRouter>
        </QueryClientProvider>,
    );
}

describe("MonitorsPage — role-aware controls (US-19)", () => {
    beforeEach(() => {
        localStorage.setItem("access_token", "test-token");
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    const mockMonitors = [
        {
            id: "mon-1",
            name: "Production Gateway",
            url: "https://api.example.com",
            method: "GET",
            enabled: true,
            check_interval_seconds: 60,
            expected_status_code: 200,
            created_at: "2026-10-01T10:00:00Z",
        },
    ];

    it("read_only user sees no Add monitor button, no Edit links, no Delete buttons, and no Members link in nav", async () => {
        vi.spyOn(roleHook, "useCurrentRole").mockReturnValue({
            role: "read_only",
            isAdmin: false,
            isOperator: false,
            isReadOnly: true,
            isLoading: false,
            isError: false,
            error: null,
            refetch: vi.fn(),
        });

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if (url.includes("/api/v1/monitors")) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                items: mockMonitors,
                                total: 1,
                                page: 1,
                                page_size: 20,
                            }),
                            {
                                status: 200,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                }
                return Promise.reject(new Error(`Unexpected url: ${url}`));
            }),
        );

        renderMonitorsPage();

        expect(
            await screen.findByRole("heading", { name: "Monitors" }),
        ).toBeInTheDocument();
        expect(await screen.findByText("Production Gateway")).toBeInTheDocument();

        // Add monitor button must NOT be present
        expect(screen.queryByTestId("add-monitor-btn")).not.toBeInTheDocument();
        expect(
            screen.queryByRole("link", { name: "Add monitor" }),
        ).not.toBeInTheDocument();

        // Edit link and Delete button must NOT be present
        expect(screen.queryByText("Edit")).not.toBeInTheDocument();
        expect(screen.queryByTestId("delete-mon-1")).not.toBeInTheDocument();

        // Actions column header must NOT be present
        expect(screen.queryByText("Actions")).not.toBeInTheDocument();

        // AppNav Members link must NOT be present for read_only
        expect(screen.queryByRole("link", { name: /members/i })).not.toBeInTheDocument();
    });

    it("admin user sees Add monitor button, Edit links, Delete buttons, and Members link in nav", async () => {
        vi.spyOn(roleHook, "useCurrentRole").mockReturnValue({
            role: "admin",
            isAdmin: true,
            isOperator: false,
            isReadOnly: false,
            isLoading: false,
            isError: false,
            error: null,
            refetch: vi.fn(),
        });

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if (url.includes("/api/v1/monitors")) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                items: mockMonitors,
                                total: 1,
                                page: 1,
                                page_size: 20,
                            }),
                            {
                                status: 200,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                }
                return Promise.reject(new Error(`Unexpected url: ${url}`));
            }),
        );

        renderMonitorsPage();

        expect(
            await screen.findByRole("heading", { name: "Monitors" }),
        ).toBeInTheDocument();
        expect(await screen.findByText("Production Gateway")).toBeInTheDocument();

        // Add monitor button must be present
        expect(screen.getByTestId("add-monitor-btn")).toBeInTheDocument();

        // Edit link and Delete button must be present
        expect(screen.getByText("Edit")).toBeInTheDocument();
        expect(screen.getByTestId("delete-mon-1")).toBeInTheDocument();

        // Actions column header must be present
        expect(screen.getByText("Actions")).toBeInTheDocument();

        // AppNav Members link must be present for admin
        expect(screen.getByRole("link", { name: /members/i })).toBeInTheDocument();
    });
});
