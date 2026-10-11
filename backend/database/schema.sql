BEGIN;

-- ---------------------------------------------------------------------
-- Extensions
-- ---------------------------------------------------------------------
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS citext;     -- case-insensitive email
CREATE EXTENSION IF NOT EXISTS vector;     -- pgvector, for embeddings

-- ---------------------------------------------------------------------
-- Enum types
-- ---------------------------------------------------------------------
CREATE TYPE team_role AS ENUM ('admin', 'operator', 'read_only');
CREATE TYPE http_method AS ENUM ('GET', 'POST', 'PUT', 'PATCH', 'DELETE', 'HEAD', 'OPTIONS');
CREATE TYPE assertion_type AS ENUM ('text_contains', 'regex', 'jsonpath');
CREATE TYPE check_status AS ENUM ('healthy', 'failing', 'degraded');
CREATE TYPE incident_status AS ENUM ('open', 'resolved');
CREATE TYPE channel_type AS ENUM ('email', 'slack', 'discord', 'webhook');
CREATE TYPE delivery_status AS ENUM ('pending', 'sent', 'failed');
CREATE TYPE maintenance_mode AS ENUM ('suppress_alerts', 'pause_monitoring');
CREATE TYPE audit_action AS ENUM ('INSERT', 'UPDATE', 'DELETE');

-- =====================================================================
-- GROUP 1: Access & people
-- =====================================================================

CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email           CITEXT NOT NULL UNIQUE,
    full_name       VARCHAR(150) NOT NULL,
    password_hash   TEXT NOT NULL,
    is_active       BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE teams (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name            VARCHAR(150) NOT NULL,
    deleted_at      TIMESTAMPTZ,               -- soft delete
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE team_memberships (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id         UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id         UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role            team_role NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_team_memberships_team_user UNIQUE (team_id, user_id)
);

-- =====================================================================
-- GROUP 2: Monitoring core
-- =====================================================================

CREATE TABLE monitors (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id                     UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    name                        VARCHAR(150) NOT NULL,
    url                         TEXT NOT NULL,
    method                      http_method NOT NULL DEFAULT 'GET',
    enabled                     BOOLEAN NOT NULL DEFAULT TRUE,
    check_interval_seconds      INTEGER NOT NULL DEFAULT 60 CHECK (check_interval_seconds > 0),
    current_interval_seconds    INTEGER NOT NULL DEFAULT 60 CHECK (current_interval_seconds > 0),
    timeout_seconds             INTEGER NOT NULL DEFAULT 10 CHECK (timeout_seconds > 0),
    failure_threshold           INTEGER NOT NULL DEFAULT 3 CHECK (failure_threshold > 0),
    recovery_threshold          INTEGER NOT NULL DEFAULT 2 CHECK (recovery_threshold > 0),
    consecutive_failures        INTEGER NOT NULL DEFAULT 0,
    consecutive_successes       INTEGER NOT NULL DEFAULT 0,
    backoff_until                TIMESTAMPTZ,
    expected_status_code       INTEGER NOT NULL DEFAULT 200,
    user_agent                  VARCHAR(255) DEFAULT 'APIMonitor/1.0',
    next_check_at               TIMESTAMPTZ,
    deleted_at                  TIMESTAMPTZ,   -- soft delete
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at                  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE monitor_assertions (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    monitor_id      UUID NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
    assertion_type  assertion_type NOT NULL,
    expression      TEXT NOT NULL,
    expected_value  TEXT,
    enabled         BOOLEAN NOT NULL DEFAULT TRUE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- Partitioned by month on checked_at, as called out in the design guide.
CREATE TABLE health_check_results (
    id                      UUID NOT NULL DEFAULT gen_random_uuid(),
    monitor_id              UUID NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
    checked_at              TIMESTAMPTZ NOT NULL,
    status                  check_status NOT NULL,
    http_status_code        INTEGER,
    response_time_ms        INTEGER,
    timeout                 BOOLEAN NOT NULL DEFAULT FALSE,
    connection_error        BOOLEAN NOT NULL DEFAULT FALSE,
    ssl_error                BOOLEAN NOT NULL DEFAULT FALSE,
    failed_assertion_id     UUID REFERENCES monitor_assertions(id) ON DELETE SET NULL,
    error_message           TEXT,
    response_body_excerpt   TEXT,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (id, checked_at)
) PARTITION BY RANGE (checked_at);

-- Rolling monthly partitions: previous, current, and next few months.
-- Adjust / automate this in production (e.g. pg_partman or a cron job).
CREATE TABLE health_check_results_2026_08 PARTITION OF health_check_results
    FOR VALUES FROM ('2026-08-01') TO ('2026-09-01');
CREATE TABLE health_check_results_2026_09 PARTITION OF health_check_results
    FOR VALUES FROM ('2026-09-01') TO ('2026-10-01');
CREATE TABLE health_check_results_2026_10 PARTITION OF health_check_results
    FOR VALUES FROM ('2026-10-01') TO ('2026-11-01');
CREATE TABLE health_check_results_2026_11 PARTITION OF health_check_results
    FOR VALUES FROM ('2026-11-01') TO ('2026-12-01');
CREATE TABLE health_check_results_2026_12 PARTITION OF health_check_results
    FOR VALUES FROM ('2026-12-01') TO ('2027-01-01');

CREATE TABLE health_check_daily_rollups (
    id                      UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    monitor_id              UUID NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
    day                     DATE NOT NULL,
    total_checks            INTEGER NOT NULL DEFAULT 0,
    failed_checks           INTEGER NOT NULL DEFAULT 0,
    avg_response_time_ms    NUMERIC(10, 2),
    p95_response_time_ms    NUMERIC(10, 2),
    uptime_percentage       NUMERIC(5, 2),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT uq_rollup_monitor_day UNIQUE (monitor_id, day)
);

CREATE TABLE maintenance_windows (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    monitor_id      UUID NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
    name            VARCHAR(150) NOT NULL,
    starts_at       TIMESTAMPTZ NOT NULL,
    ends_at         TIMESTAMPTZ NOT NULL,
    mode            maintenance_mode NOT NULL,
    reason          TEXT,
    created_by      UUID REFERENCES users(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_maintenance_window_order CHECK (ends_at > starts_at)
);

-- =====================================================================
-- GROUP 3: Problems
-- =====================================================================

CREATE TABLE incidents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    monitor_id      UUID NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
    status          incident_status NOT NULL DEFAULT 'open',
    opened_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    resolved_at     TIMESTAMPTZ,
    failure_count   INTEGER NOT NULL DEFAULT 0,
    recovery_count  INTEGER NOT NULL DEFAULT 0
);

-- =====================================================================
-- GROUP 4: Alerting
-- =====================================================================

CREATE TABLE notification_channels (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id         UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    monitor_id      UUID REFERENCES monitors(id) ON DELETE CASCADE,  -- NULL = whole team
    type            channel_type NOT NULL,
    name            VARCHAR(150) NOT NULL,
    is_enabled      BOOLEAN NOT NULL DEFAULT TRUE,
    configuration   JSONB NOT NULL DEFAULT '{}'::jsonb,
    secret_ref      TEXT,           -- pointer to a secrets vault, never the raw secret
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE alert_deliveries (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id                 UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    notification_channel_id     UUID NOT NULL REFERENCES notification_channels(id) ON DELETE CASCADE,
    status                      delivery_status NOT NULL DEFAULT 'pending',
    attempt_count               INTEGER NOT NULL DEFAULT 0,
    sent_at                     TIMESTAMPTZ,
    error_message               TEXT
);

-- =====================================================================
-- GROUP 5: Reporting / audit / AI
-- =====================================================================

CREATE TABLE reports (
    id                          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id                     UUID NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    monitor_id                  UUID REFERENCES monitors(id) ON DELETE CASCADE,  -- NULL = whole team
    requested_by                UUID REFERENCES users(id) ON DELETE SET NULL,
    period_start                TIMESTAMPTZ NOT NULL,
    period_end                  TIMESTAMPTZ NOT NULL,
    uptime_percentage           NUMERIC(5, 2),
    total_checks                INTEGER,
    failed_checks                INTEGER,
    total_downtime_seconds      INTEGER,
    created_at                  TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT ck_report_period_order CHECK (period_end > period_start)
);

-- Append-only: application role should only get INSERT + SELECT on this table.
CREATE TABLE audit_entries (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id         UUID REFERENCES users(id) ON DELETE SET NULL,
    action          audit_action NOT NULL,
    entity_type     VARCHAR(100) NOT NULL,
    entity_id       UUID NOT NULL,      -- logical reference, not a hard FK (polymorphic)
    old_values      JSONB,
    new_values      JSONB,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE ai_analyses (
    id                  UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id         UUID NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    summary             TEXT NOT NULL,
    suggested_actions   JSONB NOT NULL DEFAULT '[]'::jsonb,
    model               VARCHAR(100) NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE embeddings (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    entity_type     VARCHAR(100) NOT NULL,     -- e.g. 'ai_analysis'
    entity_id       UUID NOT NULL,             -- logical reference to ai_analyses.id
    content         TEXT NOT NULL,
    embedding       VECTOR(1536) NOT NULL,     -- adjust dimension to your embedding model
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- =====================================================================
-- Indexes (foreign keys + common query patterns)
-- =====================================================================

-- Access & people
CREATE INDEX idx_team_memberships_team_id ON team_memberships(team_id);
CREATE INDEX idx_team_memberships_user_id ON team_memberships(user_id);
CREATE UNIQUE INDEX idx_teams_name_active ON teams(name) WHERE deleted_at IS NULL;

-- Monitoring core
CREATE INDEX idx_monitors_team_id ON monitors(team_id);
CREATE INDEX idx_monitors_due ON monitors(next_check_at) WHERE enabled = TRUE AND deleted_at IS NULL;
CREATE INDEX idx_monitor_assertions_monitor_id ON monitor_assertions(monitor_id);

CREATE INDEX idx_hcr_monitor_checked_at ON health_check_results(monitor_id, checked_at DESC);
CREATE INDEX idx_hcr_failed_assertion ON health_check_results(failed_assertion_id);
CREATE INDEX idx_hcr_status ON health_check_results(status);

CREATE INDEX idx_rollups_monitor_day ON health_check_daily_rollups(monitor_id, day DESC);
CREATE INDEX idx_maintenance_windows_monitor_id ON maintenance_windows(monitor_id);
CREATE INDEX idx_maintenance_windows_active ON maintenance_windows(monitor_id, starts_at, ends_at);
CREATE INDEX idx_maintenance_windows_created_by ON maintenance_windows(created_by);

-- Problems
CREATE INDEX idx_incidents_monitor_id ON incidents(monitor_id);
CREATE INDEX idx_incidents_open ON incidents(monitor_id) WHERE status = 'open';

-- Alerting
CREATE INDEX idx_notification_channels_team_id ON notification_channels(team_id);
CREATE INDEX idx_notification_channels_monitor_id ON notification_channels(monitor_id);
CREATE INDEX idx_alert_deliveries_incident_id ON alert_deliveries(incident_id);
CREATE INDEX idx_alert_deliveries_channel_id ON alert_deliveries(notification_channel_id);

-- Reporting / audit / AI
CREATE INDEX idx_reports_team_id ON reports(team_id);
CREATE INDEX idx_reports_monitor_id ON reports(monitor_id);
CREATE INDEX idx_reports_requested_by ON reports(requested_by);
CREATE INDEX idx_audit_entries_user_id ON audit_entries(user_id);
CREATE INDEX idx_audit_entries_entity ON audit_entries(entity_type, entity_id);
CREATE INDEX idx_ai_analyses_incident_id ON ai_analyses(incident_id);
CREATE INDEX idx_embeddings_entity ON embeddings(entity_type, entity_id);
CREATE INDEX idx_embeddings_vector ON embeddings USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- =====================================================================
-- Table & column comments (self-documenting schema)
-- =====================================================================
COMMENT ON TABLE users IS 'Everyone who can log in to the monitoring platform.';
COMMENT ON TABLE teams IS 'A team/company/project that owns monitors, channels and reports.';
COMMENT ON TABLE team_memberships IS 'Bridge table for users<->teams, carries the RBAC role.';
COMMENT ON TABLE monitors IS 'One row = one API endpoint being watched, with settings and live streak state.';
COMMENT ON TABLE monitor_assertions IS 'Content-level rules checked inside a successful HTTP response.';
COMMENT ON TABLE health_check_results IS 'Raw history: one row per check. Partitioned monthly on checked_at.';
COMMENT ON TABLE health_check_daily_rollups IS 'One summary row per monitor per day, for fast reporting.';
COMMENT ON TABLE incidents IS 'A confirmed, ongoing problem — opened only after failure_threshold is hit.';
COMMENT ON TABLE notification_channels IS 'Where alerts can be sent: email, Slack, Discord or webhook.';
COMMENT ON TABLE alert_deliveries IS 'Log of each attempt to actually send an alert for an incident.';
COMMENT ON TABLE maintenance_windows IS 'Planned downtime windows: suppress_alerts or pause_monitoring.';
COMMENT ON TABLE reports IS 'Saved uptime reports for a team or a specific monitor.';
COMMENT ON TABLE audit_entries IS 'Append-only security diary of who changed what.';
COMMENT ON TABLE ai_analyses IS 'AI-written incident summary and suggestions. Never decides health/incident state.';
COMMENT ON TABLE embeddings IS 'Vector embeddings (pgvector) of AI analyses, for similarity search.';

COMMIT;
