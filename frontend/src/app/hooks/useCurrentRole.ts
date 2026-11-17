import { useQuery } from "@tanstack/react-query";
import { getMe, type Role } from "../../lib/authApi";
import { isLoggedIn } from "../../lib/auth";

export type { Role };

export interface UseCurrentRoleResult {
    role: Role;
    isReadOnly: boolean;
    isAdmin?: boolean;
    isOperator?: boolean;
    isLoading?: boolean;
    isError?: boolean;
    error?: Error | null;
    refetch?: () => void;
}

/**
 * useCurrentRole (US-19 / Task F2).
 *
 * Retrieves the authenticated user's current team role from GET /auth/me.
 *
 * Roles & Capabilities:
 * - admin: full read + write access across monitors, channels, and team members.
 * - operator: read + write monitors and channels; view-only team members (no member edits).
 * - read_only: view-only monitors, results, incidents, channels; no members access.
 */
export function useCurrentRole(): UseCurrentRoleResult {
    const loggedIn = isLoggedIn();

    const { data, isLoading, isError, error, refetch } = useQuery({
        queryKey: ["auth", "me"],
        queryFn: getMe,
        enabled: loggedIn,
        staleTime: 5 * 60 * 1000,
        retry: 1,
    });

    const role: Role = data?.team?.role ?? "admin";
    const isReadOnly = role === "read_only";
    const isAdmin = role === "admin";
    const isOperator = role === "operator";

    return {
        role,
        isReadOnly,
        isAdmin,
        isOperator,
        isLoading: loggedIn ? isLoading : false,
        isError,
        error: (error as Error) ?? null,
        refetch,
    };
}
