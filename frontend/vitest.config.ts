import { defineConfig } from "vitest/config";

export default defineConfig({
    test: {
        environment: "jsdom",
        globals: true,
        exclude: ["e2e/**", "node_modules/**"],
        setupFiles: ["./src/test/setup.ts"],
        coverage: {
            provider: "v8",
            reporter: ["text", "json", "html"],
            exclude: [
                "e2e/**",
                "node_modules/**",
                "**/*.css",
                "src/mocks/**",
                "src/test/**",
                "dist/**",
            ],
        },
    },
});
