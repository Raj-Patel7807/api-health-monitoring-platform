# API Contract — MVP (Sprints 2–4)

Base path: `/api/v1`. Frontend builds against this with mocks; backend updates
this file **in the same PR** as any endpoint change.

**Status key used below**

| Mark | Meaning |
|---|---|
| ✅ Implemented | Section written from the real backend code. |
| 📝 Planned | Agreed shape, not built yet (Sprint 3 and 4). Backend confirms or adjusts in the first two days of the sprint. |
| ❓ Verify | Carried over from the first version of this file. Not yet checked against code. |

## What changed from v1

- **Auth rewritten to match the code.** Signup returns only a token pair (no `user`/`team` object); refresh returns a new token pair; `GET /auth/me` added.
- **Errors are FastAPI's default shape** (`{"detail": ...}`), not the custom `{"error": {...}}` shape v1 promised.
- **Channel list semantics changed:** omitting `monitor_id` now returns all team channels, not only team-wide ones.
- **Sprint 3 endpoints fully specified** (fields, enums, validation, error cases).
- `/auth/me` extension proposed so the UI knows the user's team and role.

---

## Conventions

### Authentication ✅
Send `Authorization: Bearer <access_token>` on every endpoint except
`POST /auth/signup`, `POST /auth/login` and `POST /auth/refresh`.

- Access token lifetime: 15 minutes. Refresh token lifetime: 7 days.
- A refresh token cannot be used as an access token (and vice versa) → 401.
- Missing `Authorization` header: FastAPI returns 401 or 403 depending on its version.
  Frontend rule: treat any 401 as "try refresh once, then go to login".

### Errors ✅
Errors use FastAPI's default body. There is no custom error envelope.

```json
// Business errors (401, 403, 404, 409): detail is a string
{ "detail": "An account with this email address already exists." }

// Validation errors (422): detail is a list, one entry per bad field
{ "detail": [ { "type": "string_too_short", "loc": ["body", "password"],
                "msg": "String should have at least 8 characters" } ] }
```

Frontend handling: if `detail` is a string, show it as a form-level message.
If it is a list, use the last item of `loc` as the field name and show `msg`
under that field. Do not log auth error bodies (422 entries can echo input).

| Status | When |
|---|---|
| 401 | Missing/invalid/expired token, wrong credentials |
| 403 | Authenticated but the role does not allow it, or account disabled |
| 404 | Resource does not exist **or belongs to another team** (never reveal which) |
| 409 | Conflict (duplicate email, last admin demotion, ...) |
| 422 | Request body or query failed validation |

### Pagination 📝
List endpoints marked *paginated* take `?page=1&page_size=20` (`page_size` max 100)
and return:
```json
{ "items": [ ... ], "page": 1, "page_size": 20, "total": 134 }
```
Endpoints marked *not paginated* return `{ "items": [ ... ] }`.

### Formats
- IDs are UUID strings. Timestamps are ISO 8601 in UTC (`2026-10-01T10:06:00Z`).
- JSON field names are `snake_case`.

---

## Auth ✅  (US-01)

### `POST /auth/signup`
Creates the user, a team, and an `admin` membership in one transaction. The
user is logged in immediately, so the **frontend should store the tokens and go
to the app, not back to the login page.**

```json
// Request
{ "email": "rahul@gmail.com",        // valid email, unique
  "full_name": "Rahul Sharma",       // 1–150 chars
  "password": "••••••••",            // 8–128 chars, not blank
  "team_name": "FinTech Engineering" // 1–150 chars
}

// 201 Response
{ "access_token": "jwt", "refresh_token": "jwt", "token_type": "bearer" }
```
Errors: `409` duplicate email, `422` validation.

### `POST /auth/login`
```json
// Request
{ "email": "rahul@gmail.com", "password": "••••••••" }   // password 1–128 chars

// 200 Response
{ "access_token": "jwt", "refresh_token": "jwt", "token_type": "bearer" }
```
Errors: `401` "Invalid email or password." (same message for wrong email and
wrong password), `403` "Account is disabled.", `422`.

### `POST /auth/refresh`
```json
// Request
{ "refresh_token": "jwt" }

// 200 Response: a NEW pair. Store both tokens, replacing the old ones.
{ "access_token": "jwt", "refresh_token": "jwt", "token_type": "bearer" }
```
Errors: `401` invalid/expired token, wrong token type, or user not found/inactive.

### `GET /auth/me`
```json
// 200 Response (current)
{ "id": "uuid", "email": "rahul@gmail.com", "full_name": "Rahul Sharma",
  "is_active": true, "created_at": "2026-10-01T10:00:00Z" }
```

