# API Contract — MVP

Base path: `/api/v1`. Frontend builds against this with mocks; backend updates
this file **in the same PR** as any endpoint change.

**Status key used below**

| Mark | Meaning |
|---|---|
| ✅ Implemented | Written from the real backend code and checked against it. |
| 📝 Planned | Agreed shape for Sprint 4, not built yet. Backend confirms or adjusts in the first two days. |
| ❓ Verify | Built in an earlier sprint, but this shape has not been checked against the code yet. Whoever reads the router marks it ✅ or fixes the text. |

## What changed from v2

- **Sprint 4 decisions recorded** (see "Decisions" at the end): how a user's team is resolved, who can delete a monitor, and the dashboard status values.
- **`GET /auth/me` now returns `team` with the user's role** (Sprint 4).
- **Dashboard and team members endpoints fully specified**, including errors.
- **RBAC matrix rewritten per endpoint.** Deleting a monitor is admin-only; `read_only` users cannot view notification channels; viewing members needs admin or operator.
- Sprint 3 endpoints are relabelled ❓ Verify, because they are built but their shapes were not compared with the code.

---

## Conventions

### Authentication ✅
Send `Authorization: Bearer <access_token>` on every endpoint except
`POST /auth/signup`, `POST /auth/login` and `POST /auth/refresh`.

- Access token lifetime: 15 minutes. Refresh token lifetime: 7 days.
- A refresh token cannot be used as an access token (and vice versa) → 401.
- The token carries only the user id. **The role is looked up on every request**, so a role change takes effect immediately.
- Missing `Authorization` header: FastAPI returns 401 or 403 depending on its version.
  Frontend rule: treat any 401 as "try refresh once, then go to login".

### Active team (Sprint 4 decision)
A user's **active team is the team they joined most recently.** Every team-scoped
endpoint ("the caller's team") uses it. Signup creates a team and makes the user
its admin; if the user is later added to another team, that team becomes the
active one, and the signup team stays in the database unused.

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
| 409 | Conflict (duplicate email, already a member, last admin demotion) |
| 422 | Request body or query failed validation |

### Pagination
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

## Auth  (US-01)

### `POST /auth/signup` ✅
Creates the user, a team, and an `admin` membership in one transaction. The
user is logged in immediately, so the **frontend stores the tokens and goes
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

### `POST /auth/login` ✅
```json
// Request
{ "email": "rahul@gmail.com", "password": "••••••••" }   // password 1–128 chars

// 200 Response
{ "access_token": "jwt", "refresh_token": "jwt", "token_type": "bearer" }
```
Errors: `401` "Invalid email or password." (same message for wrong email and
wrong password), `403` "Account is disabled.", `422`.

### `POST /auth/refresh` ✅
```json
// Request
{ "refresh_token": "jwt" }

// 200 Response: a NEW pair. Store both tokens, replacing the old ones.
{ "access_token": "jwt", "refresh_token": "jwt", "token_type": "bearer" }
```
Errors: `401` invalid/expired token, wrong token type, or user not found/inactive.

### `GET /auth/me` ✅
Returns the current user and their role in the active team. Any authenticated user.
```json
{ "id": "uuid", "email": "rahul@gmail.com", "full_name": "Rahul Sharma",
  "is_active": true, "created_at": "2026-10-01T10:00:00Z",
  "team": { "id": "uuid", "name": "FinTech Engineering", "role": "admin" } }
```

### `PATCH /auth/me` ✅
Updates profile details (full name, email) or changes password for the authenticated user.
Any authenticated user. Sensitive changes (password change) require `current_password`.
```json
// Request (all fields optional)
{ "full_name": "Rahul Sharma",
  "email": "rahul.updated@gmail.com",
  "current_password": "oldpassword123",
  "new_password": "newpassword123" }

// 200 Response: UserResponse with active team info
{ "id": "uuid", "email": "rahul.updated@gmail.com", "full_name": "Rahul Sharma",
  "is_active": true, "created_at": "2026-10-01T10:00:00Z",
  "team": { "id": "uuid", "name": "FinTech Engineering", "role": "admin" } }
```
Errors: `400` incorrect current password or missing current password when changing password, `409` duplicate email, `422` validation error.

---

## Monitors ❓ Verify  (US-02)

### `GET /monitors` (paginated)
Roles: any member.
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
Roles: any member. The detail response includes `health_status` using the dashboard rules below. List fields plus `timeout_seconds`, `failure_threshold`,
`recovery_threshold`, `consecutive_failures`, `consecutive_successes`,
`next_check_at`, `backoff_until`.

### `PATCH /monitors/{id}`
Same body as POST, every field optional. Roles: `admin`, `operator`.

### `DELETE /monitors/{id}`
Soft delete. `204`. Role: **`admin` only.**

---

## Results, Channels, Incidents, Alerts ❓ Verify  (Sprint 3: US-03, 08, 09, 10, 11)

Built in Sprint 3. The shapes below are the agreed contract. Roles are the ones
in the RBAC matrix at the end of this file.

### Enumerations

