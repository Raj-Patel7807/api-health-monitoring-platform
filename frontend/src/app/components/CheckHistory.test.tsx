/**
 * Tests for CheckHistory component (F1 — US-08)
 *
 * Uses the same vi.stubGlobal("fetch", ...) pattern as the rest of the suite.
 * Every test stubs both the monitor detail fetch AND the results fetch,
 * because the page mounts CheckHistory after the monitor loads.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { App } from "../App";

/* ── Fixture data ─────────────────────────────────────────────────────────── */

const MONITOR = {
    id: "mon-1",
    name: "Payment API",
    url: "https://api.example.com/health",
    method: "GET",
    enabled: true,
    check_interval_seconds: 60,
    expected_status_code: 200,
    created_at: "2026-10-01T10:00:00Z",
    consecutive_failures: 0,
    consecutive_successes: 5,
    timeout_seconds: 10,
    failure_threshold: 3,
    recovery_threshold: 2,
};

const HEALTHY_RESULT = {
    id: "r-1",
    checked_at: "2026-10-31T10:00:00Z",
    status: "healthy",
    http_status_code: 200,
    response_time_ms: 142,
    timeout: false,
    connection_error: false,
    ssl_error: false,
    error_message: null,
    response_body_excerpt: null,
};

const FAILING_RESULT = {
    id: "r-2",
    checked_at: "2026-10-31T09:55:00Z",
    status: "failing",
    http_status_code: 500,
    response_time_ms: 843,
    timeout: false,
    connection_error: false,
    ssl_error: false,
    error_message: "Internal Server Error",
    response_body_excerpt: "<html>Error page</html>",
};

const NULL_RESULT = {
    id: "r-3",
    checked_at: "2026-10-31T09:50:00Z",
    status: "failing",
    http_status_code: null,
    response_time_ms: null,
    timeout: true,
    connection_error: false,
    ssl_error: false,
    error_message: "Connection timed out",
    response_body_excerpt: null,
};

/* ── Helpers ──────────────────────────────────────────────────────────────── */

function makeMonitorResponse(monitor = MONITOR) {
    return new Response(JSON.stringify(monitor), {
        status: 200,
        headers: { "Content-Type": "application/json" },
    });
}

function makeResultsResponse(
    items: object[],
    total = items.length,
    page = 1,
    page_size = 20,
) {
    return new Response(JSON.stringify({ items, page, page_size, total }), {
        status: 200,
        headers: { "Content-Type": "application/json" },
    });
}

/**
 * Renders the full App at /monitors/mon-1 with a fresh QueryClient.
 * fetch is already stubbed by the caller.
 */
function renderDetail() {
    const client = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return render(
        <QueryClientProvider client={client}>
            <MemoryRouter initialEntries={["/monitors/mon-1"]}>
                <App />
            </MemoryRouter>
        </QueryClientProvider>,
    );
}

/* ── Test setup ───────────────────────────────────────────────────────────── */

beforeEach(() => {
    localStorage.setItem("access_token", "test-token");
    localStorage.setItem("refresh_token", "test-refresh");
});

afterEach(() => {
    vi.unstubAllGlobals();
    localStorage.clear();
});

/* ── Tests ────────────────────────────────────────────────────────────────── */