**📝 Proposed extension (needed for role-aware UI in Sprint 3 and 4):**
```json
{ "id": "uuid", "email": "rahul@gmail.com", "full_name": "Rahul Sharma",
  "is_active": true, "created_at": "2026-10-01T10:00:00Z",
  "team": { "id": "uuid", "name": "FinTech Engineering", "role": "admin" } }
```
Without this, the frontend cannot tell whether to show edit controls for a
`read_only` user. The token currently carries only the user id (`sub`).

---

## Monitors ❓ Verify  (US-02)

Carried over from v1. Check each shape against the implemented router.

### `GET /monitors` (paginated)
```json
{ "items": [ {
    "id": "uuid", "name": "Payment API", "url": "https://api.example.com/health",
    "method": "GET", "enabled": true, "check_interval_seconds": 60,
    "expected_status_code": 200, "created_at": "2026-10-01T10:00:00Z"
} ], "page": 1, "page_size": 20, "total": 1 }
```

### `POST /monitors`
```json
{ "name": "Payment API", "url": "https://api.example.com/health", "method": "GET",
  "check_interval_seconds": 60, "timeout_seconds": 10, "expected_status_code": 200,
  "failure_threshold": 3, "recovery_threshold": 2 }
```
`201` returns the same shape as a list item. Roles: `admin`, `operator`.

Limits (from the database): `method` in GET/HEAD/POST/PUT/PATCH/DELETE;
`url` must start with `http://` or `https://`; `check_interval_seconds` ≥ 10;
`timeout_seconds` 1–60; `expected_status_code` 100–599; thresholds ≥ 1.

### `GET /monitors/{id}`
List fields plus `timeout_seconds`, `failure_threshold`, `recovery_threshold`,
`consecutive_failures`, `consecutive_successes`, `next_check_at`, `backoff_until`.

### `PATCH /monitors/{id}`
Same body as POST, every field optional. Roles: `admin`, `operator`.

### `DELETE /monitors/{id}`
Soft delete. `204`. Role: `admin`.

---

## Sprint 3 — Results, Channels, Incidents, Alerts 📝

