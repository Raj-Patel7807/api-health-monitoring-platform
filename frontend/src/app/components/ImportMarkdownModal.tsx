import React, { useState, useRef } from "react";
import type { ExtractedEndpoint, MonitorPayload } from "../../lib/monitors";
import {
    extractMonitorsFromMarkdown,
    createMonitorsBatch,
    ApiError,
} from "../../lib/monitorsApi";
import "./ImportMarkdownModal.css";

interface ImportMarkdownModalProps {
    isOpen: boolean;
    onClose: () => void;
    onSuccess: (count: number) => void;
}

export function ImportMarkdownModal({
    isOpen,
    onClose,
    onSuccess,
}: ImportMarkdownModalProps) {
    const [step, setStep] = useState<1 | 2>(1);
    const [markdownContent, setMarkdownContent] = useState("");
    const [baseUrl, setBaseUrl] = useState("");
    const [fileName, setFileName] = useState<string | null>(null);

    const [isExtracting, setIsExtracting] = useState(false);
    const [isImporting, setIsImporting] = useState(false);
    const [errorMessage, setErrorMessage] = useState<string | null>(null);

    const [extractedEndpoints, setExtractedEndpoints] = useState<
        ExtractedEndpoint[]
    >([]);
    const [selectedIndices, setSelectedIndices] = useState<Set<number>>(
        new Set(),
    );
    const [warnings, setWarnings] = useState<string[]>([]);
    const [usedLlm, setUsedLlm] = useState(false);

    const fileInputRef = useRef<HTMLInputElement>(null);

    if (!isOpen) return null;

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0];
        if (!file) return;
        setFileName(file.name);
        const reader = new FileReader();
        reader.onload = (event) => {
            const content = event.target?.result as string;
            setMarkdownContent(content);
            setErrorMessage(null);
        };
        reader.readAsText(file);
    };

    const handleExtract = async () => {
        if (!markdownContent.trim()) {
            setErrorMessage(
                "Please paste Markdown content or upload an API markdown file.",
            );
            return;
        }

        setIsExtracting(true);
        setErrorMessage(null);

        try {
            const result = await extractMonitorsFromMarkdown(
                markdownContent,
                baseUrl,
            );
            if (result.endpoints.length === 0) {
                setErrorMessage(
                    "No valid API endpoints could be found in the provided markdown.",
                );
                setIsExtracting(false);
                return;
            }

            setExtractedEndpoints(result.endpoints);
            setSelectedIndices(new Set(result.endpoints.map((_, idx) => idx)));
            setWarnings(result.warnings || []);
            setUsedLlm(result.used_llm);
            setStep(2);
        } catch (err) {
            setErrorMessage(
                err instanceof ApiError
                    ? err.message
                    : "Failed to extract endpoints. Check server logs.",
            );
        } finally {
            setIsExtracting(false);
        }
    };

    const toggleSelectAll = () => {
        if (selectedIndices.size === extractedEndpoints.length) {
            setSelectedIndices(new Set());
        } else {
            setSelectedIndices(
                new Set(extractedEndpoints.map((_, idx) => idx)),
            );
        }
    };

    const toggleIndex = (index: number) => {
        const next = new Set(selectedIndices);
        if (next.has(index)) {
            next.delete(index);
        } else {
            next.add(index);
        }
        setSelectedIndices(next);
    };

    const updateEndpoint = (
        index: number,
        field: keyof ExtractedEndpoint,
        value: string | number,
    ) => {
        setExtractedEndpoints((prev) => {
            const updated = [...prev];
            updated[index] = { ...updated[index], [field]: value };
            return updated;
        });
    };

    const handleImportSelected = async () => {
        const selected = extractedEndpoints.filter((_, idx) =>
            selectedIndices.has(idx),
        );
        if (selected.length === 0) {
            setErrorMessage("Please select at least one endpoint to import.");
            return;
        }

        setIsImporting(true);
        setErrorMessage(null);

        try {
            const payloads: MonitorPayload[] = selected.map((ep) => ({
                name: ep.name.trim() || `${ep.method} Endpoint`,
                url: ep.url.trim(),
                method: ep.method,
                expected_status_code: Number(ep.expected_status_code) || 200,
                check_interval_seconds: ep.check_interval_seconds || 60,
                timeout_seconds: ep.timeout_seconds || 10,
                failure_threshold: ep.failure_threshold || 3,
                recovery_threshold: ep.recovery_threshold || 2,
                enabled: true,
            }));

            const response = await createMonitorsBatch(payloads);
            onSuccess(response.count);
            handleClose();
        } catch (err) {
            setErrorMessage(
                err instanceof ApiError
                    ? err.message
                    : "Failed to batch create monitors.",
            );
        } finally {
            setIsImporting(false);
        }
    };

    const handleClose = () => {
        setStep(1);
        setMarkdownContent("");
        setFileName(null);
        setErrorMessage(null);
        setExtractedEndpoints([]);
        setSelectedIndices(new Set());
        onClose();
    };

    return (
        <div className="import-md-modal-backdrop" onClick={handleClose}>
            <div
                className="import-md-modal-panel"
                onClick={(e) => e.stopPropagation()}
            >
                <header className="import-md-modal-header">
                    <h2>
                        <span>🤖</span> Import API Endpoints from Markdown
                    </h2>
                    <button
                        type="button"
                        className="import-md-close-btn"
                        onClick={handleClose}
                        aria-label="Close dialog"
                    >
                        ×
                    </button>
                </header>

                <div className="import-md-modal-body">
                    {errorMessage && (
                        <div
                            className="import-md-warning"
                            style={{ borderColor: "#fc8181", color: "#fed7d7" }}
                        >
                            {errorMessage}
                        </div>
                    )}

                    {step === 1 && (
                        <>
                            <div
                                className="import-md-dropzone"
                                onClick={() => fileInputRef.current?.click()}
                            >
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    style={{ display: "none" }}
                                    accept=".md,.markdown,.txt"
                                    onChange={handleFileChange}
                                />
                                <div className="import-md-dropzone-icon">
                                    📄
                                </div>
                                <p>
                                    {fileName ? (
                                        <strong>
                                            Selected file: {fileName}
                                        </strong>
                                    ) : (
                                        "Click to select or upload an API Markdown (.md) file"
                                    )}
                                </p>
                            </div>

                            <div className="import-md-field">
                                <label htmlFor="base-url-input">
                                    Base URL for Relative Routes
                                </label>
                                <input
                                    id="base-url-input"
                                    type="text"
                                    className="import-md-input"
                                    value={baseUrl}
                                    onChange={(e) => setBaseUrl(e.target.value)}
                                    placeholder="https://api.example.com"
                                />
                                <span className="import-md-hint">
                                    Prepend this domain if your markdown uses
                                    relative paths like <code>/auth/login</code>
                                    .
                                </span>
                            </div>

                            <div className="import-md-field">
                                <label htmlFor="markdown-textarea">
                                    Or Paste Markdown Content Directly
                                </label>
                                <textarea
                                    id="markdown-textarea"
                                    className="import-md-textarea"
                                    rows={8}
                                    value={markdownContent}
                                    onChange={(e) =>
                                        setMarkdownContent(e.target.value)
                                    }
                                    placeholder="Paste API documentation here (e.g. ### POST /api/v1/auth/signup)..."
                                />
                            </div>
                        </>
                    )}

                    {step === 2 && (
                        <>
                            <div className="import-md-ai-badge">
                                <span>✨</span>
                                <div>
                                    <strong>
                                        {usedLlm
                                            ? "Gemini Flash-Lite Agent"
                                            : "Heuristic Parser"}
                                    </strong>
                                    : Found {extractedEndpoints.length} endpoint
                                    {extractedEndpoints.length > 1 ? "s" : ""}.
                                    Review and confirm before adding.
                                </div>
                            </div>

                            {warnings.length > 0 && (
                                <div className="import-md-warning">
                                    {warnings.map((w, idx) => (
                                        <div key={idx}>{w}</div>
                                    ))}
                                </div>
                            )}

                            <div className="import-md-table-container">
                                <table className="import-md-table">
                                    <thead>
                                        <tr>
                                            <th style={{ width: "40px" }}>
                                                <input
                                                    type="checkbox"
                                                    checked={
                                                        selectedIndices.size ===
                                                            extractedEndpoints.length &&
                                                        extractedEndpoints.length >
                                                            0
                                                    }
                                                    onChange={toggleSelectAll}
                                                    aria-label="Select all endpoints"
                                                />
                                            </th>
                                            <th style={{ width: "90px" }}>
                                                Method
                                            </th>
                                            <th>Name</th>
                                            <th>Target URL</th>
                                            <th style={{ width: "80px" }}>
                                                Status
                                            </th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {extractedEndpoints.map((ep, idx) => (
                                            <tr key={idx}>
                                                <td>
                                                    <input
                                                        type="checkbox"
                                                        checked={selectedIndices.has(
                                                            idx,
                                                        )}
                                                        onChange={() =>
                                                            toggleIndex(idx)
                                                        }
                                                        aria-label={`Select ${ep.name}`}
                                                    />
                                                </td>
                                                <td>
                                                    <span
                                                        className={`import-md-badge badge-method-${ep.method.toLowerCase()}`}
                                                    >
                                                        {ep.method}
                                                    </span>
                                                </td>
                                                <td>
                                                    <input
                                                        type="text"
                                                        className="import-md-cell-input"
                                                        value={ep.name}
                                                        onChange={(e) =>
                                                            updateEndpoint(
                                                                idx,
                                                                "name",
                                                                e.target.value,
                                                            )
                                                        }
                                                    />
                                                </td>
                                                <td>
                                                    <input
                                                        type="text"
                                                        className="import-md-cell-input"
                                                        value={ep.url}
                                                        onChange={(e) =>
                                                            updateEndpoint(
                                                                idx,
                                                                "url",
                                                                e.target.value,
                                                            )
                                                        }
                                                    />
                                                </td>
                                                <td>
                                                    <input
                                                        type="number"
                                                        className="import-md-cell-input"
                                                        style={{
                                                            width: "65px",
                                                        }}
                                                        value={
                                                            ep.expected_status_code
                                                        }
                                                        onChange={(e) =>
                                                            updateEndpoint(
                                                                idx,
                                                                "expected_status_code",
                                                                Number(
                                                                    e.target
                                                                        .value,
                                                                ),
                                                            )
                                                        }
                                                    />
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    )}
                </div>

                <footer className="import-md-modal-footer">
                    {step === 1 ? (
                        <>
                            <button
                                type="button"
                                className="monitors-button monitors-button--secondary"
                                onClick={handleClose}
                                disabled={isExtracting}
                            >
                                Cancel
                            </button>
                            <button
                                type="button"
                                className="monitors-button monitors-button--primary"
                                onClick={handleExtract}
                                disabled={
                                    isExtracting || !markdownContent.trim()
                                }
                            >
                                {isExtracting
                                    ? "Extracting with AI..."
                                    : "Extract Endpoints with AI"}
                            </button>
                        </>
                    ) : (
                        <>
                            <button
                                type="button"
                                className="monitors-button monitors-button--secondary"
                                onClick={() => setStep(1)}
                                disabled={isImporting}
                            >
                                Back to Markdown
                            </button>
                            <button
                                type="button"
                                className="monitors-button monitors-button--primary"
                                onClick={handleImportSelected}
                                disabled={
                                    isImporting || selectedIndices.size === 0
                                }
                            >
                                {isImporting
                                    ? "Adding Monitors..."
                                    : `Confirm & Add (${selectedIndices.size}) Monitors`}
                            </button>
                        </>
                    )}
                </footer>
            </div>
        </div>
    );
}
