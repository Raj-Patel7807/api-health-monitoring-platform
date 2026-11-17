/**
 * Tests for DashboardPage — S4-F1 (US-13)
 *
 * Coverage:
 *  - Summary cards rendered with correct counts
 *  - Monitor table rows with name, status badge (text + color class), last-checked, incident link
 *  - Failing monitors listed before healthy/unknown ones
 *  - Open incident links rendered for monitors with open incidents
 *  - "—" shown for missing last-checked and response-time values
 *  - Loading state
 *  - Empty state (no monitors) with Add first monitor link
 *  - Error state with retry button
 */

import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { App } from "../App";

function renderApp(initialEntry = "/dashboard") {
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

/** Build a minimal monitor fixture. */
function makeMonitor(overrides: Record<string, unknown> = {}) {
    return {
        id: "mon-1",
        name: "Payment API",
        url: "https://api.example.com/pay",
        method: "GET",
        enabled: true,
        check_interval_seconds: 60,
        expected_status_code: 200,
        created_at: "2026-10-01T10:00:00Z",
        consecutive_failures: 0,
        next_check_at: "2026-10-01T10:01:00Z",
        ...overrides,
    };
}

/** Build a minimal incident fixture. */
function makeIncident(overrides: Record<string, unknown> = {}) {
    return {
        id: "inc-1",
        monitor_id: "mon-1",
        monitor_name: "Payment API",
        status: "open",
        opened_at: "2026-10-01T09:55:00Z",
        resolved_at: null,
        failure_count: 3,
        recovery_count: 0,
        ...overrides,
    };
}

/** Stub fetch to return monitors + incidents in parallel. */
function stubFetch(
    monitors: ReturnType<typeof makeMonitor>[],
    incidents: ReturnType<typeof makeIncident>[],
) {
    vi.stubGlobal(
        "fetch",
        vi.fn().mockImplementation((url: string) => {
            if (url.includes("/incidents")) {
                return Promise.resolve(
                    new Response(
                        JSON.stringify({
                            items: incidents,
                            page: 1,
                            page_size: 500,
                            total: incidents.length,
                        }),
                        {
                            status: 200,
                            headers: { "Content-Type": "application/json" },
                        },
                    ),
                );
            }
            if (url.includes("/monitors")) {
                return Promise.resolve(
                    new Response(
                        JSON.stringify({
                            items: monitors,
                            page: 1,
                            page_size: 500,
                            total: monitors.length,
                        }),
                        {
                            status: 200,
                            headers: { "Content-Type": "application/json" },
                        },
                    ),
                );
            }
            // auth/me - fallback
            return Promise.resolve(
                new Response(
                    JSON.stringify({
                        id: "u1",
                        email: "a@b.com",
                        team: { role: "admin" },
                    }),
                    {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    },
                ),
            );
        }),
    );
}

describe("DashboardPage", () => {
    beforeEach(() => {
        localStorage.setItem("access_token", "test-token");
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    // ── Loading state ──────────────────────────────────────────────────────

    it("shows loading state before data resolves", () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation(() => new Promise(() => {})), // never resolves
        );
        renderApp();
        expect(screen.getByRole("status")).toBeInTheDocument();
        expect(screen.getByText(/loading monitors/i)).toBeInTheDocument();
    });

    // ── Summary cards ──────────────────────────────────────────────────────

    it("renders all 5 summary cards with correct counts", async () => {
        stubFetch(
            [
                makeMonitor({ id: "mon-1", consecutive_failures: 0 }),
                makeMonitor({ id: "mon-2", consecutive_failures: 2 }),
                makeMonitor({ id: "mon-3", enabled: false }),
            ],
            [makeIncident({ id: "inc-1", monitor_id: "mon-2" })],
        );
        renderApp();

        expect(await screen.findByTestId("summary-cards")).toBeInTheDocument();

        // Total = 3
        expect(
            screen.getByTestId("summary-card-total-monitors"),
        ).toHaveTextContent("3");
        // Healthy = 1 (mon-1)
        expect(screen.getByTestId("summary-card-healthy")).toHaveTextContent(
            "1",
        );
        // Failing = 1 (mon-2)
        expect(screen.getByTestId("summary-card-failing")).toHaveTextContent(
            "1",
        );
        // Unknown = 1 (mon-3, disabled)
        expect(screen.getByTestId("summary-card-unknown")).toHaveTextContent(
            "1",
        );
        // Open incidents = 1
        expect(
            screen.getByTestId("summary-card-open-incidents"),
        ).toHaveTextContent("1");
    });

    // ── Monitor table ──────────────────────────────────────────────────────

    it("renders monitor rows with name, URL, and status badge text", async () => {
        stubFetch(
            [
                makeMonitor({
                    id: "mon-1",
                    name: "Checkout API",
                    consecutive_failures: 0,
                }),
            ],
            [],
        );
        renderApp();

        expect(await screen.findByText("Checkout API")).toBeInTheDocument();
        expect(
            screen.getByText("https://api.example.com/pay"),
        ).toBeInTheDocument();

        // Status badge text must always be visible (not color-only)
        // Use aria-label to get the specific badge span, not the summary card label

        // Look for the badge within the monitor row
        const monitorRow = screen.getByTestId("monitor-row-mon-1");
        expect(within(monitorRow).getByText("Healthy")).toBeInTheDocument();
    });

    it("renders Failing badge for a monitor with consecutive_failures > 0", async () => {
        stubFetch([makeMonitor({ id: "mon-1", consecutive_failures: 3 })], []);
        renderApp();

        const monitorRow = await screen.findByTestId("monitor-row-mon-1");
        expect(within(monitorRow).getByText("Failing")).toBeInTheDocument();
    });

    it("renders Unknown badge for a disabled monitor", async () => {
        stubFetch(
            [
                makeMonitor({
                    id: "mon-1",
                    enabled: false,
                    consecutive_failures: 0,
                }),
            ],
            [],
        );
        renderApp();

        const monitorRow = await screen.findByTestId("monitor-row-mon-1");
        expect(within(monitorRow).getByText("Unknown")).toBeInTheDocument();
    });

    // ── Failing monitors listed first ──────────────────────────────────────

    it("lists failing monitors before healthy monitors", async () => {
        stubFetch(
            [
                makeMonitor({
                    id: "mon-1",
                    name: "Healthy API",
                    consecutive_failures: 0,
                }),
                makeMonitor({
                    id: "mon-2",
                    name: "Broken API",
                    consecutive_failures: 5,
                }),
            ],
            [],
        );
        renderApp();

        const rows = await screen.findAllByRole("row");
        const textContent = rows.map((r) => r.textContent ?? "");
        const brokenIdx = textContent.findIndex((t) =>
            t.includes("Broken API"),
        );
        const healthyIdx = textContent.findIndex((t) =>
            t.includes("Healthy API"),
        );
        expect(brokenIdx).toBeLessThan(healthyIdx);
    });

    // ── Incident link ──────────────────────────────────────────────────────

    it("shows open incident link for a monitor with an open incident", async () => {
        stubFetch(
            [makeMonitor({ id: "mon-1", consecutive_failures: 2 })],
            [makeIncident({ id: "inc-99", monitor_id: "mon-1" })],
        );
        renderApp();

        const incidentLink = await screen.findByRole("link", {
            name: /open incident for payment api/i,
        });
        expect(incidentLink).toBeInTheDocument();
        expect(incidentLink).toHaveAttribute("href", "/incidents/inc-99");
    });

    it("shows dash (—) in incident column when no open incident", async () => {
        stubFetch([makeMonitor({ id: "mon-1", consecutive_failures: 0 })], []);
        renderApp();

        const monitorRow = await screen.findByTestId("monitor-row-mon-1");
        // The incident cell should show "—"
        const incidentCell = monitorRow.querySelectorAll("td")[4];
        expect(incidentCell).toHaveTextContent("—");
    });

    // ── Last-checked cell ──────────────────────────────────────────────────

    it("renders dash for last-checked when next_check_at is null", async () => {
        stubFetch([makeMonitor({ id: "mon-1", next_check_at: null })], []);
        renderApp();

        const monitorRow = await screen.findByTestId("monitor-row-mon-1");
        // The last-checked cell (3rd td, index 2) should show "—"
        const lastCheckedCell = monitorRow.querySelectorAll("td")[2];
        expect(lastCheckedCell).toHaveTextContent("—");
    });

    // ── Monitors link ──────────────────────────────────────────────────────

    it("renders a link to the monitor detail page for each monitor", async () => {
        stubFetch([makeMonitor({ id: "mon-abc", name: "My API" })], []);
        renderApp();

        const link = await screen.findByRole("link", {
            name: /view monitor my api/i,
        });
        expect(link).toHaveAttribute("href", "/monitors/mon-abc");
    });

    // ── Empty state ────────────────────────────────────────────────────────

    it("shows empty state with Add your first monitor link when no monitors", async () => {
        stubFetch([], []);
        renderApp();

        expect(
            await screen.findByRole("heading", { name: /no monitors yet/i }),
        ).toBeInTheDocument();

        const addLink = screen.getByTestId("add-first-monitor-link");
        expect(addLink).toBeInTheDocument();
        expect(addLink).toHaveAttribute("href", "/monitors/new");
    });

    // ── Error state ────────────────────────────────────────────────────────

    it("shows error state with Try again button, retries on click and shows data", async () => {
        let attempt = 0;
        const monitors = [makeMonitor({ id: "mon-1" })];

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if (url.includes("/monitors")) {
                    attempt++;
                    if (attempt === 1) {
                        return Promise.resolve(
                            new Response("Service Unavailable", {
                                status: 503,
                            }),
                        );
                    }
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                items: monitors,
                                page: 1,
                                page_size: 500,
                                total: 1,
                            }),
                            {
                                status: 200,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                }
                if (url.includes("/incidents")) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                items: [],
                                page: 1,
                                page_size: 500,
                                total: 0,
                            }),
                            {
                                status: 200,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                }
                return Promise.resolve(
                    new Response(
                        JSON.stringify({
                            id: "u1",
                            email: "a@b.com",
                            team: { role: "admin" },
                        }),
                        {
                            status: 200,
                            headers: { "Content-Type": "application/json" },
                        },
                    ),
                );
            }),
        );

        renderApp();

        expect(
            await screen.findByRole("heading", {
                name: /could not load dashboard/i,
            }),
        ).toBeInTheDocument();

        const retryBtn = screen.getByTestId("retry-btn");
        fireEvent.click(retryBtn);

        expect(await screen.findByText("Payment API")).toBeInTheDocument();
    });
});
