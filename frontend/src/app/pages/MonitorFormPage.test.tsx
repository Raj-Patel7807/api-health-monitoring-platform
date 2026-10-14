import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { App } from "../App";

function renderApp(initialEntry = "/monitors/new") {
    const client = new QueryClient({
        defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
        },
    });
    return render(
        <QueryClientProvider client={client}>
            <MemoryRouter initialEntries={[initialEntry]}>
                <App />
            </MemoryRouter>
        </QueryClientProvider>,
    );
}

describe("MonitorFormPage", () => {
    beforeEach(() => {
        localStorage.setItem("access_token", "test-token");
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    describe("Create mode", () => {
        it("shows validation messages for bad input and does NOT call the API", async () => {
            const mockFetch = vi.fn();
            vi.stubGlobal("fetch", mockFetch);

            renderApp("/monitors/new");

            expect(
                screen.getByRole("heading", { name: "Add monitor" }),
            ).toBeInTheDocument();

            const submitBtn = screen.getByRole("button", {
                name: "Create monitor",
            });
            fireEvent.click(submitBtn);

            expect(
                await screen.findByText("Name is required."),
            ).toBeInTheDocument();
            expect(screen.getByText("URL is required.")).toBeInTheDocument();
            expect(mockFetch).not.toHaveBeenCalled();
        });

        it("valid submit sends exact POST body with numeric values and navigates to /monitors", async () => {
            const mockFetch = vi
                .fn()
                .mockImplementation((url: string, init?: RequestInit) => {
                    if (
                        url.includes("/api/v1/monitors") &&
                        init?.method === "POST"
                    ) {
                        return Promise.resolve(
                            new Response(
                                JSON.stringify({
                                    id: "new-mon",
                                    name: "Payment API",
                                    url: "https://api.example.com/health",
                                    method: "GET",
                                    enabled: true,
                                    check_interval_seconds: 60,
                                    timeout_seconds: 10,
                                    expected_status_code: 200,
                                    failure_threshold: 3,
                                    recovery_threshold: 2,
                                    created_at: "2026-10-01T10:00:00Z",
                                }),
                                {
                                    status: 201,
                                    headers: {
                                        "Content-Type": "application/json",
                                    },
                                },
                            ),
                        );
                    }
                    // List monitors call after navigation
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                items: [],
                                page: 1,
                                page_size: 20,
                                total: 0,
                            }),
                            {
                                status: 200,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                });
            vi.stubGlobal("fetch", mockFetch);

            renderApp("/monitors/new");

            fireEvent.change(screen.getByLabelText("Name"), {
                target: { value: "Payment API" },
            });
            fireEvent.change(screen.getByLabelText("URL"), {
                target: { value: "https://api.example.com/health" },
            });

            const submitBtn = screen.getByRole("button", {
                name: "Create monitor",
            });
            fireEvent.click(submitBtn);

            expect(
                await screen.findByRole("heading", { name: "Monitors" }),
            ).toBeInTheDocument();

            // Verify POST request body
            const postCall = mockFetch.mock.calls.find(
                (call: unknown[]) =>
                    typeof call[0] === "string" &&
                    call[0].endsWith("/api/v1/monitors") &&
                    (call[1] as RequestInit | undefined)?.method === "POST",
            );
            expect(postCall).toBeDefined();
            const body = JSON.parse(
                (postCall![1] as RequestInit).body as string,
            );
            expect(body).toEqual({
                name: "Payment API",
                url: "https://api.example.com/health",
                method: "GET",
                check_interval_seconds: 60,
                timeout_seconds: 10,
                expected_status_code: 200,
                failure_threshold: 3,
                recovery_threshold: 2,
                enabled: true,
            });
        });

        it("submit button is disabled and relabelled while saving", async () => {
            let resolvePost: (res: Response) => void;
            const postPromise = new Promise<Response>((resolve) => {
                resolvePost = resolve;
            });

            const mockFetch = vi
                .fn()
                .mockImplementation((url: string, init?: RequestInit) => {
                    if (
                        url.includes("/api/v1/monitors") &&
                        init?.method === "POST"
                    ) {
                        return postPromise;
                    }
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                items: [],
                                page: 1,
                                page_size: 20,
                                total: 0,
                            }),
                            {
                                status: 200,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                });
            vi.stubGlobal("fetch", mockFetch);

            renderApp("/monitors/new");

            fireEvent.change(screen.getByLabelText("Name"), {
                target: { value: "Delayed API" },
            });
            fireEvent.change(screen.getByLabelText("URL"), {
                target: { value: "https://delayed.example.com" },
            });

            const submitBtn = screen.getByRole("button", {
                name: "Create monitor",
            });
            fireEvent.click(submitBtn);

            expect(
                await screen.findByRole("button", { name: "Creating..." }),
            ).toBeDisabled();

            resolvePost!(
                new Response(
                    JSON.stringify({
                        id: "mon-del",
                        name: "Delayed API",
                        url: "https://delayed.example.com",
                    }),
                    {
                        status: 201,
                        headers: { "Content-Type": "application/json" },
                    },
                ),
            );

            expect(
                await screen.findByRole("heading", { name: "Monitors" }),
            ).toBeInTheDocument();
        });

        it("server field errors (422) appear next to the right field with aria-invalid", async () => {
            const mockFetch = vi.fn().mockResolvedValue(
                new Response(
                    JSON.stringify({
                        error: {
                            code: "VALIDATION_ERROR",
                            message: "Request data is invalid.",
                            details: [
                                {
                                    loc: ["body", "url"],
                                    msg: "Value error, Host is not reachable",
                                    type: "value_error",
                                },
                            ],
                        },
                    }),
                    {
                        status: 422,
                        headers: { "Content-Type": "application/json" },
                    },
                ),
            );
            vi.stubGlobal("fetch", mockFetch);

            renderApp("/monitors/new");

            fireEvent.change(screen.getByLabelText("Name"), {
                target: { value: "Test API" },
            });
            fireEvent.change(screen.getByLabelText("URL"), {
                target: { value: "https://unreachable.example.com" },
            });

            fireEvent.click(
                screen.getByRole("button", { name: "Create monitor" }),
            );

            const urlInput = await screen.findByLabelText("URL");
            expect(urlInput).toHaveAttribute("aria-invalid", "true");
            expect(
                await screen.findByText("Host is not reachable"),
            ).toBeInTheDocument();
        });

        it("unmapped server error appears in form-level alert", async () => {
            const mockFetch = vi.fn().mockResolvedValue(
                new Response(
                    JSON.stringify({
                        error: {
                            code: "VALIDATION_ERROR",
                            message: "Request data is invalid.",
                            details: [
                                {
                                    loc: ["body", "unmapped_rule"],
                                    msg: "Value error, Custom quota exceeded.",
                                    type: "value_error",
                                },
                            ],
                        },
                    }),
                    {
                        status: 422,
                        headers: { "Content-Type": "application/json" },
                    },
                ),
            );
            vi.stubGlobal("fetch", mockFetch);

            renderApp("/monitors/new");

            fireEvent.change(screen.getByLabelText("Name"), {
                target: { value: "Quota API" },
            });
            fireEvent.change(screen.getByLabelText("URL"), {
                target: { value: "https://example.com" },
            });

            fireEvent.click(
                screen.getByRole("button", { name: "Create monitor" }),
            );

            const alert = await screen.findByRole("alert");
            expect(alert).toHaveTextContent("Custom quota exceeded.");
        });

        it("403 shows permission message in form-level alert", async () => {
            const mockFetch = vi.fn().mockResolvedValue(
                new Response(
                    JSON.stringify({
                        error: {
                            code: "forbidden",
                            message: "You don't have permission to do that.",
                        },
                    }),
                    {
                        status: 403,
                        headers: { "Content-Type": "application/json" },
                    },
                ),
            );
            vi.stubGlobal("fetch", mockFetch);

            renderApp("/monitors/new");

            fireEvent.change(screen.getByLabelText("Name"), {
                target: { value: "Forbidden API" },
            });
            fireEvent.change(screen.getByLabelText("URL"), {
                target: { value: "https://example.com" },
            });

            fireEvent.click(
                screen.getByRole("button", { name: "Create monitor" }),
            );

            const alert = await screen.findByRole("alert");
            expect(alert).toHaveTextContent(
                "You don't have permission to do that.",
            );
        });

        it("network failure shows connection message in form-level alert", async () => {
            const mockFetch = vi
                .fn()
                .mockRejectedValue(new TypeError("Failed to fetch"));
            vi.stubGlobal("fetch", mockFetch);

            renderApp("/monitors/new");

            fireEvent.change(screen.getByLabelText("Name"), {
                target: { value: "Offline API" },
            });
            fireEvent.change(screen.getByLabelText("URL"), {
                target: { value: "https://example.com" },
            });

            fireEvent.click(
                screen.getByRole("button", { name: "Create monitor" }),
            );

            const alert = await screen.findByRole("alert");
            expect(alert).toHaveTextContent(
                "Could not reach the server. Check your connection and try again.",
            );
        });
    });

    describe("Edit mode", () => {
        const existingMonitor = {
            id: "mon-edit-1",
            name: "Original Name",
            url: "https://original.example.com/health",
            method: "GET",
            enabled: true,
            check_interval_seconds: 60,
            timeout_seconds: 10,
            expected_status_code: 200,
            failure_threshold: 3,
            recovery_threshold: 2,
            created_at: "2026-10-01T10:00:00Z",
        };

        it("prefills from GET, and changing only name sends PATCH containing only name", async () => {
            const mockFetch = vi
                .fn()
                .mockImplementation((url: string, init?: RequestInit) => {
                    if (url.includes("/api/v1/monitors/mon-edit-1")) {
                        if (init?.method === "PATCH") {
                            return Promise.resolve(
                                new Response(
                                    JSON.stringify({
                                        ...existingMonitor,
                                        name: "Updated Name",
                                    }),
                                    {
                                        status: 200,
                                        headers: {
                                            "Content-Type": "application/json",
                                        },
                                    },
                                ),
                            );
                        }
                        return Promise.resolve(
                            new Response(JSON.stringify(existingMonitor), {
                                status: 200,
                                headers: { "Content-Type": "application/json" },
                            }),
                        );
                    }
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                items: [],
                                page: 1,
                                page_size: 20,
                                total: 0,
                            }),
                            {
                                status: 200,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                });
            vi.stubGlobal("fetch", mockFetch);

            renderApp("/monitors/mon-edit-1/edit");

            const nameInput = await screen.findByLabelText("Name");
            expect(nameInput).toHaveValue("Original Name");
            expect(screen.getByLabelText("URL")).toHaveValue(
                "https://original.example.com/health",
            );

            fireEvent.change(nameInput, {
                target: { value: "Updated Name" },
            });

            const saveBtn = screen.getByRole("button", {
                name: "Save changes",
            });
            fireEvent.click(saveBtn);

            expect(
                await screen.findByRole("heading", { name: "Monitors" }),
            ).toBeInTheDocument();

            const patchCall = mockFetch.mock.calls.find(
                (call: unknown[]) =>
                    typeof call[0] === "string" &&
                    call[0].includes("/monitors/mon-edit-1") &&
                    (call[1] as RequestInit | undefined)?.method === "PATCH",
            );
            expect(patchCall).toBeDefined();
            expect(
                JSON.parse((patchCall![1] as RequestInit).body as string),
            ).toEqual({
                name: "Updated Name",
            });
        });

        it("no changes means no PATCH call and navigates directly to /monitors", async () => {
            const mockFetch = vi.fn().mockImplementation((url: string) => {
                if (url.includes("/api/v1/monitors/mon-edit-1")) {
                    return Promise.resolve(
                        new Response(JSON.stringify(existingMonitor), {
                            status: 200,
                            headers: { "Content-Type": "application/json" },
                        }),
                    );
                }
                return Promise.resolve(
                    new Response(
                        JSON.stringify({
                            items: [],
                            page: 1,
                            page_size: 20,
                            total: 0,
                        }),
                        {
                            status: 200,
                            headers: { "Content-Type": "application/json" },
                        },
                    ),
                );
            });
            vi.stubGlobal("fetch", mockFetch);

            renderApp("/monitors/mon-edit-1/edit");

            const saveBtn = await screen.findByRole("button", {
                name: "Save changes",
            });
            fireEvent.click(saveBtn);

            expect(
                await screen.findByRole("heading", { name: "Monitors" }),
            ).toBeInTheDocument();

            const patchCall = mockFetch.mock.calls.find(
                (call: unknown[]) =>
                    (call[1] as RequestInit | undefined)?.method === "PATCH",
            );
            expect(patchCall).toBeUndefined();
        });

        it("404 shows Monitor not found.", async () => {
            const mockFetch = vi.fn().mockResolvedValue(
                new Response(JSON.stringify({ detail: "Monitor not found." }), {
                    status: 404,
                    headers: { "Content-Type": "application/json" },
                }),
            );
            vi.stubGlobal("fetch", mockFetch);

            renderApp("/monitors/mon-missing/edit");

            expect(
                await screen.findByRole("heading", {
                    name: "Monitor not found.",
                }),
            ).toBeInTheDocument();
        });

        it("401 redirects to the login page", async () => {
            const mockFetch = vi.fn().mockResolvedValue(
                new Response(JSON.stringify({ detail: "Unauthorized" }), {
                    status: 401,
                    headers: { "Content-Type": "application/json" },
                }),
            );
            vi.stubGlobal("fetch", mockFetch);

            renderApp("/monitors/mon-edit-1/edit");

            expect(
                await screen.findByRole("heading", { name: "Welcome back" }),
            ).toBeInTheDocument();
        });
    });
});
