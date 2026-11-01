/**
 * ChannelsPage — list of notification channels (US-03).
 *
 * Shows: type, name, scope (team-wide or monitor name), enabled toggle,
 * delete button (with confirmation dialog), and an "Add channel" link.
 *
 * Role-aware: controls (Add / Delete) are hidden for read_only users via
 * useCurrentRole(). The hook is stubbed until /auth/me returns the role.
 */

import { useState, useEffect } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
    listChannels,
    deleteChannel,
    updateChannel,
    ApiError,
} from "../../lib/channelsApi";
import type { Channel } from "../../lib/channels";
import { CHANNEL_TYPE_LABELS } from "../../lib/channels";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { ToastContainer } from "../components/Toast";
import { useToast } from "../components/useToast";
import { useCurrentRole } from "../hooks/useCurrentRole";
import "./monitors.css";
import "./channels.css";

const TYPE_ICONS: Record<string, string> = {
    slack: "🔔",
    discord: "💬",
    email: "✉️",
    webhook: "🔗",
};

function formatDateTime(isoString: string): string {
    try {
        return new Intl.DateTimeFormat(undefined, {
            dateStyle: "short",
            timeStyle: "short",
        }).format(new Date(isoString));
    } catch {
        return isoString;
    }
}

export function ChannelsPage() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { toasts, addToast, dismissToast } = useToast();
    const { isReadOnly } = useCurrentRole();
    const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);

    const { data, isLoading, isError, error, refetch } = useQuery({
        queryKey: ["channels"],
        queryFn: () => listChannels(),
    });

    const items: Channel[] = data?.items ?? [];
    const pendingDeleteChannel =
        pendingDeleteId !== null
            ? (items.find((c) => c.id === pendingDeleteId) ?? null)
            : null;

    // Redirect on auth failure
    useEffect(() => {
        if (error instanceof ApiError && error.status === 401) {
            navigate("/login", { replace: true });
        }
    }, [error, navigate]);

    const toggleMutation = useMutation({
        mutationFn: ({ id, is_enabled }: { id: string; is_enabled: boolean }) =>
            updateChannel(id, { is_enabled }),
        onSuccess: async () => {
            await queryClient.invalidateQueries({ queryKey: ["channels"] });
        },
        onError: (err) => {
            addToast(
                err instanceof ApiError
                    ? err.message
                    : "Could not update channel.",
                "error",
            );
        },
    });

    const deleteMutation = useMutation({
        mutationFn: (id: string) => deleteChannel(id),
        onSuccess: async () => {
            setPendingDeleteId(null);
            await queryClient.invalidateQueries({ queryKey: ["channels"] });
            addToast("Channel deleted.", "success");
        },
        onError: (err) => {
            setPendingDeleteId(null);
            addToast(
                err instanceof ApiError
                    ? err.message
                    : "Could not delete channel. Please try again.",
                "error",
            );
        },
    });

    return (
        <>
            <main className="monitors-page">
                <header className="monitors-header">
                    <div className="monitors-header-text">
                        <h1>Notification Channels</h1>
                        <p className="monitors-subtitle">
                            Where alerts are sent when a monitor detects a
                            problem.
                        </p>
                    </div>
                    {!isReadOnly && (
                        <Link
                            to="/channels/new"
                            className="monitors-button monitors-button--primary"
                            data-testid="add-channel-btn"
                        >
                            Add channel
                        </Link>
                    )}
                </header>

                <section className="monitors-card">
                    {isLoading && (
                        <div
                            role="status"
                            className="monitors-state-box"
                            aria-live="polite"
                        >
                            <span className="spinner" aria-hidden="true" />
                            <p>Loading channels...</p>
                        </div>
                    )}

                    {isError && (
                        <div role="alert" className="monitors-state-box">
                            <h2>Could not load channels</h2>
                            <p>
                                {error instanceof Error
                                    ? error.message
                                    : "Something went wrong."}
                            </p>
                            <button
                                type="button"
                                className="monitors-button monitors-button--secondary"
                                onClick={() => void refetch()}
                            >
                                Try again
                            </button>
                        </div>
                    )}

                    {!isLoading && !isError && items.length === 0 && (
                        <div className="monitors-state-box">
                            <h2>No channels yet</h2>
                            <p>
                                Add a notification channel to receive alerts
                                when an incident is detected.
                            </p>
                            {!isReadOnly && (
                                <Link
                                    to="/channels/new"
                                    className="monitors-button monitors-button--primary"
                                >
                                    Add your first channel
                                </Link>
                            )}
                        </div>
                    )}

                    {!isLoading && !isError && items.length > 0 && (
                        <div className="monitors-table-container">
                            <table className="monitors-table">
                                <caption className="monitors-sr-only">
                                    Notification channels
                                </caption>
                                <thead>
                                    <tr>
                                        <th scope="col">Type</th>
                                        <th scope="col">Name</th>
                                        <th scope="col">Scope</th>
                                        <th scope="col">Secret</th>
                                        <th scope="col">Enabled</th>
                                        <th scope="col">Created</th>
                                        {!isReadOnly && (
                                            <th scope="col">Actions</th>
                                        )}
                                    </tr>
                                </thead>
                                <tbody>
                                    {items.map((channel) => (
                                        <tr key={channel.id}>
                                            <td>
                                                <span className="channel-type-badge">
                                                    <span aria-hidden="true">
                                                        {TYPE_ICONS[
                                                            channel.type
                                                        ] ?? "📢"}
                                                    </span>
                                                    {CHANNEL_TYPE_LABELS[
                                                        channel.type
                                                    ] ?? channel.type}
                                                </span>
                                            </td>
                                            <td className="channel-name-cell">
                                                {!isReadOnly ? (
                                                    <Link
                                                        to={`/channels/${channel.id}/edit`}
                                                        className="monitors-edit-link"
                                                    >
                                                        {channel.name}
                                                    </Link>
                                                ) : (
                                                    channel.name
                                                )}
                                            </td>
                                            <td>
                                                {channel.monitor_id ? (
                                                    <span className="monitors-chip monitors-chip--method">
                                                        Monitor
                                                    </span>
                                                ) : (
                                                    <span className="monitors-chip monitors-chip--ok">
                                                        Team-wide
                                                    </span>
                                                )}
                                            </td>
                                            <td className="channel-hint-cell">
                                                {channel.secret_display_hint ? (
                                                    <code className="channel-hint">
                                                        {
                                                            channel.secret_display_hint
                                                        }
                                                    </code>
                                                ) : (
                                                    <span className="channel-hint channel-hint--none">
                                                        —
                                                    </span>
                                                )}
                                            </td>
                                            <td>
                                                <button
                                                    type="button"
                                                    role="switch"
                                                    aria-checked={
                                                        channel.is_enabled
                                                    }
                                                    className={`channel-toggle ${
                                                        channel.is_enabled
                                                            ? "channel-toggle--on"
                                                            : "channel-toggle--off"
                                                    }`}
                                                    aria-label={`${channel.is_enabled ? "Disable" : "Enable"} ${channel.name}`}
                                                    disabled={
                                                        isReadOnly ||
                                                        toggleMutation.isPending
                                                    }
                                                    data-testid={`toggle-${channel.id}`}
                                                    onClick={() =>
                                                        void toggleMutation.mutateAsync(
                                                            {
                                                                id: channel.id,
                                                                is_enabled:
                                                                    !channel.is_enabled,
                                                            },
                                                        )
                                                    }
                                                >
                                                    <span
                                                        className="channel-toggle-knob"
                                                        aria-hidden="true"
                                                    />
                                                </button>
                                            </td>
                                            <td>
                                                {formatDateTime(
                                                    channel.created_at,
                                                )}
                                            </td>
                                            {!isReadOnly && (
                                                <td>
                                                    <div className="monitors-actions-cell">
                                                        <Link
                                                            to={`/channels/${channel.id}/edit`}
                                                            className="monitors-edit-link"
                                                            aria-label={`Edit ${channel.name}`}
                                                        >
                                                            Edit
                                                        </Link>
                                                        <button
                                                            type="button"
                                                            className="monitors-delete-btn"
                                                            aria-label={`Delete ${channel.name}`}
                                                            data-testid={`delete-${channel.id}`}
                                                            onClick={() =>
                                                                setPendingDeleteId(
                                                                    channel.id,
                                                                )
                                                            }
                                                        >
                                                            Delete
                                                        </button>
                                                    </div>
                                                </td>
                                            )}
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    )}
                </section>
            </main>

            <ConfirmDialog
                open={pendingDeleteId !== null}
                title="Delete channel?"
                description={
                    pendingDeleteChannel
                        ? `"${pendingDeleteChannel.name}" will be removed. This cannot be undone.`
                        : "This channel will be permanently removed."
                }
                confirmLabel="Delete channel"
                confirmingLabel="Deleting…"
                isConfirming={deleteMutation.isPending}
                onConfirm={() => {
                    if (pendingDeleteId) {
                        void deleteMutation.mutateAsync(pendingDeleteId);
                    }
                }}
                onCancel={() => setPendingDeleteId(null)}
            />

            <ToastContainer toasts={toasts} onDismiss={dismissToast} />
        </>
    );
}
