# Sprint Plan

The project follows Scrum. Sprint length and dates are agreed by the team, so none are invented here. `US-25` is continuous governance work in every sprint. Total planning uses 152 points across 24 stories (after removing US-23 and NFR13). See `DECISIONS.md` D-014 and D-015.

---

## Overview

| Sprint | Goal | Stories | Points | Demo / dependency |
| --- | --- | --- | ---: | --- |
| 1 | Establish a safe foundation. | US-17, US-21, US-25 | 21 | Local stack and CI; no product feature claim. |
| 2 | Build the monitoring loop. | US-01, US-02, US-05, US-16, US-06 | 29 | User signs up, registers endpoint, system detects failures with rate limiting; depends on Sprint 1. |
| 3 | Store results, confirm incidents, and alert. | US-08, US-03, US-09, US-10, US-11 | 34 | Full pipeline: check → detect → store → confirm → incident → alert; depends on Sprint 2. |
| 4 | Provide visibility, access control, and history. | US-13, US-19, US-14, US-04 | 21 | Dashboard, RBAC, uptime history, maintenance windows; depends on Sprint 3 and Sprint 1 security. |
| 5 | Harden with assertions, retries, audit, and scale. | US-07, US-12, US-18, US-22 | 26 | Response-body assertions, notification retry, audit logging, scaling; depends on core loop. |
| 6 | Data retention and Could Have work. | US-24, US-15, US-20 | 21 | Daily rollups, monthly reports, multi-region probes; US-15 and US-20 are Could Have — only if velocity allows. |

---

## Sprint 1 — Establish a Safe Foundation (21 pts)

**Goal:** Set up the repository, local development stack, CI pipeline, and data protection baseline. No product features are delivered — this sprint produces the safe environment that all future sprints build on.

| Story | Title | Pts | Priority | EPIC |
|-------|-------|----:|----------|------|
| US-17 | Protect Stored Monitoring and Configuration Data | 8 | Must Have | E5 |
| US-21 | Deploy and Maintain the Platform Within Hosting Constraints | 5 | Must Have | E6 |
| US-25 | Manage Agile Delivery, GitHub Collaboration and Requirement Decisions | 8 | Must Have | E8 |

**Key deliverables:**

- Docker Compose stack running PostgreSQL (with pgvector), Redis, backend API, and frontend dev server.
- GitHub Actions CI pipeline with linting, type checks, and test execution.
- AES-256 encryption strategy for stored secrets and TLS 1.3 requirement documented.
- `.env.example` files with safe defaults; no real secrets committed.
- Agile governance process established: branch protection, PR workflow, Slack communication, and sprint tracking.

**Dependencies:** None — this is the starting point.

**Risks:**

- Docker or CI environment issues may consume setup time. Mitigate by keeping the local stack minimal.
- US-25 (governance) is continuous and spans all sprints; allocate ongoing effort rather than treating it as a one-time delivery.

**Demo:** Local stack boots with `docker compose up --build`. CI runs green on a sample PR. `/health` endpoint returns `200 OK`. No product features are claimed.

---

## Sprint 2 — Build the Monitoring Loop (29 pts)

**Goal:** A user can sign up, register an API endpoint, and the system runs background health checks that detect failures — with responsible rate limiting and proper identification.

| Story | Title | Pts | Priority | EPIC |
|-------|-------|----:|----------|------|
| US-01 | User Account Onboarding | 3 | Must Have | E1 |
| US-02 | Register and Configure an API Endpoint | 5 | Must Have | E1 |
| US-05 | Schedule Continuous Background Health Checks | 8 | Must Have | E2 |
| US-16 | Respect Target API Rate Limits and Use Backoff | 5 | Must Have | E5 |
| US-06 | Detect API Health Failures | 8 | Must Have | E2 |

**Key deliverables:**

- User registration and authentication flow (US-01, FR11).
- Endpoint configuration API: URL, expected status code, check interval (US-02, FR1).
- Celery Beat scheduler queuing check tasks at configured intervals (US-05, FR2, DR1).
- Rate limiting, exponential backoff on repeated failures, and proper User-Agent header on outbound requests (US-16, FR12, DR4).
- Failure detection: timeout, wrong status code, connection error, and SSL certificate failure (US-06, FR3).

**Dependencies:** Sprint 1 must be complete — Docker stack, CI, and data protection baseline are required.

**Risks:**

- US-05 (scheduling) and US-06 (detection) are both 8-point stories involving Celery worker integration. If velocity is lower than expected, defer US-16 (rate limiting) to early Sprint 3 — the monitoring loop can be demoed without backoff logic.
- Authentication scope (US-01) must stay minimal — sign-up and login only. Do not scope creep into full RBAC here; that is Sprint 4 (US-19).

**Demo:** Register a test endpoint. Celery Beat schedules periodic checks. The worker pings the endpoint and logs detection results (healthy / timeout / wrong status / connection error / SSL failure). Rate limiting and backoff are visible in worker logs.

---

## Sprint 3 — Store Results, Confirm Incidents, and Alert (34 pts)

