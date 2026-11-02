import { useState, type FormEvent, type ChangeEvent } from "react";
import { Link } from "react-router-dom";

import {
    HTTP_METHODS,
    MONITOR_LIMITS,
    validateMonitorForm,
    type HttpMethod,
    type MonitorField,
    type MonitorFormValues,
} from "../../lib/monitors";
import { ApiError } from "../../lib/monitorsApi";

export type MonitorFormProps = {
    initialValues: MonitorFormValues;
    submitLabel: string;
    submittingLabel: string;
    onSubmit: (values: MonitorFormValues) => Promise<void>;
    cancelTo: string;
};

const FIELD_IDS: Record<MonitorField, string> = {
    name: "monitor-name",
    url: "monitor-url",
    method: "monitor-method",
    expected_status_code: "monitor-expected-status",
    check_interval_seconds: "monitor-check-interval",
    timeout_seconds: "monitor-timeout",
    failure_threshold: "monitor-failure-threshold",
    recovery_threshold: "monitor-recovery-threshold",
    enabled: "monitor-enabled",
};

const FIELD_ORDER: MonitorField[] = [
    "name",
    "url",
    "method",
    "expected_status_code",
    "check_interval_seconds",
    "timeout_seconds",
    "failure_threshold",
    "recovery_threshold",
];

