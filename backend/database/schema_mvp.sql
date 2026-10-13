-- =============================================================================
-- API Health & Incident Monitoring Dashboard — MVP SCHEMA
-- Scope: the 15 Must Have user stories only, matching the 4-sprint / 8-week
-- plan (SPRINTS.md). This is the schema to actually build Sprint 1's
-- migration from.
--
-- Deferred, NOT included here (add back only if you pick up the story):
--   monitor_assertions        -- needs US-07 (response-body assertions)
--   health_check_daily_rollups -- needs US-14 / US-24
--   maintenance_windows        -- needs US-04
--   reports                    -- needs US-15
--   audit_entries              -- needs US-18
--   ai_analyses, embeddings    -- not tied to any of the 25 user stories
--
-- The full 15-table design (schema.sql) remains the reference for the
-- complete project / final report. This file is the subset Sprints 1-4
-- actually need.
--
-- PostgreSQL 16+. pgvector is NOT required for this subset (dropped with
-- embeddings/ai_analyses) — add it back only when you build that feature.
--
-- Run the database in UTC: ALTER DATABASE <db> SET timezone = 'UTC';
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS citext;      -- case-insensitive email
CREATE EXTENSION IF NOT EXISTS pgcrypto;    -- gen_random_uuid()

CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END $$;

-- =============================================================================
-- Sprint 1 / Sprint 2 — Access & people  (US-01, US-19)
-- =============================================================================

