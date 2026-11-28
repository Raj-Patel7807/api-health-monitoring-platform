import { useState, useEffect, type FormEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { getMe, updateMe } from "../../lib/authApi";
import { getSessionId } from "../../lib/auth";
import { AppNav } from "../components/AppNav";
import { ToastContainer } from "../components/Toast";
import { useToast } from "../components/useToast";
import "./profile.css";

export function ProfilePage() {
    const queryClient = useQueryClient();
    const sessionId = getSessionId();
    const { toasts, addToast, dismissToast } = useToast();

    // Query authenticated user profile
    const {
        data: user,
        isLoading,
        isError,
        error,
    } = useQuery({
        queryKey: ["auth", "me", sessionId],
        queryFn: getMe,
        enabled: Boolean(sessionId),
    });

    // Profile details edit form state
    const [fullName, setFullName] = useState("");
    const [email, setEmail] = useState("");

    // Password change form state
    const [currentPassword, setCurrentPassword] = useState("");
    const [newPassword, setNewPassword] = useState("");
    const [confirmPassword, setConfirmPassword] = useState("");
    const [passwordError, setPasswordError] = useState<string | null>(null);

    // Sync input fields when user profile data loads
    useEffect(() => {
        if (user) {
            setFullName(user.full_name);
            setEmail(user.email);
        }
    }, [user]);

    // Mutation: Update Name and Email
    const updateProfileMutation = useMutation({
        mutationFn: (payload: { full_name?: string; email?: string }) =>
            updateMe(payload),
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ["auth", "me"] });
            addToast("Profile updated successfully.", "success");
        },
        onError: (err) => {
            const message =
                err instanceof Error
                    ? err.message
                    : "Could not update profile. Please try again.";
            addToast(message, "error");
        },
    });

    // Mutation: Change Password
    const changePasswordMutation = useMutation({
        mutationFn: (payload: {
            current_password: string;
            new_password: string;
        }) => updateMe(payload),
        onSuccess: async () => {
            setCurrentPassword("");
            setNewPassword("");
            setConfirmPassword("");
            setPasswordError(null);
            addToast("Password changed successfully.", "success");
        },
        onError: (err) => {
            const message =
                err instanceof Error
                    ? err.message
                    : "Could not change password. Please try again.";
            setPasswordError(message);
            addToast(message, "error");
        },
    });

    const handleUpdateProfile = (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        const trimmedName = fullName.trim();
        const trimmedEmail = email.trim();

        if (!trimmedName || !trimmedEmail) {
            addToast("Name and email are required.", "error");
            return;
        }

        updateProfileMutation.mutate({
            full_name: trimmedName,
            email: trimmedEmail,
        });
    };

    const handleChangePassword = (e: FormEvent<HTMLFormElement>) => {
        e.preventDefault();
        setPasswordError(null);

        if (!currentPassword) {
            setPasswordError("Current password is required.");
            addToast("Current password is required.", "error");
            return;
        }

        if (newPassword.length < 8) {
            const msg = "New password must be at least 8 characters.";
            setPasswordError(msg);
            addToast(msg, "error");
            return;
        }

        if (newPassword !== confirmPassword) {
            const msg = "New passwords do not match.";
            setPasswordError(msg);
            addToast(msg, "error");
            return;
        }

        changePasswordMutation.mutate({
            current_password: currentPassword,
            new_password: newPassword,
        });
    };

    const formattedDate = user?.created_at
        ? new Date(user.created_at).toLocaleDateString(undefined, {
              year: "numeric",
              month: "long",
              day: "numeric",
          })
        : "—";

    return (
        <div className="profile-page">
            <AppNav />
            <ToastContainer toasts={toasts} onDismiss={dismissToast} />

            <header className="profile-header">
                <h1>User Profile</h1>
                <p className="profile-subtitle">
                    Manage your personal information and account security.
                </p>
            </header>

            {isLoading && <p role="status">Loading profile...</p>}

            {isError && (
                <p role="alert" className="profile-error">
                    {error instanceof Error
                        ? error.message
                        : "Failed to load profile."}
                </p>
            )}

            {user && (
                <>
                    {/* Account Summary */}
                    <section
                        className="profile-card"
                        aria-labelledby="summary-heading"
                    >
                        <h2 id="summary-heading">Account Overview</h2>
                        <div className="profile-summary-grid">
                            <div className="profile-summary-item">
                                <span className="profile-summary-label">
                                    Full Name
                                </span>
                                <span
                                    className="profile-summary-value"
                                    data-testid="profile-name"
                                >
                                    {user.full_name}
                                </span>
                            </div>
                            <div className="profile-summary-item">
                                <span className="profile-summary-label">
                                    Email Address
                                </span>
                                <span
                                    className="profile-summary-value"
                                    data-testid="profile-email"
                                >
                                    {user.email}
                                </span>
                            </div>
                            <div className="profile-summary-item">
                                <span className="profile-summary-label">
                                    Team
                                </span>
                                <span
                                    className="profile-summary-value"
                                    data-testid="profile-team"
                                >
                                    {user.team?.name ?? "No Team"}
                                </span>
                            </div>
                            <div className="profile-summary-item">
                                <span className="profile-summary-label">
                                    Role
                                </span>
                                <span
                                    className="profile-role-badge"
                                    data-testid="profile-role"
                                >
                                    {user.team?.role ?? "read_only"}
                                </span>
                            </div>
                            <div className="profile-summary-item">
                                <span className="profile-summary-label">
                                    Member Since
                                </span>
                                <span
                                    className="profile-summary-value"
                                    data-testid="profile-created"
                                >
                                    {formattedDate}
                                </span>
                            </div>
                        </div>
                    </section>

                    {/* Edit Profile Form */}
                    <section
                        className="profile-card"
                        aria-labelledby="edit-profile-heading"
                    >
                        <h2 id="edit-profile-heading">Edit Profile Details</h2>
                        <form
                            className="profile-form"
                            onSubmit={handleUpdateProfile}
                            data-testid="edit-profile-form"
                        >
                            <div className="profile-form-group">
                                <label htmlFor="profile-fullname">
                                    Full Name
                                </label>
                                <input
                                    id="profile-fullname"
                                    type="text"
                                    className="profile-input"
                                    value={fullName}
                                    onChange={(e) =>
                                        setFullName(e.target.value)
                                    }
                                    required
                                    maxLength={150}
                                    placeholder="Enter your full name"
                                />
                            </div>

                            <div className="profile-form-group">
                                <label htmlFor="profile-email-input">
                                    Email Address
                                </label>
                                <input
                                    id="profile-email-input"
                                    type="email"
                                    className="profile-input"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
                                    required
                                    placeholder="Enter your email"
                                />
                            </div>

                            <button
                                type="submit"
                                className="profile-button"
                                disabled={updateProfileMutation.isPending}
                            >
                                {updateProfileMutation.isPending
                                    ? "Saving..."
                                    : "Save Details"}
                            </button>
                        </form>
                    </section>

                    {/* Change Password Form */}
                    <section
                        className="profile-card"
                        aria-labelledby="change-password-heading"
                    >
                        <h2 id="change-password-heading">Change Password</h2>
                        <form
                            className="profile-form"
                            onSubmit={handleChangePassword}
                            data-testid="change-password-form"
                        >
                            <div className="profile-form-group">
                                <label htmlFor="profile-current-password">
                                    Current Password
                                </label>
                                <input
                                    id="profile-current-password"
                                    type="password"
                                    className="profile-input"
                                    value={currentPassword}
                                    onChange={(e) =>
                                        setCurrentPassword(e.target.value)
                                    }
                                    required
                                    placeholder="Enter your current password"
                                />
                            </div>

                            <div className="profile-form-group">
                                <label htmlFor="profile-new-password">
                                    New Password
                                </label>
                                <input
                                    id="profile-new-password"
                                    type="password"
                                    className="profile-input"
                                    value={newPassword}
                                    onChange={(e) =>
                                        setNewPassword(e.target.value)
                                    }
                                    required
                                    minLength={8}
                                    maxLength={128}
                                    placeholder="At least 8 characters"
                                />
                            </div>

                            <div className="profile-form-group">
                                <label htmlFor="profile-confirm-password">
                                    Confirm New Password
                                </label>
                                <input
                                    id="profile-confirm-password"
                                    type="password"
                                    className="profile-input"
                                    value={confirmPassword}
                                    onChange={(e) =>
                                        setConfirmPassword(e.target.value)
                                    }
                                    required
                                    minLength={8}
                                    maxLength={128}
                                    placeholder="Re-enter your new password"
                                />
                            </div>

                            {passwordError && (
                                <p role="alert" className="profile-error">
                                    {passwordError}
                                </p>
                            )}

                            <button
                                type="submit"
                                className="profile-button"
                                disabled={changePasswordMutation.isPending}
                            >
                                {changePasswordMutation.isPending
                                    ? "Updating..."
                                    : "Change Password"}
                            </button>
                        </form>
                    </section>
                </>
            )}
        </div>
    );
}
