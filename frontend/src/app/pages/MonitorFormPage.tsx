import { useEffect } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";

import {
    DEFAULT_FORM_VALUES,
    changedFields,
    toFormValues,
    toPayload,
    type MonitorFormValues,
    type MonitorPayload,
} from "../../lib/monitors";
import {
    createMonitor,
    getMonitor,
    updateMonitor,
    ApiError,
} from "../../lib/monitorsApi";
import { MonitorForm } from "../components/MonitorForm";
import "./monitors.css";

export function MonitorFormPage() {
    const { monitorId } = useParams<{ monitorId?: string }>();
    const isEditMode = Boolean(monitorId);
    const navigate = useNavigate();
    const queryClient = useQueryClient();

    const {
        data: monitor,
        isLoading,
        isError,
        error,
        refetch,
    } = useQuery({
        queryKey: ["monitor", monitorId],
        queryFn: () => getMonitor(monitorId!),
        enabled: isEditMode,
    });

    const createMutation = useMutation({
        mutationFn: (payload: MonitorPayload) => createMonitor(payload),
    });

    const updateMutation = useMutation({
        mutationFn: ({
            id,
            payload,
        }: {
            id: string;
            payload: Partial<MonitorPayload>;
        }) => updateMonitor(id, payload),
    });

    useEffect(() => {
        if (error instanceof ApiError && error.status === 401) {
            navigate("/login", { replace: true });
        }
    }, [error, navigate]);

    async function handleCreate(values: MonitorFormValues) {
        try {
            await createMutation.mutateAsync(toPayload(values));
            await queryClient.invalidateQueries({ queryKey: ["monitors"] });
            navigate("/monitors");
        } catch (err) {
            if (err instanceof ApiError && err.status === 401) {
                navigate("/login", { replace: true });
                return;
            }
            throw err;
        }
    }

    async function handleEdit(values: MonitorFormValues) {
        if (!monitor || !monitorId) {
            return;
        }
        const changed = changedFields(toFormValues(monitor), values);
        if (Object.keys(changed).length === 0) {
            navigate("/monitors");
            return;
        }
        try {
            await updateMutation.mutateAsync({
                id: monitorId,
                payload: changed,
            });
            await queryClient.invalidateQueries({ queryKey: ["monitors"] });
            await queryClient.invalidateQueries({
                queryKey: ["monitor", monitorId],
            });
            navigate("/monitors");
        } catch (err) {
            if (err instanceof ApiError && err.status === 401) {
                navigate("/login", { replace: true });
                return;
            }
            throw err;
        }
    }

    if (isEditMode) {
        if (isLoading) {
            return (
                <main className="monitors-page monitors-page--form">
                    <Link to="/monitors" className="monitors-back-link">
                        Back to monitors
                    </Link>
                    <div className="monitors-card monitors-card--form">
                        <h1>Edit monitor</h1>
                        <div
                            role="status"
                            className="monitors-state-box"
                            aria-live="polite"
                        >
                            <span className="spinner" aria-hidden="true" />
                            <p>Loading monitor...</p>
                        </div>
                    </div>
                </main>
            );
        }

        if (isError) {
            const is404 = error instanceof ApiError && error.status === 404;
            return (
                <main className="monitors-page monitors-page--form">
                    <Link to="/monitors" className="monitors-back-link">
                        Back to monitors
                    </Link>
                    <div className="monitors-card monitors-card--form">
                        <h1>Edit monitor</h1>
                        <div
                            role={is404 ? undefined : "alert"}
                            className="monitors-state-box"
                        >
                            <h2>Monitor not found.</h2>
                            {is404 ? (
                                <p>
                                    The monitor you are looking for does not
                                    exist or was deleted.
                                </p>
                            ) : (
                                <p>
                                    {error instanceof Error
                                        ? error.message
                                        : "Something went wrong."}
                                </p>
                            )}
                            {is404 ? (
                                <Link
                                    to="/monitors"
                                    className="monitors-button monitors-button--secondary"
                                >
                                    Back to monitors
                                </Link>
                            ) : (
                                <button
                                    type="button"
                                    className="monitors-button monitors-button--secondary"
                                    onClick={() => void refetch()}
                                >
                                    Try again
                                </button>
                            )}
                        </div>
                    </div>
                </main>
            );
        }

        if (!monitor) {
            return null;
        }

        return (
            <main className="monitors-page monitors-page--form">
                <Link to="/monitors" className="monitors-back-link">
                    Back to monitors
                </Link>
                <div className="monitors-card monitors-card--form">
                    <h1>Edit monitor</h1>
                    <MonitorForm
                        key={monitor.id}
                        initialValues={toFormValues(monitor)}
                        submitLabel="Save changes"
                        submittingLabel="Saving..."
                        onSubmit={handleEdit}
                        cancelTo="/monitors"
                    />
                </div>
            </main>
        );
    }

    return (
        <main className="monitors-page monitors-page--form">
            <Link to="/monitors" className="monitors-back-link">
                Back to monitors
            </Link>
            <div className="monitors-card monitors-card--form">
                <h1>Add monitor</h1>
                <MonitorForm
                    initialValues={DEFAULT_FORM_VALUES}
                    submitLabel="Create monitor"
                    submittingLabel="Creating..."
                    onSubmit={handleCreate}
                    cancelTo="/monitors"
                />
            </div>
        </main>
    );
}
