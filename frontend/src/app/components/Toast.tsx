import { useEffect, useRef, type ReactNode } from "react";
import "./Toast.css";

export type ToastVariant = "success" | "error" | "info";

export type ToastMessage = {
    id: string;
    message: string;
    variant: ToastVariant;
};

const AUTO_DISMISS_MS = 4000;

const ICONS: Record<ToastVariant, ReactNode> = {
    success: (
        <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
        >
            <circle
                cx="8"
                cy="8"
                r="7"
                stroke="currentColor"
                strokeWidth="1.5"
            />
            <path
                d="M5 8l2 2 4-4"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
                strokeLinejoin="round"
            />
        </svg>
    ),
    error: (
        <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
        >
            <circle
                cx="8"
                cy="8"
                r="7"
                stroke="currentColor"
                strokeWidth="1.5"
            />
            <path
                d="M8 5v3M8 10.5v.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
            />
        </svg>
    ),
    info: (
        <svg
            width="16"
            height="16"
            viewBox="0 0 16 16"
            fill="none"
            aria-hidden="true"
        >
            <circle
                cx="8"
                cy="8"
                r="7"
                stroke="currentColor"
                strokeWidth="1.5"
            />
            <path
                d="M8 7v4M8 5.5v.5"
                stroke="currentColor"
                strokeWidth="1.5"
                strokeLinecap="round"
            />
        </svg>
    ),
};

type ToastItemProps = {
    toast: ToastMessage;
    onDismiss: (id: string) => void;
};

function ToastItem({ toast, onDismiss }: ToastItemProps) {
    const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

    useEffect(() => {
        timerRef.current = setTimeout(() => {
            onDismiss(toast.id);
        }, AUTO_DISMISS_MS);
        return () => {
            if (timerRef.current !== null) clearTimeout(timerRef.current);
        };
    }, [toast.id, onDismiss]);

    return (
        <div
            role="status"
            aria-live="polite"
            className={`toast toast--${toast.variant}`}
            data-testid="toast"
        >
            <span className="toast-icon">{ICONS[toast.variant]}</span>
            <span className="toast-message">{toast.message}</span>
            <button
                type="button"
                className="toast-close"
                aria-label="Dismiss notification"
                onClick={() => onDismiss(toast.id)}
            >
                ×
            </button>
        </div>
    );
}

type ToastContainerProps = {
    toasts: ToastMessage[];
    onDismiss: (id: string) => void;
};

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
    if (toasts.length === 0) return null;
    return (
        <div className="toast-container" aria-label="Notifications">
            {toasts.map((t) => (
                <ToastItem key={t.id} toast={t} onDismiss={onDismiss} />
            ))}
        </div>
    );
}
