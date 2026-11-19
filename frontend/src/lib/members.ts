import type { Role } from "./authApi";

export type { Role };

export interface TeamMember {
    user_id: string;
    email: string;
    full_name?: string | null;
    role: Role;
    created_at?: string;
}

export interface MembersListResponse {
    items: TeamMember[];
    total?: number;
}

export interface AddMemberPayload {
    email: string;
    role: Role;
}

export interface UpdateMemberRolePayload {
    role: Role;
}
