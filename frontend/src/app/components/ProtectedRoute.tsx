import { useSyncExternalStore } from "react";
import { Navigate, Outlet } from "react-router-dom";

import { getSessionId, subscribeSession } from "../../lib/auth";

export function ProtectedRoute() {
    const sessionId = useSyncExternalStore(subscribeSession, getSessionId);
    if (!sessionId) {
        return <Navigate to="/login" replace />;
    }
    return <Outlet key={sessionId} />;
}

export function GuestRoute() {
    return getSessionId() ? <Navigate to="/dashboard" replace /> : <Outlet />;
}
