import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
    ApiError,
    getIncident,
    getIncidentDeliveries,
    incidentHandlers,
    listIncidents,
} from "./incidentsApi";

describe("incidentsApi", () => {
    beforeEach(() => {
        localStorage.setItem("access_token", "test-token");
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    it("listIncidents sends query parameters and returns sorted items with open incidents first", async () => {
        const mockResponse = {
            items: [
                {
                    id: "inc-1",
                    monitor_id: "m-1",
                    monitor_name: "Auth API",
                    status: "resolved",
                    opened_at: "2026-10-02T10:00:00Z",
                    resolved_at: "2026-10-02T10:20:00Z",
                    failure_count: 3,
                    recovery_count: 2,
                },
                {
                    id: "inc-2",
                    monitor_id: "m-2",
                    monitor_name: "Payment API",
                    status: "open",
                    opened_at: "2026-10-01T10:00:00Z",
                    resolved_at: null,
                    failure_count: 4,
                    recovery_count: 0,
                },
            ],
            page: 1,
            page_size: 20,
            total: 2,
        };

        let requestedUrl = "";
        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                requestedUrl = url;
                return Promise.resolve(
                    new Response(JSON.stringify(mockResponse), {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    }),
                );
            }),
        );

        const result = await listIncidents({
            page: 2,
            pageSize: 10,
            status: "all",
            monitorId: "m-99",
        });

        expect(requestedUrl).toContain("/api/v1/incidents");
        expect(requestedUrl).toContain("page=2");
        expect(requestedUrl).toContain("page_size=10");
        expect(requestedUrl).toContain("monitor_id=m-99");
        // Open incident inc-2 should be first
        expect(result.items[0].id).toBe("inc-2");
        expect(result.items[1].id).toBe("inc-1");
    });

    it("getIncident returns incident detail with monitor_url", async () => {
        const mockDetail = {
            id: "inc-123",
            monitor_id: "m-1",
            monitor_name: "Payment API",
            monitor_url: "https://api.example.com/payment",
            status: "open",
            opened_at: "2026-10-01T10:00:00Z",
            resolved_at: null,
            failure_count: 3,
            recovery_count: 0,
        };

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation(() =>
                Promise.resolve(
                    new Response(JSON.stringify(mockDetail), {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    }),
                ),
            ),
        );

        const result = await getIncident("inc-123");
        expect(result.id).toBe("inc-123");
        expect(result.monitor_url).toBe("https://api.example.com/payment");
    });

    it("getIncident throws 404 ApiError when incident is missing or unauthorized", async () => {
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

        await expect(getIncident("missing-id")).rejects.toThrow(ApiError);
        try {
            await getIncident("missing-id");
        } catch (err) {
            expect(err).toBeInstanceOf(ApiError);
            expect((err as ApiError).status).toBe(404);
            expect((err as ApiError).message).toBe("Incident not found");
        }
    });

    it("getIncidentDeliveries returns delivery list items", async () => {
        const mockDeliveries = {
            items: [
                {
                    id: "del-1",
                    incident_id: "inc-1",
                    notification_channel_id: "chan-1",
                    channel_name: "Slack Alerts",
                    channel_type: "slack",
                    event_type: "opened",
                    status: "sent",
                    attempt_count: 1,
                    sent_at: "2026-10-01T10:05:00Z",
                    error_message: null,
                    created_at: "2026-10-01T10:04:00Z",
                },
            ],
        };

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation(() =>
                Promise.resolve(
                    new Response(JSON.stringify(mockDeliveries), {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    }),
                ),
            ),
        );

        const result = await getIncidentDeliveries("inc-1");
        expect(result.items.length).toBe(1);
        expect(result.items[0].channel_name).toBe("Slack Alerts");
        expect(result.items[0].status).toBe("sent");
    });

    it("incidentHandlers returns passed test fixtures", () => {
        const stubs = incidentHandlers([], []);
        expect(stubs).toEqual({ incidents: [], deliveries: [] });
    });
});
