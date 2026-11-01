/**
 * ChannelFormPage — add / edit notification channel (US-03).
 *
 * Create mode: type selector + scope selector + type-specific secret field.
 * Edit mode:   type is locked (shown as read-only); secret field is empty
 *              with "Leave blank to keep the current one" hint shown.
 *
 * 422 field errors from the API appear under the matching field;
 * other errors appear as a toast (acceptance criterion).
 */

import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
    CHANNEL_TYPES,
    CHANNEL_TYPE_LABELS,
    SECRET_META,
    DEFAULT_FORM_VALUES,
    validateChannelForm,
    toCreatePayload,
    toUpdatePayload,
    type ChannelFormValues,
    type ChannelField,
} from "../../lib/channels";
import {
    createChannel,
    updateChannel,
    listChannels,
    ApiError,
} from "../../lib/channelsApi";
import { listMonitors } from "../../lib/monitorsApi";
import { ToastContainer } from "../components/Toast";
import { useToast } from "../components/useToast";
import "./monitors.css";
import "./channels.css";

export function ChannelFormPage() {
    const { channelId } = useParams<{ channelId?: string }>();
    const isEditMode = Boolean(channelId);
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const { toasts, addToast, dismissToast } = useToast();

    // Load existing channel data for edit mode
    const { data: channelData, isLoading: channelLoading } = useQuery({
        queryKey: ["channels"],
        queryFn: () => listChannels(),
        enabled: isEditMode,
    });

    const existingChannel = channelId
        ? (channelData?.items ?? []).find((c) => c.id === channelId)
        : undefined;

    // Load monitors for the scope selector
    const { data: monitorsData } = useQuery({
        queryKey: ["monitors", { page: 1 }],
        queryFn: () => listMonitors(1, 100),
    });
    const monitors = monitorsData?.items ?? [];

    const [values, setValues] = useState<ChannelFormValues>(DEFAULT_FORM_VALUES);
    const [fieldErrors, setFieldErrors] = useState<
        Partial<Record<ChannelField, string>>
    >({});
    const [formError, setFormError] = useState<string | null>(null);

    // Populate form when edit data arrives
    useEffect(() => {
        if (existingChannel) {
            setValues({
                type: existingChannel.type,
                name: existingChannel.name,
                scope: existingChannel.monitor_id ?? "team",
                secret_value: "", // always cleared on edit
            });
        }
    }, [existingChannel]);

    const createMutation = useMutation({
        mutationFn: (v: ChannelFormValues) => createChannel(toCreatePayload(v)),
    });

    const updateMutation = useMutation({
        mutationFn: ({
            id,
            initial,
            current,
        }: {
            id: string;
            initial: ChannelFormValues;
            current: ChannelFormValues;
        }) => updateChannel(id, toUpdatePayload(current, initial)),
    });

    function handleChange(field: ChannelField, value: string) {
        setValues((prev) => ({ ...prev, [field]: value }));
        if (fieldErrors[field]) {
            setFieldErrors((prev) => {
                const next = { ...prev };
                delete next[field];
                return next;
            });
        }
    }

    async function handleSubmit(e: React.FormEvent<HTMLFormElement>) {
        e.preventDefault();
        setFormError(null);

        const errors = validateChannelForm(values, isEditMode);
        if (Object.keys(errors).length > 0) {
            setFieldErrors(errors);
            return;
        }

        try {
            if (isEditMode && channelId && existingChannel) {
                const initial: ChannelFormValues = {
                    type: existingChannel.type,
                    name: existingChannel.name,
                    scope: existingChannel.monitor_id ?? "team",
                    secret_value: "",
                };
                await updateMutation.mutateAsync({
                    id: channelId,
                    initial,
                    current: values,
                });
                await queryClient.invalidateQueries({ queryKey: ["channels"] });
                addToast("Channel updated.", "success");
                navigate("/channels");
            } else {
                await createMutation.mutateAsync(values);
                await queryClient.invalidateQueries({ queryKey: ["channels"] });
                navigate("/channels");
            }
        } catch (err) {
            if (err instanceof ApiError) {
                if (err.status === 401) {
                    navigate("/login", { replace: true });
                    return;
                }
                // 422 field errors go under the matching field
                if (err.status === 422 && Object.keys(err.fieldErrors).length > 0) {
                    const mapped: Partial<Record<ChannelField, string>> = {};
                    for (const [k, v] of Object.entries(err.fieldErrors)) {
                        if (k === "secret_value" || k === "name" || k === "type" || k === "scope") {
                            mapped[k as ChannelField] = v;
                        }
                    }
                    if (Object.keys(mapped).length > 0) {
                        setFieldErrors(mapped);
                        return;
                    }
                }
                // Other errors → toast
                addToast(err.message, "error");
            } else {
                addToast("Something went wrong. Please try again.", "error");
            }
        } finally {
            // Acceptance criterion: secret field is cleared after a successful or failed submit
            setValues((prev) => ({ ...prev, secret_value: "" }));
        }
    }

    const isSubmitting = createMutation.isPending || updateMutation.isPending;
    const meta = SECRET_META[values.type];

    if (isEditMode && channelLoading) {
        return (
            <main className="monitors-page monitors-page--form">
                <Link to="/channels" className="monitors-back-link">
                    Back to channels
                </Link>
                <div className="monitors-card monitors-card--form">
                    <h1>Edit channel</h1>
                    <div
                        role="status"
                        className="monitors-state-box"
                        aria-live="polite"
                    >
                        <span className="spinner" aria-hidden="true" />
                        <p>Loading channel...</p>
                    </div>
                </div>
            </main>
        );
    }

    if (isEditMode && !channelLoading && !existingChannel) {
        return (
            <main className="monitors-page monitors-page--form">
                <Link to="/channels" className="monitors-back-link">
                    Back to channels
                </Link>
                <div className="monitors-card monitors-card--form">
                    <h1>Edit channel</h1>
                    <div className="monitors-state-box">
                        <h2>Channel not found.</h2>
                        <p>
                            The channel you are looking for does not exist or
                            was deleted.
                        </p>
                        <Link
                            to="/channels"
                            className="monitors-button monitors-button--secondary"
                        >
                            Back to channels
                        </Link>
                    </div>
                </div>
            </main>
        );
    }

    return (
        <>
            <main className="monitors-page monitors-page--form">
                <Link to="/channels" className="monitors-back-link">
                    Back to channels
                </Link>
                <div className="monitors-card monitors-card--form">
                    <h1>{isEditMode ? "Edit channel" : "Add channel"}</h1>

                    {formError && (
                        <div role="alert" className="form-error-banner">
                            {formError}
                        </div>
                    )}

                    <form
                        onSubmit={(e) => void handleSubmit(e)}
                        noValidate
                        aria-label={
                            isEditMode
                                ? "Edit notification channel"
                                : "Add notification channel"
                        }
                    >
                        {/* ── Type (locked on edit) ── */}
                        <div className="form-field">
                            <label htmlFor="channel-type" className="form-label">
                                Type
                            </label>
                            {isEditMode ? (
                                <div className="channel-type-locked">
                                    {CHANNEL_TYPE_LABELS[values.type] ??
                                        values.type}
                                    <span className="channel-type-locked-note">
                                        Type cannot be changed after creation.
                                    </span>
                                </div>
                            ) : (
                                <select
                                    id="channel-type"
                                    className="form-input form-select"
                                    value={values.type}
                                    disabled={isSubmitting}
                                    aria-invalid={Boolean(fieldErrors.type)}
                                    aria-describedby={
                                        fieldErrors.type
                                            ? "channel-type-error"
                                            : undefined
                                    }
                                    onChange={(e) =>
                                        handleChange(
                                            "type",
                                            e.target.value,
                                        )
                                    }
                                >
                                    {CHANNEL_TYPES.map((t) => (
                                        <option key={t} value={t}>
                                            {CHANNEL_TYPE_LABELS[t]}
                                        </option>
                                    ))}
                                </select>
                            )}
                            {fieldErrors.type && (
                                <p
                                    id="channel-type-error"
                                    className="form-field-error"
                                    role="alert"
                                >
                                    {fieldErrors.type}
                                </p>
                            )}
                        </div>

                        {/* ── Name ── */}
                        <div className="form-field">
                            <label htmlFor="channel-name" className="form-label">
                                Name
                            </label>
                            <input
                                id="channel-name"
                                type="text"
                                className="form-input"
                                value={values.name}
                                maxLength={150}
                                disabled={isSubmitting}
                                aria-invalid={Boolean(fieldErrors.name)}
                                aria-describedby={
                                    fieldErrors.name
                                        ? "channel-name-error"
                                        : undefined
                                }
                                onChange={(e) =>
                                    handleChange("name", e.target.value)
                                }
                            />
                            {fieldErrors.name && (
                                <p
                                    id="channel-name-error"
                                    className="form-field-error"
                                    role="alert"
                                >
                                    {fieldErrors.name}
                                </p>
                            )}
                        </div>

                        {/* ── Scope ── */}
                        <div className="form-field">
                            <label
                                htmlFor="channel-scope"
                                className="form-label"
                            >
                                Scope
                            </label>
                            <select
                                id="channel-scope"
                                className="form-input form-select"
                                value={values.scope}
                                disabled={isSubmitting || isEditMode}
                                aria-invalid={Boolean(fieldErrors.scope)}
                                aria-describedby={
                                    fieldErrors.scope
                                        ? "channel-scope-error"
                                        : undefined
                                }
                                onChange={(e) =>
                                    handleChange("scope", e.target.value)
                                }
                            >
                                <option value="team">Team-wide</option>
                                {monitors.map((m) => (
                                    <option key={m.id} value={m.id}>
                                        {m.name}
                                    </option>
                                ))}
                            </select>
                            {isEditMode && (
                                <p className="form-field-hint">
                                    Scope cannot be changed after creation.
                                </p>
                            )}
                            {fieldErrors.scope && (
                                <p
                                    id="channel-scope-error"
                                    className="form-field-error"
                                    role="alert"
                                >
                                    {fieldErrors.scope}
                                </p>
                            )}
                        </div>

                        {/* ── Secret field (type-specific) ── */}
                        <div className="form-field">
                            <label
                                htmlFor="channel-secret"
                                className="form-label"
                            >
                                {meta.label}
                            </label>

                            {isEditMode && existingChannel?.secret_display_hint && (
                                <p className="channel-secret-hint">
                                    Current:{" "}
                                    <code>
                                        {existingChannel.secret_display_hint}
                                    </code>
                                </p>
                            )}

                            <input
                                id="channel-secret"
                                type="password"
                                className="form-input"
                                value={values.secret_value}
                                placeholder={
                                    isEditMode
                                        ? "Leave blank to keep the current one"
                                        : meta.placeholder
                                }
                                disabled={isSubmitting}
                                autoComplete="off"
                                aria-invalid={Boolean(fieldErrors.secret_value)}
                                aria-describedby={[
                                    "channel-secret-hint",
                                    fieldErrors.secret_value
                                        ? "channel-secret-error"
                                        : "",
                                ]
                                    .filter(Boolean)
                                    .join(" ")}
                                onChange={(e) =>
                                    handleChange(
                                        "secret_value",
                                        e.target.value,
                                    )
                                }
                            />
                            <p
                                id="channel-secret-hint"
                                className="form-field-hint"
                            >
                                {isEditMode
                                    ? "Leave blank to keep the current one."
                                    : meta.hint}
                            </p>
                            {fieldErrors.secret_value && (
                                <p
                                    id="channel-secret-error"
                                    className="form-field-error"
                                    role="alert"
                                >
                                    {fieldErrors.secret_value}
                                </p>
                            )}
                        </div>

                        {/* ── Actions ── */}
                        <div className="form-actions">
                            <Link
                                to="/channels"
                                className="monitors-button monitors-button--secondary"
                            >
                                Cancel
                            </Link>
                            <button
                                type="submit"
                                className="monitors-button monitors-button--primary"
                                disabled={isSubmitting}
                            >
                                {isSubmitting
                                    ? isEditMode
                                        ? "Saving…"
                                        : "Adding…"
                                    : isEditMode
                                      ? "Save changes"
                                      : "Add channel"}
                            </button>
                        </div>
                    </form>
                </div>
            </main>

            <ToastContainer toasts={toasts} onDismiss={dismissToast} />
        </>
    );
}
