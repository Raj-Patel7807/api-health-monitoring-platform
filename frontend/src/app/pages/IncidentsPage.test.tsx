import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { App } from "../App";

function renderApp(initialEntry = "/incidents") {
    const client = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return render(
        <QueryClientProvider client={client}>
            <MemoryRouter initialEntries={[initialEntry]}>
                <App />
            </MemoryRouter>
        </QueryClientProvider>,
    );
}

describe("IncidentsPage", () => {
    beforeEach(() => {
        localStorage.setItem("access_token", "test-token");
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    it("shows loading state, then rows with monitor name, status badge, opened time, duration, and failure count", async () => {
        const mockIncidents = [
            {
                id: "inc-1",
                monitor_id: "m-1",
                monitor_name: "Payment Gateway",
                status: "open",
                opened_at: "2026-10-01T10:00:00Z",
                resolved_at: null,
                failure_count: 5,
                recovery_count: 0,
            },
            {
                id: "inc-2",
                monitor_id: "m-2",
                monitor_name: "Auth Service",
                status: "resolved",
                opened_at: "2026-10-01T08:00:00Z",
                resolved_at: "2026-10-01T08:30:00Z",
                failure_count: 3,
                recovery_count: 2,
            },
        ];

        let resolveFetch: (res: Response) => void;
        const fetchPromise = new Promise<Response>((resolve) => {
            resolveFetch = resolve;
        });

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if (url.includes("/api/v1/monitors")) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({ items: [], page: 1, page_size: 100, total: 0 }),
                            { status: 200, headers: { "Content-Type": "application/json" } },
                        ),
                    );
                }
                return fetchPromise;
            }),
        );

        renderApp();

        // Loading state initially visible
        expect(screen.getByRole("status")).toBeInTheDocument();
        expect(screen.getByText("Loading incidents...")).toBeInTheDocument();

        // Resolve fetch
        resolveFetch!(
            new Response(
                JSON.stringify({
                    items: mockIncidents,
                    page: 1,
                    page_size: 20,
                    total: 2,
                }),
                {
                    status: 200,
                    headers: { "Content-Type": "application/json" },
                },
            ),
        );

        // Verify rendered table rows
        expect(await screen.findByText("Payment Gateway")).toBeInTheDocument();
        expect(screen.getByText("Auth Service")).toBeInTheDocument();

        // Status badges
        expect(screen.getByText("Open")).toBeInTheDocument();
        expect(screen.getByText("Resolved")).toBeInTheDocument();

        // Open incident shows how long it has been open
        expect(screen.getByText(/Open for/i)).toBeInTheDocument();

        // Resolved incident shows duration
        expect(screen.getByText("30m")).toBeInTheDocument();

        // Failure count
        expect(screen.getByText("5")).toBeInTheDocument();
        expect(screen.getByText("3")).toBeInTheDocument();
    });

    it("displays open incidents first by default", async () => {
        // API returns resolved first in raw list
        const mockIncidents = [
            {
                id: "inc-res",
                monitor_id: "m-1",
                monitor_name: "Resolved Service",
                status: "resolved",
                opened_at: "2026-10-02T12:00:00Z",
                resolved_at: "2026-10-02T12:15:00Z",
                failure_count: 2,
                recovery_count: 2,
            },
            {
                id: "inc-open",
                monitor_id: "m-2",
                monitor_name: "Active Outage",
                status: "open",
                opened_at: "2026-10-01T08:00:00Z",
                resolved_at: null,
                failure_count: 6,
                recovery_count: 0,
            },
        ];

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if (url.includes("/api/v1/monitors")) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({ items: [], page: 1, page_size: 100, total: 0 }),
                            { status: 200, headers: { "Content-Type": "application/json" } },
                        ),
                    );
                }
                return Promise.resolve(
                    new Response(
                        JSON.stringify({
                            items: mockIncidents,
                            page: 1,
                            page_size: 20,
                            total: 2,
                        }),
                        { status: 200, headers: { "Content-Type": "application/json" } },
                    ),
                );
            }),
        );

        renderApp();

        // The open incident should appear before the resolved incident
        const links = await screen.findAllByTestId(/^incident-link-/);
        expect(links[0]).toHaveAttribute("href", "/incidents/inc-open");
        expect(links[1]).toHaveAttribute("href", "/incidents/inc-res");
    });

    it("filters correctly by status and monitor", async () => {
        const requestedUrls: string[] = [];
        const mockMonitors = [
            {
                id: "mon-123",
                name: "Database Cluster",
                url: "https://db.example.com",
                method: "GET",
                enabled: true,
                check_interval_seconds: 60,
                expected_status_code: 200,
                created_at: "2026-10-01T00:00:00Z",
            },
        ];

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                requestedUrls.push(url);
                if (url.includes("/api/v1/monitors")) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({ items: mockMonitors, page: 1, page_size: 100, total: 1 }),
                            { status: 200, headers: { "Content-Type": "application/json" } },
                        ),
                    );
                }
                return Promise.resolve(
                    new Response(
                        JSON.stringify({
                            items: [
                                {
                                    id: "inc-filtered",
                                    monitor_id: "mon-123",
                                    monitor_name: "Database Cluster",
                                    status: "open",
                                    opened_at: "2026-10-01T10:00:00Z",
                                    resolved_at: null,
                                    failure_count: 3,
                                    recovery_count: 0,
                                },
                            ],
                            page: 1,
                            page_size: 20,
                            total: 1,
                        }),
                        { status: 200, headers: { "Content-Type": "application/json" } },
                    ),
                );
            }),
        );

        renderApp();

        expect(await screen.findByText("Database Cluster")).toBeInTheDocument();

        // Change status filter to 'open'
        const statusSelect = screen.getByLabelText("Filter by status");
        fireEvent.change(statusSelect, { target: { value: "open" } });

        // Change monitor filter to 'mon-123'
        const monitorSelect = screen.getByLabelText("Filter by monitor");
        fireEvent.change(monitorSelect, { target: { value: "mon-123" } });

        const lastIncidentCall = requestedUrls
            .filter((u) => u.includes("/api/v1/incidents"))
            .pop();

        expect(lastIncidentCall).toContain("status=open");
        expect(lastIncidentCall).toContain("monitor_id=mon-123");
    });

    it("handles pagination with previous and next buttons", async () => {
        const requestedUrls: string[] = [];

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                requestedUrls.push(url);
                return Promise.resolve(
                    new Response(
                        JSON.stringify({
                            items: [
                                {
                                    id: "inc-page1",
                                    monitor_id: "m-1",
                                    monitor_name: "Page 1 Item",
                                    status: "open",
                                    opened_at: "2026-10-01T10:00:00Z",
                                    resolved_at: null,
                                    failure_count: 1,
                                    recovery_count: 0,
                                },
                            ],
                            page: 1,
                            page_size: 20,
                            total: 35,
                        }),
                        { status: 200, headers: { "Content-Type": "application/json" } },
                    ),
                );
            }),
        );

        renderApp();

        expect(await screen.findByText("Page 1 Item")).toBeInTheDocument();
        expect(screen.getByText(/Page 1 of 2/)).toBeInTheDocument();

        const prevBtn = screen.getByRole("button", { name: "Previous page" });
        const nextBtn = screen.getByRole("button", { name: "Next page" });

        expect(prevBtn).toBeDisabled();
        expect(nextBtn).toBeEnabled();

        fireEvent.click(nextBtn);

        const lastCall = requestedUrls.pop();
        expect(lastCall).toContain("page=2");
    });

    it("displays empty state when no incidents match", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation(() =>
                Promise.resolve(
                    new Response(
                        JSON.stringify({
                            items: [],
                            page: 1,
                            page_size: 20,
                            total: 0,
                        }),
                        { status: 200, headers: { "Content-Type": "application/json" } },
                    ),
                ),
            ),
        );

        renderApp();

        expect(await screen.findByText("No incidents found")).toBeInTheDocument();
    });

    it("displays error state and allows retry", async () => {
        let attempts = 0;
        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation(() => {
                attempts++;
                if (attempts === 1) {
                    return Promise.reject(new Error("Network connection lost"));
                }
                return Promise.resolve(
                    new Response(
                        JSON.stringify({
                            items: [
                                {
                                    id: "inc-ok",
                                    monitor_id: "m-1",
                                    monitor_name: "Recovered Service",
                                    status: "resolved",
                                    opened_at: "2026-10-01T10:00:00Z",
                                    resolved_at: "2026-10-01T10:20:00Z",
                                    failure_count: 2,
                                    recovery_count: 2,
                                },
                            ],
                            page: 1,
                            page_size: 20,
                            total: 1,
                        }),
                        { status: 200, headers: { "Content-Type": "application/json" } },
                    ),
                );
            }),
        );

        renderApp();

        expect(await screen.findByRole("alert")).toBeInTheDocument();
        expect(screen.getByText("Could not load incidents")).toBeInTheDocument();

        // Click Try again
        fireEvent.click(screen.getByText("Try again"));

        expect(await screen.findByText("Recovered Service")).toBeInTheDocument();
    });

    it("renders text from the API safely as plain text", async () => {
        const maliciousName = "<script>alert('xss')</script>Safe Monitor Name";

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation(() =>
                Promise.resolve(
                    new Response(
                        JSON.stringify({
                            items: [
                                {
                                    id: "inc-xss",
                                    monitor_id: "m-1",
                                    monitor_name: maliciousName,
                                    status: "open",
                                    opened_at: "2026-10-01T10:00:00Z",
                                    resolved_at: null,
                                    failure_count: 1,
                                    recovery_count: 0,
                                },
                            ],
                            page: 1,
                            page_size: 20,
                            total: 1,
                        }),
                        { status: 200, headers: { "Content-Type": "application/json" } },
                    ),
                ),
            ),
        );

        renderApp();

        // Find by raw text content - must be plain text node, not executed or rendered HTML tags
        expect(await screen.findByText(maliciousName)).toBeInTheDocument();
        expect(document.querySelector("script")).toBeNull();
    });
});
