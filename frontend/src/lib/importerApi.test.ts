import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
    CandidateMonitor,
    commitImportedMonitors,
    ImporterApiError,
    previewApiDocs,
} from "./importerApi";

describe("importerApi", () => {
    beforeEach(() => {
        localStorage.setItem("access_token", "test-token");
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    describe("previewApiDocs", () => {
        it("uploads file and returns discovered candidates", async () => {
            const mockPreview = {
                filename: "api.md",
                total_found: 1,
                valid_count: 1,
                items: [
                    {
                        name: "GET /api/v1/health",
                        url: "https://api.example.com/api/v1/health",
                        method: "GET" as const,
                        expected_status_code: 200,
                        check_interval_seconds: 30,
                        timeout_seconds: 10,
                        failure_threshold: 3,
                        recovery_threshold: 2,
                        is_valid: true,
                    },
                ],
            };

            const fetchMock = vi.fn(
                async () =>
                    new Response(JSON.stringify(mockPreview), {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    }),
            );
            vi.stubGlobal("fetch", fetchMock);

            const file = new File(["# API\n### GET /api/v1/health"], "api.md", {
                type: "text/markdown",
            });
            const result = await previewApiDocs(
                file,
                "https://api.example.com",
            );

            expect(result).toEqual(mockPreview);
            expect(fetchMock).toHaveBeenCalledTimes(1);
        });

        it("throws ImporterApiError with detail on 413 or 400 failure", async () => {
            const fetchMock = vi.fn(
                async () =>
                    new Response(
                        JSON.stringify({
                            detail: "File size exceeds the 2MB limit.",
                        }),
                        {
                            status: 413,
                            headers: { "Content-Type": "application/json" },
                        },
                    ),
            );
            vi.stubGlobal("fetch", fetchMock);

            const file = new File(["huge content"], "huge.md", {
                type: "text/markdown",
            });
            await expect(previewApiDocs(file)).rejects.toThrow(
                ImporterApiError,
            );
        });
    });

    describe("commitImportedMonitors", () => {
        it("sends candidates payload and returns imported monitor IDs", async () => {
            const candidates: CandidateMonitor[] = [
                {
                    name: "Checkout API",
                    url: "https://api.example.com/checkout",
                    method: "POST",
                    expected_status_code: 201,
                    check_interval_seconds: 60,
                    timeout_seconds: 5,
                    failure_threshold: 3,
                    recovery_threshold: 2,
                    is_valid: true,
                },
            ];

            const mockCommit = {
                imported_count: 1,
                monitor_ids: ["m-100"],
            };

            const fetchMock = vi.fn(
                async () =>
                    new Response(JSON.stringify(mockCommit), {
                        status: 201,
                        headers: { "Content-Type": "application/json" },
                    }),
            );
            vi.stubGlobal("fetch", fetchMock);

            const result = await commitImportedMonitors(
                candidates,
                "https://api.example.com",
            );
            expect(result).toEqual(mockCommit);
            expect(fetchMock).toHaveBeenCalledTimes(1);
        });

        it("throws ImporterApiError on 400 rejection", async () => {
            const fetchMock = vi.fn(
                async () =>
                    new Response(
                        JSON.stringify({
                            detail: "Target URL is not permitted.",
                        }),
                        {
                            status: 400,
                            headers: { "Content-Type": "application/json" },
                        },
                    ),
            );
            vi.stubGlobal("fetch", fetchMock);

            await expect(commitImportedMonitors([])).rejects.toThrow(
                "Target URL is not permitted.",
            );
        });
    });
});