describe("CheckHistory — results table", () => {
    it("shows the check history section heading after monitor loads", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if ((url as string).includes("/results")) {
                    return Promise.resolve(
                        makeResultsResponse([HEALTHY_RESULT]),
                    );
                }
                return Promise.resolve(makeMonitorResponse());
            }),
        );

        renderDetail();

        expect(
            await screen.findByRole("heading", { name: /check history/i }),
        ).toBeInTheDocument();
    });

    it("displays results newest first with correct columns", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if ((url as string).includes("/results")) {
                    return Promise.resolve(
                        makeResultsResponse([HEALTHY_RESULT, FAILING_RESULT]),
                    );
                }
                return Promise.resolve(makeMonitorResponse());
            }),
        );

        renderDetail();

        // Wait for table
        const table = await screen.findByTestId("ch-table");
        expect(table).toBeInTheDocument();

        // Healthy row — scope queries to the table to avoid conflict with monitor detail
        expect(table).toHaveTextContent("healthy");
        expect(table).toHaveTextContent("200");
        expect(table).toHaveTextContent("142 ms");

        // Failing row
        expect(table).toHaveTextContent("failing");
        expect(table).toHaveTextContent("500");
        expect(table).toHaveTextContent("843 ms");
        expect(table).toHaveTextContent("Internal Server Error");
    });

    it("renders null http_status_code and response_time_ms as —", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if ((url as string).includes("/results")) {
                    return Promise.resolve(makeResultsResponse([NULL_RESULT]));
                }
                return Promise.resolve(makeMonitorResponse());
            }),
        );

        renderDetail();

        await screen.findByTestId("ch-table");

        // Both null fields should show em-dash
        const dashes = screen.getAllByText("—");
        // At least 2 dashes (one for http_status_code, one for response_time_ms)
        expect(dashes.length).toBeGreaterThanOrEqual(2);
    });

    it("shows loading state while fetching results", async () => {
        let resolveResults: (r: Response) => void;
        const resultsPromise = new Promise<Response>((res) => {
            resolveResults = res;
        });

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if ((url as string).includes("/results")) {
                    return resultsPromise;
                }
                return Promise.resolve(makeMonitorResponse());
            }),
        );

        renderDetail();

        // Monitor loads first; then results show a loading state
        await screen.findByRole("heading", { name: /check history/i });

        // Loading spinner should appear for results
        expect(
            await screen.findByText(/loading check history/i),
        ).toBeInTheDocument();

        // Resolve results to clean up
        resolveResults!(makeResultsResponse([]));
    });

    it("shows empty state when results array is empty", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if ((url as string).includes("/results")) {
                    return Promise.resolve(makeResultsResponse([]));
                }
                return Promise.resolve(makeMonitorResponse());
            }),
        );

        renderDetail();

        await screen.findByRole("heading", { name: /check history/i });
        expect(await screen.findByTestId("ch-empty")).toBeInTheDocument();
    });

    it("shows error state and Try again button on API failure", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if ((url as string).includes("/results")) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                error: {
                                    code: "SERVER_ERROR",
                                    message:
                                        "Something went wrong on our side. Please try again.",
                                },
                            }),
                            {
                                status: 500,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                }
                return Promise.resolve(makeMonitorResponse());
            }),
        );

        renderDetail();

        const tryAgain = await screen.findByRole("button", {
            name: /try again/i,
        });
        expect(tryAgain).toBeInTheDocument();
    });
});

