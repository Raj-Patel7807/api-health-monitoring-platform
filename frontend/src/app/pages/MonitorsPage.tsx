import { useState, useEffect } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import {
    keepPreviousData,
    useMutation,
    useQuery,
    useQueryClient,
} from "@tanstack/react-query";

import { listMonitors, deleteMonitor, ApiError } from "../../lib/monitorsApi";
import {
    previewApiDocs,
    commitImportedMonitors,
    type CandidateMonitor,
} from "../../lib/importerApi";
import type { Monitor } from "../../lib/monitors";
import { useCurrentRole } from "../hooks/useCurrentRole";
import { AppNav } from "../components/AppNav";
import { ConfirmDialog } from "../components/ConfirmDialog";
import { ImportMarkdownModal } from "../components/ImportMarkdownModal";
import { ToastContainer } from "../components/Toast";
import { useToast } from "../components/useToast";
import "./monitors.css";

function formatDateTime(isoString: string): string {
    try {
        return new Intl.DateTimeFormat(undefined, {
            dateStyle: "short",
            timeStyle: "short",
        }).format(new Date(isoString));
    } catch {
        return isoString;
    }
}

export function MonitorsPage() {
    const navigate = useNavigate();
    const queryClient = useQueryClient();
    const [searchParams, setSearchParams] = useSearchParams();
    const { toasts, addToast, dismissToast } = useToast();

    // ID of the monitor the user wants to delete (null = dialog closed)
    const [pendingDeleteId, setPendingDeleteId] = useState<string | null>(null);
    const [isImportModalOpen, setIsImportModalOpen] = useState(false);

    const rawPage = parseInt(searchParams.get("page") ?? "1", 10);
    const page = Number.isInteger(rawPage) && rawPage >= 1 ? rawPage : 1;

    const { data, isLoading, isError, error, refetch } = useQuery({
        queryKey: ["monitors", { page }],
        queryFn: () => listMonitors(page, 20),
        placeholderData: keepPreviousData,
    });

    const { isReadOnly, isAdmin } = useCurrentRole();

    // Importer state
    const [showImporter, setShowImporter] = useState(false);
    const [importFile, setImportFile] = useState<File | null>(null);
    const [importBaseUrl, setImportBaseUrl] = useState("");
    const [candidates, setCandidates] = useState<CandidateMonitor[]>([]);
    const [selectedIndices, setSelectedIndices] = useState<Set<number>>(
        new Set(),
    );
    const [isScanning, setIsScanning] = useState(false);
    const [isImporting, setIsImporting] = useState(false);
    const [importerError, setImporterError] = useState<string | null>(null);

    const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        if (e.target.files && e.target.files[0]) {
            setImportFile(e.target.files[0]);
            setImporterError(null);
        }
    };

    const handleScanDocs = async () => {
        if (!importFile) {
            setImporterError("Please select an API documentation file.");
            return;
        }
        setIsScanning(true);
        setImporterError(null);
        try {
            const preview = await previewApiDocs(
                importFile,
                importBaseUrl || undefined,
            );
            setCandidates(preview.items);
            // Default select valid candidates
            const validIdxs = new Set<number>();
            preview.items.forEach((item, idx) => {
                if (item.is_valid) validIdxs.add(idx);
            });
            setSelectedIndices(validIdxs);
            if (preview.items.length === 0) {
                addToast(
                    "No endpoints were detected in the uploaded file.",
                    "error",
                );
            } else {
                addToast(
                    `Found ${preview.items.length} endpoint(s).`,
                    "success",
                );
            }
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Scanning failed.";
            setImporterError(msg);
            addToast(msg, "error");
        } finally {
            setIsScanning(false);
        }
    };

    const handleCandidateToggle = (idx: number) => {
        setSelectedIndices((prev) => {
            const next = new Set(prev);
            if (next.has(idx)) {
                next.delete(idx);
            } else {
                next.add(idx);
            }
            return next;
        });
    };

    const handleCandidateFieldChange = (
        idx: number,
        field: keyof CandidateMonitor,
        val: string | number | boolean | null | undefined,
    ) => {
        setCandidates((prev) => {
            const next = [...prev];
            next[idx] = { ...next[idx], [field]: val };
            return next;
        });
    };

    const handleCommitImport = async () => {
        const itemsToImport = candidates.filter((_, idx) =>
            selectedIndices.has(idx),
        );
        if (itemsToImport.length === 0) {
            setImporterError("No endpoints selected for import.");
            return;
        }
        setIsImporting(true);
        setImporterError(null);
        try {
            const res = await commitImportedMonitors(
                itemsToImport,
                importBaseUrl || undefined,
            );
            addToast(
                `Successfully imported ${res.imported_count} monitor(s)!`,
                "success",
            );
            await queryClient.invalidateQueries({ queryKey: ["monitors"] });
            await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
            // Reset importer
            setShowImporter(false);
            setImportFile(null);
            setCandidates([]);
            setSelectedIndices(new Set());
        } catch (err) {
            const msg = err instanceof Error ? err.message : "Import failed.";
            setImporterError(msg);
            addToast(msg, "error");
        } finally {
            setIsImporting(false);
        }
    };

    // Derived after data is declared
    const pendingDeleteMonitor =
        pendingDeleteId !== null
            ? ((data?.items ?? []).find((m) => m.id === pendingDeleteId) ??
              null)
            : null;

    useEffect(() => {
        if (error instanceof ApiError && error.status === 401) {
            navigate("/login", { replace: true });
        }
    }, [error, navigate]);

    const deleteMutation = useMutation({
        mutationFn: (id: string) => deleteMonitor(id),
        onSuccess: async () => {
            setPendingDeleteId(null);
            await queryClient.invalidateQueries({ queryKey: ["monitors"] });
            addToast("Monitor deleted successfully.", "success");
        },
        onError: (err) => {
            setPendingDeleteId(null);
            addToast(
                err instanceof ApiError
                    ? err.message
                    : "Could not delete monitor. Please try again.",
                "error",
            );
        },
    });

    const total = data?.total ?? 0;
    const pageSize = data?.page_size ?? 20;
    const totalPages = Math.max(1, Math.ceil(total / pageSize));
    const items: Monitor[] = data?.items ?? [];
    const isEmpty = !isLoading && !isError && page === 1 && items.length === 0;

    return (
        <>
            <main className="monitors-page">
                <AppNav />
                <header className="monitors-header">
                    <div className="monitors-header-text">
                        <h1>Monitors</h1>
                        <p className="monitors-subtitle">
                            The endpoints your team keeps an eye on.
                        </p>
                    </div>
                    {!isReadOnly && (
                        <div
                            style={{
                                display: "flex",
                                gap: "0.75rem",
                                alignItems: "center",
                            }}
                        >
                            <button
                                type="button"
                                className="monitors-button monitors-button--secondary"
                                onClick={() => setIsImportModalOpen(true)}
                                data-testid="import-markdown-btn"
                            >
                                🤖 Import with AI
                        <div style={{ display: "flex", gap: "0.75rem" }}>
                            <button
                                type="button"
                                className="monitors-button monitors-button--secondary"
                                onClick={() => setShowImporter(!showImporter)}
                                data-testid="toggle-importer-btn"
                            >
                                {showImporter
                                    ? "Close Import"
                                    : "📁 Import from Docs"}
                            </button>
                            <Link
                                to="/monitors/new"
                                className="monitors-button monitors-button--primary"
                                data-testid="add-monitor-btn"
                            >
                                Add monitor
                            </Link>
                        </div>
                    )}
                </header>

                {showImporter && (
                    <section
                        className="importer-panel"
                        data-testid="importer-panel"
                    >
                        <h2>Import Monitors from API Documentation</h2>
                        <p
                            className="monitors-subtitle"
                            style={{ marginBottom: "1rem" }}
                        >
                            Upload an api.md file or OpenAPI specification to
                            automatically discover and create monitors.
                        </p>

                        <div className="importer-dropzone">
                            <input
                                type="file"
                                accept=".md,.markdown,.json,.yaml,.yml,.txt"
                                onChange={handleFileChange}
                                className="importer-dropzone-input"
                                data-testid="importer-file-input"
                            />
                            {importFile && (
                                <p
                                    style={{
                                        marginTop: "0.5rem",
                                        fontWeight: 600,
                                    }}
                                >
                                    Selected file: {importFile.name} (
                                    {(importFile.size / 1024).toFixed(1)} KB)
                                </p>
                            )}
                        </div>

                        <div
                            style={{
                                display: "flex",
                                gap: "1rem",
                                alignItems: "flex-end",
                                marginBottom: "1rem",
                            }}
                        >
                            <div style={{ flex: 1 }}>
                                <label
                                    style={{
                                        display: "block",
                                        fontSize: "0.85rem",
                                        marginBottom: "0.25rem",
                                    }}
                                >
                                    Base URL (Prepended to relative paths, e.g.
                                    https://api.example.com):
                                </label>
                                <input
                                    type="url"
                                    className="importer-preview-input"
                                    placeholder="https://api.example.com"
                                    value={importBaseUrl}
                                    onChange={(e) =>
                                        setImportBaseUrl(e.target.value)
                                    }
                                    data-testid="importer-base-url-input"
                                />
                            </div>
                            <button
                                type="button"
                                className="monitors-button monitors-button--secondary"
                                onClick={handleScanDocs}
                                disabled={!importFile || isScanning}
                                data-testid="scan-docs-btn"
                            >
                                {isScanning ? "Scanning..." : "Scan Document"}
                            </button>
                        </div>

                        {importerError && (
                            <div
                                role="alert"
                                style={{
                                    color: "#f87171",
                                    marginBottom: "1rem",
                                }}
                            >
                                {importerError}
                            </div>
                        )}

                        {candidates.length > 0 && (
                            <div style={{ marginTop: "1rem" }}>
                                <div
                                    style={{
                                        display: "flex",
                                        justifyContent: "space-between",
                                        alignItems: "center",
                                    }}
                                >
                                    <h3>
                                        Discovered Endpoints (
                                        {candidates.length})
                                    </h3>
                                    <button
                                        type="button"
                                        className="monitors-button monitors-button--primary"
                                        onClick={handleCommitImport}
                                        disabled={
                                            isImporting ||
                                            selectedIndices.size === 0
                                        }
                                        data-testid="commit-import-btn"
                                    >
                                        {isImporting
                                            ? "Importing..."
                                            : `Import Selected (${selectedIndices.size})`}
                                    </button>
                                </div>

                                <div style={{ overflowX: "auto" }}>
                                    <table className="importer-preview-table">
                                        <thead>
                                            <tr>
                                                <th style={{ width: "40px" }}>
                                                    Select
                                                </th>
                                                <th>Name</th>
                                                <th>Method</th>
                                                <th>URL / Path</th>
                                                <th style={{ width: "80px" }}>
                                                    Status
                                                </th>
                                                <th>Validation</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            {candidates.map((cand, idx) => (
                                                <tr key={idx}>
                                                    <td>
                                                        <input
                                                            type="checkbox"
                                                            checked={selectedIndices.has(
                                                                idx,
                                                            )}
                                                            onChange={() =>
                                                                handleCandidateToggle(
                                                                    idx,
                                                                )
                                                            }
                                                            disabled={
                                                                !cand.is_valid &&
                                                                !importBaseUrl
                                                            }
                                                        />
                                                    </td>
                                                    <td>
                                                        <input
                                                            type="text"
                                                            className="importer-preview-input"
                                                            value={cand.name}
                                                            onChange={(e) =>
                                                                handleCandidateFieldChange(
                                                                    idx,
                                                                    "name",
                                                                    e.target
                                                                        .value,
                                                                )
                                                            }
                                                        />
                                                    </td>
                                                    <td>
                                                        <span className="monitors-chip monitors-chip--method">
                                                            {cand.method}
                                                        </span>
                                                    </td>
                                                    <td>
                                                        <input
                                                            type="text"
                                                            className="importer-preview-input"
                                                            value={cand.url}
                                                            onChange={(e) =>
                                                                handleCandidateFieldChange(
                                                                    idx,
                                                                    "url",
                                                                    e.target
                                                                        .value,
                                                                )
                                                            }
                                                        />
                                                    </td>
                                                    <td>
                                                        <input
                                                            type="number"
                                                            className="importer-preview-input"
                                                            value={
                                                                cand.expected_status_code
                                                            }
                                                            onChange={(e) =>
                                                                handleCandidateFieldChange(
                                                                    idx,
                                                                    "expected_status_code",
                                                                    parseInt(
                                                                        e.target
                                                                            .value,
                                                                        10,
                                                                    ),
                                                                )
                                                            }
                                                        />
                                                    </td>
                                                    <td>
                                                        {cand.is_valid ? (
                                                            <span className="importer-badge-valid">
                                                                Valid
                                                            </span>
                                                        ) : (
                                                            <span
                                                                className="importer-badge-invalid"
                                                                title={
                                                                    cand.validation_error ||
                                                                    ""
                                                                }
                                                            >
                                                                {cand.validation_error ||
                                                                    "Invalid"}
                                                            </span>
                                                        )}
                                                    </td>
                                                </tr>
                                            ))}
                                        </tbody>
                                    </table>
                                </div>
                            </div>
                        )}
                    </section>
                )}

                <section className="monitors-card">
                    {isLoading && (
                        <div
                            role="status"
                            className="monitors-state-box"
                            aria-live="polite"
                        >
                            <span className="spinner" aria-hidden="true" />
                            <p>Loading monitors...</p>
                        </div>
                    )}

                    {isError && (
                        <div role="alert" className="monitors-state-box">
                            <h2>Could not load monitors</h2>
                            <p>
                                {error instanceof Error
                                    ? error.message
                                    : "Something went wrong."}
                            </p>
                            <button
                                type="button"
                                className="monitors-button monitors-button--secondary"
                                onClick={() => void refetch()}
                            >
                                Try again
                            </button>
                        </div>
                    )}

                    {isEmpty && (
                        <div className="monitors-state-box">
                            <h2>No monitors yet</h2>
                            <p>
                                Start tracking your endpoints to detect downtime
                                and incidents early.
                            </p>
                            {!isReadOnly && (
                                <Link
                                    to="/monitors/new"
                                    className="monitors-button monitors-button--primary"
                                >
                                    Add your first monitor
                                </Link>
                            )}
                        </div>
                    )}

                    {!isLoading && !isError && !isEmpty && (
                        <>
                            <div className="monitors-table-container">
                                <table className="monitors-table">
                                    <caption className="monitors-sr-only">
                                        Monitors
                                    </caption>
                                    <thead>
                                        <tr>
                                            <th scope="col">Name</th>
                                            <th scope="col">Method</th>
                                            <th scope="col">Status</th>
                                            <th scope="col">Interval</th>
                                            <th scope="col">Expected</th>
                                            <th scope="col">Created</th>
                                            {!isReadOnly && (
                                                <th scope="col">Actions</th>
                                            )}
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {items.map((monitor) => (
                                            <tr key={monitor.id}>
                                                <td>
                                                    <div className="monitors-cell-name">
                                                        <Link
                                                            to={`/monitors/${monitor.id}`}
                                                        >
                                                            {monitor.name}
                                                        </Link>
                                                        <span className="monitors-url">
                                                            {monitor.url}
                                                        </span>
                                                    </div>
                                                </td>
                                                <td>
                                                    <span className="monitors-chip monitors-chip--method">
                                                        {monitor.method}
                                                    </span>
                                                </td>
                                                <td>
                                                    <span
                                                        className={`monitors-chip ${
                                                            monitor.enabled
                                                                ? "monitors-chip--ok"
                                                                : "monitors-chip--warning"
                                                        }`}
                                                    >
                                                        {monitor.enabled
                                                            ? "Enabled"
                                                            : "Paused"}
                                                    </span>
                                                </td>
                                                <td>
                                                    Every{" "}
                                                    {
                                                        monitor.check_interval_seconds
                                                    }
                                                    s
                                                </td>
                                                <td>
                                                    {
                                                        monitor.expected_status_code
                                                    }
                                                </td>
                                                <td>
                                                    {formatDateTime(
                                                        monitor.created_at,
                                                    )}
                                                </td>
                                                {!isReadOnly && (
                                                    <td>
                                                        <div className="monitors-actions-cell">
                                                            <Link
                                                                to={`/monitors/${monitor.id}/edit`}
                                                                className="monitors-edit-link"
                                                                aria-label={`Edit ${monitor.name}`}
                                                            >
                                                                Edit
                                                            </Link>
                                                            {isAdmin && (
                                                                <button
                                                                    type="button"
                                                                    className="monitors-delete-btn"
                                                                    aria-label={`Delete ${monitor.name}`}
                                                                    onClick={() =>
                                                                        setPendingDeleteId(
                                                                            monitor.id,
                                                                        )
                                                                    }
                                                                    data-testid={`delete-${monitor.id}`}
                                                                >
                                                                    Delete
                                                                </button>
                                                            )}
                                                        </div>
                                                    </td>
                                                )}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>

                            <nav
                                aria-label="Pagination"
                                className="monitors-pagination"
                            >
                                <span className="monitors-pagination-info">
                                    Page {page} of {totalPages} · {total}{" "}
                                    monitors
                                </span>
                                <div className="monitors-pagination-actions">
                                    <button
                                        type="button"
                                        className="monitors-button monitors-button--secondary"
                                        disabled={page <= 1}
                                        onClick={() =>
                                            setSearchParams({
                                                page: String(page - 1),
                                            })
                                        }
                                    >
                                        Previous
                                    </button>
                                    <button
                                        type="button"
                                        className="monitors-button monitors-button--secondary"
                                        disabled={page >= totalPages}
                                        onClick={() =>
                                            setSearchParams({
                                                page: String(page + 1),
                                            })
                                        }
                                    >
                                        Next
                                    </button>
                                </div>
                            </nav>
                        </>
                    )}
                </section>
            </main>

            {/* Delete confirmation */}
            <ConfirmDialog
                open={pendingDeleteId !== null}
                title="Delete monitor?"
                description={
                    pendingDeleteMonitor
                        ? `"${pendingDeleteMonitor.name}" and all its history will be permanently removed. This cannot be undone.`
                        : "This monitor will be permanently removed."
                }
                confirmLabel="Delete monitor"
                confirmingLabel="Deleting…"
                isConfirming={deleteMutation.isPending}
                onConfirm={() => {
                    if (pendingDeleteId) {
                        void deleteMutation.mutateAsync(pendingDeleteId);
                    }
                }}
                onCancel={() => setPendingDeleteId(null)}
            />

            {/* Toast notifications */}
            <ToastContainer toasts={toasts} onDismiss={dismissToast} />

            {/* AI Markdown Import Modal */}
            <ImportMarkdownModal
                isOpen={isImportModalOpen}
                onClose={() => setIsImportModalOpen(false)}
                onSuccess={(count) => {
                    void queryClient.invalidateQueries({
                        queryKey: ["monitors"],
                    });
                    addToast(
                        `${count} monitor${count > 1 ? "s" : ""} imported successfully!`,
                        "success",
                    );
                }}
            />
        </>
    );
}
