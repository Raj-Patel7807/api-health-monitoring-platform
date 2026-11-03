import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { App } from "../App";

function renderApp(initialEntry = "/incidents/inc-123") {
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

describe("IncidentDetailPage", () => {
    beforeEach(() => {
        localStorage.setItem("access_token", "test-token");
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    it("renders incident details, monitor link and URL, counts, and deliveries panel", async () => {
        const mockIncident = {
            id: "inc-123",
            monitor_id: "mon-abc",
            monitor_name: "Payment Gateway",
            monitor_url: "https://api.example.com/v1/payments",
            status: "open",
            opened_at: "2026-10-01T10:00:00Z",
            resolved_at: null,
            failure_count: 4,
            recovery_count: 0,
        };

        const mockDeliveries = {
            items: [
                {
                    id: "del-1",
                    incident_id: "inc-123",
                    notification_channel_id: "chan-1",
                    channel_name: "Ops Team Slack",
                    channel_type: "slack",
                    event_type: "opened",
                    status: "sent",
                    attempt_count: 1,
                    sent_at: "2026-10-01T10:01:00Z",
                    error_message: null,
                    created_at: "2026-10-01T10:00:30Z",
                },
            ],
        };

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if (url.includes("/alert-deliveries")) {
                    return Promise.resolve(
                        new Response(JSON.stringify(mockDeliveries), {
                            status: 200,
                            headers: { "Content-Type": "application/json" },
                        }),
                    );
                }
                return Promise.resolve(
                    new Response(JSON.stringify(mockIncident), {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    }),
                );
            }),
        );

        renderApp("/incidents/inc-123");

        // Heading with monitor name
        expect(
            await screen.findByRole("heading", {
                name: "Incident for Payment Gateway",
            }),
        ).toBeInTheDocument();

        // Monitor link
        const monitorLink = screen.getByRole("link", {
            name: "Payment Gateway",
        });
        expect(monitorLink).toHaveAttribute("href", "/monitors/mon-abc");

        // Monitor URL
        expect(
            screen.getByText("https://api.example.com/v1/payments"),
        ).toBeInTheDocument();

        // Failure count and Recovery count
        expect(screen.getByText("4")).toBeInTheDocument();
        expect(screen.getByText("0")).toBeInTheDocument();

        // Deliveries panel
        expect(screen.getByText("Alert Deliveries")).toBeInTheDocument();
        expect(screen.getByText("Ops Team Slack")).toBeInTheDocument();
        expect(screen.getByText("Slack")).toBeInTheDocument();
        expect(screen.getByText("Event: opened")).toBeInTheDocument();
        expect(screen.getByTestId("delivery-status-sent")).toBeInTheDocument();
        expect(screen.getByText("Attempts:")).toBeInTheDocument();
    });

    it("shows how long an open incident has been open", async () => {
        const mockIncident = {
            id: "inc-open",
            monitor_id: "mon-abc",
            monitor_name: "Orders API",
            monitor_url: "https://orders.example.com",
            status: "open",
            opened_at: "2026-10-01T10:00:00Z",
            resolved_at: null,
            failure_count: 3,
            recovery_count: 0,
        };

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if (url.includes("/alert-deliveries")) {
                    return Promise.resolve(
                        new Response(JSON.stringify({ items: [] }), {
                            status: 200,
                            headers: { "Content-Type": "application/json" },
                        }),
                    );
                }
                return Promise.resolve(
                    new Response(JSON.stringify(mockIncident), {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    }),
                );
            }),
        );

        renderApp("/incidents/inc-open");

        expect(await screen.findByText(/Open for/i)).toBeInTheDocument();
        expect(screen.getByTestId("incident-status-badge")).toHaveTextContent(
            "Open",
        );
    });

    it("shows duration for a resolved incident", async () => {
        const mockIncident = {
            id: "inc-res",
            monitor_id: "mon-abc",
            monitor_name: "Search API",
            monitor_url: "https://search.example.com",
            status: "resolved",
            opened_at: "2026-10-01T10:00:00Z",
            resolved_at: "2026-10-01T10:45:00Z",
            failure_count: 3,
            recovery_count: 2,
        };

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if (url.includes("/alert-deliveries")) {
                    return Promise.resolve(
                        new Response(JSON.stringify({ items: [] }), {
                            status: 200,
                            headers: { "Content-Type": "application/json" },
                        }),
                    );
                }
                return Promise.resolve(
                    new Response(JSON.stringify(mockIncident), {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    }),
                );
            }),
        );

        renderApp("/incidents/inc-res");

        expect(await screen.findByText(/duration: 45m/i)).toBeInTheDocument();
        expect(screen.getByTestId("incident-status-badge")).toHaveTextContent(
            "Resolved",
        );
    });

    it("shows distinct badges for sent, failed and pending deliveries, and failed deliveries display their error message", async () => {
        const mockIncident = {
            id: "inc-deliv",
            monitor_id: "mon-1",
            monitor_name: "Notification Engine",
            monitor_url: "https://notify.example.com",
            status: "resolved",
            opened_at: "2026-10-01T10:00:00Z",
            resolved_at: "2026-10-01T10:30:00Z",
            failure_count: 3,
            recovery_count: 2,
        };

        const mockDeliveries = {
            items: [
                {
                    id: "del-sent",
                    incident_id: "inc-deliv",
                    notification_channel_id: "chan-1",
                    channel_name: "Slack Channel",
                    channel_type: "slack",
                    event_type: "opened",
                    status: "sent",
                    attempt_count: 1,
                    sent_at: "2026-10-01T10:02:00Z",
                    error_message: null,
                    created_at: "2026-10-01T10:01:00Z",
                },
                {
                    id: "del-pending",
                    incident_id: "inc-deliv",
                    notification_channel_id: "chan-2",
                    channel_name: "Email Alerts",
                    channel_type: "email",
                    event_type: "opened",
                    status: "pending",
                    attempt_count: 0,
                    sent_at: null,
                    error_message: null,
                    created_at: "2026-10-01T10:01:00Z",
                },
                {
                    id: "del-failed",
                    incident_id: "inc-deliv",
                    notification_channel_id: "chan-3",
                    channel_name: "Incident Webhook",
                    channel_type: "webhook",
                    event_type: "opened",
                    status: "failed",
                    attempt_count: 4,
                    sent_at: null,
                    error_message:
                        "Connection refused: endpoint host unreachable after 4 retries",
                    created_at: "2026-10-01T10:01:00Z",
                },
            ],
        };

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if (url.includes("/alert-deliveries")) {
                    return Promise.resolve(
                        new Response(JSON.stringify(mockDeliveries), {
                            status: 200,
                            headers: { "Content-Type": "application/json" },
                        }),
                    );
                }
                return Promise.resolve(
                    new Response(JSON.stringify(mockIncident), {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    }),
                );
            }),
        );

        renderApp("/incidents/inc-deliv");

        // Wait for deliveries list
        expect(
            await screen.findByTestId("deliveries-list"),
        ).toBeInTheDocument();

        // Verify distinct badges
        expect(screen.getByTestId("delivery-status-sent")).toHaveTextContent(
            "sent",
        );
        expect(screen.getByTestId("delivery-status-pending")).toHaveTextContent(
            "pending",
        );
        expect(screen.getByTestId("delivery-status-failed")).toHaveTextContent(
            "failed",
        );

        // Verify failed delivery shows its error message
        const errorBox = screen.getByTestId("delivery-error-box");
        expect(errorBox).toBeInTheDocument();
        expect(errorBox).toHaveTextContent(
            "Connection refused: endpoint host unreachable after 4 retries",
        );
    });

    it("displays a 404 not found page when incident is missing or unauthorized", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation(() =>
                Promise.resolve(
                    new Response(
                        JSON.stringify({ detail: "Incident not found" }),
                        {
                            status: 404,
                            headers: { "Content-Type": "application/json" },
                        },
                    ),
                ),
            ),
        );

        renderApp("/incidents/non-existent-id");

        expect(
            await screen.findByRole("heading", { name: "Incident not found" }),
        ).toBeInTheDocument();
        expect(
            screen.getByText(
                "The requested incident does not exist or belongs to another team.",
            ),
        ).toBeInTheDocument();
        expect(
            screen.getByRole("link", { name: "Return to incidents list" }),
        ).toHaveAttribute("href", "/incidents");
    });

    it("renders text from the API safely as plain text in detail and delivery views", async () => {
        const xssPayload = "<img src=x onerror=alert('xss')>";
        const xssErrorMessage =
            "<b>Danger</b> Error: <script>alert(1)</script>";

        const mockIncident = {
            id: "inc-xss-detail",
            monitor_id: "mon-xss",
            monitor_name: xssPayload,
            monitor_url: "https://example.com/test",
            status: "open",
            opened_at: "2026-10-01T10:00:00Z",
            resolved_at: null,
            failure_count: 1,
            recovery_count: 0,
        };

        const mockDeliveries = {
            items: [
                {
                    id: "del-xss",
                    incident_id: "inc-xss-detail",
                    notification_channel_id: "chan-x",
                    channel_name: "<marquee>Channel XSS</marquee>",
                    channel_type: "webhook",
                    event_type: "opened",
                    status: "failed",
                    attempt_count: 1,
                    sent_at: null,
                    error_message: xssErrorMessage,
                    created_at: "2026-10-01T10:00:00Z",
                },
            ],
        };

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if (url.includes("/alert-deliveries")) {
                    return Promise.resolve(
                        new Response(JSON.stringify(mockDeliveries), {
                            status: 200,
                            headers: { "Content-Type": "application/json" },
                        }),
                    );
                }
                return Promise.resolve(
                    new Response(JSON.stringify(mockIncident), {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    }),
                );
            }),
        );

        renderApp("/incidents/inc-xss-detail");

        // The text should be rendered as plain text string, not executed or rendered HTML elements
        expect(await screen.findByText(xssErrorMessage)).toBeInTheDocument();
        expect(document.querySelector("marquee")).toBeNull();
        expect(document.querySelector("script")).toBeNull();
    });
});
