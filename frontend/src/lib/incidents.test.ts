import { describe, expect, it } from "vitest";
import {
    formatDateTime,
    formatDuration,
    formatIncidentDuration,
    sortIncidentsOpenFirst,
    type Incident,
} from "./incidents";

describe("incidents helpers", () => {
    describe("formatDateTime", () => {
        it("returns dash for null or undefined", () => {
            expect(formatDateTime(null)).toBe("—");
            expect(formatDateTime(undefined)).toBe("—");
        });

        it("formats a valid ISO timestamp", () => {
            const formatted = formatDateTime("2026-10-01T10:06:00Z");
            expect(formatted).not.toBe("—");
            expect(formatted).toBeTruthy();
        });
    });

    describe("formatDuration", () => {
        it("formats seconds", () => {
            const opened = "2026-10-01T10:00:00Z";
            const resolved = "2026-10-01T10:00:45Z";
            expect(formatDuration(opened, resolved)).toBe("45s");
        });

        it("formats minutes", () => {
            const opened = "2026-10-01T10:00:00Z";
            const resolved = "2026-10-01T10:15:00Z";
            expect(formatDuration(opened, resolved)).toBe("15m");
        });

        it("formats hours and minutes", () => {
            const opened = "2026-10-01T10:00:00Z";
            const resolved = "2026-10-01T12:30:00Z";
            expect(formatDuration(opened, resolved)).toBe("2h 30m");
        });

        it("formats days and hours", () => {
            const opened = "2026-10-01T10:00:00Z";
            const resolved = "2026-10-03T14:00:00Z";
            expect(formatDuration(opened, resolved)).toBe("2d 4h");
        });

        it("returns dash for invalid date input", () => {
            expect(formatDuration("invalid", "invalid")).toBe("—");
        });
    });

    describe("formatIncidentDuration", () => {
        it("formats an open incident as 'Open for <duration>'", () => {
            const openedAt = "2026-10-01T10:00:00Z";
            const now = new Date("2026-10-01T10:25:00Z");
            const result = formatIncidentDuration(
                { status: "open", opened_at: openedAt, resolved_at: null },
                now,
            );
            expect(result).toBe("Open for 25m");
        });

        it("formats a resolved incident as duration '<duration>'", () => {
            const openedAt = "2026-10-01T10:00:00Z";
            const resolvedAt = "2026-10-01T10:45:00Z";
            const result = formatIncidentDuration({
                status: "resolved",
                opened_at: openedAt,
                resolved_at: resolvedAt,
            });
            expect(result).toBe("45m");
        });
    });

    describe("sortIncidentsOpenFirst", () => {
        it("puts open incidents before resolved incidents, newest first", () => {
            const incidents: Incident[] = [
                {
                    id: "inc-1",
                    monitor_id: "m-1",
                    monitor_name: "API 1",
                    status: "resolved",
                    opened_at: "2026-10-02T10:00:00Z",
                    resolved_at: "2026-10-02T10:30:00Z",
                    failure_count: 3,
                    recovery_count: 2,
                },
                {
                    id: "inc-2",
                    monitor_id: "m-2",
                    monitor_name: "API 2",
                    status: "open",
                    opened_at: "2026-10-01T08:00:00Z",
                    resolved_at: null,
                    failure_count: 4,
                    recovery_count: 0,
                },
                {
                    id: "inc-3",
                    monitor_id: "m-3",
                    monitor_name: "API 3",
                    status: "open",
                    opened_at: "2026-10-03T12:00:00Z",
                    resolved_at: null,
                    failure_count: 5,
                    recovery_count: 0,
                },
            ];

            const sorted = sortIncidentsOpenFirst(incidents);
            expect(sorted.map((i) => i.id)).toEqual([
                "inc-3",
                "inc-2",
                "inc-1",
            ]);
        });
    });
});