CREATE TABLE users (
    id             uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email          citext NOT NULL UNIQUE,
    full_name      varchar(150) NOT NULL,
    password_hash  text NOT NULL,
    is_active      boolean NOT NULL DEFAULT true,
    created_at     timestamptz NOT NULL DEFAULT now(),
    updated_at     timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE teams (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    name        varchar(150) NOT NULL,
    deleted_at  timestamptz,
    created_at  timestamptz NOT NULL DEFAULT now(),
    updated_at  timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE team_memberships (
    id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id     uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    user_id     uuid NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role        text NOT NULL CHECK (role IN ('admin', 'operator', 'read_only')),  -- US-19 RBAC
    created_at  timestamptz NOT NULL DEFAULT now(),
    UNIQUE (team_id, user_id)
);
CREATE INDEX ix_team_memberships_user ON team_memberships (user_id);

-- =============================================================================
-- Sprint 2 — Monitoring core  (US-02, US-05, US-06, US-08, US-13, US-16)
-- =============================================================================

CREATE TABLE monitors (
    id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id                   uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    name                      varchar(150) NOT NULL,
    url                       text NOT NULL CHECK (url ~* '^https?://'),
    method                    text NOT NULL DEFAULT 'GET'
                                  CHECK (method IN ('GET','HEAD','POST','PUT','PATCH','DELETE')),
    enabled                   boolean NOT NULL DEFAULT true,
    check_interval_seconds    integer NOT NULL DEFAULT 60 CHECK (check_interval_seconds >= 10),
    current_interval_seconds  integer NOT NULL DEFAULT 60 CHECK (current_interval_seconds >= 10),  -- US-16 backoff
    timeout_seconds           integer NOT NULL DEFAULT 10 CHECK (timeout_seconds BETWEEN 1 AND 60),
    failure_threshold         integer NOT NULL DEFAULT 3 CHECK (failure_threshold >= 1),            -- US-09
    recovery_threshold        integer NOT NULL DEFAULT 2 CHECK (recovery_threshold >= 1),           -- US-10
    consecutive_failures      integer NOT NULL DEFAULT 0 CHECK (consecutive_failures >= 0),
    consecutive_successes     integer NOT NULL DEFAULT 0 CHECK (consecutive_successes >= 0),
    backoff_until             timestamptz,                                                          -- US-16
    expected_status_code      integer NOT NULL DEFAULT 200 CHECK (expected_status_code BETWEEN 100 AND 599),
    user_agent                varchar(255) NOT NULL DEFAULT 'APIMonitor/1.0',                       -- US-16
    next_check_at             timestamptz,                                                          -- US-05 scheduling
    deleted_at                timestamptz,
    created_at                timestamptz NOT NULL DEFAULT now(),
    updated_at                timestamptz NOT NULL DEFAULT now()
);
CREATE INDEX ix_monitors_team ON monitors (team_id) WHERE deleted_at IS NULL;
CREATE INDEX ix_monitors_due ON monitors (next_check_at)
    WHERE deleted_at IS NULL AND enabled = true;

-- Raw check history, partitioned by month (checked_at is the partition key).
-- NOTE: no failed_assertion_id column here — that belongs to monitor_assertions,
-- which is deferred. Add both together if you pick up US-07.
CREATE TABLE health_check_results (
    id                      uuid NOT NULL DEFAULT gen_random_uuid(),
    monitor_id              uuid NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
    checked_at              timestamptz NOT NULL DEFAULT now(),
    status                  text NOT NULL CHECK (status IN ('healthy','failing','degraded')),
    http_status_code        integer,
    response_time_ms        integer CHECK (response_time_ms >= 0),
    timeout                 boolean NOT NULL DEFAULT false,
    connection_error        boolean NOT NULL DEFAULT false,
    ssl_error               boolean NOT NULL DEFAULT false,
    error_message           text,
    response_body_excerpt   text,
    created_at              timestamptz NOT NULL DEFAULT now(),
    PRIMARY KEY (id, checked_at)
) PARTITION BY RANGE (checked_at);

CREATE INDEX ix_results_monitor_time ON health_check_results (monitor_id, checked_at DESC);

CREATE TABLE health_check_results_default PARTITION OF health_check_results DEFAULT;

-- Call monthly (and at deploy time) so partitions always exist a month ahead.
CREATE OR REPLACE FUNCTION create_health_check_partition(p_month date) RETURNS void
LANGUAGE plpgsql AS $$
DECLARE
    start_d date := date_trunc('month', p_month)::date;
    end_d   date := (date_trunc('month', p_month) + interval '1 month')::date;
    part    text := format('health_check_results_%s', to_char(start_d, 'YYYY_MM'));
BEGIN
    EXECUTE format(
        'CREATE TABLE IF NOT EXISTS %I PARTITION OF health_check_results FOR VALUES FROM (%L) TO (%L)',
        part, start_d, end_d);
END $$;

SELECT create_health_check_partition(current_date);
SELECT create_health_check_partition((current_date + interval '1 month')::date);

-- =============================================================================
-- Sprint 3 — Problems  (US-09, US-10)
-- =============================================================================

CREATE TABLE incidents (
    id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    monitor_id      uuid NOT NULL REFERENCES monitors(id) ON DELETE CASCADE,
    status          text NOT NULL DEFAULT 'open' CHECK (status IN ('open','resolved')),
    opened_at       timestamptz NOT NULL DEFAULT now(),
    resolved_at     timestamptz,
    failure_count   integer NOT NULL DEFAULT 0,
    recovery_count  integer NOT NULL DEFAULT 0,
    CHECK ((status = 'open' AND resolved_at IS NULL) OR (status = 'resolved' AND resolved_at IS NOT NULL))
);
-- At most one open incident per monitor => the app can't accidentally open a duplicate.
CREATE UNIQUE INDEX ux_incident_one_open_per_monitor ON incidents (monitor_id) WHERE status = 'open';
CREATE INDEX ix_incidents_monitor_opened ON incidents (monitor_id, opened_at DESC);

-- =============================================================================
-- Sprint 3 — Alerting  (US-03, US-11)
-- =============================================================================

-- Secrets (webhook URLs/tokens) are encrypted in the app with an AES-256 key
-- from .env / GitHub Actions secrets, then stored as ciphertext here.
CREATE TABLE notification_channels (
    id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    team_id             uuid NOT NULL REFERENCES teams(id) ON DELETE CASCADE,
    monitor_id          uuid REFERENCES monitors(id) ON DELETE CASCADE,  -- NULL = whole team
    type                text NOT NULL CHECK (type IN ('email','slack','discord','webhook')),
    name                varchar(150) NOT NULL,
    is_enabled          boolean NOT NULL DEFAULT true,
    configuration       jsonb NOT NULL DEFAULT '{}'::jsonb,   -- non-secret settings only
    secret_ciphertext   bytea,                                 -- AES-256-GCM encrypted webhook URL/token
    secret_nonce        bytea,                                 -- unique nonce/IV used for that encryption
    secret_display_hint text,                                  -- masked value safe for the UI
    created_at          timestamptz NOT NULL DEFAULT now(),
    updated_at          timestamptz NOT NULL DEFAULT now(),
    CHECK ((secret_ciphertext IS NULL) = (secret_nonce IS NULL))
);
CREATE INDEX ix_channels_team ON notification_channels (team_id);
CREATE INDEX ix_channels_monitor ON notification_channels (monitor_id) WHERE monitor_id IS NOT NULL;

-- event_type + UNIQUE constraint guarantee one alert per state change (FR6 / US-10).
CREATE TABLE alert_deliveries (
    id                        uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    incident_id               uuid NOT NULL REFERENCES incidents(id) ON DELETE CASCADE,
    notification_channel_id   uuid NOT NULL REFERENCES notification_channels(id),
    event_type                text NOT NULL CHECK (event_type IN ('opened','resolved')),
    status                    text NOT NULL DEFAULT 'pending' CHECK (status IN ('pending','sent','failed')),
    attempt_count             integer NOT NULL DEFAULT 0 CHECK (attempt_count BETWEEN 0 AND 4),
    sent_at                   timestamptz,
    error_message             text,
    created_at                timestamptz NOT NULL DEFAULT now(),
    updated_at                timestamptz NOT NULL DEFAULT now(),
    UNIQUE (incident_id, notification_channel_id, event_type)
);
CREATE INDEX ix_deliveries_incident ON alert_deliveries (incident_id);
CREATE INDEX ix_deliveries_pending ON alert_deliveries (status) WHERE status = 'pending';

-- =============================================================================
-- updated_at triggers
-- =============================================================================
DO $$
DECLARE t text;
BEGIN
    FOREACH t IN ARRAY ARRAY[
        'users', 'teams', 'monitors', 'notification_channels', 'alert_deliveries'
    ] LOOP
        EXECUTE format(
            'CREATE TRIGGER trg_%1$s_updated_at BEFORE UPDATE ON %1$I
             FOR EACH ROW EXECUTE FUNCTION set_updated_at()', t);
    END LOOP;
END $$;
