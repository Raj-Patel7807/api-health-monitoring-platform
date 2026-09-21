# Database Design

PostgreSQL is the source of truth. pgvector is enabled in the same database for future embeddings and retrieval; no separate vector database is planned. Use UUID primary keys, `snake_case` names, UTC `created_at` and `updated_at` timestamps, and Alembic for every schema change. Do not apply manual production schema edits.

Planned entities include users, teams/memberships, monitors, maintenance windows, health check results, incidents, notification channels, alert deliveries, reports, audit entries, AI analyses, and embeddings. Relationships follow ownership: a team owns monitors, a monitor has results and incidents, and an incident has deliveries and optional AI analysis.

Planned access indexes include `health_check_results(monitor_id, checked_at DESC)`, `incidents(monitor_id, status, opened_at DESC)`, `monitors(next_check_at, enabled)`, and `alert_deliveries(incident_id, created_at DESC)`. Add an index only for a known access pattern. Recent 30-day data must stay fast (`NFR2`, `NFR4`); older raw data remains reachable and can gain daily rollups (`US-24`). Rollups must preserve required history rather than delete it.

Use transactions for changes that must succeed together, such as opening an incident and recording its transition. Audit important configuration and permission changes. Store secrets encrypted or with a secure secret manager when that feature is added; never store plaintext passwords, webhook secrets, access tokens, or provider keys in normal fields. Migrations are committed, named clearly, backward-aware, and not rewritten after sharing. The initial baseline enables `vector` idempotently.
