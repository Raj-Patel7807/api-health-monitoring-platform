import { z } from "zod";

export const HTTP_METHODS = [
    "GET",
    "HEAD",
    "POST",
    "PUT",
    "PATCH",
    "DELETE",
] as const;

export type HttpMethod = (typeof HTTP_METHODS)[number];

export type MonitorField =
    | "name"
    | "url"
    | "method"
    | "check_interval_seconds"
    | "timeout_seconds"
    | "expected_status_code"
    | "failure_threshold"
    | "recovery_threshold"
    | "enabled";

// Mirror backend/database/schema_mvp.sql and must change together with it.
export const MONITOR_LIMITS = {
    name: {
        maxLength: 150,
    },
    url: {
        regex: /^https?:\/\//i,
    },
    check_interval_seconds: {
        min: 10,
    },
    timeout_seconds: {
        min: 1,
        max: 60,
    },
    expected_status_code: {
        min: 100,
        max: 599,
    },
    failure_threshold: {
        min: 1,
    },
    recovery_threshold: {
        min: 1,
    },
} as const;

export type Monitor = {
    id: string;
    name: string;
    url: string;
    method: HttpMethod;
    enabled: boolean;
    check_interval_seconds: number;
    expected_status_code: number;
    created_at: string;
    timeout_seconds?: number;
    failure_threshold?: number;
    recovery_threshold?: number;
    consecutive_failures?: number;
    consecutive_successes?: number;
    next_check_at?: string | null;
    backoff_until?: string | null;
};

export type MonitorListResponse = {
    items: Monitor[];
    page: number;
    page_size: number;
    total: number;
};

export type MonitorFormValues = {
    name: string;
    url: string;
    method: HttpMethod;
    check_interval_seconds: string;
    timeout_seconds: string;
    expected_status_code: string;
    failure_threshold: string;
    recovery_threshold: string;
    enabled: boolean;
};

export type MonitorPayload = {
    name: string;
    url: string;
    method: HttpMethod;
    check_interval_seconds: number;
    timeout_seconds: number;
    expected_status_code: number;
    failure_threshold: number;
    recovery_threshold: number;
    enabled: boolean;
};

export const DEFAULT_FORM_VALUES: MonitorFormValues = {
    name: "",
    url: "",
    method: "GET",
    check_interval_seconds: "60",
    timeout_seconds: "10",
    expected_status_code: "200",
    failure_threshold: "3",
    recovery_threshold: "2",
    enabled: true,
};

const INTEGER_REGEX = /^-?\d+$/;

function isValidHttpUrl(value: string): boolean {
    try {
        const parsed = new URL(value);
        return parsed.protocol === "http:" || parsed.protocol === "https:";
    } catch {
        return false;
    }
}

export const monitorFormSchema = z.object({
    name: z
        .string()
        .trim()
        .min(1, "Name is required.")
        .max(
            MONITOR_LIMITS.name.maxLength,
            "Name must be 150 characters or fewer.",
        ),
    url: z
        .string()
        .trim()
        .min(1, "URL is required.")
        .refine(
            isValidHttpUrl,
            "Enter a valid URL starting with http:// or https://.",
        ),
    method: z.enum(HTTP_METHODS, {
        errorMap: () => ({ message: "Choose a valid HTTP method." }),
    }),
    check_interval_seconds: z
        .string()
        .trim()
        .min(1, "Check interval (seconds) is required.")
        .regex(INTEGER_REGEX, "Enter a whole number.")
        .refine(
            (val) => Number(val) >= MONITOR_LIMITS.check_interval_seconds.min,
            {
                message: "Check interval must be at least 10 seconds.",
            },
        ),
    timeout_seconds: z
        .string()
        .trim()
        .min(1, "Timeout (seconds) is required.")
        .regex(INTEGER_REGEX, "Enter a whole number.")
        .refine(
            (val) => {
                const num = Number(val);
                return (
                    num >= MONITOR_LIMITS.timeout_seconds.min &&
                    num <= MONITOR_LIMITS.timeout_seconds.max
                );
            },
            {
                message: "Timeout must be between 1 and 60 seconds.",
            },
        ),
    expected_status_code: z
        .string()
        .trim()
        .min(1, "Expected status code is required.")
        .regex(INTEGER_REGEX, "Enter a whole number.")
        .refine(
            (val) => {
                const num = Number(val);
                return (
                    num >= MONITOR_LIMITS.expected_status_code.min &&
                    num <= MONITOR_LIMITS.expected_status_code.max
                );
            },
            {
                message: "Expected status code must be between 100 and 599.",
            },
        ),
    failure_threshold: z
        .string()
        .trim()
        .min(1, "Failure threshold is required.")
        .regex(INTEGER_REGEX, "Enter a whole number.")
        .refine((val) => Number(val) >= MONITOR_LIMITS.failure_threshold.min, {
            message: "Failure threshold must be at least 1.",
        }),
    recovery_threshold: z
        .string()
        .trim()
        .min(1, "Recovery threshold is required.")
        .regex(INTEGER_REGEX, "Enter a whole number.")
        .refine((val) => Number(val) >= MONITOR_LIMITS.recovery_threshold.min, {
            message: "Recovery threshold must be at least 1.",
        }),
    enabled: z.boolean(),
});

