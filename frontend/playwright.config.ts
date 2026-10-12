import { defineConfig, devices } from "@playwright/test";

export default defineConfig({
    testDir: "./e2e",
    forbidOnly: !!process.env.CI,
    workers: process.env.CI ? 1 : undefined,
    reporter: process.env.CI ? [["list"], ["html", { open: "never" }]] : "list",
    use: {
        baseURL: "http://127.0.0.1:4173",
        trace: "retain-on-failure",
        screenshot: "only-on-failure",
    },
    webServer: {
        command: "npm run preview -- --host 127.0.0.1",
        port: 4173,
        reuseExistingServer: !process.env.CI,
    },
    projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
});
