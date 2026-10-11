# API Health & Incident Monitoring — Database Documentation

Companion to `schema.sql` and `erd.md`. One sentence per table's job, the columns
that matter, how tables relate, and what each enum means.

## The system in one sentence

Users belong to teams → teams own monitors → monitors are checked repeatedly →
each check produces a result → N failures in a row open an incident → an incident
sends alerts → N successes in a row resolve it.

---

## Access & people

### `users`
Everyone who can log in.
- **Key columns:** `email` (CITEXT, case-insensitive, unique login), `password_hash` (never the raw password), `is_active` (deactivate without deleting).
- **Relationships:** 1 user → many `team_memberships`, `audit_entries`, `maintenance_windows` (as creator), `reports` (as requester).

### `teams`
A company/project that owns everything else.
- **Key columns:** `deleted_at` — soft delete; row stays, just hidden.
- **Relationships:** 1 team → many `monitors`, `notification_channels`, `reports`, `team_memberships`.

### `team_memberships`
Bridge table for the users↔teams many-to-many, and where RBAC lives.
- **Key columns:** `role` (enum `team_role`).
- **Status/type meaning:**
  - `admin` — full control, including delete.
  - `operator` — day-to-day create/edit (monitors, maintenance).
  - `read_only` — view only; writes return HTTP 403.

---

## Monitoring core

### `monitors` — core table
One row = one API endpoint being watched. Holds both the config and the live streak state.
- **Key columns:** `check_interval_seconds` vs `current_interval_seconds` (the latter grows during backoff), `failure_threshold`/`recovery_threshold` (how many in a row to open/close an incident), `consecutive_failures`/`consecutive_successes` (the live streak), `backoff_until`, `next_check_at` (drives the scheduler).
- **Relationships:** 1 monitor → many `monitor_assertions`, `health_check_results`, `health_check_daily_rollups`, `incidents`, `maintenance_windows`; optionally scoped by `notification_channels` and `reports`.

### `monitor_assertions`
Content-level rules checked inside an already-200 response (HTTP 200 doesn't mean *correct*).
- **Status/type meaning (`assertion_type`):** `text_contains`, `regex`, `jsonpath` — how `expression` is evaluated against the response body, compared to `expected_value`.

### `health_check_results` — core table
Raw evidence: one row per check, ever.
- **Key columns:** `checked_at` (also the partition key), `status`, `http_status_code`, `response_time_ms`, `timeout`/`connection_error`/`ssl_error` (distinct failure modes), `failed_assertion_id` (which rule failed, if any).
- **Status/type meaning (`check_status`):** `healthy`, `failing`, `degraded`.
- **Special PostgreSQL feature:** **range-partitioned monthly** on `checked_at` (`health_check_results_2026_09`, `_10`, …). At 1 check/min per monitor this table grows ~1,440 rows/monitor/day, so partitioning keeps queries fast and lets old months be archived or dropped cheaply. The primary key is composite (`id, checked_at`) because Postgres requires the partition key in the PK.

### `health_check_daily_rollups`
One pre-computed summary row per monitor per day, so "what was uptime on Sept 20?" doesn't scan raw history.
- **Key columns:** `uptime_percentage`, `p95_response_time_ms` (95% of checks were faster than this — shows outliers `avg` hides).
- Does **not** replace raw data; `health_check_results` stays untouched.

### `maintenance_windows`
Planned downtime, so it isn't treated as a real incident.
- **Status/type meaning (`maintenance_mode`):**
  - `suppress_alerts` — still checks and stores results, but creates/sends no alerts.
  - `pause_monitoring` — no checks at all: no result, no incident, no alert.
- The app layer must branch on this mode; it's not a plain boolean.

---

## Problems

### `incidents` — core table
A *confirmed* ongoing problem — never opened by a single failed check.
- **Key columns:** `failure_count`/`recovery_count`, `opened_at`/`resolved_at` (latter NULL while open).
- **Status/type meaning (`incident_status`):** `open`, `resolved`.
- **Relationships:** 1 incident → many `alert_deliveries`, many `ai_analyses`.

---

## Alerting

### `notification_channels`
*Where* alerts can go: email, Slack, Discord, webhook.
- **Key columns:** `monitor_id` nullable — NULL means "applies to the whole team," filled means monitor-specific. `configuration` (JSONB, non-secret settings) vs `secret_ref` (pointer to a vault — actual tokens are never stored here).
- **Status/type meaning (`channel_type`):** `email`, `slack`, `discord`, `webhook`.

### `alert_deliveries`
Log of what actually happened each time an alert was sent (channels = *can* send; deliveries = *did* send).
- **Key columns:** `attempt_count` (increments on retry), `sent_at`, `error_message`.
- **Status/type meaning (`delivery_status`):** `pending`, `sent`, `failed`.

---

## Reporting / audit / AI

### `reports`
Saved uptime reports for a team or one monitor over a period.
- **Key columns:** `period_start`/`period_end`, `uptime_percentage`, `total_downtime_seconds`.

### `audit_entries`
Security diary — who changed what, and when.
- **Key columns:** `entity_type` + `entity_id` (logical/polymorphic reference — not a real FK, since it can point at any table), `old_values`/`new_values` (JSONB before/after).
- **Status/type meaning (`audit_action`):** `INSERT`, `UPDATE`, `DELETE`.
- **Special PostgreSQL feature:** intended to be **append-only** — grant the app's DB role `INSERT`/`SELECT` only, never `UPDATE`/`DELETE`, so normal application code can't rewrite history.

### `ai_analyses`
AI-written explanation of an incident: summary + suggested next steps.
- **Key columns:** `suggested_actions` (JSONB list), `model` (which AI model produced it).
- **Golden rule:** AI never decides whether an API is healthy, whether an incident opens/closes, or what uptime is — those are always deterministic, rule-based columns elsewhere. AI only explains and suggests.

### `embeddings`
Vectorized text so similar past incidents can be found even when worded differently.
- **Key columns:** `entity_type` + `entity_id` (logical reference, typically to `ai_analyses`), `embedding` (`vector(1536)` via pgvector).
- **Special PostgreSQL feature:** **pgvector extension**, with an `ivfflat` cosine-similarity index (`vector_cosine_ops`) for fast nearest-neighbor search. Rebuild/tune the index once you have real data volume — it degrades with very small tables.

---

## Special PostgreSQL features used throughout

| Feature | Where | Why |
|---|---|---|
| `CITEXT` extension | `users.email` | Case-insensitive uniqueness without app-side `LOWER()` |
| `pgcrypto` (`gen_random_uuid()`) | every PK | UUID primary keys generated in the database |
| `pgvector` | `embeddings.embedding` | Similarity search over AI-analysis text |
| Range partitioning | `health_check_results` | Monthly partitions keep the highest-volume table fast; needs a new partition created each month (cron or `pg_partman`) |
| `JSONB` | `notification_channels.configuration`, `audit_entries.old_values/new_values`, `ai_analyses.suggested_actions` | Flexible, queryable semi-structured data |
| Soft delete (`deleted_at`) | `teams`, `monitors` | Preserve history instead of hard-deleting |
| `ENUM` types | roles, statuses, methods, etc. (see table above) | Constrains values at the database level instead of relying on app-side validation |
| Composite PK | `health_check_results (id, checked_at)` | Required by Postgres when partitioning by a column not otherwise in the PK |

## The five tables to learn first

```
monitors → health_check_results → incidents → alert_deliveries → notification_channels
```
