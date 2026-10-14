import { useCallback, useState } from "react";
import type { ToastMessage, ToastVariant } from "./Toast";

let nextId = 1;

export type UseToastReturn = {
    toasts: ToastMessage[];
    addToast: (message: string, variant?: ToastVariant) => void;
    dismissToast: (id: string) => void;
};

/**
 * Manages transient toast notifications.
 * Caps at 5 toasts to prevent pile-up; oldest is dropped when cap is exceeded.
 */
export function useToast(): UseToastReturn {
    const [toasts, setToasts] = useState<ToastMessage[]>([]);

    const addToast = useCallback(
        (message: string, variant: ToastVariant = "info") => {
            const id = String(nextId++);
            setToasts((prev) => {
                const next = [...prev, { id, message, variant }];
                return next.length > 5 ? next.slice(next.length - 5) : next;
            });
        },
        [],
    );

    const dismissToast = useCallback((id: string) => {
        setToasts((prev) => prev.filter((t) => t.id !== id));
    }, []);

    return { toasts, addToast, dismissToast };
}