| Field | Allowed values |
|---|---|
| result `status` | `healthy`, `failing`, `degraded` |
| channel `type` | `slack`, `discord`, `email`, `webhook` |
| incident `status` | `open`, `resolved` |
| delivery `event_type` | `opened`, `resolved` |
| delivery `status` | `pending`, `sent`, `failed` |
| dashboard monitor `status` | `healthy`, `failing`, `unknown` |
| member `role` | `admin`, `operator`, `read_only` |

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
at most 500 characters otherwise. The `degraded` status is not produced yet.
Errors: `404` monitor not found.

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

All channel endpoints are for `admin` and `operator`. A `read_only` user gets
`403`, even to list them.

#### `GET /notification-channels` (not paginated)
Query: `monitor_id=<uuid>` returns channels attached to that monitor;
`scope=team` returns only team-wide channels. With no query, returns all
channels for the team.

#### `POST /notification-channels`
```json
{ "type": "slack", "name": "Team Alerts",     // name 1–150 chars
  "monitor_id": null,                          // optional
  "secret_value": "https://hooks.slack.com/services/T00/B00/XXXX",
  "configuration": {} }
```
`201` returns the channel object. Errors: `404` monitor not found, `422` bad
URL/email for the chosen type.

#### `PATCH /notification-channels/{id}`
Optional fields: `name`, `is_enabled`, `secret_value`, `configuration`.
Omit `secret_value` to keep the current one. `type` and `monitor_id` cannot be
changed (delete and recreate instead). `200` returns the channel object.

#### `DELETE /notification-channels/{id}`
Soft delete, `204`. The channel disappears from the list and the alert
dispatcher skips it; its past alert deliveries are kept.

### Incidents

Incident object:
```json
{ "id": "uuid", "monitor_id": "uuid", "monitor_name": "Payment API",
  "status": "open", "opened_at": "2026-10-01T10:06:00Z", "resolved_at": null,
  "failure_count": 3, "recovery_count": 0 }
```
Incidents are created and resolved only by the backend state machine. There
are no create, update or delete endpoints. Roles: any member.

#### `GET /incidents` (paginated)
Query: `status=open|resolved`, `monitor_id=<uuid>`. Newest first (`opened_at`).

#### `GET /incidents/{id}`
The incident object plus `monitor_url`. `404` if not found or not in the
caller's team.

#### `GET /incidents/{id}/alert-deliveries` (not paginated)
Roles: any member.
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
`error_message` never contains the webhook URL or token.

---

## Dashboard and team  📝  (Sprint 4: US-13, US-19)

### `GET /dashboard`
One call for the whole dashboard. Roles: any member.

```json
{ "monitors": [ {
    "id": "uuid", "name": "Payment API", "status": "failing",
    "last_checked_at": "2026-10-01T10:06:00Z", "last_response_time_ms": 842,
    "open_incident_id": "uuid"
} ],
  "summary": { "total_monitors": 12, "healthy": 9, "failing": 2, "unknown": 1, "open_incidents": 2 } }
```

Rules:
- `status` is `failing` when the monitor has an open incident. It is `healthy` when it has a recent result and no open incident (one or two failures below the threshold are not yet an incident). It is `unknown` when there is no open incident and no result in the last 24 hours.
- Disabled and deleted monitors are not returned and are not counted.
- Ordered failing first, then unknown, then healthy, and by name inside each group.
- `last_checked_at`, `last_response_time_ms` and `open_incident_id` are `null` when there is nothing to show. `last_response_time_ms` is also `null` when the last check timed out or could not connect.
- The backend uses a fixed number of queries no matter how many monitors there are.

### `GET /team/members` (not paginated)
Roles: `admin`, `operator`. `read_only` gets `403`.
```json
{ "items": [ { "user_id": "uuid", "email": "priya@gmail.com", "full_name": "Priya", "role": "operator" } ] }
```

### `POST /team/members`
Role: `admin`. Adds an **existing** user to the caller's team; the user must
have signed up already. This team becomes the user's active team.
```json
// Request
{ "email": "arjun@gmail.com", "role": "read_only" }

// 201 Response
{ "user_id": "uuid", "email": "arjun@gmail.com", "full_name": "Arjun", "role": "read_only" }
```
Errors: `404` no user with that email, `409` already a member, `422` bad role.

### `PATCH /team/members/{user_id}`
Role: `admin`.
```json
// Request
{ "role": "operator" }

// 200 Response: the member object, same shape as above
```
Errors: `404` the user is not a member of this team, `409` the change would
leave the team with no `admin` (this includes an admin changing their own role
when they are the last one), `422` bad role.

There is no endpoint to remove a member yet.

---

## Monitor Import — API Documentation Upload ✅

### `POST /monitors/import/preview` ✅

Uploads an API documentation file (Markdown or OpenAPI JSON/YAML) and returns
a preview of discovered endpoint candidates. No monitors are created yet.

**Auth:** Admin or Operator (Operator+ write permission required).

**Request:** multipart/form-data

| Field | Type | Required | Description |
|---|---|:---:|---|
| `file` | File | ✅ | The API documentation file. Max 2 MB, UTF-8. |
| `base_url` | string | ❌ | Optional base URL prepended to relative endpoint paths. |

