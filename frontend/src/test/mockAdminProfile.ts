import { vi } from "vitest";
import * as authApi from "../lib/authApi";

export function mockAdminProfile() {
    return vi.spyOn(authApi, "getMe").mockResolvedValue({
        id: "u-1",
        full_name: "Admin",
        email: "admin@example.com",
        is_active: true,
        created_at: "2026-10-01T10:00:00Z",
        team: { id: "t-1", name: "Team", role: "admin" },
    });
}
