/**
 * Types, enums, and helper functions for Incidents and Alert Deliveries (US-09, US-10, US-11).
 */

export type IncidentStatus = "open" | "resolved";

export type IncidentFilterStatus = "all" | "open" | "resolved";

export type DeliveryStatus = "pending" | "sent" | "failed";

export type DeliveryEventType = "opened" | "resolved";

export type ChannelType = "slack" | "discord" | "email" | "webhook";

export const CHANNEL_TYPE_LABELS: Record<ChannelType, string> = {
    slack: "Slack",
    discord: "Discord",
    email: "Email",
    webhook: "Webhook",
};

export const CHANNEL_TYPE_ICONS: Record<ChannelType, string> = {
    slack: "🔔",
    discord: "💬",
    email: "✉️",
    webhook: "🔗",
};

export type Incident = {
    id: string;
    monitor_id: string;
    monitor_name: string;
    status: IncidentStatus;
    opened_at: string;
    resolved_at: string | null;
    failure_count: number;
    recovery_count: number;
};

export type IncidentDetail = Incident & {
    monitor_url: string;
};

export type IncidentListResponse = {
    items: Incident[];
    page: number;
    page_size: number;
    total: number;
};

export type AlertDelivery = {
    id: string;
    incident_id: string;
    notification_channel_id: string;
    channel_name: string;
    channel_type: ChannelType;
    event_type: DeliveryEventType;
    status: DeliveryStatus;
    attempt_count: number;
    sent_at: string | null;
    error_message: string | null;
    created_at: string;
};

export type AlertDeliveryListResponse = {
    items: AlertDelivery[];
};

/**
 * Format an ISO date string to a locale-friendly date and time.
 */
export function formatDateTime(iso: string | null | undefined): string {
    if (!iso) return "—";
    try {
        return new Intl.DateTimeFormat(undefined, {
            dateStyle: "medium",
            timeStyle: "short",
        }).format(new Date(iso));
    } catch {
        return iso;
    }
}

/**
 * Calculates and formats a duration between opened_at and resolved_at (or now if unresolved).
 * Returns compact human-readable text such as "45s", "12m", "2h 15m", or "3d 4h".
 */
export function formatDuration(
    openedAt: string,
    resolvedAt?: string | null,
    now: Date = new Date(),
): string {
    const start = new Date(openedAt).getTime();
    const end = resolvedAt ? new Date(resolvedAt).getTime() : now.getTime();

    if (isNaN(start) || isNaN(end) || end < start) {
        return "—";
    }

    const diffSeconds = Math.max(0, Math.floor((end - start) / 1000));
    const mins = Math.floor(diffSeconds / 60);
    const hours = Math.floor(mins / 60);
    const days = Math.floor(hours / 24);

    if (days > 0) {
        const remHours = hours % 24;
        return remHours > 0 ? `${days}d ${remHours}h` : `${days}d`;
    }
    if (hours > 0) {
        const remMins = mins % 60;
        return remMins > 0 ? `${hours}h ${remMins}m` : `${hours}h`;
    }
    if (mins > 0) {
        return `${mins}m`;
    }
    return `${diffSeconds}s`;
}

/**
 * Formats duration specifically according to incident acceptance criteria:
 * - An open incident shows how long it has been open (e.g. "Open for 15m").
 * - A resolved one shows its duration (e.g. "15m").
 */
export function formatIncidentDuration(
    incident: {
        status: IncidentStatus;
        opened_at: string;
        resolved_at?: string | null;
    },
    now: Date = new Date(),
): string {
    if (incident.status === "open") {
        const duration = formatDuration(incident.opened_at, null, now);
        return duration === "—" ? "Open" : `Open for ${duration}`;
    }
    return formatDuration(incident.opened_at, incident.resolved_at, now);
}

/**
 * Sorts incidents so open incidents appear first, ordered newest first by opened_at.
 */
export function sortIncidentsOpenFirst(incidents: Incident[]): Incident[] {
    return [...incidents].sort((a, b) => {
        if (a.status === "open" && b.status !== "open") return -1;
        if (a.status !== "open" && b.status === "open") return 1;
        return new Date(b.opened_at).getTime() - new Date(a.opened_at).getTime();
    });
}