export function validateMonitorForm(
    values: MonitorFormValues,
): Partial<Record<MonitorField, string>> {
    const result = monitorFormSchema.safeParse(values);
    if (result.success) {
        return {};
    }

    const fieldErrors: Partial<Record<MonitorField, string>> = {};
    for (const issue of result.error.issues) {
        const field = issue.path[0] as MonitorField;
        if (field && !fieldErrors[field]) {
            fieldErrors[field] = issue.message;
        }
    }
    return fieldErrors;
}

export function toPayload(values: MonitorFormValues): MonitorPayload {
    return {
        name: values.name.trim(),
        url: values.url.trim(),
        method: values.method,
        check_interval_seconds: Number(values.check_interval_seconds.trim()),
        timeout_seconds: Number(values.timeout_seconds.trim()),
        expected_status_code: Number(values.expected_status_code.trim()),
        failure_threshold: Number(values.failure_threshold.trim()),
        recovery_threshold: Number(values.recovery_threshold.trim()),
        enabled: values.enabled,
    };
}

export function toFormValues(monitor: Monitor): MonitorFormValues {
    return {
        name: monitor.name,
        url: monitor.url,
        method: monitor.method,
        check_interval_seconds: String(monitor.check_interval_seconds),
        timeout_seconds: String(
            monitor.timeout_seconds ?? DEFAULT_FORM_VALUES.timeout_seconds,
        ),
        expected_status_code: String(monitor.expected_status_code),
        failure_threshold: String(
            monitor.failure_threshold ?? DEFAULT_FORM_VALUES.failure_threshold,
        ),
        recovery_threshold: String(
            monitor.recovery_threshold ??
                DEFAULT_FORM_VALUES.recovery_threshold,
        ),
        enabled: monitor.enabled,
    };
}

export function changedFields(
    initial: MonitorFormValues,
    current: MonitorFormValues,
): Partial<MonitorPayload> {
    const changes: Partial<MonitorPayload> = {};

    if (initial.name.trim() !== current.name.trim()) {
        changes.name = current.name.trim();
    }
    if (initial.url.trim() !== current.url.trim()) {
        changes.url = current.url.trim();
    }
    if (initial.method !== current.method) {
        changes.method = current.method;
    }
    if (
        initial.check_interval_seconds.trim() !==
        current.check_interval_seconds.trim()
    ) {
        changes.check_interval_seconds = Number(
            current.check_interval_seconds.trim(),
        );
    }
    if (initial.timeout_seconds.trim() !== current.timeout_seconds.trim()) {
        changes.timeout_seconds = Number(current.timeout_seconds.trim());
    }
    if (
        initial.expected_status_code.trim() !==
        current.expected_status_code.trim()
    ) {
        changes.expected_status_code = Number(
            current.expected_status_code.trim(),
        );
    }
    if (initial.failure_threshold.trim() !== current.failure_threshold.trim()) {
        changes.failure_threshold = Number(current.failure_threshold.trim());
    }
    if (
        initial.recovery_threshold.trim() !== current.recovery_threshold.trim()
    ) {
        changes.recovery_threshold = Number(current.recovery_threshold.trim());
    }
    if (initial.enabled !== current.enabled) {
        changes.enabled = current.enabled;
    }

    return changes;
}
