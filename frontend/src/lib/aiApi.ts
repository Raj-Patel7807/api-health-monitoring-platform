import { authenticatedFetch } from "./authenticatedFetch";

export type AIAnalysis = {
    id: string;
    incident_id: string;
    status: string;
    summary: string;
    root_cause?: string | null;
    suggested_actions: string[];
    investigation_steps: string[];
    prevention_steps: string[];
    model: string;
    error_message?: string | null;
    created_at: string;
};

export type AIAnalysisResponse = AIAnalysis;

export class AIApiError extends Error {
    constructor(
        message: string,
        public status: number,
    ) {
        super(message);
        this.name = "AIApiError";
    }
}

export async function fetchIncidentAIAnalysis(
    incidentId: string,
): Promise<AIAnalysis> {
    const response = await authenticatedFetch(
        `/api/v1/incidents/${incidentId}/ai-analysis`,
    );
    if (!response.ok) {
        let msg = "Could not fetch AI analysis for incident.";
        try {
            const err = await response.json();
            if (err?.detail) msg = err.detail;
        } catch {
            // keep default
        }
        throw new AIApiError(msg, response.status);
    }
    return response.json();
}

export async function triggerIncidentAIAnalysis(
    incidentId: string,
): Promise<AIAnalysis> {
    const response = await authenticatedFetch(
        `/api/v1/incidents/${incidentId}/ai-analysis`,
        {
            method: "POST",
        },
    );
    if (!response.ok) {
        let msg = "Could not generate AI analysis for incident.";
        try {
            const err = await response.json();
            if (err?.detail) msg = err.detail;
        } catch {
            // keep default
        }
        throw new AIApiError(msg, response.status);
    }
    return response.json();
}