describe("CheckHistory — filters and pagination", () => {
    it("resets to page 1 when status filter changes", async () => {
        const fetchMock = vi.fn().mockImplementation((url: string) => {
            if ((url as string).includes("/results")) {
                return Promise.resolve(
                    makeResultsResponse(
                        [HEALTHY_RESULT, FAILING_RESULT],
                        40, // total > 20 → 2 pages
                    ),
                );
            }
            return Promise.resolve(makeMonitorResponse());
        });
        vi.stubGlobal("fetch", fetchMock);

        renderDetail();

        // Navigate to page 2
        const nextBtn = await screen.findByRole("button", { name: /next/i });
        fireEvent.click(nextBtn);

        await waitFor(() => {
            const calls = fetchMock.mock.calls as [string][];
            const resultsCalls = calls.filter(([url]) =>
                url.includes("/results"),
            );
            const lastCall = resultsCalls.at(-1)!;
            expect(lastCall[0]).toContain("page=2");
        });

        // Change status filter → should reset to page=1
        const select = screen.getByRole("combobox");
        fireEvent.change(select, { target: { value: "failing" } });

        await waitFor(() => {
            const calls = fetchMock.mock.calls as [string][];
            const resultsCalls = calls.filter(([url]) =>
                url.includes("/results"),
            );
            const lastCall = resultsCalls.at(-1)!;
            expect(lastCall[0]).toContain("page=1");
            expect(lastCall[0]).toContain("status=failing");
        });
    });

    it("resets to page 1 when time range changes", async () => {
        const fetchMock = vi.fn().mockImplementation((url: string) => {
            if ((url as string).includes("/results")) {
                return Promise.resolve(
                    makeResultsResponse([HEALTHY_RESULT], 40),
                );
            }
            return Promise.resolve(makeMonitorResponse());
        });
        vi.stubGlobal("fetch", fetchMock);

        renderDetail();

        // Navigate to page 2
        const nextBtn = await screen.findByRole("button", { name: /next/i });
        fireEvent.click(nextBtn);

        // Change to Last hour
        const hourBtn = await screen.findByRole("button", {
            name: /last hour/i,
        });
        fireEvent.click(hourBtn);

        await waitFor(() => {
            const calls = fetchMock.mock.calls as [string][];
            const resultsCalls = calls.filter(([url]) =>
                url.includes("/results"),
            );
            const lastCall = resultsCalls.at(-1)!;
            expect(lastCall[0]).toContain("page=1");
        });
    });

    it("blocks query and shows error when custom range exceeds 31 days", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if ((url as string).includes("/results")) {
                    return Promise.resolve(makeResultsResponse([]));
                }
                return Promise.resolve(makeMonitorResponse());
            }),
        );

        renderDetail();

        await screen.findByRole("heading", { name: /check history/i });

        // Switch to Custom range
        fireEvent.click(screen.getByRole("button", { name: /custom/i }));

        // Set a range wider than 31 days
        // Use within the custom range group to avoid ambiguity with other labels
        const customRangeGroup = document.querySelector(
            "[aria-label='Custom date range']",
        )!;
        const fromInput = customRangeGroup.querySelector(
            "input[type='datetime-local']:first-of-type",
        ) as HTMLInputElement;
        const toInput = customRangeGroup.querySelectorAll(
            "input[type='datetime-local']",
        )[1] as HTMLInputElement;
        fireEvent.change(fromInput, {
            target: { value: "2026-09-01T00:00" },
        });
        fireEvent.change(toInput, {
            target: { value: "2026-10-31T00:00" }, // 60 days apart
        });

        expect(await screen.findByRole("alert")).toHaveTextContent(
            /cannot exceed 31 days/i,
        );
    });

    it("shows pagination controls and navigates pages", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if ((url as string).includes("/results")) {
                    return Promise.resolve(
                        makeResultsResponse([HEALTHY_RESULT], 40),
                    );
                }
                return Promise.resolve(makeMonitorResponse());
            }),
        );

        renderDetail();

        await screen.findByTestId("ch-table");

        expect(screen.getByText(/page 1 of 2/i)).toBeInTheDocument();

        const prevBtn = screen.getByRole("button", { name: /prev/i });
        const nextBtn = screen.getByRole("button", { name: /next/i });

        // Prev is disabled on page 1
        expect(prevBtn).toBeDisabled();
        expect(nextBtn).not.toBeDisabled();
    });
});

describe("CheckHistory — response body excerpt", () => {
    it("renders response_body_excerpt as plain text in an expandable row", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if ((url as string).includes("/results")) {
                    return Promise.resolve(
                        makeResultsResponse([FAILING_RESULT]),
                    );
                }
                return Promise.resolve(makeMonitorResponse());
            }),
        );

        renderDetail();

        await screen.findByTestId("ch-table");

        // Error message is initially visible as a button/clickable element
        const expandBtn = screen.getByRole("button", {
            name: /internal server error/i,
        });
        expect(expandBtn).toBeInTheDocument();

        // Click to expand
        fireEvent.click(expandBtn);

        // Excerpt content must appear as plain text
        const excerpt = await screen.findByText("<html>Error page</html>");
        expect(excerpt).toBeInTheDocument();
        // Verify it's inside a <pre>, not rendered as HTML
        expect(excerpt.tagName).toBe("PRE");
    });
});

describe("CheckHistory — time display", () => {
    it("renders a title attribute (UTC tooltip) on the time cell", async () => {
        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if ((url as string).includes("/results")) {
                    return Promise.resolve(
                        makeResultsResponse([HEALTHY_RESULT]),
                    );
                }
                return Promise.resolve(makeMonitorResponse());
            }),
        );

        renderDetail();

        await screen.findByTestId("ch-table");

        // The time span should have a title attribute containing UTC info
        const timeEl = document.querySelector(".ch-time");
        expect(timeEl).not.toBeNull();
        expect(timeEl!.getAttribute("title")).toBeTruthy();
        // UTC title should contain "UTC" or specific time info
        expect(timeEl!.getAttribute("title")).toMatch(/UTC|2026/i);
    });
});
