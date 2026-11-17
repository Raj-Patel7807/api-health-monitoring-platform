import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { MembersPage } from "./MembersPage";
import * as roleHook from "../hooks/useCurrentRole";

function renderMembersPage() {
    const client = new QueryClient({
        defaultOptions: { queries: { retry: false } },
    });
    return render(
        <QueryClientProvider client={client}>
            <MemoryRouter initialEntries={["/members"]}>
                <MembersPage />
            </MemoryRouter>
        </QueryClientProvider>,
    );
}

describe("MembersPage (US-19)", () => {
    beforeEach(() => {
        localStorage.setItem("access_token", "test-token");
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    const mockMembers = [
        {
            user_id: "u-1",
            full_name: "Admin Alice",
            email: "alice@example.com",
            role: "admin",
            joined_at: "2026-10-01T10:00:00Z",
        },
        {
            user_id: "u-2",
            full_name: "Bob Operator",
            email: "bob@example.com",
            role: "operator",
            joined_at: "2026-10-02T10:00:00Z",
        },
    ];

    it("admin view: renders members list, add form, and editable role selects", async () => {
        vi.spyOn(roleHook, "useCurrentRole").mockReturnValue({
            role: "admin",
            isAdmin: true,
            isOperator: false,
            isReadOnly: false,
            isLoading: false,
            isError: false,
            error: null,
            refetch: vi.fn(),
        });

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if (url.includes("/api/v1/team/members")) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                items: mockMembers,
                                total: 2,
                            }),
                            {
                                status: 200,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                }
                return Promise.reject(new Error(`Unexpected url: ${url}`));
            }),
        );

        renderMembersPage();

        expect(
            await screen.findByRole("heading", { name: "Team Members" }),
        ).toBeInTheDocument();
        expect(
            screen.getByRole("heading", { name: "Add a team member" }),
        ).toBeInTheDocument();
        expect(screen.getByLabelText("Email address")).toBeInTheDocument();
        expect(screen.getByTestId("add-member-btn")).toBeInTheDocument();

        // Check members in table
        expect(await screen.findByText("Admin Alice")).toBeInTheDocument();
        expect(screen.getByText("alice@example.com")).toBeInTheDocument();
        expect(screen.getByText("Bob Operator")).toBeInTheDocument();
        expect(screen.getByText("bob@example.com")).toBeInTheDocument();

        // Role selects exist for admin
        expect(screen.getByTestId("role-select-u-1")).toHaveValue("admin");
        expect(screen.getByTestId("role-select-u-2")).toHaveValue("operator");
    });

    it("admin adds member: submits payload and updates UI", async () => {
        vi.spyOn(roleHook, "useCurrentRole").mockReturnValue({
            role: "admin",
            isAdmin: true,
            isOperator: false,
            isReadOnly: false,
            isLoading: false,
            isError: false,
            error: null,
            refetch: vi.fn(),
        });

        let membersList = [...mockMembers];
        const mockFetch = vi
            .fn()
            .mockImplementation((url: string, init?: RequestInit) => {
                if (
                    url.includes("/api/v1/team/members") &&
                    init?.method === "POST"
                ) {
                    const body = JSON.parse(init.body as string);
                    membersList = [
                        ...membersList,
                        {
                            user_id: "u-3",
                            full_name: "Charlie Viewer",
                            email: body.email,
                            role: body.role,
                            joined_at: "2026-10-03T10:00:00Z",
                        },
                    ];
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                user_id: "u-3",
                                email: body.email,
                                role: body.role,
                            }),
                            {
                                status: 201,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                }
                if (url.includes("/api/v1/team/members")) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                items: membersList,
                                total: membersList.length,
                            }),
                            {
                                status: 200,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                }
                return Promise.reject(new Error(`Unexpected url: ${url}`));
            });
        vi.stubGlobal("fetch", mockFetch);

        renderMembersPage();

        expect(await screen.findByText("Admin Alice")).toBeInTheDocument();

        fireEvent.change(screen.getByLabelText("Email address"), {
            target: { value: "charlie@example.com" },
        });
        fireEvent.change(screen.getByLabelText("Assigned role"), {
            target: { value: "read_only" },
        });

        fireEvent.click(screen.getByTestId("add-member-btn"));

        await waitFor(() => {
            expect(screen.getByText("charlie@example.com")).toBeInTheDocument();
        });
        expect(
            screen.getByText("Member added successfully."),
        ).toBeInTheDocument();
    });

    it("demoting the last admin shows the API 409 message and changes nothing on screen", async () => {
        vi.spyOn(roleHook, "useCurrentRole").mockReturnValue({
            role: "admin",
            isAdmin: true,
            isOperator: false,
            isReadOnly: false,
            isLoading: false,
            isError: false,
            error: null,
            refetch: vi.fn(),
        });

        const mockFetch = vi
            .fn()
            .mockImplementation((url: string, init?: RequestInit) => {
                if (
                    url.includes("/api/v1/team/members/u-1") &&
                    init?.method === "PATCH"
                ) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                detail: "Cannot demote the last admin of the team.",
                            }),
                            {
                                status: 409,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                }
                if (url.includes("/api/v1/team/members")) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                items: mockMembers,
                                total: 2,
                            }),
                            {
                                status: 200,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                }
                return Promise.reject(new Error(`Unexpected url: ${url}`));
            });
        vi.stubGlobal("fetch", mockFetch);

        renderMembersPage();

        expect(
            await screen.findByTestId("role-select-u-1"),
        ).toBeInTheDocument();

        // Attempt demoting the last admin to operator
        fireEvent.change(screen.getByTestId("role-select-u-1"), {
            target: { value: "operator" },
        });

        // Verify toast error displays 409 detail
        expect(
            await screen.findByText(
                "Cannot demote the last admin of the team.",
            ),
        ).toBeInTheDocument();

        // Verify screen still shows admin role for u-1
        expect(screen.getByTestId("role-select-u-1")).toHaveValue("admin");
    });

    it("operator view: renders list without Add Member form and without role change controls", async () => {
        vi.spyOn(roleHook, "useCurrentRole").mockReturnValue({
            role: "operator",
            isAdmin: false,
            isOperator: true,
            isReadOnly: false,
            isLoading: false,
            isError: false,
            error: null,
            refetch: vi.fn(),
        });

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if (url.includes("/api/v1/team/members")) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                items: mockMembers,
                                total: 2,
                            }),
                            {
                                status: 200,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                }
                return Promise.reject(new Error(`Unexpected url: ${url}`));
            }),
        );

        renderMembersPage();

        expect(
            await screen.findByRole("heading", { name: "Team Members" }),
        ).toBeInTheDocument();

        // Add member form should NOT be present
        expect(
            screen.queryByRole("heading", { name: "Add a team member" }),
        ).not.toBeInTheDocument();
        expect(
            screen.queryByLabelText("Email address"),
        ).not.toBeInTheDocument();
        expect(screen.queryByTestId("add-member-btn")).not.toBeInTheDocument();

        // Wait for members to render
        expect(await screen.findByText("Admin Alice")).toBeInTheDocument();

        // Role change selects should NOT be present; static badges should appear instead
        expect(screen.queryByTestId("role-select-u-1")).not.toBeInTheDocument();
        expect(screen.queryByTestId("role-select-u-2")).not.toBeInTheDocument();

        expect(screen.getByTestId("role-badge-u-1")).toHaveTextContent("Admin");
        expect(screen.getByTestId("role-badge-u-2")).toHaveTextContent(
            "Operator",
        );
    });

    it("read_only view: direct navigation renders Access Denied page with Back to monitors link", async () => {
        vi.spyOn(roleHook, "useCurrentRole").mockReturnValue({
            role: "read_only",
            isAdmin: false,
            isOperator: false,
            isReadOnly: true,
            isLoading: false,
            isError: false,
            error: null,
            refetch: vi.fn(),
        });

        renderMembersPage();

        expect(
            await screen.findByRole("heading", { name: "Access Denied" }),
        ).toBeInTheDocument();
        expect(
            screen.getByText(
                /You do not have permission to view or manage team members/i,
            ),
        ).toBeInTheDocument();
        const backLink = screen.getByRole("link", { name: "Back to monitors" });
        expect(backLink).toBeInTheDocument();
        expect(backLink).toHaveAttribute("href", "/monitors");

        // Table and add form must not be present
        expect(screen.queryByText("Add a team member")).not.toBeInTheDocument();
        expect(screen.queryByRole("table")).not.toBeInTheDocument();
    });

    it("shows clear error message on 403 Forbidden and stays usable", async () => {
        vi.spyOn(roleHook, "useCurrentRole").mockReturnValue({
            role: "operator",
            isAdmin: false,
            isOperator: true,
            isReadOnly: false,
            isLoading: false,
            isError: false,
            error: null,
            refetch: vi.fn(),
        });

        vi.stubGlobal(
            "fetch",
            vi.fn().mockImplementation((url: string) => {
                if (url.includes("/api/v1/team/members")) {
                    return Promise.resolve(
                        new Response(
                            JSON.stringify({
                                detail: "Forbidden: insufficient permissions.",
                            }),
                            {
                                status: 403,
                                headers: { "Content-Type": "application/json" },
                            },
                        ),
                    );
                }
                return Promise.reject(new Error(`Unexpected url: ${url}`));
            }),
        );

        renderMembersPage();

        expect(
            await screen.findByRole("heading", { name: "Access Restricted" }),
        ).toBeInTheDocument();
        expect(
            screen.getByText("Forbidden: insufficient permissions."),
        ).toBeInTheDocument();

        // The screen does not crash and the nav remains usable
        expect(
            screen.getByLabelText("Main platform navigation"),
        ).toBeInTheDocument();
    });
});
