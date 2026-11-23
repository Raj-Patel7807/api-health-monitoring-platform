import { authenticatedFetch } from "./authenticatedFetch";

export type CandidateMonitor = {
    name: string;
    url: string;
    method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE" | "HEAD" | "OPTIONS";
    expected_status_code: number;
    check_interval_seconds: number;
    timeout_seconds: number;
    failure_threshold: number;
    recovery_threshold: number;
    description?: string | null;
    is_valid: boolean;
    validation_error?: string | null;
};

export type ImportPreviewResponse = {
    filename: string;
    total_found: number;
    valid_count: number;
    items: CandidateMonitor[];
};

export type ImportCommitResponse = {
    imported_count: number;
    monitor_ids: string[];
};

export class ImporterApiError extends Error {
    constructor(
        message: string,
        public status: number,
    ) {
        super(message);
        this.name = "ImporterApiError";
    }
}

export async function previewApiDocs(
    file: File,
    baseUrl?: string,
): Promise<ImportPreviewResponse> {
    const formData = new FormData();
    formData.append("file", file);
    if (baseUrl) {
        formData.append("base_url", baseUrl);
    }

    const response = await authenticatedFetch(
        "/api/v1/monitors/import/preview",
        {
            method: "POST",
            body: formData,
        },
    );

    if (!response.ok) {
        let msg = "Failed to preview API documentation.";
        try {
            const err = await response.json();
            if (err?.detail) msg = err.detail;
        } catch {
            // keep fallback
        }
        throw new ImporterApiError(msg, response.status);
    }

    return response.json();
}

export async function commitImportedMonitors(
    items: CandidateMonitor[],
    baseUrl?: string,
): Promise<ImportCommitResponse> {
    const response = await authenticatedFetch(
        "/api/v1/monitors/import/commit",
        {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
            },
            body: JSON.stringify({
                base_url: baseUrl || null,
                items,
            }),
        },
    );

    if (!response.ok) {
        let msg = "Failed to import monitors.";
        try {
            const err = await response.json();
            if (err?.detail) msg = err.detail;
        } catch {
            // keep fallback
        }
        throw new ImporterApiError(msg, response.status);
    }

    return response.json();
}
