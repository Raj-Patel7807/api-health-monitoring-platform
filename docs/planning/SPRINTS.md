# Sprint Plan


---

## Table of Contents

1. [Purpose](#1-purpose)
2. [Planning Assumptions](#2-planning-assumptions)
3. [Sprint Overview & Calendar](#3-sprint-overview--calendar)
4. [Sprint 1 — Foundation & Security Baseline](#sprint-1--foundation--security-baseline)
5. [Sprint 2 — Core Monitoring Engine](#sprint-2--core-monitoring-engine)
6. [Sprint 3 — Incident Detection & Access Control](#sprint-3--incident-detection--access-control)
7. [Sprint 4 — Alerting, Dashboard & Audit](#sprint-4--alerting-dashboard--audit)
8. [Sprint 5 — Advanced Monitoring, Reliability & Enhancements](#sprint-5--advanced-monitoring-reliability--enhancements)
9. [Final Week — Hardening, Testing & Submission](#final-week--hardening-testing--submission)
10. [Dependency Validation](#10-dependency-validation)
11. [Velocity & Burndown Target](#11-velocity--burndown-target)
12. [Risks & Mitigations](#12-risks--mitigations)
13. [Descoping Priority Order](#13-descoping-priority-order)
14. [Definition of Done (Sprint-Level)](#14-definition-of-done-sprint-level)
15. [Traceability](#15-traceability)
16. [Keeping This Document Current](#16-keeping-this-document-current)

---

## 1. Purpose

This document assigns all 25 user stories to sprints so that:

- **Must Have** stories land early and are fully complete well before the deadline, respecting their documented dependency chains.
- **Should Have** stories follow the core loop they extend.
- **Could Have** stories are scheduled last and are the first thing to drop if the team runs out of time.
- **US-25** (Agile/GitHub/Slack/requirement governance) is treated as a continuing activity across every sprint, per its own nature (see `EPIC_GROUPING.md` §5, E8), not a one-sprint deliverable.
- A **fixed October 31 deadline is respected** by reserving the final week purely for hardening rather than new feature work.

---

## 2. Planning Assumptions

| Assumption | Value | Basis |
|---|---|---|
| **Start date** | September 22 | Given |
| **Hard deadline** | October 31 | Given |
| **Available time** | ~5.5 weeks (39 days) | Sep 22 → Oct 31 |
| **Sprint length** | **1 week** (not the 2-week default) | Compressed to fit the deadline; still a valid SCRUM cadence under NFR16 |
| **Number of delivery sprints** | 5 | Leaves a full final week as buffer |
| **Final week** | Reserved for testing, bug-fixing, docs, deployment hardening, and demo prep — **no new stories** | Standard practice before a hard deadline; also lets US-25's process/governance criteria be finalized |
| **Team size** | 9 members (`STAKEHOLDERS.md` S5) | Given |
| **Parallelization** | With 1-week sprints and 160 points to deliver, the team **must work multiple stories in parallel within each sprint** (different sub-teams on different stories), not serially one story at a time | Necessary to hit ~30+ pts/week with a 9-person team |
| **Target velocity** | ~30–32 points/sprint (Sprints 1–4), ~50 points in Sprint 5 (larger, lower-risk Should/Could Have batch, more parallelizable) | Fits 160 points into 5 sprints |

---

## 3. Sprint Overview & Calendar

| Sprint | Dates (2026) | Theme | Stories | Points |
|---|---|---|---|---:|
| **1** | Sep 22 – Sep 28 | Foundation & Security Baseline | US-25, US-01, US-17, US-21, US-02 | **29** |
| **2** | Sep 29 – Oct 5 | Core Monitoring Engine | US-16, US-05, US-06, US-03 | **26** |
| **3** | Oct 6 – Oct 12 | Incident Detection & Access Control | US-08, US-09, US-10, US-19 | **29** |
| **4** | Oct 13 – Oct 19 | Alerting, Dashboard & Audit | US-11, US-13, US-12, US-04, US-18 | **26** |
| **5** | Oct 20 – Oct 26 | Advanced Monitoring, Reliability & Enhancements | US-07, US-14, US-22, US-23, US-24, US-15, US-20 | **50** |
| **Final** | Oct 27 – Oct 31 | Hardening, Testing & Submission | *(no new stories — see below)* | **—** |
| | | **Total** | **25 stories** | **160** |

**Milestone:** All 15 Must Have stories (97 of 160 points) are scheduled for completion by the end of Sprint 4 (October 19), 12 days before the deadline. This buffer is deliberate and serves as the schedule margin if Sprints 1 through 4 run over.

---

## Sprint 1 — Foundation & Security Baseline

**Dates:** Sep 22 – Sep 28 | **Goal:** Stand up process scaffolding, hosting, security baseline, and the first user-facing flow.

| ID | Story | EPIC | Pts | Priority |
|---|---|---|---:|---|
| US-25 | Manage Agile Delivery, GitHub Collaboration and Requirement Decisions | E8 | 8 | Must Have |
| US-17 | Protect Stored Monitoring and Configuration Data | E5 | 8 | Must Have |
| US-21 | Deploy and Maintain the Platform Within Hosting Constraints | E6 | 5 | Must Have |
| US-01 | User Account Onboarding | E1 | 3 | Must Have |
| US-02 | Register and Configure an API Endpoint | E1 | 5 | Must Have |
| | **Sprint Total** | | **29** | |

**Parallel work streams (suggested, 9-person team):** Team A (2–3 people) — US-25 process setup + repo scaffolding. Team B (2–3 people) — US-21 hosting/deployment + US-17 encryption. Team C (2–3 people) — US-01 → US-02 (shared validation logic, build once).

**Why this order:** US-25 first so SCRUM/GitHub/Slack tracking exists before "real" work is logged. US-17 and US-21 before any data is stored — `EPIC_GROUPING.md` §5 (E5, E6) explicitly flags both as needing to land before secrets (US-03) and the scheduler (US-05) exist. US-01 → US-02 reuse shared registration/validation logic.

**Sprint Goal (demoable):** Sign up, register one endpoint, infrastructure and encryption provably in place.

---

## Sprint 2 — Core Monitoring Engine

**Dates:** Sep 29 – Oct 5 | **Goal:** Build the health-check pipeline and notification destinations.

| ID | Story | EPIC | Pts | Priority |
|---|---|---|---:|---|
| US-16 | Respect Target API Rate Limits and Use Backoff | E5 | 5 | Must Have |
| US-05 | Schedule Continuous Background Health Checks | E2 | 8 | Must Have |
| US-06 | Detect API Health Failures | E2 | 8 | Must Have |
| US-03 | Configure Notification Details | E1 | 5 | Must Have |
| | **Sprint Total** | | **26** | |

**Why this order:** US-16 alongside US-05 (`EPIC_GROUPING.md` §5, E5: *"implement them alongside the scheduler rather than retrofitting"*). US-05 → US-06 per the documented monitoring chain. US-03 now (not Sprint 1) because US-17's encryption is already in place, satisfying AC-03.6/AC-17.3 immediately.

**Sprint Goal (demoable):** Registered endpoints are checked automatically via BullMQ; failures are classified by type; notification destinations can be configured.

---

## Sprint 3 — Incident Detection & Access Control

**Dates:** Oct 6 – Oct 12 | **Goal:** Confirmed incidents, health-check history, and RBAC.

| ID | Story | EPIC | Pts | Priority |
|---|---|---|---:|---|
| US-08 | Record Health-Check Results and Response Time | E2 | 5 | Must Have |
| US-09 | Create an Incident Only After Confirmed Failure | E3 | 8 | Must Have |
| US-10 | Manage Incident State and Avoid Duplicate Alerts | E3 | 8 | Must Have |
| US-19 | Securely Manage Team Access Through RBAC | E6 | 8 | Must Have |
| | **Sprint Total** | | **29** | |

**Why this order:** US-08 continues `US-05 → US-06 → US-08`. US-06 → US-09 → US-10 is the documented incident chain. US-19 placed here (not later, despite its EPIC being scheduled last) because `EPIC_GROUPING.md` §5 (E6) warns *"introducing it early is cheaper than retrofitting"* — and US-17 (its dependency) is already done.

**Sprint Goal (demoable):** Threshold-based incident lifecycle working internally; role-based permissions enforced app-wide.

---

## Sprint 4 — Alerting, Dashboard & Audit

**Dates:** Oct 13 – Oct 19 | **Goal:** Close out the remaining Must Have work — real alert delivery and the dashboard — plus directly-attached Should Have refinements.

| ID | Story | EPIC | Pts | Priority |
|---|---|---|---:|---|
| US-11 | Send Incident Alerts Through Configured Channels | E3 | 8 | Must Have |
| US-13 | View Overall API Health Dashboard | E4 | 5 | Must Have |
| US-12 | Retry Failed Notification Delivery | E3 | 5 | Should Have |
| US-04 | Configure an Endpoint Maintenance Window | E1 | 3 | Should Have |
| US-18 | Maintain Tamper-Proof Operational Audit Logs | E5 | 5 | Should Have |
| | **Sprint Total** | | **26** | |

**Why this order:** US-11 needs US-03 (Sprint 2) and US-10 (Sprint 3). US-11 → US-12 (same delivery mechanism). US-13 needs US-08 + US-10 as data sources. US-04 layers maintenance-window suppression onto the now-existing incident engine — this is a **derived/soft dependency**, not a hard blocker (see §10). US-18 follows US-17 (Sprint 1).

**Milestone — All 15 Must Have Stories Complete.** This is the schedule checkpoint for October 19, 12 days before the deadline. If the project is on schedule at this point, Sprint 5 and the final week proceed as planned. If not, the descoping order in Section 13 should be applied immediately.

**Sprint Goal (demoable):** Full Must Have core product, end to end: register → monitor → detect → confirm incident → alert → dashboard, with retries, maintenance suppression, and audit trails.

---

## Sprint 5 — Advanced Monitoring, Reliability & Enhancements

**Dates:** Oct 20 – Oct 26 | **Goal:** Deliver all remaining Should Have and Could Have stories in one larger, more parallelizable sprint, since none of them block the core product.

| ID | Story | EPIC | Pts | Priority |
|---|---|---|---:|---|
| US-07 | Validate Response Body and JSONPath Content | E2 | 8 | Should Have |
| US-14 | View Uptime and Historical Performance | E4 | 5 | Should Have |
| US-22 | Scale Monitoring Resources as Usage Grows | E7 | 8 | Should Have |
| US-23 | Automatically Fail Over Monitoring Workers | E7 | 8 | Should Have |
| US-24 | Preserve Long-Term Monitoring Data Through Data Rollups | E7 | 8 | Should Have |
| US-15 | Generate Monthly Uptime Reports | E4 | 5 | Could Have |
| US-20 | Monitor APIs From Multiple Geographic Regions | E6 | 8 | Could Have |
| | **Sprint Total** | | **50** | |

**This sprint is deliberately overloaded (50 pts) because:**
1. None of these stories are Must Have — if the sprint runs long, it simply bleeds into the final week or gets trimmed (§13), without risking the core deliverable.
2. All seven stories are largely independent of each other (E2 extension, E4 extensions, three E7 infra stories, one E6 extension) — genuinely parallelizable across 9 people, unlike the tightly sequential Sprints 1–3.

**Before this sprint starts:** resolve the US-08/US-24 retention-model question flagged in `EPIC_GROUPING.md` §9 (item 4) — *"no deletion in normal operation" (AC-08.7) vs. "roll up older data" (US-24)* — in a short design discussion at the start of the sprint, not mid-build.

**Sprint Goal (demoable):** Silent-failure detection, historical uptime views, auto-scaling, worker failover, long-term data rollups, monthly reports, and multi-region monitoring — full 160-point scope.

---

## Final Week — Hardening, Testing & Submission

**Dates:** Oct 27 – Oct 31 | **No new stories.** This week is protected time for:

1. **End-to-end regression testing** across all 25 stories' acceptance criteria (not just the ones built that week).
2. **Bug fixing** from Sprint 5 and any carried-over items from earlier sprints.
3. **Security/performance verification** against the NFR targets (AC-17.5, AC-09.6, AC-11.6, AC-13.6, AC-22.3, etc.) — these are measured outcomes, not features, and need dedicated verification time (see §12).
4. **Documentation finalization** — README, deployment docs, requirement traceability docs kept current per §16.
5. **US-25 governance wrap-up** — final check against all 23 acceptance criteria (AC-25.1–25.23), including confirming no unresolved requirement conflicts remain (AC-25.23).
6. **Demo/presentation prep** for course submission.
7. **Buffer** for anything that slipped from Sprints 1–5.

---

## 10. Dependency Validation

| Dependency (source → target) | Source sprint | Target sprint | Status |
|---|---|---|---|
| US-01 → US-02 | 1 | 1 | Satisfied — same sprint, build order preserved |
| US-02 → US-05 | 1 | 2 | Satisfied |
| US-16 → US-05 | 2 | 2 | Satisfied — same sprint, implemented alongside per `EPIC_GROUPING.md` §5 |
| US-05 → US-06 | 2 | 2 | Satisfied — same sprint |
| US-06 → US-08 | 2 | 3 | Satisfied |
| US-06 / US-07 → US-09 | 2 / 5 | 3 | Satisfied — US-06 alone satisfies this; US-07 confirmed non-blocking in source doc |
| US-09 → US-10 | 3 | 3 | Satisfied — same sprint |
| US-03 → US-11 | 2 | 4 | Satisfied |
| US-10 → US-11 | 3 | 4 | Satisfied |
| US-11 → US-12 | 4 | 4 | Satisfied — same sprint |
| US-08 → US-13 | 3 | 4 | Satisfied |
| US-10 → US-13 | 3 | 4 | Satisfied |
| US-13 → US-14 | 4 | 5 | Satisfied |
| US-19 → US-15 | 3 | 5 | Satisfied |
| US-14 → US-15 | 5 | 5 | Satisfied — same sprint |
| US-17 → US-18 | 1 | 4 | Satisfied |
| US-17 → US-19 | 1 | 3 | Satisfied |
| US-17 → US-03 | 1 | 2 | Satisfied |
| US-05 → US-21 | 2 | 1 | Deviation — see note below |
| US-21 → US-22 | 1 | 5 | Satisfied |
| US-22 → US-23 | 5 | 5 | Satisfied — same sprint |
| US-05 → US-23 | 2 | 5 | Satisfied |
| US-05 → US-20 | 2 | 5 | Satisfied |
| US-08 → US-24 | 3 | 5 | Satisfied |
| US-04 → US-09 / US-10 | 4 | 3 | Deviation — see note below |

**Two intentional deviations from the literal chain text, both already validated in the source documents:**

1. **US-21 before US-05.** `EPIC_GROUPING.md` §5 (E6): *"US-21 is foundational in delivery... even though it sits here."* Hosting must exist before the scheduler that runs on it.
2. **US-04 after US-09/US-10.** Marked **Derived**, not **Source**, in `EPIC_GROUPING.md` §7.2. It represents a suppression rule layered onto an existing incident engine rather than a prerequisite for building one.

---

## 11. Velocity & Burndown Target

| Sprint | Dates | Planned Points | Cumulative | % of 160 |
|---|---|---:|---:|---:|
| 1 | Sep 22–28 | 29 | 29 | 18% |
| 2 | Sep 29–Oct 5 | 26 | 55 | 34% |
| 3 | Oct 6–12 | 29 | 84 | 53% |
| 4 | Oct 13–19 | 26 | 110 | **69% — all Must Have done** |
| 5 | Oct 20–26 | 50 | 160 | 100% |
| Final | Oct 27–31 | — (hardening) | 160 | — |

Progress against this table should be reviewed weekly. If cumulative actual points fall materially behind this line by the end of Sprint 2 (Oct 5), the descoping order in Section 13 should be applied immediately rather than deferred to Sprint 5, which already carries the largest planned workload.

---

## 12. Risks & Mitigations

| # | Risk | Affected Sprint(s) | Mitigation |
|---|---|---|---|
| 1 | 1-week sprints are aggressive for 26–29-point loads; Sprints 1 and 3 carry the most estimation uncertainty (security, RBAC, scheduling). | 1, 3 | Parallelize across sub-teams from day one (see per-sprint suggestions); if behind, split US-17/US-19 into smaller tasks rather than deferring — both are Must Have. |
| 2 | US-08 (AC-08.7: no deletion) and US-24 (rollups) may conflict without upfront design. | 3, 5 | Resolve retention model at the **start of Sprint 5**, not mid-sprint. |
| 3 | Several acceptance criteria are measured outcomes rather than features (AC-10.5, AC-10.6, AC-17.5, AC-22.5, AC-22.6) and cannot be marked "done" within a single sprint. | 3, 4, 5 | Verify these during the Final Week rather than treating them as sprint exit criteria. |
| 4 | Sprint 5 is overloaded (50 pts) by design; if Sprints 1–4 slip even slightly, Sprint 5 has no slack of its own. | 5 | This is intentional; see Section 13. Sprint 5 content is the designated descoping target, not the Final Week. |
| 5 | 9-person team parallelization requires clear task ownership within each 1-week sprint, or work stalls on handoffs. | All | Assign explicit sub-team ownership at each sprint's kickoff (see Sprint 1's example); track via GitHub issues per AC-25.3. |

---

## 13. Descoping Priority Order

This order should be agreed upon by the team in advance, before it is needed:

1. **US-20** (Multi-Region Monitoring, Could Have, 8 pts) — drop first. Fully optional; no other story depends on it.
2. **US-15** (Monthly Uptime Reports, Could Have, 5 pts) — drop second. Depends only on already-built US-14/US-19.
3. **US-24** (Data Rollups, Should Have, 8 pts) — defer third; document as a known limitation (raw data still stored per US-08, just not rolled up).
4. **US-22 / US-23** (Scaling / Failover, Should Have, 8 pts each) — defer fourth; these are operational-maturity features, not needed for a course demo of core functionality.
5. **US-07** (Response-Body Validation, Should Have, 8 pts) — defer only as a last resort, as it is the most visible advanced feature among the Should Have stories.
6. **Never cut** any Must Have story (US-01–03, 05, 06, 08–11, 13, 16, 17, 19, 21, 25) or US-04/US-12/US-14/US-18 (Should Have, but small and already load-bearing for the core loop's polish) without a full team decision and a documented requirement-conflict entry (AC-25.17–25.23).

---

## 14. Definition of Done (Sprint-Level)

A **sprint** is complete when every planned story satisfies the story-level Definition of Done (`USER_STORIES.md` §11), **and**:

1. All planned stories are Done or explicitly carried over with a documented reason (AC-25.3).
2. A sprint review/demo has been held showing the sprint goal working end-to-end.
3. A brief retrospective has been held (even a 15-minute one, given the 1-week cadence) and action items logged.
4. Dependency validation (§10) is re-checked against what was actually built.
5. Any newly discovered requirement conflict is logged and routed through AC-25.17–25.23.

---

## 15. Traceability

```text
Stakeholders → Requirements (FR / NFR / DR) → User Stories → Acceptance Criteria
            → Story Points + Priority → EPICs → Sprints (this document) → Implementation → Testing
```

| Document | Role in this plan |
|---|---|
| `STAKEHOLDERS.md` | Defines who each sprint's delivered features serve |
| `ELICITATION.md` | Source of the evidence behind requirements |
| `FR.md` / `NFR.md` | Requirement definitions traced by story |
| `USER_STORIES.md` | Story text, acceptance criteria, Definition of Done |
| `STORY_POINTS_AND_PRIORITY.md` | Points, MoSCoW priority, documented dependency chains used to order sprints |
| `EPIC_GROUPING.md` | EPIC structure, cross-EPIC dependencies, known tensions reflected in §10 and §12 |
| **`SPRINTS.md`** *(this document)* | Assigns every story to a sprint against a hard Oct 31 deadline, validates dependency order, defines cut priorities and sprint-level DoD |

---

## 16. Keeping This Document Current

| When this happens… | Update… |
|---|---|
| A sprint's actual velocity differs from plan | §11 (log actual vs. planned) at the end of every sprint |
| Sprint 1 or 2 finishes behind schedule | Apply §13 immediately — do not wait for Sprint 4 |
| A new dependency is discovered mid-sprint | §10, and re-validate downstream sprints |
| The team decides US-04 is a hard prerequisite for US-09/US-10 after all | Move US-04 into Sprint 3, re-total Sprints 3–4 |
| A requirement conflict changes story scope | The affected story in `USER_STORIES.md` first, then this document |
| A sprint completes | §14 checklist, then log actual results for the next sprint's forecast |

---
