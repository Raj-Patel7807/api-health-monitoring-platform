/**
 * E2E smoke test — signup → add monitor (US-02)
 *
 * Strategy: the test runs against the preview build (vite preview).
 * The backend API is mocked via Playwright route interception so the test
 * is self-contained and deterministic (no live server required).
 *
 * Covered assertions:
 *  1. Signup form submits → user is redirected to /monitors
 *  2. Monitors page renders correctly with "Add monitor" button
 *  3. Monitor form is filled and submitted → list shows the new monitor
 *  4. Clicking the monitor name navigates to the detail page
 *  5. Detail page shows status, next_check_at, failure counts, and backoff
 */

import { expect, test, type Page, type Route } from "@playwright/test";

/* ── Shared fixture data ─────────────────────────────────────────────────── */

const FAKE_TOKEN =
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9" +
    ".eyJzdWIiOiJ1c2VyLTEiLCJleHAiOjk5OTk5OTk5OTl9" +
    ".fake_signature";

const MONITOR_ID = "mon-e2e-001";

const MONITOR_DETAIL = {
    id: MONITOR_ID,
    name: "Payment API",
    url: "https://api.example.com/health",
    method: "GET",
    enabled: true,
    check_interval_seconds: 60,
    timeout_seconds: 10,
    expected_status_code: 200,
    created_at: "2026-10-01T10:00:00Z",
    // Detail-only fields (US-02 "Done when" criteria)
    consecutive_failures: 2,
    consecutive_successes: 0,
    failure_threshold: 3,
    recovery_threshold: 2,
    next_check_at: new Date(Date.now() + 45_000).toISOString(), // ~45 s from now
    backoff_until: new Date(Date.now() + 120_000).toISOString(), // 2 min backoff
};

/* ── Route mock helper ───────────────────────────────────────────────────── */

async function mockApi(page: Page) {
    // POST /auth/signup → 201 with tokens
    await page.route("**/api/v1/auth/signup", async (route: Route) => {
        await route.fulfill({
            status: 201,
            contentType: "application/json",
            body: JSON.stringify({
                user: {
                    id: "user-1",
                    email: "e2e@test.com",
                    full_name: "E2E User",
                },
                team: { id: "team-1", name: "E2E Team" },
                access_token: FAKE_TOKEN,
                refresh_token: FAKE_TOKEN,
            }),
        });
    });

    // POST /auth/login (fallback if needed)
    await page.route("**/api/v1/auth/login", async (route: Route) => {
        await route.fulfill({
            status: 200,
            contentType: "application/json",
            body: JSON.stringify({
                access_token: FAKE_TOKEN,
                refresh_token: FAKE_TOKEN,
            }),
        });
    });

    // GET /monitors (list — initially empty, then one item)
    let monitorCreated = false;
    await page.route(/\/api\/v1\/monitors(\?.*)?$/, async (route: Route) => {
        if (route.request().method() === "GET") {
            const items = monitorCreated ? [MONITOR_DETAIL] : [];
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    items,
                    page: 1,
                    page_size: 20,
                    total: items.length,
                }),
            });
        } else if (route.request().method() === "POST") {
            // POST /monitors → 201
            monitorCreated = true;
            await route.fulfill({
                status: 201,
                contentType: "application/json",
                body: JSON.stringify(MONITOR_DETAIL),
            });
        } else {
            await route.continue();
        }
    });

    // GET /monitors/:id (detail)
    await page.route(
        `**/api/v1/monitors/${MONITOR_ID}`,
        async (route: Route) => {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify(MONITOR_DETAIL),
            });
        },
    );
}

/* ── Test ────────────────────────────────────────────────────────────────── */

test("signup → add monitor → detail page shows status, next_check_at, failure counts and backoff", async ({
    page,
}) => {
    await mockApi(page);

    /* ── 1. Navigate to signup ── */
    await page.goto("/signup");
    await expect(
        page.getByRole("heading", { name: "Create your account" }),
    ).toBeVisible();

    /* ── 2. Fill signup form ── */
    await page.fill("#signup-name", "E2E User");
    await page.fill("#signup-email", "e2e@test.com");
    await page.fill("#signup-password", "password123");
    await page.fill("#signup-team", "E2E Team");

    /* ── 3. Submit and wait for redirect to /monitors ── */
    await page.click('button[type="submit"]');
    await page.waitForURL("**/monitors", { timeout: 10_000 });
    await expect(
        page.getByRole("heading", { name: "Monitors", exact: true }),
    ).toBeVisible();

    /* ── 4. Navigate to Add monitor form ── */
    await page.click('[data-testid="add-monitor-btn"]');
    await page.waitForURL("**/monitors/new", { timeout: 5_000 });
    await expect(
        page.getByRole("heading", { name: "Add monitor" }),
    ).toBeVisible();

    /* ── 5. Fill the monitor form ── */
    await page.fill("#monitor-name", "Payment API");
    await page.fill("#monitor-url", "https://api.example.com/health");
    // Method select defaults to GET — leave it
    await page.fill("#monitor-expected-status", "200");
    await page.fill("#monitor-check-interval", "60");
    await page.fill("#monitor-timeout", "10");
    await page.fill("#monitor-failure-threshold", "3");
    await page.fill("#monitor-recovery-threshold", "2");

    /* ── 6. Submit the form and wait for redirect back to /monitors ── */
    await page.click('button[type="submit"]');
    await page.waitForURL("**/monitors", { timeout: 10_000 });

    /* ── 7. Monitors list shows the new monitor ── */
    await expect(
        page.getByRole("link", { name: "Payment API", exact: true }),
    ).toBeVisible();

    /* ── 8. Click through to the detail page ── */
    await page.getByRole("link", { name: "Payment API", exact: true }).click();
    await page.waitForURL(`**/monitors/${MONITOR_ID}`, { timeout: 5_000 });

    /* ── 9. Detail page: verify status chip ── */
    await expect(page.getByText("Backing off")).toBeVisible();

    /* ── 10. Detail page: verify next_check_at is shown ── */
    // The formatted date text appears inside the runtime status card
    await expect(
        page.getByRole("region", { name: /runtime status/i }),
    ).toContainText("Next check");

    /* ── 11. Detail page: failure counter shows consecutive_failures = 2 ── */
    await expect(page.getByTestId("consecutive-failures")).toHaveText("2");
    await expect(page.getByTestId("consecutive-successes")).toHaveText("0");

    /* ── 12. Detail page: backoff section is shown ── */
    await expect(
        page.getByRole("region", { name: /runtime status/i }),
    ).toContainText("Backoff until");
    // The backoff timestamp should be rendered (not the "—" placeholder)
    const backoffRow = page
        .getByRole("region", { name: /runtime status/i })
        .locator(".detail-row", { hasText: "Backoff until" });
    await expect(backoffRow).not.toContainText("—");
});
