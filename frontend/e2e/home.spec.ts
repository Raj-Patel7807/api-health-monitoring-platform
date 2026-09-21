import { expect, test } from "@playwright/test";

test("shows the foundation page", async ({ page }) => {
    await page.goto("/");
    await expect(
        page.getByRole("heading", { name: "API Health Monitor" }),
    ).toBeVisible();
});