export function MonitorForm({
    initialValues,
    submitLabel,
    submittingLabel,
    onSubmit,
    cancelTo,
}: MonitorFormProps) {
    const [values, setValues] = useState<MonitorFormValues>(initialValues);
    const [fieldErrors, setFieldErrors] = useState<
        Partial<Record<MonitorField, string>>
    >({});
    const [formError, setFormError] = useState<string | null>(null);
    const [isSubmitting, setIsSubmitting] = useState(false);

    function handleChange(
        field: MonitorField,
        value: string | boolean | HttpMethod,
    ) {
        setValues((prev) => ({ ...prev, [field]: value }));
        if (fieldErrors[field]) {
            setFieldErrors((prev) => {
                const next = { ...prev };
                delete next[field];
                return next;
            });
        }
    }

    async function handleSubmit(event: FormEvent<HTMLFormElement>) {
        event.preventDefault();
        setFormError(null);

        const errors = validateMonitorForm(values);
        if (Object.keys(errors).length > 0) {
            setFieldErrors(errors);
            for (const field of FIELD_ORDER) {
                if (errors[field]) {
                    const el = document.getElementById(FIELD_IDS[field]);
                    el?.focus();
                    break;
                }
            }
            return;
        }

        setIsSubmitting(true);
        try {
            await onSubmit(values);
        } catch (err) {
            if (err instanceof ApiError) {
                const mapped: Partial<Record<MonitorField, string>> = {};
                const unmapped: string[] = [];

                for (const [key, msg] of Object.entries(err.fieldErrors)) {
                    if (msg && FIELD_ORDER.includes(key as MonitorField)) {
                        mapped[key as MonitorField] = msg;
                    } else if (msg) {
                        unmapped.push(msg);
                    }
                }

                setFieldErrors(mapped);

                if (unmapped.length > 0) {
                    setFormError(unmapped.join(" "));
                } else if (Object.keys(mapped).length === 0 && err.message) {
                    setFormError(err.message);
                } else {
                    setFormError(null);
                }
            } else {
                setFormError("Something went wrong. Please try again.");
            }
        } finally {
            setIsSubmitting(false);
        }
    }

    function getDescribedBy(
        field: MonitorField,
        hasHelpText: boolean,
    ): string | undefined {
        const hasError = Boolean(fieldErrors[field]);
        const errorId = `${field}-error`;
        const helpId = `${field}-help`;

        if (hasError && hasHelpText) {
            return `${errorId} ${helpId}`;
        }
        if (hasError) {
            return errorId;
        }
        if (hasHelpText) {
            return helpId;
        }
        return undefined;
    }

    return (
        <form noValidate className="monitors-form" onSubmit={handleSubmit}>
            {/* 1. Name */}
            <div className="monitors-field">
                <label htmlFor={FIELD_IDS.name}>Name</label>
                <input
                    id={FIELD_IDS.name}
                    type="text"
                    placeholder="Payment API"
                    value={values.name}
                    maxLength={MONITOR_LIMITS.name.maxLength}
                    aria-invalid={Boolean(fieldErrors.name)}
                    aria-describedby={getDescribedBy("name", false)}
                    onChange={(event: ChangeEvent<HTMLInputElement>) =>
                        handleChange("name", event.target.value)
                    }
                />
                {fieldErrors.name && (
                    <p
                        id="name-error"
                        role="alert"
                        className="monitors-field-error"
                    >
                        {fieldErrors.name}
                    </p>
                )}
            </div>

            {/* 2. URL */}
            <div className="monitors-field">
                <label htmlFor={FIELD_IDS.url}>URL</label>
                <input
                    id={FIELD_IDS.url}
                    type="url"
                    placeholder="https://api.example.com/health"
                    value={values.url}
                    aria-invalid={Boolean(fieldErrors.url)}
                    aria-describedby={getDescribedBy("url", false)}
                    onChange={(event: ChangeEvent<HTMLInputElement>) =>
                        handleChange("url", event.target.value)
                    }
                />
                {fieldErrors.url && (
                    <p
                        id="url-error"
                        role="alert"
                        className="monitors-field-error"
                    >
                        {fieldErrors.url}
                    </p>
                )}
            </div>

            {/* 3. HTTP method */}
            <div className="monitors-field">
                <label htmlFor={FIELD_IDS.method}>HTTP method</label>
                <select
                    id={FIELD_IDS.method}
                    value={values.method}
                    aria-invalid={Boolean(fieldErrors.method)}
                    aria-describedby={getDescribedBy("method", false)}
                    onChange={(event: ChangeEvent<HTMLSelectElement>) =>
                        handleChange("method", event.target.value as HttpMethod)
                    }
                >
                    {HTTP_METHODS.map((method) => (
                        <option key={method} value={method}>
                            {method}
                        </option>
                    ))}
                </select>
                {fieldErrors.method && (
                    <p
                        id="method-error"
                        role="alert"
                        className="monitors-field-error"
                    >
                        {fieldErrors.method}
                    </p>
                )}
            </div>

            {/* 4. Expected status code */}
            <div className="monitors-field">
                <label htmlFor={FIELD_IDS.expected_status_code}>
                    Expected status code
                </label>
                <input
                    id={FIELD_IDS.expected_status_code}
                    type="number"
                    inputMode="numeric"
                    step={1}
                    min={MONITOR_LIMITS.expected_status_code.min}
                    max={MONITOR_LIMITS.expected_status_code.max}
                    value={values.expected_status_code}
                    aria-invalid={Boolean(fieldErrors.expected_status_code)}
                    aria-describedby={getDescribedBy(
                        "expected_status_code",
                        true,
                    )}
                    onChange={(event: ChangeEvent<HTMLInputElement>) =>
                        handleChange("expected_status_code", event.target.value)
                    }
                />
                <p
                    id="expected_status_code-help"
                    className="monitors-help-text"
                >
                    100 to 599, usually 200.
                </p>
                {fieldErrors.expected_status_code && (
                    <p
                        id="expected_status_code-error"
                        role="alert"
                        className="monitors-field-error"
                    >
                        {fieldErrors.expected_status_code}
                    </p>
                )}
            </div>

            {/* 5. Check settings */}
            <fieldset className="monitors-fieldset">
                <legend className="monitors-legend">Check settings</legend>

                <div className="monitors-grid-2">
                    {/* Check interval */}
                    <div className="monitors-field">
                        <label htmlFor={FIELD_IDS.check_interval_seconds}>
                            Check interval (seconds)
                        </label>
                        <input
                            id={FIELD_IDS.check_interval_seconds}
                            type="number"
                            inputMode="numeric"
                            step={1}
                            min={MONITOR_LIMITS.check_interval_seconds.min}
                            value={values.check_interval_seconds}
                            aria-invalid={Boolean(
                                fieldErrors.check_interval_seconds,
                            )}
                            aria-describedby={getDescribedBy(
                                "check_interval_seconds",
                                true,
                            )}
                            onChange={(event: ChangeEvent<HTMLInputElement>) =>
                                handleChange(
                                    "check_interval_seconds",
                                    event.target.value,
                                )
                            }
                        />
                        <p
                            id="check_interval_seconds-help"
                            className="monitors-help-text"
                        >
                            Minimum 10 seconds.
                        </p>
                        {fieldErrors.check_interval_seconds && (
                            <p
                                id="check_interval_seconds-error"
                                role="alert"
                                className="monitors-field-error"
                            >
                                {fieldErrors.check_interval_seconds}
                            </p>
                        )}
                    </div>

                    {/* Timeout */}
                    <div className="monitors-field">
                        <label htmlFor={FIELD_IDS.timeout_seconds}>
                            Timeout (seconds)
                        </label>
                        <input
                            id={FIELD_IDS.timeout_seconds}
                            type="number"
                            inputMode="numeric"
                            step={1}
                            min={MONITOR_LIMITS.timeout_seconds.min}
                            max={MONITOR_LIMITS.timeout_seconds.max}
                            value={values.timeout_seconds}
                            aria-invalid={Boolean(fieldErrors.timeout_seconds)}
                            aria-describedby={getDescribedBy(
                                "timeout_seconds",
                                true,
                            )}
                            onChange={(event: ChangeEvent<HTMLInputElement>) =>
                                handleChange(
                                    "timeout_seconds",
                                    event.target.value,
                                )
                            }
                        />
                        <p
                            id="timeout_seconds-help"
                            className="monitors-help-text"
                        >
                            Between 1 and 60 seconds.
                        </p>
                        {fieldErrors.timeout_seconds && (
                            <p
                                id="timeout_seconds-error"
                                role="alert"
                                className="monitors-field-error"
                            >
                                {fieldErrors.timeout_seconds}
                            </p>
                        )}
                    </div>
                </div>

                <div className="monitors-grid-2">
                    {/* Failure threshold */}
                    <div className="monitors-field">
                        <label htmlFor={FIELD_IDS.failure_threshold}>
                            Failure threshold
                        </label>
                        <input
                            id={FIELD_IDS.failure_threshold}
                            type="number"
                            inputMode="numeric"
                            step={1}
                            min={MONITOR_LIMITS.failure_threshold.min}
                            value={values.failure_threshold}
                            aria-invalid={Boolean(
                                fieldErrors.failure_threshold,
                            )}
                            aria-describedby={getDescribedBy(
                                "failure_threshold",
                                true,
                            )}
                            onChange={(event: ChangeEvent<HTMLInputElement>) =>
                                handleChange(
                                    "failure_threshold",
                                    event.target.value,
                                )
                            }
                        />
                        <p
                            id="failure_threshold-help"
                            className="monitors-help-text"
                        >
                            Consecutive failures before an incident opens.
                            Minimum 1.
                        </p>
                        {fieldErrors.failure_threshold && (
                            <p
                                id="failure_threshold-error"
                                role="alert"
                                className="monitors-field-error"
                            >
                                {fieldErrors.failure_threshold}
                            </p>
                        )}
                    </div>

                    {/* Recovery threshold */}
                    <div className="monitors-field">
                        <label htmlFor={FIELD_IDS.recovery_threshold}>
                            Recovery threshold
                        </label>
                        <input
                            id={FIELD_IDS.recovery_threshold}
                            type="number"
                            inputMode="numeric"
                            step={1}
                            min={MONITOR_LIMITS.recovery_threshold.min}
                            value={values.recovery_threshold}
                            aria-invalid={Boolean(
                                fieldErrors.recovery_threshold,
                            )}
                            aria-describedby={getDescribedBy(
                                "recovery_threshold",
                                true,
                            )}
                            onChange={(event: ChangeEvent<HTMLInputElement>) =>
                                handleChange(
                                    "recovery_threshold",
                                    event.target.value,
                                )
                            }
                        />
                        <p
                            id="recovery_threshold-help"
                            className="monitors-help-text"
                        >
                            Consecutive successes before an incident resolves.
                            Minimum 1.
                        </p>
                        {fieldErrors.recovery_threshold && (
                            <p
                                id="recovery_threshold-error"
                                role="alert"
                                className="monitors-field-error"
                            >
                                {fieldErrors.recovery_threshold}
                            </p>
                        )}
                    </div>
                </div>
            </fieldset>

            {/* 6. Enabled checkbox */}
            <div className="monitors-checkbox-field">
                <input
                    id={FIELD_IDS.enabled}
                    type="checkbox"
                    checked={values.enabled}
                    onChange={(event: ChangeEvent<HTMLInputElement>) =>
                        handleChange("enabled", event.target.checked)
                    }
                />
                <label htmlFor={FIELD_IDS.enabled}>
                    Run scheduled checks for this monitor
                </label>
            </div>

            {/* Form-level error */}
            {formError && (
                <p role="alert" className="monitors-error-box">
                    {formError}
                </p>
            )}

            {/* Buttons */}
            <div className="monitors-form-actions">
                <button
                    type="submit"
                    className="monitors-button monitors-button--primary"
                    disabled={isSubmitting}
                >
                    {isSubmitting ? submittingLabel : submitLabel}
                </button>
                <Link
                    to={cancelTo}
                    className="monitors-button monitors-button--secondary"
                >
                    Cancel
                </Link>
            </div>
        </form>
    );
}