**Goal:** Complete the end-to-end pipeline. Health-check results are persisted, confirmed failures create incidents, and users receive exactly one alert per state transition.

| Story | Title | Pts | Priority | EPIC |
|-------|-------|----:|----------|------|
| US-08 | Record Health-Check Results and Response Time | 5 | Must Have | E2 |
| US-03 | Configure Notification Details | 5 | Must Have | E1 |
| US-09 | Create an Incident Only After Confirmed Failure | 8 | Must Have | E3 |
| US-10 | Manage Incident State and Avoid Duplicate Alerts | 8 | Must Have | E3 |
| US-11 | Send Incident Alerts Through Configured Channels | 8 | Must Have | E3 |

**Key deliverables:**

- Durable storage of every health-check result with status, response time, and timestamps (US-08, FR9).
- Notification channel configuration API: Slack webhook, Discord webhook, email address, or generic webhook per user or endpoint (US-03, FR13).
- Failure threshold logic: consecutive failures must cross the configured threshold (e.g., 3 in a row) before an incident is opened (US-09, FR5, DR5).
- Incident state machine: `healthy → failing → recovering → healthy` with exactly one alert per state transition — no duplicate alerts per failed check (US-10, FR6).
- Alert dispatch through the user's configured channel on incident state change (US-11, FR7).

**Dependencies:** Sprint 2 must be complete — the scheduler, failure detection, and endpoint registration feed directly into this sprint.

**Risks:**

- This is the highest-load sprint at 34 points. However, US-08 (result storage) and US-03 (notification config) are 5-point configuration/plumbing stories with limited complexity. The heavy lifting is in US-09 (threshold logic), US-10 (state machine), and US-11 (alert dispatch).
- Notification integration with external services (Slack, Discord, Email) must use fake/mock providers in tests — CI must never call real APIs.
- If the sprint is too heavy, US-03 can be started in Sprint 2 (it has no Sprint 2 blocker) to front-load the work.

**Demo:** Register an endpoint that intentionally fails. After 3 consecutive failures, an incident is created. A Slack/Email/Webhook alert is sent. Repeated failures do not generate duplicate alerts. When the endpoint recovers, the incident is resolved and a recovery notification is sent.

---

## Sprint 4 — Visibility, Access Control, and History (21 pts)

**Goal:** Give team leads a dashboard view, enforce role-based access, provide historical uptime data, and let users suppress alerts during planned maintenance.

| Story | Title | Pts | Priority | EPIC |
|-------|-------|----:|----------|------|
| US-13 | View Overall API Health Dashboard | 5 | Must Have | E4 |
| US-19 | Securely Manage Team Access Through RBAC | 8 | Must Have | E6 |
| US-14 | View Uptime and Historical Performance | 5 | Should Have | E4 |
| US-04 | Configure an Endpoint Maintenance Window | 3 | Should Have | E1 |

**Key deliverables:**

- React dashboard displaying all monitored endpoints with current status, response time, and open incidents at a glance (US-13, FR10).
- RBAC with Admin, Operator, and Read-Only roles — backend authorization enforced on every protected endpoint (US-19, FR17).
- Historical uptime and response-time views with the standard formula: `(Total Time − Downtime) / Total Time × 100` (US-14, FR4, DR3).
- Maintenance window configuration: a user can set a time range during which checks still run but incident/alert creation is suppressed (US-04, FR15).

**Dependencies:**

- US-13 and US-14 depend on US-08 (result storage, Sprint 3) for data to display.
- US-19 depends on US-17 (data protection, Sprint 1) for the security foundation.
- US-04 depends on US-09/US-10 (incident logic, Sprint 3) for suppression behavior.

**Risks:**

- RBAC (US-19) at 8 points is the most complex story here. Retrofitting authorization across existing endpoints requires careful review of all Sprint 2–3 APIs. Plan for this integration effort.
- Dashboard load time must stay under 3 seconds (NFR9). Use efficient queries and consider pagination early.

**Demo:** A team lead logs in, sees a dashboard with all endpoints' health status. Admin assigns Operator and Read-Only roles to team members. Read-Only users cannot modify endpoints. Historical uptime is displayed. A maintenance window is created, and during that window, failures are detected but no incident or alert is raised.

---

## Sprint 5 — Assertions, Retries, Audit, and Scale (26 pts)

**Goal:** Harden the platform with advanced failure detection, resilient notifications, operational audit trails, and infrastructure scaling.

| Story | Title | Pts | Priority | EPIC |
|-------|-------|----:|----------|------|
| US-07 | Validate Response Body and JSONPath Content | 8 | Should Have | E2 |
| US-12 | Retry Failed Notification Delivery | 5 | Should Have | E3 |
| US-18 | Maintain Tamper-Proof Operational Audit Logs | 5 | Should Have | E5 |
| US-22 | Scale Monitoring Resources as Usage Grows | 8 | Should Have | E7 |

**Key deliverables:**

