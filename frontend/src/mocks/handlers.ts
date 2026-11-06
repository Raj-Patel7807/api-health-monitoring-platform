import { http, HttpResponse } from "msw";

export const handlers = [
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
];
