import { useEffect, useRef } from "react";
import "./ConfirmDialog.css";

export type ConfirmDialogProps = {
    /** Whether the dialog is open */
    open: boolean;
    /** Title shown in the dialog header */
    title: string;
    /** Explanatory body text */
    description: string;
    /** Label for the destructive confirm button */
    confirmLabel?: string;
    /** Label shown while the async action runs */
    confirmingLabel?: string;
    /** Whether the action is in-flight (disables both buttons) */
    isConfirming?: boolean;
    onConfirm: () => void;
    onCancel: () => void;
};

/**
 * Accessible confirmation dialog built on the native <dialog> element.
 * - Closes on Escape and on backdrop click.
 * - Focuses the Cancel button on open (safe default).
 * - Renders nothing while closed so it has no DOM cost.
 */
export function ConfirmDialog({
    open,
    title,
    description,
    confirmLabel = "Delete",
    confirmingLabel = "Deleting…",
    isConfirming = false,
    onConfirm,
    onCancel,
}: ConfirmDialogProps) {
    const dialogRef = useRef<HTMLDialogElement>(null);
    const cancelBtnRef = useRef<HTMLButtonElement>(null);

    // Sync React open state → native dialog open/close
    useEffect(() => {
        const el = dialogRef.current;
        if (!el) return;
        if (open && !el.open) {
            el.showModal();
            cancelBtnRef.current?.focus();
        } else if (!open && el.open) {
            el.close();
        }
    }, [open]);

    // Handle Escape via the native 'cancel' event (prevent browser's own close)
    useEffect(() => {
        const el = dialogRef.current;
        if (!el) return;
        const handle = (e: Event) => {
            e.preventDefault();
            onCancel();
        };
        el.addEventListener("cancel", handle);
        return () => el.removeEventListener("cancel", handle);
    }, [onCancel]);

    function handleBackdropClick(e: React.MouseEvent<HTMLDialogElement>) {
        // The dialog element itself is the backdrop in native dialogs
        if (e.target === dialogRef.current) onCancel();
    }

    return (
        <dialog
            ref={dialogRef}
            className="confirm-dialog"
            aria-labelledby="confirm-dialog-title"
            aria-describedby="confirm-dialog-desc"
            onClick={handleBackdropClick}
        >
            <div className="confirm-dialog-panel">
                <div className="confirm-dialog-icon" aria-hidden="true">
                    <svg
                        width="22"
                        height="22"
                        viewBox="0 0 24 24"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="1.75"
                        strokeLinecap="round"
                        strokeLinejoin="round"
                    >
                        <path d="M10.29 3.86L1.82 18a2 2 0 001.71 3h16.94a2 2 0 001.71-3L13.71 3.86a2 2 0 00-3.42 0z" />
                        <line x1="12" y1="9" x2="12" y2="13" />
                        <line x1="12" y1="17" x2="12.01" y2="17" />
                    </svg>
                </div>

                <h2 id="confirm-dialog-title" className="confirm-dialog-title">
                    {title}
                </h2>

                <p id="confirm-dialog-desc" className="confirm-dialog-desc">
                    {description}
                </p>

                <div className="confirm-dialog-actions">
                    <button
                        ref={cancelBtnRef}
                        type="button"
                        className="monitors-button monitors-button--secondary"
                        disabled={isConfirming}
                        onClick={onCancel}
                    >
                        Cancel
                    </button>
                    <button
                        type="button"
                        className="monitors-button monitors-button--danger"
                        disabled={isConfirming}
                        onClick={onConfirm}
                        data-testid="confirm-delete-btn"
                    >
                        {isConfirming ? confirmingLabel : confirmLabel}
                    </button>
                </div>
            </div>
        </dialog>
    );
}