Build the role checks into every Sprint 3 endpoint from day one (a
`require_role(...)` dependency based on the user's team membership). That avoids
retrofitting all of them in Sprint 4.

### Enumerations

| Field | Allowed values |
|---|---|
| result `status` | `healthy`, `failing`, `degraded` |
| channel `type` | `slack`, `discord`, `email`, `webhook` |
| incident `status` | `open`, `resolved` |
| delivery `event_type` | `opened`, `resolved` |
| delivery `status` | `pending`, `sent`, `failed` |

### `GET /monitors/{monitor_id}/results` (paginated)
Check history, newest first. Roles: any member.

Query: `from` and `to` (ISO 8601, UTC), `status` (optional filter).
Defaults: `to` = now, `from` = `to` − 24 hours. Maximum span 31 days, otherwise
`422`. (Results are stored in monthly partitions; an unbounded query would scan
all of them.)

```json
{ "items": [ {
    "id": "uuid", "monitor_id": "uuid",
    "checked_at": "2026-10-01T10:06:00Z", "status": "failing",
    "http_status_code": 500, "response_time_ms": 842,
    "timeout": false, "connection_error": false, "ssl_error": false,
    "error_message": "Expected status 200, got 500",
    "response_body_excerpt": null
} ], "page": 1, "page_size": 20, "total": 1440 }
```
Notes: `http_status_code` and `response_time_ms` are `null` on timeouts and
connection errors. `response_body_excerpt` is `null` for healthy checks and
at most 500 characters otherwise. Errors: `404` monitor not found.

### Notification channels

Channel object (returned by every channel endpoint):
```json
{ "id": "uuid", "type": "slack", "name": "Team Alerts",
  "monitor_id": null, "is_enabled": true,
  "secret_display_hint": "hooks.slack.com/…/X7Q",
  "configuration": {},
  "created_at": "2026-10-01T10:00:00Z", "updated_at": "2026-10-01T10:00:00Z" }
```
`monitor_id: null` means the channel applies to the whole team. A channel tied
to a monitor applies only to that monitor. The secret is **write-only**: it is
never returned, never logged, and appears only as `secret_display_hint`.

What `secret_value` holds per type:

| `type` | `secret_value` | Validation |
|---|---|---|
| `slack` | Incoming webhook URL | `https://hooks.slack.com/...` |
| `discord` | Webhook URL | `https://discord.com/api/webhooks/...` |
| `webhook` | Target URL | `https://` only; reject localhost and private IP ranges (SSRF) |
| `email` | Recipient email address | Valid email |

`configuration` is an optional object for non-secret options. No keys are
required for any type yet.

#### `GET /notification-channels` (not paginated)
Query: `monitor_id=<uuid>` returns channels attached to that monitor;
`scope=team` returns only team-wide channels. With no query, returns all
channels for the team. Roles: `admin`, `operator`. A `read_only` user gets
`403` (matches the RBAC matrix below).

#### `POST /notification-channels`
```json
{ "type": "slack", "name": "Team Alerts",     // name 1–150 chars
  "monitor_id": null,                          // optional
  "secret_value": "https://hooks.slack.com/services/T00/B00/XXXX",
  "configuration": {} }
```
`201` returns the channel object. Roles: `admin`, `operator`.
Errors: `404` monitor not found, `422` bad URL/email for the chosen type.

#### `PATCH /notification-channels/{id}`
Optional fields: `name`, `is_enabled`, `secret_value`, `configuration`.
Omit `secret_value` to keep the current one. `type` and `monitor_id` cannot be
changed (delete and recreate instead). `200` returns the channel object.

#### `DELETE /notification-channels/{id}`
`204`. Roles: `admin`, `operator`.

> **Backend note:** `alert_deliveries` has a foreign key to
> `notification_channels`, so a hard delete fails once a channel has any
> delivery history. Add a `deleted_at` column in a migration; DELETE sets it,
> the list hides deleted channels, and the alert dispatcher skips them.

### Incidents

Incident object:
```json
{ "id": "uuid", "monitor_id": "uuid", "monitor_name": "Payment API",
  "status": "open", "opened_at": "2026-10-01T10:06:00Z", "resolved_at": null,
  "failure_count": 3, "recovery_count": 0 }
```
Incidents are created and resolved only by the backend state machine. There
are no create, update or delete endpoints.

#### `GET /incidents` (paginated)
Query: `status=open|resolved`, `monitor_id=<uuid>`. Newest first (`opened_at`).
Roles: any member.

#### `GET /incidents/{id}`
The incident object plus `monitor_url`. `404` if not found or not in the
caller's team. (Acknowledge and timeline endpoints are out of Must Have scope.)

#### `GET /incidents/{id}/alert-deliveries` (not paginated)
```json
{ "items": [ {
    "id": "uuid", "incident_id": "uuid",
    "notification_channel_id": "uuid", "channel_name": "Team Alerts", "channel_type": "slack",
    "event_type": "opened", "status": "sent", "attempt_count": 1,
    "sent_at": "2026-10-01T10:06:05Z", "error_message": null,
    "created_at": "2026-10-01T10:06:02Z"
} ] }
```
Read-only. There is at most one delivery per incident, channel and event type.
`attempt_count` is 0–4. `error_message` must never contain the webhook URL or
token (HTTP client errors often include the URL, so scrub it).

---

## Sprint 4 — Dashboard & RBAC 📝  (US-13, US-19)

Unchanged from v1.

### `GET /dashboard`
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
Roles: `admin`, `operator`.

### `POST /team/members`
```json
{ "email": "arjun@gmail.com", "role": "read_only" }
```
Role: `admin`. Attaches an existing user to the team.

### `PATCH /team/members/{user_id}`
```json
{ "role": "operator" }
```
Role: `admin`. Demoting the last remaining `admin` returns `409`.

### RBAC matrix

| Action | admin | operator | read_only |
|---|:---:|:---:|:---:|
| View monitors, results, incidents, dashboard | ✅ | ✅ | ✅ |
| Create / edit / delete monitors | ✅ | ✅ | ❌ |
| View, create, edit, delete notification channels | ✅ | ✅ | ❌ |
| Manage team members and roles | ✅ | ❌ | ❌ |

A disallowed action returns `403` with `{"detail": "..."}`.

---

## Open questions for the backend team

1. **One team per user?** Endpoints say "the caller's team". Signup creates one team per user, so confirm that a user has exactly one team for the MVP and how the backend resolves it.
2. **`/auth/me` with team and role** (proposed above). Who adds it, and by when? Frontend needs it in week 5.
3. **Error shape:** confirm there is no custom exception handler that changes the `{"detail": ...}` format.
4. **Channel soft delete:** confirm the `deleted_at` migration (see the note under `DELETE /notification-channels`).
5. **Monitors section:** someone who has read the monitor router should compare it with the shapes above and mark it ✅.

## Not in this contract (deferred stories, do not build UI for these)

Response assertions (US-07), maintenance windows (US-04), uptime history and
rollups (US-14, US-24), reports (US-15), audit log (US-18), multi-region
(US-20), notification retry detail (US-12).