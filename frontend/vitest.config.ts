import { defineConfig } from "vitest/config";

export default defineConfig({
    test: {
        environment: "jsdom",
        globals: true,
        exclude: ["e2e/**", "node_modules/**"],
        setupFiles: ["./src/test/setup.ts"],
    },
});
