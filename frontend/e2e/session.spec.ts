import { expect, test } from "@playwright/test";

test("a returning browser renews its login and can explicitly log out", async ({
    playwright,
    baseURL,
    channel,
}, testInfo) => {
    const profile = testInfo.outputPath("profile");
    let accessToken = "first-access";
    let logins = 0;
    let renewals = 0;

    async function openBrowser() {
        const context = await playwright.chromium.launchPersistentContext(
            profile,
            {
                baseURL,
                channel,
                headless: true,
                serviceWorkers: "block",
            },
        );
        await context.route("**/api/v1/**", async (route) => {
            const request = route.request();
            const path = new URL(request.url()).pathname;
            if (path.endsWith("/auth/login")) {
                logins++;
                return route.fulfill({
                    json: {
                        access_token: accessToken,
                        refresh_token: "refresh",
                    },
                });
            }
            if (path.endsWith("/auth/refresh")) {
                expect(request.postDataJSON()).toEqual({
                    refresh_token: "refresh",
                });
                renewals++;
                return route.fulfill({
                    json: {
                        access_token: accessToken,
                        refresh_token: "renewed-refresh",
                    },
                });
            }
            if (request.headers().authorization !== `Bearer ${accessToken}`) {
                return route.fulfill({
                    status: 401,
                    json: { detail: "Expired" },
                });
            }
            if (path.endsWith("/auth/me"))
                return route.fulfill({ json: { team: { role: "admin" } } });
            const items = path.endsWith("/monitors")
                ? [
                      {
                          id: "sample",
                          name: "Session test monitor",
                          url: "https://example.com",
                          enabled: true,
                      },
                  ]
                : [];
            return route.fulfill({
                json: { items, total: items.length, page: 1 },
            });
        });
        return context;
    }

    let context = await openBrowser();
    try {
        const page = await context.newPage();
        await page.goto("/login");
        await page.getByLabel("Email").fill("session@example.test");
        await page.getByLabel("Password").fill("synthetic-password");
        await page.getByRole("button", { name: "Log in" }).click();
        await expect(page.getByText("Session test monitor")).toBeVisible();
    } finally {
        await context.close();
    }

    accessToken = "renewed-access";
    context = await openBrowser();
    try {
        const page = await context.newPage();
        for (const path of ["/", "/login", "/signup"]) {
            await page.goto(path);
            await expect(page).toHaveURL(/\/dashboard$/);
            await expect(page.getByText("Session test monitor")).toBeVisible();
        }
        expect(logins).toBe(1);
        expect(renewals).toBe(1);
        const otherTab = await context.newPage();
        await otherTab.goto("/dashboard");
        await expect(otherTab.getByText("Session test monitor")).toBeVisible();
        await page.getByRole("button", { name: "Log out" }).click();
        await expect(page).toHaveURL(/\/login$/);
        await expect(otherTab).toHaveURL(/\/login$/);
        await page.goto("/dashboard");
        await expect(page.getByLabel("Password")).toBeVisible();
        expect(logins).toBe(1);
    } finally {
        await context.close();
    }
});
