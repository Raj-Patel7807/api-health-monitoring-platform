import { http, HttpResponse } from "msw";

const MOCK_MONITORS = [
    {
        id: "mon-1",
        name: "Payment API",
        url: "https://api.example.com/payment",
        method: "GET",
        enabled: true,
        check_interval_seconds: 60,
        expected_status_code: 200,
        created_at: "2026-10-01T10:00:00Z",
        consecutive_failures: 0,
        next_check_at: new Date(Date.now() - 30000).toISOString(),
    },
    {
        id: "mon-2",
        name: "Auth API",
        url: "https://api.example.com/auth",
        method: "POST",
        enabled: true,
        check_interval_seconds: 120,
        expected_status_code: 201,
        created_at: "2026-10-02T10:00:00Z",
        consecutive_failures: 3,
        next_check_at: new Date(Date.now() - 120000).toISOString(),
    },
    {
        id: "mon-3",
        name: "Webhook Service",
        url: "https://hooks.example.com/notify",
        method: "POST",
        enabled: false,
        check_interval_seconds: 300,
        expected_status_code: 200,
        created_at: "2026-10-03T10:00:00Z",
        consecutive_failures: 0,
        next_check_at: null,
    },
];

const MOCK_OPEN_INCIDENTS = [
    {
        id: "inc-1",
        monitor_id: "mon-2",
        monitor_name: "Auth API",
        status: "open",
        opened_at: new Date(Date.now() - 900000).toISOString(),
        resolved_at: null,
        failure_count: 3,
        recovery_count: 0,
    },
];

export const handlers = [
    // ── Monitor check results ───────────────────────────────────────────────
    http.get("*/api/v1/monitors/:id/results", ({ request, params }) => {
        const url = new URL(request.url);
        const page = Number(url.searchParams.get("page") || 1);
        const monitorId = String(params.id);

        return HttpResponse.json({
            items: [
                {
                    id: "res-1",
                    monitor_id: monitorId,
                    checked_at: new Date().toISOString(),
                    status: "healthy",
                    http_status_code: 200,
                    response_time_ms: 120,
                    timeout: false,
                    connection_error: false,
                    ssl_error: false,
                    error_message: null,
                    response_body_excerpt: null,
                },
                {
                    id: "res-2",
                    monitor_id: monitorId,
                    checked_at: new Date(Date.now() - 60000).toISOString(),
                    status: "failing",
                    http_status_code: 500,
                    response_time_ms: 850,
                    timeout: false,
                    connection_error: false,
                    ssl_error: false,
                    error_message: "Internal Server Error",
                    response_body_excerpt:
                        '{"error": "Database connection timeout"}',
                },
            ],
            page,
            page_size: 20,
            total: 2,
            start_time: new Date(Date.now() - 86400000).toISOString(),
            end_time: new Date().toISOString(),
        });
    }),

    // ── Dashboard: monitors list ────────────────────────────────────────────
    http.get("*/api/v1/monitors", ({ request }) => {
        const url = new URL(request.url);
        const page = Number(url.searchParams.get("page") || 1);
        const pageSize = Number(url.searchParams.get("page_size") || 20);

        return HttpResponse.json({
            items: MOCK_MONITORS,
            page,
            page_size: pageSize,
            total: MOCK_MONITORS.length,
        });
    }),

    // ── Dashboard: open incidents ────────────────────────────────────────────
    http.get("*/api/v1/incidents", ({ request }) => {
        const url = new URL(request.url);
        const status = url.searchParams.get("status");
        const page = Number(url.searchParams.get("page") || 1);
        const pageSize = Number(url.searchParams.get("page_size") || 20);

        const items =
            status === "open" ? MOCK_OPEN_INCIDENTS : MOCK_OPEN_INCIDENTS;

        return HttpResponse.json({
            items,
            page,
            page_size: pageSize,
            total: items.length,
        });
    }),
];
