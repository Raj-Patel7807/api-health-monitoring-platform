# Sprint Plan — 8-Week Revision

## Distributed API Health & Incident Monitoring Platform

This revises the original 6-sprint / 152-point plan for an **8-week implementation
window**. Scope is cut to the **15 Must Have user stories (97 points)** from
`STORY_POINTS_AND_PRIORITY.md`. All Should Have and Could Have stories are
deferred as documented future work (see §5). `US-25` (Agile/GitHub/Slack
governance) is continuous across every sprint, as in the original plan.



---

## Overview

| Sprint | Weeks | Goal | Stories | Points |
| --- | --- | --- | --- | --- |
| 1 | 1–2 | Safe foundation | US-17, US-21, US-25 | 21 |
| 2 | 3–4 | Monitoring loop | US-01, US-02, US-05, US-16, US-06 | 29 |
| 3 | 5–6 | Store, confirm, alert | US-08, US-03, US-09, US-10, US-11 | 34 |
| 4 | 7–8 | Visibility & access control | US-13, US-19 | 13 |
| | | **Total** | **12 stories + US-25** | **97** |

This is unchanged from the original plan for Sprints 1–3. Sprint 4 is trimmed:
US-14 (uptime history) and US-04 (maintenance windows) are removed to fit two
weeks, since both are Should Have, not Must Have.

---

## Sprint 1 — Establish a Safe Foundation (Weeks 1–2, 21 pts)

**Goal:** Repository, local dev stack, CI pipeline, and data-protection baseline.
No product features — this is the environment everything else builds on.

| Story | Title | Pts | EPIC |
|-------|-------|----:|------|
| US-17 | Protect Stored Monitoring and Configuration Data | 8 | E5 |
| US-21 | Deploy and Maintain the Platform Within Hosting Constraints | 5 | E6 |
| US-25 | Manage Agile Delivery, GitHub Collaboration and Requirement Decisions | 8 | E8 |

**Key deliverables**
- Docker Compose stack: PostgreSQL (pgvector), Redis, backend API, frontend dev server.
- GitHub Actions CI: lint, type-check, test.
- AES-256 encryption key sourced from `.env` locally / GitHub Actions secrets at
  deploy time — used to encrypt notification-channel secrets (see schema.sql).
- `.env.example` committed with safe defaults; no real secrets in Git.
- Branch protection, PR workflow, Slack channels, sprint tracking set up.

**Dependencies:** None — starting point.

**Risks:** Docker/CI setup eats time — keep the local stack minimal. US-25 is
continuous; assign it as ongoing effort, not a one-sprint task.

**Demo:** `docker compose up --build` boots the stack. CI is green on a sample
PR. `/health` returns `200 OK`.

---

## Sprint 2 — Build the Monitoring Loop (Weeks 3–4, 29 pts)

**Goal:** A user can sign up, register an endpoint, and the system runs
background checks that detect failures — with responsible rate limiting.

| Story | Title | Pts | EPIC |
|-------|-------|----:|------|
| US-01 | User Account Onboarding | 3 | E1 |
| US-02 | Register and Configure an API Endpoint | 5 | E1 |
| US-05 | Schedule Continuous Background Health Checks | 8 | E2 |
| US-16 | Respect Target API Rate Limits and Use Backoff | 5 | E5 |
| US-06 | Detect API Health Failures | 8 | E2 |

**Key deliverables**
- Registration/login (US-01).
- Endpoint config API: URL, expected status, check interval (US-02).
- Celery Beat scheduling checks at configured intervals, non-blocking (US-05).
- Rate limiting, backoff, proper User-Agent on outbound requests (US-16).
- Failure classification: timeout, wrong status, connection error, SSL error (US-06).

**Dependencies:** Sprint 1 complete (stack, CI, encryption baseline).

**Risks:** US-05 and US-06 are both 8-point stories involving real async/worker
integration — this is where most teams first hit real technical difficulty.
If velocity is low, it is safe to let US-16 (rate limiting) slip a few days
into Sprint 3 without breaking the demo — the loop still works without backoff
tuning, just less politely.

**Demo:** Register a test endpoint. Celery Beat schedules checks. Worker pings
it and logs healthy / timeout / wrong-status / connection-error / SSL-failure
results. Rate limiting visible in logs.

---

## Sprint 3 — Store, Confirm, and Alert (Weeks 5–6, 34 pts)

**Goal:** Complete the pipeline end to end. Results are stored, confirmed
failures open incidents, and exactly one alert goes out per state change.

This is the heaviest sprint in the plan and the one most likely to slip.
**Run it as three parallel workstreams from day one**, not five stories done
in sequence — most of the work has no cross-dependency until final integration.

| Story | Title | Pts | EPIC |
|-------|-------|----:|------|
| US-08 | Record Health-Check Results and Response Time | 5 | E2 |
| US-03 | Configure Notification Details | 5 | E1 |
| US-09 | Create an Incident Only After Confirmed Failure | 8 | E3 |
| US-10 | Manage Incident State and Avoid Duplicate Alerts | 8 | E3 |
| US-11 | Send Incident Alerts Through Configured Channels | 8 | E3 |

### Parallel workstream split (9-person team)

