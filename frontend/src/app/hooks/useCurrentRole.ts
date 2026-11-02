/**
 * useCurrentRole — stubbed role hook (US-03).
 *
 * Returns the authenticated user's team role. Stubbed as "admin" until
 * GET /auth/me is extended to return the team + role (see API.md §Proposed
 * extension). Once that endpoint lands, replace this stub with a real
 * useQuery call.
 *
 * Acceptance criterion (US-03): a read_only user sees no add/edit/delete
 * controls. This hook provides the isReadOnly boolean that pages use for
 * conditional rendering.
 */

// Stub: hard-coded to "admin" so all controls are visible.
// Replace with: const { data } = useQuery({ queryKey: ["me"], queryFn: getMe })
//               return data?.team?.role ?? "read_only"
type Role = "admin" | "operator" | "read_only";

export function useCurrentRole(): { role: Role; isReadOnly: boolean } {
    // TODO(US-13): replace with real /auth/me call once backend ships the
    //              team+role extension.
    const role: Role = "admin";
    const isReadOnly = (role as string) === "read_only";
    return { role, isReadOnly };
}
