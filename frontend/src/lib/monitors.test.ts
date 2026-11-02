import { describe, expect, it } from "vitest";

import {
    DEFAULT_FORM_VALUES,
    changedFields,
    toFormValues,
    toPayload,
    validateMonitorForm,
    type Monitor,
    type MonitorFormValues,
} from "./monitors";

describe("monitors validation and helpers", () => {
    it("valid defaults pass with no errors", () => {
        const errors = validateMonitorForm(DEFAULT_FORM_VALUES);
        // Note: name and url default to "" which requires user input
        expect(errors.method).toBeUndefined();
        expect(errors.check_interval_seconds).toBeUndefined();
        expect(errors.timeout_seconds).toBeUndefined();
        expect(errors.expected_status_code).toBeUndefined();
        expect(errors.failure_threshold).toBeUndefined();
        expect(errors.recovery_threshold).toBeUndefined();

        const validForm: MonitorFormValues = {
            ...DEFAULT_FORM_VALUES,
            name: "My Monitor",
            url: "https://example.com/health",
        };
        expect(validateMonitorForm(validForm)).toEqual({});
    });

    describe("boundaries and rules", () => {
        const baseValid: MonitorFormValues = {
            ...DEFAULT_FORM_VALUES,
            name: "API Service",
            url: "https://example.com/api",
        };

        it("validates name boundaries", () => {
            const emptyName = validateMonitorForm({
                ...baseValid,
                name: "   ",
            });
            expect(emptyName.name).toBe("Name is required.");

            const exact150 = "a".repeat(150);
            expect(
                validateMonitorForm({ ...baseValid, name: exact150 }).name,
            ).toBeUndefined();

            const over150 = "a".repeat(151);
            expect(
                validateMonitorForm({ ...baseValid, name: over150 }).name,
            ).toBe("Name must be 150 characters or fewer.");
        });

        it("validates url boundaries and protocols", () => {
            expect(validateMonitorForm({ ...baseValid, url: "" }).url).toBe(
                "URL is required.",
            );

            expect(
                validateMonitorForm({ ...baseValid, url: "ftp://x" }).url,
            ).toBe("Enter a valid URL starting with http:// or https://.");

            expect(
                validateMonitorForm({ ...baseValid, url: "example.com" }).url,
            ).toBe("Enter a valid URL starting with http:// or https://.");

            expect(
                validateMonitorForm({
                    ...baseValid,
                    url: "https://a.b/health",
                }).url,
            ).toBeUndefined();

            expect(
                validateMonitorForm({
                    ...baseValid,
                    url: "http://localhost:8000/health",
                }).url,
            ).toBeUndefined();
        });

        it("validates check_interval_seconds boundaries", () => {
            expect(
                validateMonitorForm({
                    ...baseValid,
                    check_interval_seconds: "9",
                }).check_interval_seconds,
            ).toBe("Check interval must be at least 10 seconds.");

            expect(
                validateMonitorForm({
                    ...baseValid,
                    check_interval_seconds: "10",
                }).check_interval_seconds,
            ).toBeUndefined();
        });

        it("validates timeout_seconds boundaries", () => {
            expect(
                validateMonitorForm({
                    ...baseValid,
                    timeout_seconds: "0",
                }).timeout_seconds,
            ).toBe("Timeout must be between 1 and 60 seconds.");

            expect(
                validateMonitorForm({
                    ...baseValid,
                    timeout_seconds: "61",
                }).timeout_seconds,
            ).toBe("Timeout must be between 1 and 60 seconds.");

            expect(
                validateMonitorForm({
                    ...baseValid,
                    timeout_seconds: "1",
                }).timeout_seconds,
            ).toBeUndefined();

            expect(
                validateMonitorForm({
                    ...baseValid,
                    timeout_seconds: "60",
                }).timeout_seconds,
            ).toBeUndefined();
        });

        it("validates expected_status_code boundaries", () => {
            expect(
                validateMonitorForm({
                    ...baseValid,
                    expected_status_code: "99",
                }).expected_status_code,
            ).toBe("Expected status code must be between 100 and 599.");

            expect(
                validateMonitorForm({
                    ...baseValid,
                    expected_status_code: "600",
                }).expected_status_code,
            ).toBe("Expected status code must be between 100 and 599.");

            expect(
                validateMonitorForm({
                    ...baseValid,
                    expected_status_code: "100",
                }).expected_status_code,
            ).toBeUndefined();

            expect(
                validateMonitorForm({
                    ...baseValid,
                    expected_status_code: "599",
                }).expected_status_code,
            ).toBeUndefined();
        });

        it("validates failure and recovery thresholds boundaries", () => {
            expect(
                validateMonitorForm({
                    ...baseValid,
                    failure_threshold: "0",
                }).failure_threshold,
            ).toBe("Failure threshold must be at least 1.");

            expect(
                validateMonitorForm({
                    ...baseValid,
                    failure_threshold: "1",
                }).failure_threshold,
            ).toBeUndefined();

            expect(
                validateMonitorForm({
                    ...baseValid,
                    recovery_threshold: "0",
                }).recovery_threshold,
            ).toBe("Recovery threshold must be at least 1.");

            expect(
                validateMonitorForm({
                    ...baseValid,
                    recovery_threshold: "1",
                }).recovery_threshold,
            ).toBeUndefined();
        });

        it("fails non-integer numeric inputs with Enter a whole number.", () => {
            expect(
                validateMonitorForm({
                    ...baseValid,
                    check_interval_seconds: "10.5",
                }).check_interval_seconds,
            ).toBe("Enter a whole number.");

            expect(
                validateMonitorForm({
                    ...baseValid,
                    timeout_seconds: "abc",
                }).timeout_seconds,
            ).toBe("Enter a whole number.");

            expect(
                validateMonitorForm({
                    ...baseValid,
                    expected_status_code: "200.5",
                }).expected_status_code,
            ).toBe("Enter a whole number.");

            expect(
                validateMonitorForm({
                    ...baseValid,
                    failure_threshold: "xyz",
                }).failure_threshold,
            ).toBe("Enter a whole number.");
        });
    });

    describe("conversion helpers", () => {
        it("toPayload converts strings to numbers and trims name and url", () => {
            const formValues: MonitorFormValues = {
                name: "  Payment Service  ",
                url: "  https://example.com/health  ",
                method: "POST",
                check_interval_seconds: " 120 ",
                timeout_seconds: " 15 ",
                expected_status_code: " 201 ",
                failure_threshold: " 5 ",
                recovery_threshold: " 3 ",
                enabled: false,
            };

            const payload = toPayload(formValues);
            expect(payload).toEqual({
                name: "Payment Service",
                url: "https://example.com/health",
                method: "POST",
                check_interval_seconds: 120,
                timeout_seconds: 15,
                expected_status_code: 201,
                failure_threshold: 5,
                recovery_threshold: 3,
                enabled: false,
            });
        });

        it("toFormValues falls back to defaults for missing optional fields", () => {
            const apiMonitor: Monitor = {
                id: "mon-123",
                name: "Auth Service",
                url: "https://auth.example.com/health",
                method: "GET",
                enabled: true,
                check_interval_seconds: 45,
                expected_status_code: 200,
                created_at: "2026-10-01T12:00:00Z",
                // timeout_seconds, failure_threshold, recovery_threshold are omitted
            };

            const formValues = toFormValues(apiMonitor);
            expect(formValues).toEqual({
                name: "Auth Service",
                url: "https://auth.example.com/health",
                method: "GET",
                enabled: true,
                check_interval_seconds: "45",
                timeout_seconds: "10",
                expected_status_code: "200",
                failure_threshold: "3",
                recovery_threshold: "2",
            });
        });

        it("changedFields returns only edited fields", () => {
            const initial: MonitorFormValues = {
                name: "Service A",
                url: "https://a.com/health",
                method: "GET",
                check_interval_seconds: "60",
                timeout_seconds: "10",
                expected_status_code: "200",
                failure_threshold: "3",
                recovery_threshold: "2",
                enabled: true,
            };

            // Identical values produce empty changes
            expect(changedFields(initial, { ...initial })).toEqual({});

            // Changing name only
            expect(
                changedFields(initial, { ...initial, name: "Service B" }),
            ).toEqual({ name: "Service B" });

            // Changing multiple fields
            expect(
                changedFields(initial, {
                    ...initial,
                    method: "POST",
                    check_interval_seconds: "120",
                    enabled: false,
                }),
            ).toEqual({
                method: "POST",
                check_interval_seconds: 120,
                enabled: false,
            });
        });
    });
});