| Workstream | Stories | Suggested size | Why it can start immediately |
|---|---|---|---|
| **A — Storage** | US-08 | 2–3 people | Just persists what US-06 already produces. No dependency on B or C. |
| **B — Notification config** | US-03 | 2–3 people | Pure CRUD + encryption (already specified in schema.sql). No dependency on A or C. |
| **C — Incident logic** | US-09, US-10, US-11 | 3–4 people (your strongest here) | The actual hard part: threshold logic, state machine, exactly-once alert dispatch. Needs A's stored results and B's channels only at final integration, not from day one. |

Integrate A + B + C in the last 2–3 days of the sprint, not the last day.

**Key deliverables**
- Durable result storage with status, response time, timestamps (US-08).
- Notification channel config: Slack/Discord webhook, email, generic webhook,
  encrypted at rest (US-03).
- Failure-threshold logic: consecutive failures must cross the configured
  threshold before an incident opens (US-09).
- Incident state machine: healthy → failing → recovering → healthy, exactly
  one alert per transition — enforced by the `UNIQUE(incident_id,
  notification_channel_id, event_type)` constraint in the schema (US-10).
- Alert dispatch on state change through the configured channel (US-11).

**Dependencies:** Sprint 2 complete (scheduler, failure detection, endpoint
registration).

**Risks:**
- This is 34 points in 2 weeks — the single highest-risk sprint in the plan.
  The parallel split above is the main mitigation.
- Mock all external notification services (Slack/Discord/Email) in tests —
  CI must never call real APIs. Decide the mocking approach in the first two
  days, not partway through.
- If the sprint runs long, let it use 1–2 days from Sprint 4's slack (Sprint 4
  is light at 13 points) rather than compressing Sprint 4's own scope.

**Demo:** Register a deliberately failing endpoint. After 3 consecutive
failures, an incident opens and one alert is sent. Repeated failures do not
produce duplicate alerts. Recovery resolves the incident and sends one
recovery alert.

---

## Sprint 4 — Visibility and Access Control (Weeks 7–8, 13 pts)

**Goal:** A dashboard view and role-based access control. Trimmed from the
original Sprint 4 — US-14 and US-04 removed (both Should Have) to fit two weeks.

| Story | Title | Pts | EPIC |
|-------|-------|----:|------|
| US-13 | View Overall API Health Dashboard | 5 | E4 |
| US-19 | Securely Manage Team Access Through RBAC | 8 | E6 |

**Key deliverables**
- React dashboard: all endpoints, current status, response time, open
  incidents at a glance (US-13).
- RBAC — Admin, Operator, Read-Only — enforced on every protected endpoint
  built in Sprints 2–3 (US-19).

**Dependencies:**
- US-13 depends on US-08 (Sprint 3) for data to display.
- US-19 depends on US-17 (Sprint 1) for the security foundation, and must be
  retrofitted across every API route built so far — budget real time for this,
  it is not just adding a decorator.

**Risks:** US-19's retrofit is the main risk here, not its raw point count.
Review every existing endpoint from Sprints 2–3 explicitly rather than
assuming a global middleware catches everything. This sprint has slack
(13 pts vs. ~25 average) specifically to absorb Sprint 3 overflow — use it
for that first if needed, then RBAC.

**Demo:** Team lead logs in, sees dashboard with all endpoints' health.
Admin assigns Operator/Read-Only roles. Read-Only users cannot modify
endpoints or see full secret values. Attempted unauthorized actions return
403.

---

## Load Distribution

```text
Sprint 1  ████████████████████░░░░░░░░░░░░░░  21 pts  (Foundation)
Sprint 2  █████████████████████████████░░░░░  29 pts  (Monitoring loop)
Sprint 3  ██████████████████████████████████  34 pts  (Results + Incidents)
Sprint 4  █████████████░░░░░░░░░░░░░░░░░░░░░  13 pts  (Dashboard + RBAC)
           Average: ~24 pts/sprint
```

Sprint 4 is deliberately underloaded relative to the others — it is the
buffer for Sprint 3 slipping, not a sign of an unbalanced plan.

---

## What's Deferred (Should Have / Could Have — 55 pts, not scheduled)


| Priority to add back | Story | Pts | Why this order |
|---|---|---|---|
| 1 | US-04 — Maintenance windows | 3 | Small, self-contained, schema already supports both modes (`suppress_alerts` / `pause_monitoring`). |
| 2 | US-14 — Uptime & history view | 5 | Mostly a read/reporting view on data you already store. |
| 3 | US-12 — Notification retry | 5 | Extends US-11, moderate complexity. |
| 4 | US-07 — Response-body assertions | 8 | Higher complexity (regex/JSONPath), extends US-06. |
| 5 | US-18 — Audit logging | 5 | Schema trigger already exists (`schema.sql`); mainly wiring it into every write path. |
| — | US-15, US-20, US-22, US-24 | 34 | Not realistic in 8 weeks. Document as future work only. |


---

## Definition of Done 

A user story is complete when:
- Acceptance criteria from `USER_STORIES.md` are met.
- Code is reviewed and approved through a pull request.
- Relevant unit/integration tests are added and pass.
- Formatter, linter, type checks, and CI are green.
- Documentation is updated for any behavior/schema/API change.
- No known critical bug is introduced.
- The change is merged through the approved branch and review process.
