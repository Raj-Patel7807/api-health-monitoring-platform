/**
 * E2E tests for Role-Based Access Control (RBAC) and Team Members (US-19 / Task F2).
 *
 * Acceptance criteria covered:
 * 1. Admin signs up → redirected to /monitors with full edit controls.
 * 2. Admin adds a monitor → appears in list with Edit and Delete controls.
 * 3. Admin visits /members → adds second user (readonly@test.com) as read_only.
 * 4. User logs in as that second user (read_only).
 * 5. read_only user sees no Add, Edit, or Delete controls on monitors, and no Members link in nav.
 * 6. Direct visit to /members as read_only is blocked with "Access Denied" page.
 */

import { expect, test, type Route } from "@playwright/test";

const ADMIN_TOKEN = "e2e-token-admin";
const READONLY_TOKEN = "e2e-token-readonly";

test("RBAC flow: admin signup → add monitor → add read_only member → login as read_only → verify controls hidden and /members blocked", async ({
    page,
}) => {
    let currentUser: "admin" | "read_only" = "admin";
    const monitors: Array<Record<string, unknown>> = [];
    const members: Array<Record<string, unknown>> = [
        {
            user_id: "user-admin",
            full_name: "Admin User",
            email: "admin@test.com",
            role: "admin",
            joined_at: new Date().toISOString(),
        },
    ];

    // Mock API endpoints
    await page.route("**/api/v1/auth/signup", async (route: Route) => {
        currentUser = "admin";
        await route.fulfill({
            status: 201,
            contentType: "application/json",
            body: JSON.stringify({
                user: {
                    id: "user-admin",
                    email: "admin@test.com",
                    full_name: "Admin User",
                },
                team: { id: "team-1", name: "Engineering", role: "admin" },
                access_token: ADMIN_TOKEN,
                refresh_token: ADMIN_TOKEN,
            }),
        });
    });

    await page.route("**/api/v1/auth/login", async (route: Route) => {
        const body = JSON.parse(route.request().postData() ?? "{}");
        if (body.email === "readonly@test.com") {
            currentUser = "read_only";
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    access_token: READONLY_TOKEN,
                    refresh_token: READONLY_TOKEN,
                }),
            });
        } else {
            currentUser = "admin";
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    access_token: ADMIN_TOKEN,
                    refresh_token: ADMIN_TOKEN,
                }),
            });
        }
    });

    await page.route("**/api/v1/auth/me", async (route: Route) => {
        if (currentUser === "read_only") {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    id: "user-readonly",
                    email: "readonly@test.com",
                    full_name: "Read Only User",
                    is_active: true,
                    created_at: new Date().toISOString(),
                    team: {
                        id: "team-1",
                        name: "Engineering",
                        role: "read_only",
                    },
                }),
            });
        } else {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    id: "user-admin",
                    email: "admin@test.com",
                    full_name: "Admin User",
                    is_active: true,
                    created_at: new Date().toISOString(),
                    team: {
                        id: "team-1",
                        name: "Engineering",
                        role: "admin",
                    },
                }),
            });
        }
    });

    await page.route(/\/api\/v1\/monitors(\?.*)?$/, async (route: Route) => {
        if (route.request().method() === "GET") {
            await route.fulfill({
                status: 200,
                contentType: "application/json",
                body: JSON.stringify({
                    items: monitors,
                    page: 1,
                    page_size: 20,
                    total: monitors.length,
                }),
            });
        } else if (route.request().method() === "POST") {
            const body = JSON.parse(route.request().postData() ?? "{}");
            const newMon = {
                id: "mon-e2e-1",
                name: body.name ?? "Production Service",
                url: body.url ?? "https://service.example.com",
                method: body.method ?? "GET",
                enabled: body.enabled ?? true,
                check_interval_seconds: body.check_interval_seconds ?? 60,
                timeout_seconds: body.timeout_seconds ?? 10,
                expected_status_code: body.expected_status_code ?? 200,
                created_at: new Date().toISOString(),
            };
            monitors.push(newMon);
            await route.fulfill({
                status: 201,
                contentType: "application/json",
                body: JSON.stringify(newMon),
            });
        } else {
            await route.continue();
        }
    });

    await page.route(/\/api\/v1\/team\/members(\?.*)?$/, async (route: Route) => {
        if (route.request().method() === "GET") {
            if (currentUser === "read_only") {
                await route.fulfill({
                    status: 403,
                    contentType: "application/json",
                    body: JSON.stringify({
                        detail: "Forbidden: insufficient permissions.",
                    }),
                });
            } else {
                await route.fulfill({
                    status: 200,
                    contentType: "application/json",
                    body: JSON.stringify({
                        items: members,
                        total: members.length,
                    }),
                });
            }
        } else if (route.request().method() === "POST") {
            const body = JSON.parse(route.request().postData() ?? "{}");
            const newMember = {
                user_id: "user-readonly",
                full_name: "Read Only User",
                email: body.email,
                role: body.role,
                joined_at: new Date().toISOString(),
            };
            members.push(newMember);
            await route.fulfill({
                status: 201,
                contentType: "application/json",
                body: JSON.stringify(newMember),
            });
        } else {
            await route.continue();
        }
    });

    /* ── 1. Admin signs up ── */
    await page.goto("/signup");
    await expect(
        page.getByRole("heading", { name: "Create your account" }),
    ).toBeVisible();

    await page.fill("#signup-name", "Admin User");
    await page.fill("#signup-email", "admin@test.com");
    await page.fill("#signup-password", "password123");
    await page.fill("#signup-team", "Engineering");
    await page.click('button[type="submit"]');

    await page.waitForURL("**/monitors", { timeout: 10_000 });
    await expect(
        page.getByRole("heading", { name: "Monitors", exact: true }),
    ).toBeVisible();

    // Verify admin sees Add monitor button and Members link
    await expect(page.locator('[data-testid="add-monitor-btn"]')).toBeVisible();
    await expect(page.locator('[data-testid="nav-members-link"]')).toBeVisible();

    /* ── 2. Admin adds a monitor ── */
    await page.click('[data-testid="add-monitor-btn"]');
    await page.waitForURL("**/monitors/new", { timeout: 5_000 });
    await expect(
        page.getByRole("heading", { name: "Add monitor" }),
    ).toBeVisible();

    await page.fill("#monitor-name", "Production Service");
    await page.fill("#monitor-url", "https://service.example.com");
    await page.click('button[type="submit"]');

    await page.waitForURL("**/monitors", { timeout: 10_000 });
    await expect(
        page.getByRole("link", { name: "Production Service", exact: true }),
    ).toBeVisible();

    // Admin sees Edit link and Delete button
    await expect(
        page.getByRole("link", { name: "Edit Production Service" }),
    ).toBeVisible();
    await expect(
        page.locator('[data-testid="delete-mon-e2e-1"]'),
    ).toBeVisible();

    /* ── 3. Admin visits /members and adds second user as read_only ── */
    await page.click('[data-testid="nav-members-link"]');
    await page.waitForURL("**/members", { timeout: 5_000 });
    await expect(
        page.getByRole("heading", { name: "Team Members", exact: true }),
    ).toBeVisible();
    await expect(
        page.getByRole("heading", { name: "Add a team member" }),
    ).toBeVisible();

    await page.fill("#member-email", "readonly@test.com");
    await page.selectOption("#member-role", "read_only");
    await page.click('[data-testid="add-member-btn"]');

    // Wait for the member to be listed
    await expect(page.getByText("readonly@test.com")).toBeVisible();

    /* ── 4. Log in as second user (read_only) ── */
    await page.goto("/login");
    await expect(
        page.getByRole("heading", { name: "Welcome back" }),
    ).toBeVisible();

    await page.fill("#login-email", "readonly@test.com");
    await page.fill("#login-password", "password123");
    await page.click('button[type="submit"]');

    // Login redirects to /dashboard; navigate to /monitors to inspect controls
    await page.waitForURL("**/dashboard", { timeout: 10_000 });
    await page.goto("/monitors");
    await page.waitForURL("**/monitors", { timeout: 10_000 });
    await expect(
        page.getByRole("heading", { name: "Monitors", exact: true }),
    ).toBeVisible();

    /* ── 5. Verify read_only sees no edit controls on monitors ── */
    // Monitor row is visible
    await expect(
        page.getByRole("link", { name: "Production Service", exact: true }),
    ).toBeVisible();

    // Add monitor button is NOT visible
    await expect(
        page.locator('[data-testid="add-monitor-btn"]'),
    ).not.toBeVisible();

    // Edit link and Delete button are NOT visible
    await expect(
        page.getByRole("link", { name: "Edit Production Service" }),
    ).not.toBeVisible();
    await expect(
        page.locator('[data-testid="delete-mon-e2e-1"]'),
    ).not.toBeVisible();

    // Actions column is NOT visible
    await expect(page.getByRole("columnheader", { name: "Actions" })).not.toBeVisible();

    // Members link in AppNav is NOT visible
    await expect(
        page.locator('[data-testid="nav-members-link"]'),
    ).not.toBeVisible();

    /* ── 6. Direct visit to /members as read_only shows "Access Denied" ── */
    await page.goto("/members");
    await expect(
        page.getByRole("heading", { name: "Access Denied" }),
    ).toBeVisible();
    await expect(
        page.getByText(/You do not have permission to view or manage team members/i),
    ).toBeVisible();
    await expect(
        page.getByRole("link", { name: "Back to monitors" }),
    ).toBeVisible();
});