- Response-body assertions: text string matching, regex patterns, and JSONPath value checks to detect "silent failures" where an endpoint returns HTTP 200 but with corrupted or empty data (US-07, FR16).
- Notification retry with exponential backoff: up to 3 retries on delivery failure, then mark as permanently failed and log it (US-12, FR8).
- Tamper-proof audit logging for configuration and permission changes — append-only records with timestamps and actor identity (US-18, NFR15).
- Infrastructure scaling: worker replicas, queue-specific concurrency, per-check cost tracking toward the $0.01 target for 95% of checks (US-22, NFR8, NFR10).

**Dependencies:** All stories depend on the core monitoring loop (Sprints 2–3). US-07 extends US-06 (failure detection). US-12 extends US-11 (alert dispatch). US-18 builds on the security baseline from US-17 (Sprint 1). US-22 depends on US-05 and US-21.

**Risks:**

- JSONPath assertion parsing (US-07) can be complex. Use a mature library rather than building a custom parser.
- Scaling work (US-22) is infrastructure-focused and may require Docker Compose and CI pipeline changes. Coordinate with the team to avoid merge conflicts.

**Demo:** Configure a JSONPath assertion on an endpoint. An endpoint returning `200 OK` with an empty body triggers a failure. A notification that fails to deliver is retried 3 times. Configuration changes appear in the audit log. Multiple worker replicas process checks concurrently.

---

## Sprint 6 — Data Retention and Could Have Work (21 pts)

**Goal:** Ensure long-term data sustainability through daily rollups. Attempt Could Have features (monthly reports, multi-region probes) only if team velocity permits.

| Story | Title | Pts | Priority | EPIC |
|-------|-------|----:|----------|------|
| US-24 | Preserve Long-Term Monitoring Data Through Data Rollups | 8 | Should Have | E7 |
| US-15 | Generate Monthly Uptime Reports | 5 | Could Have | E4 |
| US-20 | Monitor APIs From Multiple Geographic Regions | 8 | Could Have | E6 |

**Key deliverables:**

- Daily rollups of older minute-level monitoring data into aggregated summaries. Recent data (30 days) stays at full resolution; older data remains accessible but summarized (US-24, NFR4, NFR14).
- *(If velocity allows)* Monthly uptime report generation, downloadable or fetchable through the API (US-15, FR14).
- *(If velocity allows)* Multi-region probe selection: health checks from multiple geographic origins to detect localized routing issues (US-20, FR18).

**Dependencies:** US-24 depends on US-08 (result storage, Sprint 3). US-15 depends on US-14 (uptime history, Sprint 4) and US-19 (RBAC, Sprint 4) for authorization. US-20 depends on the monitoring pipeline (Sprint 2).

**Risks:**

- US-24 (rollups) requires careful data-management logic. Must preserve required history — agree on what "no loss of required history" means before implementing (see `EPIC_GROUPING.md` E7 boundaries).
- US-15 and US-20 are Could Have. If the team is behind schedule, drop them entirely and focus Sprint 6 on US-24 alone (8 pts). Do not let Could Have work delay the project.
- Multi-region monitoring (US-20) is architecturally significant. If attempted, keep the implementation minimal — tag results by region, do not build a distributed probe network.

**Demo:** Older monitoring data is rolled up into daily summaries. Recent data loads under 5 seconds; historical data remains accessible. *(If completed)* A monthly report is generated. *(If completed)* Health checks run from multiple configured regions.

---

## Load Distribution

```text
Sprint 1  ████████████████████░░░░░░░░░░░░░░  21 pts  (Foundation)
Sprint 2  █████████████████████████████░░░░░  29 pts  (Monitoring loop)
Sprint 3  ██████████████████████████████████  34 pts  (Results + Incidents)
Sprint 4  █████████████████████░░░░░░░░░░░░░  21 pts  (Dashboard + Access)
Sprint 5  ██████████████████████████░░░░░░░░  26 pts  (Hardening)
Sprint 6  █████████████████████░░░░░░░░░░░░░  21 pts  (Retention + Optional)
           Average: ~25 pts/sprint
```

## Load Rationale

Sprint 2 moved US-08 to Sprint 3 to reduce from 34 → 29 points; detection can be demoed without durable result storage. Sprint 4 absorbed US-14 and US-04 from the former Sprint 5 because they have no blockers and the original Sprint 4 was underloaded at 13 points. US-22 moved from the former Sprint 6 to Sprint 5 because its dependencies (US-05, US-21) are satisfied by Sprint 2. The former Sprints 6 and 7 were merged because the Could Have stories (US-15, US-20) do not justify a separate sprint ceremony.

---

## Definition of Done

A user story is considered complete when all of the following are satisfied:

- Acceptance criteria from `USER_STORIES.md` are met.
- Code is reviewed and approved through a pull request.
- Relevant unit tests and integration tests are added and pass.
- Formatter, linter, type checks, and CI pipeline are green.
- Documentation is updated for any behavior, schema, configuration, or API change.
- There is no known critical bug introduced by the change.
- The change is merged through the approved branch and review process.
