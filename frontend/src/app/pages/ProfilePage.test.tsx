import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";

import { ProfilePage } from "./ProfilePage";
import * as authApi from "../../lib/authApi";
import { startSession } from "../../lib/auth";

function renderProfilePage() {
    const client = new QueryClient({
        defaultOptions: {
            queries: { retry: false },
            mutations: { retry: false },
        },
    });
    return render(
        <QueryClientProvider client={client}>
            <MemoryRouter initialEntries={["/profile"]}>
                <ProfilePage />
            </MemoryRouter>
        </QueryClientProvider>,
    );
}

describe("ProfilePage (US-01, US-19, Issue #77)", () => {
    const mockUser: authApi.UserProfile = {
        id: "usr-123",
        email: "prince@example.com",
        full_name: "Prince Satapara",
        is_active: true,
        created_at: "2026-05-15T12:00:00Z",
        team: {
            id: "team-123",
            name: "Core Engineering",
            role: "admin",
        },
    };

    beforeEach(() => {
        startSession("test-token", "test-refresh");
        vi.spyOn(authApi, "getMe").mockResolvedValue(mockUser);
    });

    afterEach(() => {
        vi.restoreAllMocks();
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    it("renders user profile data correctly", async () => {
        renderProfilePage();

        expect(
            await screen.findByRole("heading", { name: "User Profile" }),
        ).toBeInTheDocument();
        expect(await screen.findByTestId("profile-name")).toHaveTextContent(
            "Prince Satapara",
        );
        expect(screen.getByTestId("profile-email")).toHaveTextContent(
            "prince@example.com",
        );
        expect(screen.getByTestId("profile-team")).toHaveTextContent(
            "Core Engineering",
        );
        expect(screen.getByTestId("profile-role")).toHaveTextContent("admin");
        expect(screen.getByTestId("profile-created")).toBeInTheDocument();
        expect(screen.getByTestId("nav-profile-link")).toBeInTheDocument();
    });

    it("allows editing full name and email", async () => {
        const updateSpy = vi.spyOn(authApi, "updateMe").mockResolvedValue({
            ...mockUser,
            full_name: "Prince Updated",
            email: "prince.updated@example.com",
        });

        renderProfilePage();

        expect(await screen.findByTestId("profile-name")).toBeInTheDocument();

        const nameInput = screen.getByLabelText("Full Name");
        const emailInput = screen.getByLabelText("Email Address");

        expect(nameInput).toHaveValue("Prince Satapara");
        expect(emailInput).toHaveValue("prince@example.com");

        fireEvent.change(nameInput, { target: { value: "Prince Updated" } });
        fireEvent.change(emailInput, {
            target: { value: "prince.updated@example.com" },
        });

        fireEvent.click(screen.getByRole("button", { name: "Save Details" }));

        await waitFor(() => {
            expect(updateSpy).toHaveBeenCalledWith({
                full_name: "Prince Updated",
                email: "prince.updated@example.com",
            });
        });

        expect(
            await screen.findByText("Profile updated successfully."),
        ).toBeInTheDocument();
    });

    it("validates and submits password change", async () => {
        const updateSpy = vi.spyOn(authApi, "updateMe").mockResolvedValue({
            ...mockUser,
        });

        renderProfilePage();

        expect(await screen.findByTestId("profile-name")).toBeInTheDocument();

        const currentPwdInput = screen.getByLabelText("Current Password");
        const newPwdInput = screen.getByLabelText("New Password");
        const confirmPwdInput = screen.getByLabelText("Confirm New Password");

        // Test mismatch validation
        fireEvent.change(currentPwdInput, {
            target: { value: "oldpassword123" },
        });
        fireEvent.change(newPwdInput, { target: { value: "newpassword123" } });
        fireEvent.change(confirmPwdInput, {
            target: { value: "mismatchpass" },
        });

        fireEvent.click(
            screen.getByRole("button", { name: "Change Password" }),
        );

        expect(await screen.findByRole("alert")).toHaveTextContent(
            "New passwords do not match.",
        );
        expect(updateSpy).not.toHaveBeenCalled();

        // Fix mismatch and submit
        fireEvent.change(confirmPwdInput, {
            target: { value: "newpassword123" },
        });
        fireEvent.click(
            screen.getByRole("button", { name: "Change Password" }),
        );

        await waitFor(() => {
            expect(updateSpy).toHaveBeenCalledWith({
                current_password: "oldpassword123",
                new_password: "newpassword123",
            });
        });

        expect(
            await screen.findByText("Password changed successfully."),
        ).toBeInTheDocument();
        expect(currentPwdInput).toHaveValue("");
        expect(newPwdInput).toHaveValue("");
        expect(confirmPwdInput).toHaveValue("");
    });

    it("handles password change error from API", async () => {
        vi.spyOn(authApi, "updateMe").mockRejectedValue(
            new Error("Incorrect current password."),
        );

        renderProfilePage();

        expect(await screen.findByTestId("profile-name")).toBeInTheDocument();

        fireEvent.change(screen.getByLabelText("Current Password"), {
            target: { value: "wrongoldpass" },
        });
        fireEvent.change(screen.getByLabelText("New Password"), {
            target: { value: "newpassword123" },
        });
        fireEvent.change(screen.getByLabelText("Confirm New Password"), {
            target: { value: "newpassword123" },
        });

        fireEvent.click(
            screen.getByRole("button", { name: "Change Password" }),
        );

        expect(await screen.findByRole("alert")).toHaveTextContent(
            "Incorrect current password.",
        );
    });
});
