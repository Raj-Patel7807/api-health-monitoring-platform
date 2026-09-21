# EPIC Grouping — Distributed API Health & Incident Monitoring Platform

> **What this document is:** a reference for how the project's **25 user stories** are grouped into **8 EPICs** — what each EPIC contains, why the stories belong together, how large and how important each EPIC is, how EPICs depend on one another, and how everything traces back to requirements.
>
> **Built from:** [`USER_STORIES.md`](USER_STORIES.md) (stories, acceptance criteria, traceability) and [`STORY_POINTS_AND_PRIORITY.md`](STORY_POINTS_AND_PRIORITY.md) (estimates, MoSCoW priority, dependencies).

---

## Table of Contents

1. [About This Document](#1-about-this-document)
2. [EPICs at a Glance](#2-epics-at-a-glance)
3. [How the Stories Were Grouped](#3-how-the-stories-were-grouped)
4. [EPIC Map](#4-epic-map)
5. [EPIC Details](#5-epic-details) (E1 – E8)
6. [Master Story → EPIC Mapping](#6-master-story--epic-mapping)
7. [Dependencies](#7-dependencies)
8. [Requirement Traceability by EPIC](#8-requirement-traceability-by-epic)
9. [Grouping Health Check](#9-grouping-health-check)
10. [Suggested Delivery Increments](#10-suggested-delivery-increments)
11. [Source Consistency Notes](#11-source-consistency-notes)
12. [Using This Document](#12-using-this-document)
13. [Sources](#13-sources)

---

## 1. About This Document

The platform lets API owners register endpoints, checks them continuously in the background, confirms real failures, raises incidents, alerts the right people, and reports uptime. The 25 user stories cover that product workflow plus the security, scale, and project-process concerns around it.

An **EPIC** is a large, cohesive area of work that contains several related user stories. EPICs sit between individual stories and sprint-level planning, so the team can discuss scope, priority, and effort at a higher level without losing story-level traceability.

**Conventions used here**

| Convention | Meaning |
|---|---|
| **Points** | Relative story-point estimates (modified Fibonacci: 3, 5, 8 are used). Not hours. |
| **Priority** | MoSCoW priority as assigned in `STORY_POINTS_AND_PRIORITY.md`. |
| **Source** vs **Derived** | *Source* = stated in the two project documents. *Derived* = inferred from acceptance criteria (AC) while writing this README. |
| **Proposal** | Suggestions in §9 and §10 that are **not** part of the source documents and are for team discussion. |

> **Scope note:** This is an **EPIC grouping**, not a formal User Story Map. A story map organises work along a user journey with release slices. §4 and §10 offer a light journey/release view, but the authoritative structure remains the EPIC grouping defined in `USER_STORIES.md`.

---

## 2. EPICs at a Glance

| EPIC | Name | Role in the platform | Stories | Points | Share |
|---|---|---|---:|---:|---:|
| **E1** | User Onboarding & API Configuration | Product workflow — *Configure* | 4 | 16 | 10.0% |
| **E2** | API Monitoring & Health Checks | Product workflow — *Monitor* | 4 | 29 | 18.1% |
| **E3** | Incident Management & Alerting | Product workflow — *Respond* | 4 | 29 | 18.1% |
| **E4** | Dashboard, Uptime & Reporting | Product workflow — *Observe* | 3 | 15 | 9.4% |
| **E5** | Responsible Monitoring & Security | Platform / cross-cutting | 3 | 18 | 11.3% |
| **E6** | Access Control & Advanced Monitoring | Platform / cross-cutting | 3 | 21 | 13.1% |
| **E7** | Scalability, Reliability & Data Management | Platform / cross-cutting | 3 | 24 | 15.0% |
| **E8** | Project Governance & Requirement Management | Project process | 1 | 8 | 5.0% |
| | **Total** | | **25** | **160** | **100%** |

### Priority mix per EPIC

| EPIC | Must Have (stories / pts) | Should Have (stories / pts) | Could Have (stories / pts) |
|---|---:|---:|---:|
| E1 | 3 / 13 | 1 / 3 | 0 / 0 |
| E2 | 3 / 21 | 1 / 8 | 0 / 0 |
| E3 | 3 / 24 | 1 / 5 | 0 / 0 |
| E4 | 1 / 5 | 1 / 5 | 1 / 5 |
| E5 | 2 / 13 | 1 / 5 | 0 / 0 |
| E6 | 2 / 13 | 0 / 0 | 1 / 8 |
| E7 | 0 / 0 | 3 / 24 | 0 / 0 |
| E8 | 1 / 8 | 0 / 0 | 0 / 0 |
| **Total** | **15 / 97** | **8 / 50** | **2 / 13** |

**What the numbers say**

- **E2 + E3 carry 58 of 160 points (36%).** The monitoring engine and incident logic are the heaviest parts of the project.
- **E7 has no Must Have stories.** All three of its 8-point stories are Should Have, so the whole EPIC can follow the core system.
- **E4 is the smallest product EPIC** and only one of its three stories is Must Have (the dashboard).
- **Sizing profile:** 2 stories at 3 pts, 10 at 5 pts, 13 at 8 pts, none at 13. No story currently needs mandatory splitting, but many 8-point stories are large.

---

## 3. How the Stories Were Grouped

Stories were grouped using the following criteria, roughly in order of weight:

1. **Primary capability or system responsibility** — does the story contribute to the same functional area as its neighbours?
2. **Position in the workflow** — *Configure → Monitor → Respond → Observe*.
3. **Primary actor** — stories serving the same person tend to share an EPIC (e.g. incident responder in E3).
4. **Shared requirement families** — stories tracing to related FR / NFR / DR items sit together.
5. **Dependency cohesion** — within an EPIC, stories should depend mostly on each other rather than on many other EPICs.
6. **Product vs process separation** — project-delivery activities are kept apart from runtime product features.

Applying these criteria produces three tiers:

| Tier | EPICs | Points | Share | Description |
|---|---|---:|---:|---|
| **Workflow spine** | E1, E2, E3, E4 | 89 | 55.6% | The end-to-end user-visible monitoring loop |
| **Platform / cross-cutting** | E5, E6, E7 | 63 | 39.4% | Controls, environment, and sustainability that support the spine |
| **Project process** | E8 | 8 | 5.0% | How the team delivers and governs requirements |

---

## 4. EPIC Map

```text
  PROJECT PROCESS
  ┌──────────────────────────────────────────────────────────────────────┐
  │ E8  Project Governance & Requirement Management            (US-25)   │
  └──────────────────────────────────────────────────────────────────────┘

  PRODUCT WORKFLOW ("spine")

   E1 Configure ────►  E2 Monitor  ────►  E3 Respond  ────►  E4 Observe
   US-01 – US-04       US-05 – US-08      US-09 – US-12      US-13 – US-15
   account, endpoint,  schedule, detect,  confirm, incident  dashboard, uptime,
   notifications,      validate, record   state, alerts,     reports
   maintenance                            retries

  PLATFORM / CROSS-CUTTING (applies across the whole spine)
  ┌──────────────────────────────────────────────────────────────────────┐
  │ E5  Responsible Monitoring & Security        US-16 – US-18           │
  │ E6  Access Control & Advanced Monitoring     US-19 – US-21           │
  │ E7  Scalability, Reliability & Data Mgmt     US-22 – US-24           │
  └──────────────────────────────────────────────────────────────────────┘
```

The individual stories are listed in workflow order in `USER_STORIES.md` (§12), but that list is a **narrative flow, not a strict build order** — see §7 for real dependencies.

---

## 5. EPIC Details

### E1 — User Onboarding & API Configuration

**Role:** Workflow spine — *Configure* | **Points:** 16 | **Stories:** 4 | **Primary actor:** API Developer / API Owner

**Goal.** Give users everything they must set up before monitoring can run: an account, a first endpoint, notification destinations, and planned maintenance periods.

| ID | Story | Pts | Priority | Source requirements |
|---|---|---:|---|---|
| US-01 | User Account Onboarding | 3 | Must Have | FR11, NFR9 |
| US-02 | Register and Configure an API Endpoint | 5 | Must Have | FR1 |
| US-03 | Configure Notification Details | 5 | Must Have | FR7, FR13, NFR3 |
| US-04 | Configure an Endpoint Maintenance Window | 3 | Should Have | FR15, DR4 |

**What this EPIC delivers**

- Sign-up plus first-endpoint setup achievable within **5 minutes** (AC-01.6).
- Endpoint URL, expected status code, and check frequency stored; the endpoint then becomes eligible for scheduled checks (AC-02.1 – 02.6).
- Notification destinations for **Slack, Discord, Email, and Webhook**, at account and endpoint level, with secrets not exposed in the UI or logs (AC-03.2 – 03.6).
- Maintenance windows during which checks continue but incidents and alerts are suppressed (AC-04.2 – 04.4).

**Why these stories belong together.** All four are *configuration inputs* that the rest of the platform consumes. They share an actor (the API owner), are performed before or around monitoring, and produce data rather than runtime behaviour.

**Boundaries and notes**

- **Feeds:** US-02 → US-05 (scheduling); US-03 → US-11 (alert delivery); US-04 → US-09 / US-10 (incident suppression).
- **Overlap to manage:** US-01's first-endpoint step (AC-01.3) reuses the registration and validation logic of US-02. Build that logic once as a shared component so the two stories do not diverge.
- US-04 is configured here, but its *behaviour* takes effect in E3.

---

### E2 — API Monitoring & Health Checks

**Role:** Workflow spine — *Monitor* | **Points:** 29 | **Stories:** 4 | **Primary actor:** API Developer / API Owner

**Goal.** The monitoring engine: run checks automatically in the background, classify failures, optionally validate response content, and store the results.

| ID | Story | Pts | Priority | Source requirements |
|---|---|---:|---|---|
| US-05 | Schedule Continuous Background Health Checks | 8 | Must Have | FR2, DR1 |
| US-06 | Detect API Health Failures | 8 | Must Have | FR3, DR2, DR5 |
| US-07 | Validate Response Body and JSONPath Content | 8 | Should Have | FR16 |
| US-08 | Record Health-Check Results and Response Time | 5 | Must Have | FR9, NFR2, NFR4 |

**What this EPIC delivers**

- Recurring checks scheduled through **BullMQ**, running without manual action and without blocking the user-facing app (AC-05.2 – 05.5).
- Distinct failure classes: wrong status code, timeout, connection failure, SSL/TLS failure — with a single temporary failure **not** treated as a confirmed incident (AC-06.2 – 06.6).
- Text, regex, and JSONPath assertions so an HTTP 200 with bad content can still be unhealthy (AC-07.1 – 07.6).
- Stored results and response times: last **30 days retrievable in under 5 seconds**, older data reachable within 5 minutes, and no deletion through normal operation (AC-08.5 – 08.7).

**Why these stories belong together.** They form one continuous **health-check pipeline** — schedule, execute, classify, validate, record — and are tightly coupled through shared job and result data.

**Boundaries and notes**

- **Feeds:** US-06 / US-07 → US-09 (incident confirmation); US-08 → E4 (all reporting) and E7 (US-24 rollups).
- **US-08 is the data spine of the product.** Its retention behaviour (AC-08.7) must be designed together with the rollups in US-24 (see §9).
- **US-07 is an optional extension.** Per the source dependency chain, US-08 follows US-06 directly, so it must not be blocked by the Should Have US-07.

---

### E3 — Incident Management & Alerting

**Role:** Workflow spine — *Respond* | **Points:** 29 | **Stories:** 4 | **Primary actor:** Incident Responder / On-call Developer

**Goal.** Convert detected failures into confirmed incidents, manage their lifecycle without alert noise, and deliver alerts reliably.

| ID | Story | Pts | Priority | Source requirements |
|---|---|---:|---|---|
| US-09 | Create an Incident Only After Confirmed Failure | 8 | Must Have | FR5, NFR1, DR5 |
| US-10 | Manage Incident State and Avoid Duplicate Alerts | 8 | Must Have | FR6, NFR7, DR5 |
| US-11 | Send Incident Alerts Through Configured Channels | 8 | Must Have | FR7, FR13, NFR3 |
| US-12 | Retry Failed Notification Delivery | 5 | Should Have | FR8, NFR3 |

**What this EPIC delivers**

- A configurable failure threshold so temporary blips do not raise incidents; detection target of **2 minutes for at least 95 of 100 qualifying incidents** (AC-09.2, 09.6).
- Healthy → failing → recovered state tracking, with **one alert per state change** rather than per failed check (AC-10.1 – 10.4).
- Delivery through Slack, Discord, Email, and Webhook, with a **99 / 100 delivery target** and acknowledgement within 5 seconds where supported (AC-11.6, 11.7).
- Up to **3 retries with growing wait time**, then a logged final failure (AC-12.2 – 12.5).

**Why these stories belong together.** They are successive stages of one lifecycle — *Failure → Confirmation → Incident state → Notification → Retry* — all acting on the output of E2.

**Boundaries and notes**

- **Consumes:** E2 failure results; E1 notification destinations (US-03) and maintenance windows (US-04).
- **Feeds:** open-incident state to the E4 dashboard (US-13).
- Some targets (AC-10.5 "90 of 100 alerts actionable", AC-10.6 "resolution under 30 minutes") are **operational outcomes**: they are measured after release rather than implemented as a feature, so plan instrumentation for them.

---

### E4 — Dashboard, Uptime & Reporting

**Role:** Workflow spine — *Observe* | **Points:** 15 | **Stories:** 3 | **Primary actors:** Team Lead / Project Maintainer; API Developer / API Owner

**Goal.** Show users the current state of their APIs, their historical reliability, and periodic reports.

| ID | Story | Pts | Priority | Source requirements |
|---|---|---:|---|---|
| US-13 | View Overall API Health Dashboard | 5 | Must Have | FR10, NFR9, NFR10 |
| US-14 | View Uptime and Historical Performance | 5 | Should Have | FR4, FR9, NFR2, NFR4, DR3 |
| US-15 | Generate Monthly Uptime Reports | 5 | Could Have | FR14 |

**What this EPIC delivers**

- A consolidated dashboard showing each endpoint's health and open incidents, loading in **under 3 seconds** (AC-13.2, 13.3, 13.6).
- Uptime calculated as `((Total Time − Downtime) / Total Time) × 100`, plus response-time history, exposed via the reporting API (AC-14.1 – 14.4).
- Monthly reports for a requested period, downloadable and available through the API, restricted to data the user is authorised to see (AC-15.1 – 15.6).

**Why these stories belong together.** All three **read and present** data produced by E2 and E3. They differ in time horizon (now → history → periodic report) but share data sources and consumers.

**Boundaries and notes**

- **Consumes:** US-08 (results), US-10 (open-incident state), US-19 (authorisation for reports, AC-15.6).
- Ordered by value: only the dashboard is Must Have; history is Should Have and reports are Could Have.

---

### E5 — Responsible Monitoring & Security

**Role:** Platform / cross-cutting | **Points:** 18 | **Stories:** 3 | **Primary actors:** Monitored API Owner / Target Service; Platform Administrator

**Goal.** Make monitoring respectful of the APIs being checked and protect the data the platform stores.

| ID | Story | Pts | Priority | Source requirements |
|---|---|---:|---|---|
| US-16 | Respect Target API Rate Limits and Use Backoff | 5 | Must Have | FR12, NFR11, DR4 |
| US-17 | Protect Stored Monitoring and Configuration Data | 8 | Must Have | NFR5, NFR6, DR2 |
| US-18 | Maintain Tamper-Proof Operational Audit Logs | 5 | Should Have | NFR15 |

**What this EPIC delivers**

- Configurable frequency, rate limiting, backoff, and request identification so monitoring does not look like abusive traffic (AC-16.1 – 16.6).
- **AES-256** at rest, **TLS 1.3** in transit, and no unnecessary exposure of secrets; target of zero critical/high security incidents over 12 months (AC-17.1 – 17.5).
- Audit records for configuration and administrative changes that cannot be casually modified or deleted (AC-18.1 – 18.7).

**Why these stories belong together.** None is a step in the user journey; each **constrains or protects** the spine. They are *controls* — outbound (US-16), stored data (US-17), and traceability (US-18).

**Boundaries and notes**

- **US-16 constrains US-05.** Rate limiting and backoff apply to scheduled checks, so implement them alongside the scheduler rather than retrofitting.
- **US-17 should land before secrets are stored.** US-03 stores webhook URLs and tokens; AC-03.6 and AC-17.3 both require that secrets are protected.
- **Documented dependency:** US-17 → US-18 and US-17 → US-19 (the latter crosses into E6).

---

### E6 — Access Control & Advanced Monitoring

**Role:** Platform / cross-cutting | **Points:** 21 | **Stories:** 3 | **Primary actors:** Platform Administrator; API Developer / API Owner; DevOps / Deployment-Experienced Developer

**Goal.** Control who can do what, extend monitoring beyond a single location, and make the platform deployable in its hosting environment.

| ID | Story | Pts | Priority | Source requirements |
|---|---|---:|---|---|
| US-19 | Securely Manage Team Access Through RBAC | 8 | Must Have | FR17, NFR5, NFR6 |
| US-20 | Monitor APIs From Multiple Geographic Regions | 8 | Could Have | FR18 |
| US-21 | Deploy and Maintain the Platform Within Hosting Constraints | 5 | Must Have | NFR12 |

**What this EPIC delivers**

- **Admin / Operator / Read-Only** roles, with unauthorised operations rejected and permissions enforced consistently; sensitive configuration hidden from users without permission (AC-19.2 – 19.7).
- Region selection (examples: US-East, EU-Central, AP-South), with every result identifying its origin region and different regional outcomes representable (AC-20.1 – 20.6).
- A repeatable, maintainable deployment covering app, workers, database, storage, CPU/memory, and network (AC-21.1 – 21.8).

**Why these stories belong together.** They extend the platform beyond *one team, one location, one environment*. This is the **least cohesive** EPIC — see §9 for the analysis and an optional alternative.

**Boundaries and notes**

- **US-21 is foundational in delivery** (workers, database, and storage must exist) even though it sits here. `USER_STORIES.md` marks it Medium, while the MoSCoW file promotes it to Must Have (see §11).
- **US-19 affects everything.** Authorisation must be "enforced consistently across protected resources" (AC-19.6); introducing it early is cheaper than retrofitting.
- **US-20 is the only Could Have in this EPIC** and can be deferred without affecting the core loop.

---

### E7 — Scalability, Reliability & Data Management

**Role:** Platform / cross-cutting | **Points:** 24 | **Stories:** 3 | **Primary actors:** Platform Administrator / Project Development Team; DevOps; API Owner; Database Administrator

**Goal.** Keep the platform working — and affordable — as users, endpoints, workers, and stored history grow.

| ID | Story | Pts | Priority | Source requirements |
|---|---|---:|---|---|
| US-22 | Scale Monitoring Resources as Usage Grows | 8 | Should Have | NFR8, NFR10 |
| US-23 | Automatically Fail Over Monitoring Workers | 8 | Should Have | NFR13, DR1 |
| US-24 | Preserve Long-Term Monitoring Data Through Data Rollups | 8 | Should Have | NFR4, NFR14 |

**What this EPIC delivers**

- Support for growth toward **200 active users within 3 months**, with per-check cost **below $0.01 for 95% of checks**, and no extra traffic to monitored APIs caused by scaling (AC-22.1 – 22.4).
- A standby worker that takes over **within 10 seconds** of a primary crash, without losing or duplicating jobs (AC-23.4, 23.5, 23.7).
- Daily rollups of older minute-level data that preserve what long-term reporting needs and keep history reachable (AC-24.2 – 24.6).

**Why these stories belong together.** All three protect **long-term operation** — compute (US-22), availability (US-23), and storage (US-24) — and become important only once the core loop is running under real load.

**Boundaries and notes**

- **All Should Have, all 8 points:** this EPIC can follow the core system, but it is 24 points of infrastructure-heavy work.
- **Design decision to settle early:** US-08 says monitoring data is not deleted in normal operation (AC-08.7), while US-24 aggregates older data into daily summaries. Agree what "no loss of required history" means (AC-24.5) *before* implementing either.
- **Measured vs built:** AC-22.5 (churn below 5%) and AC-22.6 (satisfaction of 4.5/5 or higher) are business KPIs that must be *measurable*, not features to build.
- **Documented dependency chain:** US-05 → US-21 → US-22 → US-23.

---

### E8 — Project Governance & Requirement Management

**Role:** Project process | **Points:** 8 | **Stories:** 1 | **Primary actor:** Project Team / Project Maintainer

**Goal.** Ensure development follows a structured, traceable process for delivery, collaboration, and requirement decisions.

| ID | Story | Pts | Priority | Source requirements |
|---|---|---:|---|---|
| US-25 | Manage Agile Delivery, GitHub Collaboration and Requirement Decisions | 8 | Must Have | NFR16, NFR17, NFR18, DR6, DR7 |

**What this EPIC delivers.** Its 23 acceptance criteria fall into five areas:

| Area | ACs | Focus |
|---|---|---|
| A. Agile / SCRUM | AC-25.1 – 25.4 | Sprints, objectives, work tracking, acceptance-criteria validation |
| B. Requirement structure | AC-25.5 – 25.8 | User-story format, acceptance criteria, EPIC grouping, sprint assignment |
| C. GitHub development | AC-25.9 – 25.13 | Repository use, individual identity, traceable and descriptive commits |
| D. Slack communication | AC-25.14 – 25.16 | Central channels, decisions, updates |
| E. Requirement conflict management | AC-25.17 – 25.23 | Identify, document, resolve, and trace requirement conflicts |

**Why it is a separate EPIC.** US-25 governs *how the team works*, not what the platform does. Keeping it apart prevents process work from being mixed into product functionality and hiding in a product EPIC's totals.

**Boundaries and notes**

- It applies **throughout the project** rather than at one point in the workflow, so it behaves as a continuing activity, not a one-sprint deliverable.
- It has the **largest acceptance-criteria count** of any story. If the team finds 8 points too coarse to track, it splits naturally along the five areas above.
- This EPIC is the source of the rule that stories are grouped into EPICs (AC-25.7), which makes this document part of US-25's evidence.

---

## 6. Master Story → EPIC Mapping

| ID | User Story | EPIC | Pts | Priority | Source requirements |
|---|---|---|---:|---|---|
| US-01 | User Account Onboarding | E1 | 3 | Must Have | FR11, NFR9 |
| US-02 | Register and Configure an API Endpoint | E1 | 5 | Must Have | FR1 |
| US-03 | Configure Notification Details | E1 | 5 | Must Have | FR7, FR13, NFR3 |
| US-04 | Configure an Endpoint Maintenance Window | E1 | 3 | Should Have | FR15, DR4 |
| US-05 | Schedule Continuous Background Health Checks | E2 | 8 | Must Have | FR2, DR1 |
| US-06 | Detect API Health Failures | E2 | 8 | Must Have | FR3, DR2, DR5 |
| US-07 | Validate Response Body and JSONPath Content | E2 | 8 | Should Have | FR16 |
| US-08 | Record Health-Check Results and Response Time | E2 | 5 | Must Have | FR9, NFR2, NFR4 |
| US-09 | Create an Incident Only After Confirmed Failure | E3 | 8 | Must Have | FR5, NFR1, DR5 |
| US-10 | Manage Incident State and Avoid Duplicate Alerts | E3 | 8 | Must Have | FR6, NFR7, DR5 |
| US-11 | Send Incident Alerts Through Configured Channels | E3 | 8 | Must Have | FR7, FR13, NFR3 |
| US-12 | Retry Failed Notification Delivery | E3 | 5 | Should Have | FR8, NFR3 |
| US-13 | View Overall API Health Dashboard | E4 | 5 | Must Have | FR10, NFR9, NFR10 |
| US-14 | View Uptime and Historical Performance | E4 | 5 | Should Have | FR4, FR9, NFR2, NFR4, DR3 |
| US-15 | Generate Monthly Uptime Reports | E4 | 5 | Could Have | FR14 |
| US-16 | Respect Target API Rate Limits and Use Backoff | E5 | 5 | Must Have | FR12, NFR11, DR4 |
| US-17 | Protect Stored Monitoring and Configuration Data | E5 | 8 | Must Have | NFR5, NFR6, DR2 |
| US-18 | Maintain Tamper-Proof Operational Audit Logs | E5 | 5 | Should Have | NFR15 |
| US-19 | Securely Manage Team Access Through RBAC | E6 | 8 | Must Have | FR17, NFR5, NFR6 |
| US-20 | Monitor APIs From Multiple Geographic Regions | E6 | 8 | Could Have | FR18 |
| US-21 | Deploy and Maintain the Platform Within Hosting Constraints | E6 | 5 | Must Have | NFR12 |
| US-22 | Scale Monitoring Resources as Usage Grows | E7 | 8 | Should Have | NFR8, NFR10 |
| US-23 | Automatically Fail Over Monitoring Workers | E7 | 8 | Should Have | NFR13, DR1 |
| US-24 | Preserve Long-Term Monitoring Data Through Data Rollups | E7 | 8 | Should Have | NFR4, NFR14 |
| US-25 | Manage Agile Delivery, GitHub Collaboration and Requirement Decisions | E8 | 8 | Must Have | NFR16, NFR17, NFR18, DR6, DR7 |

**Priority membership**

- **Must Have (15):** US-01, 02, 03, 05, 06, 08, 09, 10, 11, 13, 16, 17, 19, 21, 25
- **Should Have (8):** US-04, 07, 12, 14, 18, 22, 23, 24
- **Could Have (2):** US-15, 20
- **Won't Have (0)**

---

## 7. Dependencies

### 7.1 Documented dependency chains (source)

These are stated in `STORY_POINTS_AND_PRIORITY.md` (§12).

```text
Monitoring:       US-02 → US-05 → US-06 → US-08
Incidents:        US-06 / US-07 → US-09 → US-10 → US-11 → US-12
Dashboard/report: US-08 → US-13 → US-14 → US-15
Security:         US-17 → US-18
                  US-17 → US-19
Infrastructure:   US-05 → US-21 → US-22 → US-23
```

### 7.2 Cross-EPIC dependency view

| From | To | Why | Basis |
|---|---|---|---|
| US-02 (E1) | US-05 (E2) | Endpoint must be registered to become eligible for scheduling (AC-02.6) | Source |
| US-06 / US-07 (E2) | US-09 (E3) | Failures and assertion failures feed incident confirmation (AC-07.6) | Source |
| US-08 (E2) | US-13 / US-14 / US-15 (E4) | Dashboards and reports read stored results | Source |
| US-05 (E2) | US-21 (E6) | Continuous background workers need a hosting environment | Source |
| US-17 (E5) | US-19 (E6) | Access control builds on data-protection controls | Source |
| US-03 (E1) | US-11 (E3) | Destinations must exist for alert delivery (AC-03.3) | Derived |
| US-04 (E1) | US-09 / US-10 (E3) | Maintenance windows suppress incidents and alerts (AC-04.3, 04.4) | Derived |
| US-10 (E3) | US-13 (E4) | Dashboard shows endpoints with open incidents (AC-13.3) | Derived |
| US-16 (E5) | US-05 (E2) | Rate limiting and backoff govern scheduled checks (AC-16.2, 16.3) | Derived |
| US-17 (E5) | US-03 (E1) | Secrets stored for notifications must be protected (AC-03.6, 17.3) | Derived |
| US-19 (E6) | US-15 (E4) | Reports respect user authorisation (AC-15.6) | Derived |
| US-08 (E2) | US-24 (E7) | Rollups summarise stored results | Derived |
| US-05 / US-06 / US-08 (E2) | US-20 (E6) | Regional checks reuse the pipeline and tag results by region (AC-20.3, 20.4) | Derived |
| US-05 (E2) | US-23 (E7) | Failover must take over scheduled jobs (AC-23.5) | Derived |

### 7.3 Reading the flow correctly

The narrative flow in `USER_STORIES.md` (§12) lists US-03 and US-04 in sequence before US-05. In reality they are **configuration inputs consumed later by E3**, not prerequisites for the scheduler. The same applies to the long US-05 → … → US-15 chain: it describes a user journey, whereas the dependency chains above are what constrain build order.

---

## 8. Requirement Traceability by EPIC

The full requirement-to-story matrix is maintained in `USER_STORIES.md` §10. This table rolls it up to EPIC level.

| EPIC | Functional (FR) | Non-functional (NFR) | Domain (DR) |
|---|---|---|---|
| **E1** | FR1, FR7, FR11, FR13, FR15 | NFR3, NFR9 | DR4 |
| **E2** | FR2, FR3, FR9, FR16 | NFR2, NFR4 | DR1, DR2, DR5 |
| **E3** | FR5, FR6, FR7, FR8, FR13 | NFR1, NFR3, NFR7 | DR5 |
| **E4** | FR4, FR9, FR10, FR14 | NFR2, NFR4, NFR9, NFR10 | DR3 |
| **E5** | FR12 | NFR5, NFR6, NFR11, NFR15 | DR2, DR4 |
| **E6** | FR17, FR18 | NFR5, NFR6, NFR12 | DR2 |
| **E7** | — | NFR4, NFR8, NFR10, NFR13, NFR14 | DR1 |
| **E8** | — | NFR16, NFR17, NFR18 | DR6, DR7 |

**Coverage check:** all **18 FR**, **18 NFR**, and **7 DR** items appear in at least one EPIC. Some links (US-21 → NFR5 / DR2, US-23 → DR1) come from the traceability matrix rather than the story header; both are included above.

**Pattern worth noting:** functional requirements concentrate in E1–E4 (the spine), non-functional requirements dominate E5–E7, and E8 alone carries the process requirements. The EPIC boundaries therefore also separate *what the product does* from *how well and how safely it does it*.

The traceability chain is unchanged by this grouping:

```text
Stakeholders → Requirements (FR / NFR / DR) → User Stories → Acceptance Criteria
            → Story Points + Priority → EPICs → Sprints → Implementation → Testing
```

---

## 9. Grouping Health Check

The EPIC structure is sound overall — E1 to E4 follow the workflow cleanly and E8 is correctly separated. The points below are **observations for discussion**, not changes. IDs and EPIC assignments in this document match the source files.

| # | Observation | Effect | Suggested handling |
|---|---|---|---|
| 1 | **E6 mixes three themes:** access control (US-19), a monitoring capability (US-20), and deployment (US-21). | Weakest cohesion; the EPIC name hides that two of its three stories are foundational. | Keep for now; consider the alternative below. |
| 2 | **Security is split across E5 and E6.** US-17, US-18, and US-19 share NFR5 / NFR6 and a documented dependency chain, but US-19 lives in E6. | A security-minded reader must look in two EPICs. | Cross-reference in planning; optionally regroup. |
| 3 | **US-01 and US-02 overlap** on first-endpoint setup. | Risk of duplicated or divergent validation logic. | Implement endpoint validation once and reuse. |
| 4 | **US-08 vs US-24:** "no deletion in normal operation" and "roll up older data" must be reconciled. | Conflicting storage behaviour if designed separately. | Decide the retention model before either story starts. |
| 5 | **Some ACs are measured outcomes, not features** (AC-10.5, AC-10.6, AC-22.5, AC-22.6, AC-17.5). | They cannot be "done" in one sprint; they need instrumentation and time. | Track separately from implementable criteria. |
| 6 | **US-25 is a continuing process story** with 23 ACs across five areas. | Hard to declare "complete" in a sprint. | Treat as a recurring governance item, or split by area. |

### Optional alternative grouping (Proposal — not adopted)

If the team wants tighter EPIC cohesion, redistributing E6 gives **7 EPICs**:

| Story | Current | Alternative | Rationale |
|---|---|---|---|
| US-19 RBAC | E6 | **E5** | Same security family as US-17 / US-18; shares NFR5 / NFR6 |
| US-21 Deployment | E6 | **E7** | Hosting is an operational-sustainability concern alongside scaling and failover |
| US-20 Multi-region | E6 | **E2** | It is an extension of the monitoring engine |

| EPIC | Points (current) | Points (alternative) |
|---|---:|---:|
| E1 | 16 | 16 |
| E2 | 29 | 37 |
| E3 | 29 | 29 |
| E4 | 15 | 15 |
| E5 | 18 | 26 |
| E6 | 21 | *(removed)* |
| E7 | 24 | 29 |
| E8 | 8 | 8 |
| **Total** | **160** | **160** |

Story IDs would not change. If the team adopts this, update the EPIC field in `USER_STORIES.md` first so all documents stay aligned.

---

## 10. Suggested Delivery Increments

> **Proposal.** This view is derived from MoSCoW priority and the dependencies in §7. It is **not** in the source documents. "Increment" is deliberately not the same as "sprint": each may span several sprints depending on measured velocity.

| Increment | Theme | Stories | Points |
|---|---|---|---:|
| **1** | Foundation and core monitoring | US-21, US-17, US-01, US-02, US-05, US-16, US-06, US-08 | 47 |
| **2** | Incidents, alerts, and visibility | US-03, US-09, US-10, US-11, US-13 | 34 |
| **3** | Access control | US-19 | 8 |
| **4** | Should Have product features | US-04, US-07, US-12, US-14, US-18 | 26 |
| **5** | Scale and resilience | US-22, US-23, US-24 | 24 |
| **6** | Could Have enhancements | US-15, US-20 | 13 |
| **Continuous** | Project governance | US-25 | 8 |
| | **Total** | | **160** |

**Reasoning**

- **Must Have product work totals 89 points** across Increments 1–3 (97 with US-25). Increment 1 delivers a working *monitor-and-record* loop; Increment 2 completes *detect → alert → see*.
- **US-17 and US-21 come first** because storage, workers, and secret protection must exist before endpoints, credentials, and jobs are stored.
- **US-19 is placed early** despite being a separate increment, because retrofitting consistent authorisation (AC-19.6) across finished features is costly.
- **US-04, US-07, and US-12** are Should Have refinements of the core loop and follow it.
- **US-25 runs alongside everything** rather than in a single sprint.

Increment 1 is large at 47 points. If velocity is lower than that, split it after US-05 / US-06 / US-08 so the first demo is the monitoring loop, then add US-16 and the remaining setup work.

---

## 11. Source Consistency Notes

These are inconsistencies found *between or inside* the two source documents. This README follows the values noted in the "Used here" column.

| # | Topic | What the sources say | Used here |
|---|---|---|---|
| 1 | **Total story points** | `STORY_POINTS_AND_PRIORITY.md` states **157** in two places. Summing its own per-story values, and its own distribution table (2×3 + 10×5 + 13×8), both give **160**. | **160** |
| 2 | **Priority scale** | `USER_STORIES.md` uses **High / Medium** (19 High, 6 Medium). `STORY_POINTS_AND_PRIORITY.md` uses **MoSCoW**. | **MoSCoW** |
| 3 | **US-21 priority** | Medium in `USER_STORIES.md`, **Must Have** in the MoSCoW file. It is the only story whose priority rises. | **Must Have** |
| 4 | **High → Should Have** | Five stories rated High become Should Have: US-07, US-12, US-14, US-18, US-23. | **Should Have** |
| 5 | **US-25 title** | The story index in `USER_STORIES.md` says "…Agile Delivery, Collaboration and…", while the detailed heading and the points file say "…Agile Delivery, **GitHub** Collaboration and…". | **Heading / points-file title** |
| 6 | **Traceability details** | US-13 lists NFR10 in its header, but the matrix maps NFR10 only to US-22. The matrix maps US-21 to NFR5 / DR2 and US-23 to DR1, though their headers do not list them. | **Union of both** |

**Recommended fixes in the source documents**

1. Correct the stated total in `STORY_POINTS_AND_PRIORITY.md` from 157 to **160** before velocity or sprint plans are calculated from it.
2. Update the `Priority` field of each story in `USER_STORIES.md` to the MoSCoW value (or add a MoSCoW field), so one scale is used everywhere.
3. Make the US-25 title identical in the index and the heading.

The mapping of priorities from the two scales is:

| USER_STORIES.md | → MoSCoW | Stories |
|---|---|---|
| High | Must Have (14) | US-01, 02, 03, 05, 06, 08, 09, 10, 11, 13, 16, 17, 19, 25 |
| High | Should Have (5) | US-07, 12, 14, 18, 23 |
| Medium | Must Have (1) | US-21 |
| Medium | Should Have (3) | US-04, 22, 24 |
| Medium | Could Have (2) | US-15, 20 |

---

## 12. Using This Document

### For sprint planning

1. **Start from priority and dependencies, not from EPIC order.** An EPIC is not a sprint; E7 has no Must Haves while E2 does.
2. **Plan against real velocity.** Points are relative; 160 is a scope size, not a schedule.
3. **Watch the 8-point stories.** 13 of 25 stories are 8 points, and the estimation guideline says anything larger should be split.
4. **Budget for testing and measurement.** Several ACs are performance or outcome targets (see §9, item 5).
5. **Do not close a story until its acceptance criteria pass** — including security, logging, and audit checks where applicable.

### Definition of Done (summary)

The full 11-point Definition of Done is in `USER_STORIES.md` §11. In short, a story is done when it is implemented, all mandatory acceptance criteria pass, positive/negative/edge cases are tested, error handling and security/authorisation are verified, existing behaviour is not broken, documentation is updated, and the change has been reviewed through GitHub and merged.

### Keeping this document current

| When this happens… | Update… |
|---|---|
| A story is added, removed, or renamed | §2, §5 (its EPIC), §6, §8 |
| Story points or priority change | §2, §5, §6, §10, and the source estimation file |
| A story moves between EPICs | The EPIC field in `USER_STORIES.md` **first**, then §2, §5, §6, §8 |
| A dependency is discovered | §7 |
| A requirement conflict changes behaviour | The affected stories/ACs first (per AC-25.22), then this document |

**Rules of thumb for placing a new story:** put it in the EPIC whose *capability* it extends; if it fits two, choose the one where most of its dependencies live; and never change a story ID, since IDs anchor traceability to requirements, acceptance criteria, sprints, and tests.

---

## 13. Sources

| Document | Used for |
|---|---|
| [`USER_STORIES.md`](USER_STORIES.md) | Story definitions, EPIC assignments, acceptance criteria, FR/NFR/DR traceability, stakeholders, Definition of Done |
| [`STORY_POINTS_AND_PRIORITY.md`](STORY_POINTS_AND_PRIORITY.md) | Story points, MoSCoW priority, estimation scale, documented dependencies |

Everything marked **Derived** or **Proposal** was produced during analysis for this README and should be reviewed by the team before being treated as project decisions.
