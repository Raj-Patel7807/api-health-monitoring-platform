/**
 * Types, validation schemas, and helpers for notification channels (US-03).
 *
 * Secret handling rules (acceptance criteria):
 * - The raw secret is NEVER written to localStorage, sessionStorage,
 *   console logs, or the query cache — only submitted over HTTPS and
 *   immediately discarded.
 * - secret_display_hint from the API is a safe, truncated preview shown to
 *   users (e.g. "hooks.slack.com/…/X7Q"); editing shows it with a "leave
 *   blank to keep the current one" note.
 */

import { z } from "zod";

// ---------------------------------------------------------------------------
// Enumerations
// ---------------------------------------------------------------------------

export const CHANNEL_TYPES = ["slack", "discord", "email", "webhook"] as const;
export type ChannelType = (typeof CHANNEL_TYPES)[number];

/** Human-readable labels for channel types */
export const CHANNEL_TYPE_LABELS: Record<ChannelType, string> = {
    slack: "Slack",
    discord: "Discord",
    email: "Email",
    webhook: "Webhook",
};

// ---------------------------------------------------------------------------
// API shapes
// ---------------------------------------------------------------------------

export type Channel = {
    id: string;
    type: ChannelType;
    name: string;
    monitor_id: string | null;
    is_enabled: boolean;
    /** Safe, truncated preview of the secret (never the real value). */
    secret_display_hint: string | null;
    configuration: Record<string, unknown>;
    created_at: string;
    updated_at: string;
};

export type ChannelListResponse = {
    items: Channel[];
};

// ---------------------------------------------------------------------------
// Form values
// ---------------------------------------------------------------------------

export type ChannelFormValues = {
    /** Immutable after creation (enforced by the form locking the select). */
    type: ChannelType;
    name: string;
    /** "team" = team-wide (monitor_id null); any other string = a monitor UUID. */
    scope: "team" | string;
    /**
     * Write-only field.  Never stored in state after a successful submit.
     * Left empty on edit; "leave blank to keep current" note is shown.
     */
    secret_value: string;
};

export type ChannelField = keyof ChannelFormValues;

export const DEFAULT_FORM_VALUES: ChannelFormValues = {
    type: "slack",
    name: "",
    scope: "team",
    secret_value: "",
};

// ---------------------------------------------------------------------------
// Per-type secret field metadata (label, placeholder, validation hint)
// Mirrors the validation rules defined in API.md and backend schemas.py
// ---------------------------------------------------------------------------

export type SecretFieldMeta = {
    label: string;
    placeholder: string;
    hint: string;
};

export const SECRET_META: Record<ChannelType, SecretFieldMeta> = {
    slack: {
        label: "Slack Webhook URL",
        placeholder: "https://hooks.slack.com/services/…",
        hint: "Must start with https://hooks.slack.com/",
    },
    discord: {
        label: "Discord Webhook URL",
        placeholder: "https://discord.com/api/webhooks/…",
        hint: "Must start with https://discord.com/api/webhooks/",
    },
    email: {
        label: "Recipient Email",
        placeholder: "alerts@example.com",
        hint: "Must be a valid email address.",
    },
    webhook: {
        label: "Webhook URL",
        placeholder: "https://your-service.example.com/hook",
        hint: "Must use https:// and must not target localhost or private networks.",
    },
};

// ---------------------------------------------------------------------------
// Zod validation schema (client-side, mirrors backend rules)
// ---------------------------------------------------------------------------

function slackSecret(val: string): boolean {
    return val.startsWith("https://hooks.slack.com/");
}

function discordSecret(val: string): boolean {
    return val.startsWith("https://discord.com/api/webhooks/");
}

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;

function emailSecret(val: string): boolean {
    return EMAIL_RE.test(val);
}

const PRIVATE_HOSTS = [
    "localhost",
    "127.",
    "10.",
    "192.168.",
    "0.",
    "169.254.",
    "::1",
];

function isPrivateWebhook(val: string): boolean {
    try {
        const url = new URL(val);
        const host = url.hostname.toLowerCase();
        return PRIVATE_HOSTS.some(
            (pfx) => host === pfx || host.startsWith(pfx),
        );
    } catch {
        return false;
    }
}

/**
 * Validate the secret_value for a given channel type.
 * Returns an error message string, or null if valid.
 */
export function validateSecret(
    type: ChannelType,
    value: string,
): string | null {
    if (!value.trim()) return null; // empty = "keep current" on edit; required check done separately
    const v = value.trim();
    if (type === "slack") {
        return slackSecret(v)
            ? null
            : "Must start with https://hooks.slack.com/";
    }
    if (type === "discord") {
        return discordSecret(v)
            ? null
            : "Must start with https://discord.com/api/webhooks/";
    }
    if (type === "email") {
        return emailSecret(v) ? null : "Must be a valid email address.";
    }
    if (type === "webhook") {
        if (!v.startsWith("https://")) return "Must use https://";
        if (isPrivateWebhook(v))
            return "Must not target localhost or private networks.";
        return null;
    }
    return null;
}

// ---------------------------------------------------------------------------
// Full form validation
// ---------------------------------------------------------------------------

export const channelFormSchema = z.object({
    type: z.enum(CHANNEL_TYPES, {
        errorMap: () => ({ message: "Choose a valid channel type." }),
    }),
    name: z
        .string()
        .trim()
        .min(1, "Name is required.")
        .max(150, "Name must be 150 characters or fewer."),
    scope: z.string().min(1, "Scope is required."),
    // secret_value intentionally not run through Zod here — we use validateSecret
    // so we can provide type-specific messages.
    secret_value: z.string(),
});

export function validateChannelForm(
    values: ChannelFormValues,
    isEditMode: boolean,
): Partial<Record<ChannelField, string>> {
    const errors: Partial<Record<ChannelField, string>> = {};

    // Name
    if (!values.name.trim()) {
        errors.name = "Name is required.";
    } else if (values.name.trim().length > 150) {
        errors.name = "Name must be 150 characters or fewer.";
    }

    // Secret — required on create; optional (blank = keep current) on edit
    if (!isEditMode && !values.secret_value.trim()) {
        errors.secret_value = `${SECRET_META[values.type].label} is required.`;
    } else if (values.secret_value.trim()) {
        const secretErr = validateSecret(values.type, values.secret_value);
        if (secretErr) errors.secret_value = secretErr;
    }

    return errors;
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

/** Build the API payload for a create request. */
export function toCreatePayload(values: ChannelFormValues): {
    type: ChannelType;
    name: string;
    monitor_id: string | null;
    secret_value: string;
    configuration: Record<string, unknown>;
} {
    return {
        type: values.type,
        name: values.name.trim(),
        monitor_id: values.scope === "team" ? null : values.scope,
        secret_value: values.secret_value.trim(),
        configuration: {},
    };
}

/** Build the API payload for an update request (omit secret if blank). */
export function toUpdatePayload(
    values: ChannelFormValues,
    initial: ChannelFormValues,
): { name?: string; is_enabled?: boolean; secret_value?: string } {
    const patch: { name?: string; secret_value?: string } = {};

    if (initial.name.trim() !== values.name.trim()) {
        patch.name = values.name.trim();
    }
    if (values.secret_value.trim()) {
        patch.secret_value = values.secret_value.trim();
    }
    return patch;
}
