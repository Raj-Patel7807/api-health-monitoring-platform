# Database Design

PostgreSQL 16 is the single durable source of truth. Schema versioning is managed strictly via forward-only Alembic migrations. Direct or manual production schema modifications are prohibited.

---

## Active Schema & Entities

The production database schema comprises the following core entities:

1. **`users`**: User identities with secure bcrypt password hashes and email authentication.
2. **`teams`**: Multi-tenant organizations.
3. **`team_memberships`**: RBAC role bindings (`admin`, `operator`, `read_only`) associating users to teams.
4. **`monitors`**: Health check configurations (target URL, HTTP method, intervals, timeouts, failure/recovery thresholds, exponential backoff, soft delete).
5. **`health_check_results`**: Historical ping execution records (status code, response time in ms, timeout, connection/SSL errors, checked_at timestamp). Partition-friendly indexing by `(monitor_id, checked_at DESC)`.
6. **`incidents`**: Threshold-based incident states (`open`, `resolved`). Enforces a partial unique constraint (`ux_incident_one_open_per_monitor`) ensuring at most one active open incident per monitor.
7. **`alert_channels`**: Team notification targets (email, webhook) with encrypted credentials.
8. **`alert_deliveries`**: Log of alert notification attempts, idempotency keys, delivery status, and timestamps.
9. **`ai_analyses`**: Advisory explanations, probable root causes, recommended remediation, investigation steps, and prevention steps associated with incidents.

---

## Migration 0007 Cleanup (Problem C)

A forward-only migration (`0007_cleanup_unused_tables.py`) safely streamlined the schema by dropping unmapped, unused baseline tables that were deferred from the MVP:
- Dropped: `embeddings`, `audit_entries`, `reports`, `maintenance_windows`, `health_check_daily_rollups`, `monitor_assertions`.
- Cleaned: Foreign key `failed_assertion_id` removed from `health_check_results`.
- Enhanced: `ai_analyses` updated with structured diagnosis fields (`status`, `root_cause`, `suggested_actions`, `investigation_steps`, `prevention_steps`, `model`, `error_message`).

---

## Indexing & Performance Strategy

Key access indexes maintain high-throughput sub-50ms query latency (`NFR2`, `NFR4`):
- `health_check_results (monitor_id, checked_at DESC)`: Fast history retrieval and dashboard latest-result subqueries.
- `incidents (monitor_id, status, opened_at DESC)`: Rapid open-incident discovery and threshold state evaluation.
- `monitors (next_check_at, enabled)`: Efficient scheduling polling for Celery workers.
- `alert_deliveries (incident_id, created_at DESC)`: Incident timeline and delivery auditing.
- `team_memberships (user_id, team_id)`: Instantaneous RBAC validation and active-team resolution.

---

## Security & Reliability

- Sensitive values (webhook secrets, API credentials) are encrypted at rest using AES-256-GCM / Fernet keys.
- All transactional writes follow ACID semantics. Concurrency-critical state transitions (such as last-admin protection and concurrent check results) use row-level locking (`with_for_update()`) and transaction savepoints.
