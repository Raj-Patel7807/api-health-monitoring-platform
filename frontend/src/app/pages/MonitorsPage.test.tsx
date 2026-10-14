import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { App } from "../App";

function renderApp(initialEntry = "/monitors") {
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

describe("MonitorsPage", () => {
    beforeEach(() => {
        localStorage.setItem("access_token", "test-token");
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    it("shows loading state, then rows with name, url, method, status, interval, and expected status", async () => {
        const mockMonitors = [
            {
                id: "mon-1",
                name: "Payment API",
                url: "https://api.example.com/payment",
                method: "GET",
                enabled: true,
                check_interval_seconds: 60,
                expected_status_code: 200,
                created_at: "2026-10-01T10:00:00Z",
            },
            {
                id: "mon-2",
                name: "Auth API",
                url: "https://api.example.com/auth",
                method: "POST",
                enabled: false,
                check_interval_seconds: 120,
                expected_status_code: 201,
                created_at: "2026-10-02T10:00:00Z",
            },
        ];

        let resolveFetch: (res: Response) => void;
        const fetchPromise = new Promise<Response>((resolve) => {
            resolveFetch = resolve;
        });

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation(() => fetchPromise),
        );

        renderApp();

        // Loading state initially visible
        expect(screen.getByRole("status")).toBeInTheDocument();
        expect(screen.getByText("Loading monitors...")).toBeInTheDocument();

        // Resolve API call
        resolveFetch!(
            new Response(
                JSON.stringify({
                    items: mockMonitors,
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

        // Await rendered rows
        expect(await screen.findByText("Payment API")).toBeInTheDocument();
        expect(
            screen.getByText("https://api.example.com/payment"),
        ).toBeInTheDocument();
        expect(screen.getByText("GET")).toBeInTheDocument();
        expect(screen.getByText("Enabled")).toBeInTheDocument();
        expect(screen.getByText("Every 60s")).toBeInTheDocument();
        expect(screen.getByText("200")).toBeInTheDocument();

        expect(screen.getByText("Auth API")).toBeInTheDocument();
        expect(
            screen.getByText("https://api.example.com/auth"),
        ).toBeInTheDocument();
        expect(screen.getByText("POST")).toBeInTheDocument();
        expect(screen.getByText("Paused")).toBeInTheDocument();
        expect(screen.getByText("Every 120s")).toBeInTheDocument();
        expect(screen.getByText("201")).toBeInTheDocument();
    });

    it("shows empty state with Add your first monitor link", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue(
                new Response(
                    JSON.stringify({
                        items: [],
                        page: 1,
                        page_size: 20,
                        total: 0,
                    }),
                    {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    },
                ),
            ),
        );

        renderApp();

        expect(
            await screen.findByRole("heading", { name: "No monitors yet" }),
        ).toBeInTheDocument();
        const emptyLink = screen.getByRole("link", {
            name: "Add your first monitor",
        });
        expect(emptyLink).toBeInTheDocument();
        expect(emptyLink).toHaveAttribute("href", "/monitors/new");
    });

    it("shows error state with working Try again button", async () => {
        let attempt = 0;
        const mockFetch = vi.fn().mockImplementation(() => {
            attempt++;
            if (attempt === 1) {
                return Promise.resolve(
                    new Response("Service Unavailable", { status: 503 }),
                );
            }
            return Promise.resolve(
                new Response(
                    JSON.stringify({
                        items: [
                            {
                                id: "mon-1",
                                name: "Recovered API",
                                url: "https://example.com",
                                method: "GET",
                                enabled: true,
                                check_interval_seconds: 60,
                                expected_status_code: 200,
                                created_at: "2026-10-01T10:00:00Z",
                            },
                        ],
                        page: 1,
                        page_size: 20,
                        total: 1,
                    }),
                    {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    },
                ),
            );
        });
        vi.stubGlobal("fetch", mockFetch);

        renderApp();

        expect(
            await screen.findByRole("heading", {
                name: "Could not load monitors",
            }),
        ).toBeInTheDocument();

        const retryButton = screen.getByRole("button", { name: "Try again" });
        fireEvent.click(retryButton);

        expect(await screen.findByText("Recovered API")).toBeInTheDocument();
    });

    it("handles pagination calling API with next page and disables Previous on page 1", async () => {
        const mockFetch = vi.fn().mockImplementation((url: string) => {
            const page = url.includes("page=2") ? 2 : 1;
            return Promise.resolve(
                new Response(
                    JSON.stringify({
                        items: [
                            {
                                id: `mon-${page}`,
                                name: `Monitor Page ${page}`,
                                url: "https://example.com",
                                method: "GET",
                                enabled: true,
                                check_interval_seconds: 60,
                                expected_status_code: 200,
                                created_at: "2026-10-01T10:00:00Z",
                            },
                        ],
                        page,
                        page_size: 20,
                        total: 35,
                    }),
                    {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    },
                ),
            );
        });
        vi.stubGlobal("fetch", mockFetch);

        renderApp();

        expect(await screen.findByText("Monitor Page 1")).toBeInTheDocument();
        expect(screen.getByText(/Page 1 of 2/)).toBeInTheDocument();

        const prevButton = screen.getByRole("button", { name: "Previous" });
        const nextButton = screen.getByRole("button", { name: "Next" });

        expect(prevButton).toBeDisabled();
        expect(nextButton).not.toBeDisabled();

        fireEvent.click(nextButton);

        expect(await screen.findByText("Monitor Page 2")).toBeInTheDocument();
        expect(screen.getByText(/Page 2 of 2/)).toBeInTheDocument();
        expect(screen.getByRole("button", { name: "Next" })).toBeDisabled();
        expect(
            screen.getByRole("button", { name: "Previous" }),
        ).not.toBeDisabled();
    });

    it("Add monitor and each Edit link point to the right routes", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockResolvedValue(
                new Response(
                    JSON.stringify({
                        items: [
                            {
                                id: "mon-abc",
                                name: "Billing API",
                                url: "https://billing.example.com",
                                method: "GET",
                                enabled: true,
                                check_interval_seconds: 60,
                                expected_status_code: 200,
                                created_at: "2026-10-01T10:00:00Z",
                            },
                        ],
                        page: 1,
                        page_size: 20,
                        total: 1,
                    }),
                    {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    },
                ),
            ),
        );

        renderApp();

        expect(await screen.findByText("Billing API")).toBeInTheDocument();

        const addLink = screen.getByRole("link", { name: "Add monitor" });
        expect(addLink).toHaveAttribute("href", "/monitors/new");

        const editLink = screen.getByRole("link", { name: "Edit Billing API" });
        expect(editLink).toHaveAttribute("href", "/monitors/mon-abc/edit");
    });
});