Supported file formats:
- Markdown (`.md`): Parses `### GET /path` headings and `| METHOD | /path | STATUS |` tables.
- OpenAPI / Swagger (`openapi.json`, `swagger.yaml`, etc.): Parses `paths` from JSON or YAML.

```json
// 200 Response
{
    "filename": "api.md",
    "total_found": 5,
    "valid_count": 4,
    "items": [
        {
            "name": "GET /api/v1/users",
            "url": "https://api.example.com/api/v1/users",
            "method": "GET",
            "expected_status_code": 200,
            "check_interval_seconds": 30,
            "timeout_seconds": 10,
            "failure_threshold": 3,
            "recovery_threshold": 2,
            "description": "List users",
            "is_valid": true,
            "validation_error": null
        }
    ]
}
```

Errors: `400` non-UTF-8 file, `403` read_only role, `413` file exceeds 2 MB, `422` missing file.

---

### `POST /monitors/import/commit` ✅

Persists selected candidate monitors from the preview step as active monitors
belonging to the caller's team. SSRF validation is re-applied on each URL.

**Auth:** Admin or Operator.

**Request:** `application/json`

```json
{
    "base_url": null,
    "items": [
        {
            "name": "GET /api/v1/users",
            "url": "https://api.example.com/api/v1/users",
            "method": "GET",
            "expected_status_code": 200,
            "check_interval_seconds": 60,
            "timeout_seconds": 10
        }
    ]
}
```

```json
// 201 Response
{
    "imported_count": 2,
    "monitor_ids": ["uuid1", "uuid2"]
}
```

Errors: `400` empty items or SSRF-blocked URL, `403` read_only role, `422` invalid fields.

---

## AI Incident Assistance ✅

Asynchronous, advisory-only AI-generated incident analysis. Monitoring and
incident status remain strictly deterministic. AI is never the source of truth.

### `GET /incidents/{id}/ai-analysis` ✅

Returns the existing analysis for an incident, or synchronously generates one
using the configured AI provider (deterministic rules engine by default).

**Auth:** Caller must have read access to the incident's monitor's team.

```json
// 200 Response
{
    "id": "uuid",
    "incident_id": "uuid",
    "status": "completed",
    "summary": "The endpoint https://api.example.com/checkout timed out after 3 consecutive failures.",
    "root_cause": "High server latency or network saturation may have caused the timeout.",
    "suggested_actions": ["Check server CPU and memory", "Review recent deployments"],
    "investigation_steps": ["Inspect server logs", "Run curl with verbose output"],
    "prevention_steps": ["Set up auto-scaling", "Add circuit breakers"],
    "model": "deterministic-rules",
    "error_message": null,
    "created_at": "2026-11-24T00:00:00Z"
}
```

Errors: `404` incident not found or cross-team access.

---

### `POST /incidents/{id}/ai-analysis` ✅

Forces regeneration of the AI analysis for the given incident. Useful for
re-running after reviewing logs or changing LLM configuration.

**Auth:** Caller must have write access to the incident's monitor's team (operator+).

Returns the same response shape as `GET /incidents/{id}/ai-analysis`.

Errors: `403` read_only role, `404` incident not found or cross-team access.

---

## RBAC matrix

Enforced by a `require_role(...)` dependency on every route below. A resource
that belongs to another team returns `404` regardless of role.

| Action | admin | operator | read_only |
|---|:---:|:---:|:---:|
| View monitors, results, incidents, alert deliveries, dashboard | ✅ | ✅ | ✅ |
| Create and edit monitors | ✅ | ✅ | ❌ |
| Delete monitors | ✅ | ❌ | ❌ |
| View, create, edit and delete notification channels | ✅ | ✅ | ❌ (403, even to view) |
| View team members | ✅ | ✅ | ❌ |
| Add members and change roles | ✅ | ❌ | ❌ |
| Import API documentation (preview) | ✅ | ✅ | ❌ |
| Import API documentation (commit) | ✅ | ✅ | ❌ |
| View AI incident analysis | ✅ | ✅ | ✅ |
| Re-trigger AI incident analysis | ✅ | ✅ | ❌ |
| `GET /auth/me` | ✅ | ✅ | ✅ |
| `PATCH /auth/me` | ✅ | ✅ | ✅ |

Public routes (no token): signup, login, refresh, the health check, and the API docs.

A disallowed action returns `403` with `{"detail": "..."}`.

---

## Decisions

Made on day 1 of Sprint 4:
1. **Active team** is the team the user joined most recently (see Conventions).
2. **Deleting a monitor** is admin only.
3. **Dashboard statuses** are `healthy`, `failing`, `unknown`, with the rules above.

Still to verify:
- Compare the Monitors and Sprint 3 sections with the implemented routers and mark each ✅ or fix the text.
- Confirm there is no custom exception handler that changes the `{"detail": ...}` error format.

## Not in this contract (deferred stories, do not build UI for these)

Response assertions (US-07), maintenance windows (US-04), uptime history and
rollups (US-14, US-24), reports (US-15), audit log (US-18), multi-region
(US-20), notification retry detail (US-12), removing team members.