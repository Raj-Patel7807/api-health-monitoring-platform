import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import {
    AIApiError,
    AIAnalysisResponse,
    fetchIncidentAIAnalysis,
    triggerIncidentAIAnalysis,
} from "./aiApi";

describe("aiApi", () => {
    beforeEach(() => {
        localStorage.setItem("access_token", "test-token");
    });

    afterEach(() => {
        vi.unstubAllGlobals();
        localStorage.clear();
    });

    const mockAnalysis: AIAnalysisResponse = {
        id: "ai-1",
        incident_id: "inc-1",
        status: "completed",
        summary: "The endpoint timed out after 3 attempts.",
        root_cause: "High latency on target host.",
        suggested_actions: ["Check server resources", "Scale replicas"],
        investigation_steps: ["Examine server logs", "Test connectivity"],
        prevention_steps: ["Add auto-scaling", "Improve connection pool"],
        model: "deterministic-rules",
        error_message: null,
        created_at: "2026-11-24T00:00:00Z",
    };

    describe("fetchIncidentAIAnalysis", () => {
        it("returns AI analysis for the specified incident", async () => {
            const fetchMock = vi.fn(
                async () =>
                    new Response(JSON.stringify(mockAnalysis), {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    }),
            );
            vi.stubGlobal("fetch", fetchMock);

            const result = await fetchIncidentAIAnalysis("inc-1");
            expect(result).toEqual(mockAnalysis);
            expect(fetchMock).toHaveBeenCalledWith(
                "/api/v1/incidents/inc-1/ai-analysis",
                expect.any(Object),
            );
        });

        it("throws AIApiError on 404 or other error", async () => {
            const fetchMock = vi.fn(
                async () =>
                    new Response(
                        JSON.stringify({ detail: "Incident not found." }),
                        {
                            status: 404,
                            headers: { "Content-Type": "application/json" },
                        },
                    ),
            );
            vi.stubGlobal("fetch", fetchMock);

            await expect(fetchIncidentAIAnalysis("unknown")).rejects.toThrow(
                AIApiError,
            );
        });
    });

    describe("triggerIncidentAIAnalysis", () => {
        it("triggers re-generation and returns updated analysis", async () => {
            const fetchMock = vi.fn(
                async () =>
                    new Response(JSON.stringify(mockAnalysis), {
                        status: 200,
                        headers: { "Content-Type": "application/json" },
                    }),
            );
            vi.stubGlobal("fetch", fetchMock);

            const result = await triggerIncidentAIAnalysis("inc-1");
            expect(result).toEqual(mockAnalysis);
            expect(fetchMock).toHaveBeenCalledWith(
                "/api/v1/incidents/inc-1/ai-analysis",
                expect.objectContaining({ method: "POST" }),
            );
        });

        it("throws AIApiError on 403 forbidden", async () => {
            const fetchMock = vi.fn(
                async () =>
                    new Response(JSON.stringify({ detail: "Forbidden." }), {
                        status: 403,
                        headers: { "Content-Type": "application/json" },
                    }),
            );
            vi.stubGlobal("fetch", fetchMock);

            await expect(triggerIncidentAIAnalysis("inc-1")).rejects.toThrow(
                "Forbidden.",
            );
        });
    });
});
