import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import { useCurrentRole, type Role } from "../hooks/useCurrentRole";
import {
    listMembers,
    addMember,
    changeMemberRole,
    ApiError,
} from "../../lib/membersApi";
import type { TeamMember } from "../../lib/members";
import { AppNav } from "../components/AppNav";
import { ToastContainer } from "../components/Toast";
import { useToast } from "../components/useToast";
import "./members.css";

export function MembersPage() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { toasts, addToast, dismissToast } = useToast();
    const { isReadOnly, isAdmin, isLoading: isRoleLoading } = useCurrentRole();

    // Add member form state
    const [newEmail, setNewEmail] = useState("");
    const [newRole, setNewRole] = useState<Role>("operator");
    const [formError, setFormError] = useState<string | null>(null);

    // Fetch team members
    const {
        data,
        isLoading: isMembersLoading,
        isError,
        error,
        refetch,
    } = useQuery({
        queryKey: ["team", "members"],
        queryFn: listMembers,
        enabled: !isReadOnly && !isRoleLoading,
    });

    // Handle authentication expiration
    useEffect(() => {
        if (error instanceof ApiError && error.status === 401) {
            navigate("/login", { replace: true });
        }
    }, [error, navigate]);

    // Mutation: Add team member
    const addMemberMutation = useMutation({
        mutationFn: ({ email, role }: { email: string; role: Role }) =>
            addMember({ email, role }),
        onSuccess: async () => {
            setNewEmail("");
            setNewRole("operator");
            setFormError(null);
            await queryClient.invalidateQueries({
                queryKey: ["team", "members"],
            });
            addToast("Member added successfully.", "success");
        },
        onError: (err) => {
            const message =
                err instanceof ApiError
                    ? err.message
                    : "Could not add member. Please try again.";
            setFormError(message);
            addToast(message, "error");
        },
    });

    // Mutation: Change member role
    const changeRoleMutation = useMutation({
        mutationFn: ({ userId, role }: { userId: string; role: Role }) =>
            changeMemberRole(userId, role),
        onSuccess: async () => {
            await queryClient.invalidateQueries({
                queryKey: ["team", "members"],
            });
            addToast("Member role updated successfully.", "success");
        },
        onError: (err) => {
            // AC: Demoting the last admin shows the API's message and changes nothing on screen.
            const message =
                err instanceof ApiError
                    ? err.message
                    : "Could not change role. Please try again.";
            addToast(message, "error");
            // Invalidate queries to guarantee UI reflects the true database state
            void queryClient.invalidateQueries({
                queryKey: ["team", "members"],
            });
        },
    });

    const handleAddMember = (e: React.FormEvent) => {
        e.preventDefault();
        setFormError(null);
        const trimmedEmail = newEmail.trim();
        if (!trimmedEmail) {
            setFormError("Email address is required.");
            return;
        }
        addMemberMutation.mutate({ email: trimmedEmail, role: newRole });
    };

    const handleRoleChange = (userId: string, targetRole: Role) => {
        changeRoleMutation.mutate({ userId, role: targetRole });
    };

    // ── Access Denied for read_only users (AC: opening URL directly shows a "not allowed" page) ──
    if (!isRoleLoading && isReadOnly) {
        return (
            <main className="members-page">
                <AppNav />
                <div role="alert" className="members-card members-state-box">
                    <h2>Access Denied</h2>
                    <p>
                        You do not have permission to view or manage team
                        members. This area is restricted to team administrators
                        and operators.
                    </p>
                    <Link
                        to="/monitors"
                        className="members-button members-button--primary"
                    >
                        Back to monitors
                    </Link>
                </div>
            </main>
        );
    }

    const items: TeamMember[] = data?.items ?? [];
    const isLoading = isRoleLoading || isMembersLoading;
    const is403 = error instanceof ApiError && error.status === 403;

    return (
        <>
            <main className="members-page">
                <AppNav />

                <header className="members-header">
                    <div className="members-header-text">
                        <h1>Team Members</h1>
                        <p className="members-subtitle">
                            Manage who has access to your team and their
                            permission roles.
                        </p>
                    </div>
                </header>

                {/* ── Add Member Form (Admin only) ── */}
                {isAdmin && (
                    <section
                        className="members-form-card"
                        aria-labelledby="add-member-heading"
                    >
                        <h2 id="add-member-heading">Add a team member</h2>
                        {formError && (
                            <div role="alert" className="members-error-banner">
                                <span>{formError}</span>
                                <button
                                    type="button"
                                    onClick={() => setFormError(null)}
                                    aria-label="Dismiss error"
                                    style={{
                                        background: "none",
                                        border: "none",
                                        color: "inherit",
                                        cursor: "pointer",
                                    }}
                                >
                                    ✕
                                </button>
                            </div>
                        )}
                        <form
                            className="members-add-form"
                            onSubmit={handleAddMember}
                            noValidate
                        >
                            <div className="members-form-group">
                                <label htmlFor="member-email">
                                    Email address
                                </label>
                                <input
                                    id="member-email"
                                    type="email"
                                    className="members-input"
                                    placeholder="colleague@example.com"
                                    value={newEmail}
                                    onChange={(e) =>
                                        setNewEmail(e.target.value)
                                    }
                                    disabled={addMemberMutation.isPending}
                                    required
                                />
                            </div>

                            <div
                                className="members-form-group"
                                style={{ maxWidth: "200px" }}
                            >
                                <label htmlFor="member-role">
                                    Assigned role
                                </label>
                                <select
                                    id="member-role"
                                    className="members-select"
                                    value={newRole}
                                    onChange={(e) =>
                                        setNewRole(e.target.value as Role)
                                    }
                                    disabled={addMemberMutation.isPending}
                                >
                                    <option value="operator">Operator</option>
                                    <option value="read_only">Read-only</option>
                                    <option value="admin">Admin</option>
                                </select>
                            </div>

                            <button
                                type="submit"
                                className="members-button members-button--primary"
                                disabled={addMemberMutation.isPending}
                                data-testid="add-member-btn"
                            >
                                {addMemberMutation.isPending
                                    ? "Adding..."
                                    : "Add member"}
                            </button>
                        </form>
                    </section>
                )}

                {/* ── Members List ── */}
                <section
                    className="members-card"
                    aria-labelledby="members-list-heading"
                >
                    <h2 id="members-list-heading" className="sr-only">
                        Team Members List
                    </h2>

                    {isLoading && (
                        <div
                            role="status"
                            className="members-state-box"
                            aria-live="polite"
                        >
                            <span className="spinner" aria-hidden="true" />
                            <p>Loading team members...</p>
                        </div>
                    )}

                    {isError && (
                        <div role="alert" className="members-state-box">
                            <h2>
                                {is403
                                    ? "Access Restricted"
                                    : "Could not load team members"}
                            </h2>
                            <p>
                                {error instanceof Error
                                    ? error.message
                                    : "You do not have permission to view team members."}
                            </p>
                            {!is403 && (
                                <button
                                    type="button"
                                    className="members-button members-button--secondary"
                                    onClick={() => void refetch()}
                                >
                                    Try again
                                </button>
                            )}
                        </div>
                    )}

                    {!isLoading && !isError && items.length === 0 && (
                        <div className="members-state-box">
                            <p>No team members found.</p>
                        </div>
                    )}

                    {!isLoading && !isError && items.length > 0 && (
                        <div className="members-table-wrapper">
                            <table className="members-table">
                                <thead>
                                    <tr>
                                        <th scope="col">Name</th>
                                        <th scope="col">Email</th>
                                        <th scope="col">Role</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {items.map((member) => (
                                        <tr key={member.user_id}>
                                            <td>
                                                <strong>
                                                    {member.full_name || "—"}
                                                </strong>
                                            </td>
                                            <td className="members-email-cell">
                                                {member.email}
                                            </td>
                                            <td>
                                                {isAdmin ? (
                                                    <select
                                                        className="members-role-select"
                                                        value={member.role}
                                                        aria-label={`Change role for ${member.email}`}
                                                        data-testid={`role-select-${member.user_id}`}
                                                        disabled={
                                                            changeRoleMutation.isPending
                                                        }
                                                        onChange={(e) =>
                                                            handleRoleChange(
                                                                member.user_id,
                                                                e.target
                                                                    .value as Role,
                                                            )
                                                        }
                                                    >
                                                        <option value="admin">
                                                            Admin
                                                        </option>
                                                        <option value="operator">
                                                            Operator
                                                        </option>
                                                        <option value="read_only">
                                                            Read-only
                                                        </option>
                                                    </select>
                                                ) : (
                                                    <span
                                                        className={`members-role-badge members-role-badge--${member.role}`}
                                                        data-testid={`role-badge-${member.user_id}`}
                                                    >
                                                        {member.role ===
                                                        "read_only"
                                                            ? "Read-only"
                                                            : member.role ===
                                                                "operator"
                                                              ? "Operator"
                                                              : "Admin"}
                                                    </span>
                                                )}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>
            </main>
            <ToastContainer toasts={toasts} onDismiss={dismissToast} />
        </>
    );
}
