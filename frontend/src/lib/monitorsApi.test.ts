import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import {
    ApiError,
    createMonitor,
    getMonitor,
    listMonitors,
    updateMonitor,
} from "./monitorsApi";
import type { MonitorPayload } from "./monitors";

describe("monitorsApi", () => {
    beforeEach(() => {
        localStorage.setItem("access_token", "test-token");
        localStorage.setItem("refresh_token", "test-refresh-token");
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    describe("successful requests", () => {
        it("sends Bearer header and correct URL/params for listMonitors", async () => {
            const mockFetch = vi.fn().mockResolvedValue(
                new Response(
                    JSON.stringify({
                        items: [],
                        page: 2,
                        page_size: 20,
                        total: 0,
                    }),
                    {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    },
                ),
            );
            vi.stubGlobal("fetch", mockFetch);

            const result = await listMonitors(2, 20);

            expect(mockFetch).toHaveBeenCalledTimes(1);
            const [url, init] = mockFetch.mock.calls[0] as [
                string,
                RequestInit,
            ];
            expect(url).toContain("/api/v1/monitors?page=2&page_size=20");
            expect(init.method).toBe("GET");
            expect(new Headers(init.headers).get("Authorization")).toBe(
                "Bearer test-token",
            );
            expect(result.page).toBe(2);
        });

        it("sends correct URL for getMonitor", async () => {
            const mockFetch = vi.fn().mockResolvedValue(
                new Response(
                    JSON.stringify({ id: "mon-1", name: "Test API" }),
                    {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    },
                ),
            );
            vi.stubGlobal("fetch", mockFetch);

            const result = await getMonitor("mon-1");

            expect(mockFetch).toHaveBeenCalledTimes(1);
            const [url, init] = mockFetch.mock.calls[0] as [
                string,
                RequestInit,
            ];
            expect(url).toContain("/api/v1/monitors/mon-1");
            expect(init.method).toBe("GET");
            expect(result.id).toBe("mon-1");
        });

        it("sends POST with payload body for createMonitor", async () => {
            const payload: MonitorPayload = {
                name: "New API",
                url: "https://example.com/health",
                method: "GET",
                check_interval_seconds: 60,
                timeout_seconds: 10,
                expected_status_code: 200,
                failure_threshold: 3,
                recovery_threshold: 2,
                enabled: true,
            };

            const mockFetch = vi.fn().mockResolvedValue(
                new Response(JSON.stringify({ id: "mon-new", ...payload }), {
                    status: 201,
                    headers: { "Content-Type": "application/json" },
                }),
            );
            vi.stubGlobal("fetch", mockFetch);

            const result = await createMonitor(payload);

            expect(mockFetch).toHaveBeenCalledTimes(1);
            const [url, init] = mockFetch.mock.calls[0] as [
                string,
                RequestInit,
            ];
            expect(url).toContain("/api/v1/monitors");
            expect(init.method).toBe("POST");
            expect(JSON.parse(init.body as string)).toEqual(payload);
            expect(result.id).toBe("mon-new");
        });

        it("sends PATCH with partial body for updateMonitor", async () => {
            const partial = { name: "Updated Name" };
            const mockFetch = vi.fn().mockResolvedValue(
                new Response(
                    JSON.stringify({ id: "mon-1", name: "Updated Name" }),
                    {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    },
                ),
            );
            vi.stubGlobal("fetch", mockFetch);

            const result = await updateMonitor("mon-1", partial);

            expect(mockFetch).toHaveBeenCalledTimes(1);
            const [url, init] = mockFetch.mock.calls[0] as [
                string,
                RequestInit,
            ];
            expect(url).toContain("/api/v1/monitors/mon-1");
            expect(init.method).toBe("PATCH");
            expect(JSON.parse(init.body as string)).toEqual(partial);
            expect(result.name).toBe("Updated Name");
        });
    });

    describe("401 and token refresh", () => {
        it("401 then successful refresh then retry succeeds", async () => {
            let attempt = 0;
            const mockFetch = vi.fn().mockImplementation((url: string) => {
                if (url.includes("/auth/refresh")) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                access_token: "refreshed-access-token",
                                refresh_token: "refreshed-refresh-token",
                            }),
                            {
                                status: 200,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                }

                attempt++;
                if (attempt === 1) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({ detail: "Token expired" }),
                            {
                                status: 401,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                }

                return Promise.resolve(
                    new Response(
                        JSON.stringify({ id: "mon-1", name: "Success" }),
                        {
                            status: 200,
                            headers: { "Content-Type": "application/json" },
                        },
                    ),
                );
            });
            vi.stubGlobal("fetch", mockFetch);

            const result = await getMonitor("mon-1");

            expect(result.name).toBe("Success");
            expect(localStorage.getItem("access_token")).toBe(
                "refreshed-access-token",
            );
            // Verify retried request sent the new token
            const thirdCall = mockFetch.mock.calls[2] as [string, RequestInit];
            expect(new Headers(thirdCall[1].headers).get("Authorization")).toBe(
                "Bearer refreshed-access-token",
            );
        });

        it("401 with failed refresh clears tokens and throws status 401", async () => {
            const mockFetch = vi.fn().mockImplementation((url: string) => {
                if (url.includes("/auth/refresh")) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({ detail: "Invalid refresh token" }),
                            { status: 401 },
                        ),
                    );
                }
                return Promise.resolve(
                    new Response(JSON.stringify({ detail: "Unauthorized" }), {
                        status: 401,
                    }),
                );
            });
            vi.stubGlobal("fetch", mockFetch);

            await expect(getMonitor("mon-1")).rejects.toMatchObject({
                status: 401,
            });

            expect(localStorage.getItem("access_token")).toBeNull();
            expect(localStorage.getItem("refresh_token")).toBeNull();
        });
    });

    describe("error shapes parsing", () => {
        it("parses 422 validation array shape with loc and strips Value error, prefix", async () => {
            const errorPayload = {
                error: {
                    code: "VALIDATION_ERROR",
                    message: "Request data is invalid.",
                    details: [
                        {
                            loc: ["body", "url"],
                            msg: "Value error, invalid URL scheme",
                            type: "value_error",
                        },
                    ],
                },
            };

            const mockFetch = vi.fn().mockResolvedValue(
                new Response(JSON.stringify(errorPayload), {
                    status: 422,
                    headers: { "Content-Type": "application/json" },
                }),
            );
            vi.stubGlobal("fetch", mockFetch);

            try {
                await getMonitor("mon-1");
                expect.fail("Expected getMonitor to throw");
            } catch (err) {
                expect(err).toBeInstanceOf(ApiError);
                const apiErr = err as ApiError;
                expect(apiErr.status).toBe(422);
                expect(apiErr.code).toBe("VALIDATION_ERROR");
                expect(apiErr.fieldErrors.url).toBe("invalid URL scheme");
            }
        });

        it("parses details object shape and strips Value error,", async () => {
            const errorPayload = {
                error: {
                    code: "CONFLICT",
                    message: "Monitor conflict.",
                    details: {
                        name: "Value error, name already exists",
                    },
                },
            };

            const mockFetch = vi.fn().mockResolvedValue(
                new Response(JSON.stringify(errorPayload), {
                    status: 409,
                    headers: { "Content-Type": "application/json" },
                }),
            );
            vi.stubGlobal("fetch", mockFetch);

            try {
                await getMonitor("mon-1");
                expect.fail("Expected getMonitor to throw");
            } catch (err) {
                expect(err).toBeInstanceOf(ApiError);
                const apiErr = err as ApiError;
                expect(apiErr.status).toBe(409);
                expect(apiErr.code).toBe("CONFLICT");
                expect(apiErr.message).toBe("Monitor conflict.");
                expect(apiErr.fieldErrors.name).toBe("name already exists");
            }
        });

        it("parses FastAPI default detail string and detail array shapes", async () => {
            // Test detail string
            const mockFetchString = vi.fn().mockResolvedValue(
                new Response(
                    JSON.stringify({
                        detail: "Value error, bad request detail",
                    }),
                    {
                        status: 400,
                        headers: { "Content-Type": "application/json" },
                    },
                ),
            );
            vi.stubGlobal("fetch", mockFetchString);

            try {
                await getMonitor("mon-1");
                expect.fail("Expected getMonitor to throw");
            } catch (err) {
                expect(err).toBeInstanceOf(ApiError);
                const apiErr = err as ApiError;
                expect(apiErr.status).toBe(400);
                expect(apiErr.message).toBe("bad request detail");
            }

            // Test detail array
            const mockFetchArray = vi.fn().mockResolvedValue(
                new Response(
                    JSON.stringify({
                        detail: [
                            {
                                loc: ["body", "check_interval_seconds"],
                                msg: "Value error, interval too small",
                            },
                        ],
                    }),
                    {
                        status: 422,
                        headers: { "Content-Type": "application/json" },
                    },
                ),
            );
            vi.stubGlobal("fetch", mockFetchArray);

            try {
                await getMonitor("mon-1");
                expect.fail("Expected getMonitor to throw");
            } catch (err) {
                expect(err).toBeInstanceOf(ApiError);
                const apiErr = err as ApiError;
                expect(apiErr.status).toBe(422);
                expect(apiErr.fieldErrors.check_interval_seconds).toBe(
                    "interval too small",
                );
            }
        });

        it("non-JSON error body and rejected fetch give fallback messages", async () => {
            // 403 non-JSON
            vi.stubGlobal(
                "fetch",
                vi
                    .fn()
                    .mockResolvedValue(
                        new Response("Forbidden text", { status: 403 }),
                    ),
            );
            await expect(getMonitor("mon-1")).rejects.toMatchObject({
                status: 403,
                message: "You don't have permission to do that.",
            });

            // 404 non-JSON
            vi.stubGlobal(
                "fetch",
                vi
                    .fn()
                    .mockResolvedValue(
                        new Response("Not Found", { status: 404 }),
                    ),
            );
            await expect(getMonitor("mon-1")).rejects.toMatchObject({
                status: 404,
                message: "Monitor not found.",
            });

            // 502 non-JSON
            vi.stubGlobal(
                "fetch",
                vi.fn().mockResolvedValue(
                    new Response("<html>Bad Gateway</html>", {
                        status: 502,
                    }),
                ),
            );
            await expect(getMonitor("mon-1")).rejects.toMatchObject({
                status: 502,
                message: "Something went wrong on our side. Please try again.",
            });

            // Rejected fetch (network down)
            vi.stubGlobal(
                "fetch",
                vi.fn().mockRejectedValue(new TypeError("Failed to fetch")),
            );
            await expect(getMonitor("mon-1")).rejects.toMatchObject({
                status: 0,
                message:
                    "Could not reach the server. Check your connection and try again.",
            });
        });
    });
});
