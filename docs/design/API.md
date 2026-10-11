# API Contract — MVP (Sprints 2–4)

This is the contract for the 15 Must Have stories in `SPRINTS.md`. Frontend
can build against this with mock data now; each section is unlocked as
backend delivers the matching sprint. Base path: `/api/v1`.

**Auth:** Bearer JWT in `Authorization: Header` on every endpoint except
`POST /auth/signup` and `POST /auth/login`. 401 if missing/invalid, 403 if
the role doesn't permit the action (see RBAC notes per endpoint, Sprint 4).

**Common error shape** (all non-2xx responses):
```json
{ "error": { "code": "string", "message": "human readable", "details": {} } }
```

**Pagination** (any list endpoint): query params `?page=1&page_size=20`,
response wrapper:
```json
{ "items": [...], "page": 1, "page_size": 20, "total": 134 }
```

---

## Sprint 2 — Auth & Endpoint Registration (US-01, US-02)

### `POST /auth/signup`
```json
// Request
{ "email": "rahul@gmail.com", "full_name": "Rahul Sharma", "password": "••••••••", "team_name": "FinTech Engineering" }

// 201 Response
{ "user": { "id": "uuid", "email": "rahul@gmail.com", "full_name": "Rahul Sharma" },
  "team": { "id": "uuid", "name": "FinTech Engineering" },
  "access_token": "jwt", "refresh_token": "jwt" }
```
Creates the user AND their first team in one call (US-01 — fast onboarding).
First team membership role is always `admin`.

### `POST /auth/login`
```json
// Request
{ "email": "rahul@gmail.com", "password": "••••••••" }
// 200 Response
{ "access_token": "jwt", "refresh_token": "jwt" }
```

### `POST /auth/refresh`
```json
{ "refresh_token": "jwt" } → { "access_token": "jwt" }
```

### `GET /monitors`
List monitors for the caller's team.
```json
{ "items": [ {
    "id": "uuid", "name": "Payment API", "url": "https://api.example.com/health",
    "method": "GET", "enabled": true, "check_interval_seconds": 60,
    "expected_status_code": 200, "created_at": "2026-10-01T10:00:00Z"
} ], "page": 1, "page_size": 20, "total": 1 }
```

### `POST /monitors`
```json
// Request
{ "name": "Payment API", "url": "https://api.example.com/health", "method": "GET",
  "check_interval_seconds": 60, "timeout_seconds": 10, "expected_status_code": 200,
  "failure_threshold": 3, "recovery_threshold": 2 }
// 201 Response: same shape as GET item above
```
Role required: `admin` or `operator`.

### `GET /monitors/{id}`
Full detail — same fields as list, plus `consecutive_failures`,
`consecutive_successes`, `next_check_at`, `backoff_until`.

### `PATCH /monitors/{id}`
Partial update, same body shape as POST (all fields optional). Role: `admin`/`operator`.

### `DELETE /monitors/{id}`
Soft delete (`deleted_at` set). 204 No Content. Role: `admin`.

---

## Sprint 3 — Results, Incidents, Notifications, Alerts (US-03, 08, 09, 10, 11)

### `GET /monitors/{id}/results`
Raw health-check history, most recent first.
```json
{ "items": [ {
    "id": "uuid", "checked_at": "2026-10-01T10:06:00Z", "status": "failing",
    "http_status_code": 500, "response_time_ms": 842,
    "timeout": false, "connection_error": false, "ssl_error": false,
    "error_message": "Internal Server Error"
} ], "page": 1, "page_size": 20, "total": 1440 }
```
Supports `?from=ISO8601&to=ISO8601` to scope the time range.

### `GET /notification-channels?monitor_id={id|null}`
`monitor_id` omitted or empty → team-wide channels only.
```json
{ "items": [ {
    "id": "uuid", "type": "slack", "name": "Team Alerts",
    "is_enabled": true, "secret_display_hint": "hooks.slack.com/…/X7Q",
    "monitor_id": null
} ] }
```
**Never returns the decrypted secret.** Only `secret_display_hint`.

### `POST /notification-channels`
```json
// Request
{ "type": "slack", "name": "Team Alerts", "monitor_id": null,
  "secret_value": "https://hooks.slack.com/services/T00/B00/XXXX",
  "configuration": {} }
// 201 Response: same shape as GET item above (secret_value never echoed back)
```
Role: `admin`/`operator`. Backend encrypts `secret_value` before storing;
never log it.

### `PATCH /notification-channels/{id}` / `DELETE /notification-channels/{id}`
Standard update/delete. `secret_value` optional on PATCH (omit to leave unchanged).

### `GET /incidents?status=open|resolved&monitor_id={id}`
```json
{ "items": [ {
    "id": "uuid", "monitor_id": "uuid", "status": "open",
    "opened_at": "2026-10-01T10:06:00Z", "resolved_at": null,
    "failure_count": 3, "recovery_count": 0
} ] }
```

### `GET /incidents/{id}`
Same shape as above, single object. (Timeline/acknowledge endpoints are
deferred — not in Must Have scope.)

### `GET /incidents/{id}/alert-deliveries`
```json
{ "items": [ {
    "id": "uuid", "notification_channel_id": "uuid", "event_type": "opened",
    "status": "sent", "attempt_count": 1, "sent_at": "2026-10-01T10:06:05Z"
} ] }
```
Read-only — alerts are triggered internally by the incident state machine,
never created directly via the API.

---

## Sprint 4 — Dashboard & RBAC (US-13, US-19)

### `GET /dashboard`
One call for the whole dashboard view (avoids N+1 calls from frontend).
```json
{ "monitors": [ {
    "id": "uuid", "name": "Payment API", "status": "failing",
    "last_checked_at": "2026-10-01T10:06:00Z", "last_response_time_ms": 842,
    "open_incident_id": "uuid"
} ],
  "summary": { "total_monitors": 12, "healthy": 10, "failing": 2, "open_incidents": 2 } }
```

### `GET /team/members`
```json
{ "items": [ { "user_id": "uuid", "email": "priya@gmail.com", "full_name": "Priya", "role": "operator" } ] }
```
Role: `admin`/`operator` to view; `admin` only to see pending invites.

### `POST /team/members`
```json
{ "email": "arjun@gmail.com", "role": "read_only" }
```
Role: `admin` only. Invites or attaches an existing user to the team.

### `PATCH /team/members/{user_id}`
```json
{ "role": "operator" }
```
Role: `admin` only. Cannot demote the last remaining `admin` on a team (409 if attempted).

### RBAC matrix (enforced on every endpoint above)

| Action | admin | operator | read_only |
|---|:---:|:---:|:---:|
| View monitors, results, incidents, dashboard | ✅ | ✅ | ✅ |
| Create/edit/delete monitors | ✅ | ✅ | ❌ |
| Create/edit/delete notification channels | ✅ | ✅ | ❌ |
| View notification channel secrets (even masked) | ✅ | ✅ | ❌ (name/type only) |
| Manage team members / roles | ✅ | ❌ | ❌ |

Any disallowed action → `403` with the common error shape, `code: "forbidden"`.

---

## Not in this contract (deferred stories — do not build UI for these yet)

`monitor_assertions` (US-07), `maintenance_windows` (US-04),
`health_check_daily_rollups` / uptime history (US-14, US-24), `reports`
(US-15), `audit_entries` (US-18), multi-region (US-20), notification retry
detail (US-12). If any of these get picked up later, this file gets a new
section at that time — don't design frontend screens for them now.
