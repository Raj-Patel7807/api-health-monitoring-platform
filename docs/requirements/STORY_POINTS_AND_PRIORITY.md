# Story Points & Priority

## Distributed API Health & Incident Monitoring Platform

## 1. Purpose

This document defines the **Story Point Estimation and Priority Assignment** for the updated 25 user stories of the **Distributed API Health & Incident Monitoring Platform**.

The estimation is based on the updated user stories, their acceptance criteria, technical scope, dependencies, and role in the overall monitoring workflow. The updated source contains **25 user stories across 8 EPICs**. fileciteturn1file0L55-L65

---

# 2. Story Point Estimation

## 2.1 What Are Story Points?

Story points are a **relative measure of effort and complexity** used to estimate the size of a user story.

They do not directly represent development hours. The estimation considers:

- **Complexity** — technical difficulty of implementation.
- **Effort** — amount of development work involved.
- **Uncertainty** — technical or implementation uncertainty.
- **Dependencies** — dependency on other system components or services.
- **Testing effort** — effort required to verify acceptance criteria.
- **Integration effort** — interaction with external services, workers, infrastructure, or data stores.

---

# 3. Story Point Scale

The project uses a modified **Fibonacci scale**:

| Story Points | Relative Size | Description |
|---:|---|---|
| **1** | Very Small | Very simple change with minimal implementation effort |
| **2** | Small | Straightforward functionality with limited complexity |
| **3** | Small–Medium | Moderate but well-understood functionality |
| **5** | Medium | Multiple components or moderate technical complexity |
| **8** | Large | Complex functionality involving multiple components, integrations, or significant testing |
| **13** | Very Large | Highly complex or uncertain work that should generally be split into smaller stories |

> **Estimation rule:** No current story is assigned 13 points. Stories larger than 8 points should be considered for decomposition before sprint planning.

---

# 4. Priority Assignment

## 4.1 MoSCoW Prioritization

| Priority | Meaning |
|---|---|
| **Must Have** | Essential functionality required for the core system to operate |
| **Should Have** | Important functionality that improves the system but is not essential to the minimum usable system |
| **Could Have** | Useful enhancement that can be implemented if time and resources permit |
| **Won't Have** | Functionality intentionally excluded from the current scope |

## 4.2 Prioritization Principles

Priority is assigned based on:

1. Contribution to the core API monitoring workflow.
2. Dependency on or support for other user stories.
3. User and operational value.
4. Security and reliability importance.
5. Technical necessity for a functioning platform.
6. Whether the feature can reasonably be deferred without preventing the core system from operating.

> **Note:** Story points measure relative effort, while priority represents implementation importance. They are separate dimensions.

---

# 5. Updated Story Point & Priority Assignment

| ID | User Story | EPIC | Story Points | Priority |
|---|---|---|---:|---|
| **US-01** | User Account Onboarding | E1 | **3** | **Must Have** |
| **US-02** | Register and Configure an API Endpoint | E1 | **5** | **Must Have** |
| **US-03** | Configure Notification Details | E1 | **5** | **Must Have** |
| **US-04** | Configure an Endpoint Maintenance Window | E1 | **3** | **Should Have** |
| **US-05** | Schedule Continuous Background Health Checks | E2 | **8** | **Must Have** |
| **US-06** | Detect API Health Failures | E2 | **8** | **Must Have** |
| **US-07** | Validate Response Body and JSONPath Content | E2 | **8** | **Should Have** |
| **US-08** | Record Health-Check Results and Response Time | E2 | **5** | **Must Have** |
| **US-09** | Create an Incident Only After Confirmed Failure | E3 | **8** | **Must Have** |
| **US-10** | Manage Incident State and Avoid Duplicate Alerts | E3 | **8** | **Must Have** |
| **US-11** | Send Incident Alerts Through Configured Channels | E3 | **8** | **Must Have** |
| **US-12** | Retry Failed Notification Delivery | E3 | **5** | **Should Have** |
| **US-13** | View Overall API Health Dashboard | E4 | **5** | **Must Have** |
| **US-14** | View Uptime and Historical Performance | E4 | **5** | **Should Have** |
| **US-15** | Generate Monthly Uptime Reports | E4 | **5** | **Could Have** |
| **US-16** | Respect Target API Rate Limits and Use Backoff | E5 | **5** | **Must Have** |
| **US-17** | Protect Stored Monitoring and Configuration Data | E5 | **8** | **Must Have** |
| **US-18** | Maintain Tamper-Proof Operational Audit Logs | E5 | **5** | **Should Have** |
| **US-19** | Securely Manage Team Access Through RBAC | E6 | **8** | **Must Have** |
| **US-20** | Monitor APIs From Multiple Geographic Regions | E6 | **8** | **Could Have** |
| **US-21** | Deploy and Maintain the Platform Within Hosting Constraints | E6 | **5** | **Must Have** |
| **US-22** | Scale Monitoring Resources as Usage Grows | E7 | **8** | **Should Have** |

| **US-24** | Preserve Long-Term Monitoring Data Through Data Rollups | E7 | **8** | **Should Have** |
| **US-25** | Manage Agile Delivery, GitHub Collaboration and Requirement Decisions | E8 | **8** | **Must Have** |

---

# 6. Detailed Story Point Justification

## US-01 — User Account Onboarding

**Story Points:** 3  
**Priority:** Must Have

The story covers account registration, validation, first-endpoint setup, invalid-input handling, configuration persistence, and a five-minute onboarding target. The workflow is relatively contained, making it a 3-point story. It is Must Have because users need a basic onboarding path before using the platform.

## US-02 — Register and Configure an API Endpoint

**Story Points:** 5  
**Priority:** Must Have

The story includes endpoint URL, expected status code, monitoring frequency, validation, persistence, and monitoring eligibility. It directly feeds the monitoring workflow and therefore is Must Have. The multiple configuration and validation steps justify 5 points.

## US-03 — Configure Notification Details

**Story Points:** 5  
**Priority:** Must Have

The updated story supports Slack, Discord, Email, and Webhook destinations, including account-level and endpoint-level configuration and secure handling of notification details. Multiple integrations and routing scopes make this a medium-complexity story.

## US-04 — Configure an Endpoint Maintenance Window

**Story Points:** 3  
**Priority:** Should Have

The story requires saving a maintenance period and changing incident/alert behaviour while the window is active. It is relatively contained and improves operational accuracy, but it is not essential to the basic monitoring path.

## US-05 — Schedule Continuous Background Health Checks

**Story Points:** 8  
**Priority:** Must Have

This involves BullMQ, background scheduling, repeated monitoring, automatic execution, non-blocking application behaviour, and worker/job failure visibility. It is a core architectural capability and has substantial implementation effort.

## US-06 — Detect API Health Failures

**Story Points:** 8  
**Priority:** Must Have

The monitoring engine must detect wrong status codes, timeouts, connection failures, SSL/TLS failures, and temporary failure conditions. Multiple error paths and testing scenarios make this an 8-point core story.

## US-07 — Validate Response Body and JSONPath Content

**Story Points:** 8  
**Priority:** Should Have

The story adds text, regular-expression, and JSONPath assertions and integrates assertion failures with the incident workflow. This is technically significant, but basic monitoring can operate without response-body assertions, so it is Should Have.

## US-08 — Record Health-Check Results and Response Time

**Story Points:** 5  
**Priority:** Must Have

The story stores successful/failed results, response times, failure information, historical data, and retention information. It is a medium-complexity data-management story and is necessary for monitoring history.

## US-09 — Create an Incident Only After Confirmed Failure

**Story Points:** 8  
**Priority:** Must Have

The story applies failure thresholds, distinguishes temporary failures from confirmed incidents, and includes a failure-detection performance target. It is central to preventing false incidents.

## US-10 — Manage Incident State and Avoid Duplicate Alerts

**Story Points:** 8  
**Priority:** Must Have

The story manages healthy-to-failing transitions, incident opening, duplicate-alert prevention, recovery, new incidents after recovery, actionable-alert targets, and resolution targets. This state-management logic is substantial.

## US-11 — Send Incident Alerts Through Configured Channels

**Story Points:** 8  
**Priority:** Must Have

The story integrates Slack, Discord, Email, and Webhook notifications and includes alert content, delivery success, and acknowledgement requirements. Multiple integrations make it complex, while alerting is core to incident management.

## US-12 — Retry Failed Notification Delivery

**Story Points:** 5  
**Priority:** Should Have

The story requires failure detection, up to three retries, growing wait time, stopping retries after success, and final failure logging. It improves reliability but can follow the core notification mechanism.

## US-13 — View Overall API Health Dashboard

**Story Points:** 5  
**Priority:** Must Have

The dashboard provides endpoint overview, health state, open incidents, consolidated information, current monitoring data, and a performance target. It is the primary user-facing operational view.

## US-14 — View Uptime and Historical Performance

**Story Points:** 5  
**Priority:** Should Have

The story includes uptime calculation, the standard uptime formula, response-time history, reporting API access, and historical availability. It provides important analytical value but can follow the core monitoring workflow.

## US-15 — Generate Monthly Uptime Reports

**Story Points:** 5  
**Priority:** Could Have

The updated story includes monthly report generation, reporting-period correctness, relevant data, download, API access, and authorization. The expanded scope justifies 5 points, but monthly reporting is not required for basic real-time monitoring.

## US-16 — Respect Target API Rate Limits and Use Backoff

**Story Points:** 5  
**Priority:** Must Have

The story includes configurable frequency, rate limiting, backoff, reasonable intervals, request identification, and avoidance of abusive traffic. It is important for responsible monitoring of external APIs.

## US-17 — Protect Stored Monitoring and Configuration Data

**Story Points:** 8  
**Priority:** Must Have

The story covers AES-256 at rest, TLS 1.3 in transit, secret protection, secure communication, security incident targets, and compliance checks. Security affects multiple system components and requires significant testing.

## US-18 — Maintain Tamper-Proof Operational Audit Logs

**Story Points:** 5  
**Priority:** Should Have

The story requires configuration-change logging, administrative action tracking, event details, tamper resistance, deletion protection, access protection, and investigation support. It is important for governance/security but can follow the core functionality.

## US-19 — Securely Manage Team Access Through RBAC

**Story Points:** 8  
**Priority:** Must Have

The story introduces role assignment, Admin/Operator/Read-Only permissions, unauthorized-operation rejection, consistent authorization, and sensitive configuration protection. Authorization is cross-cutting and therefore complex.

## US-20 — Monitor APIs From Multiple Geographic Regions

**Story Points:** 8  
**Priority:** Could Have

The story requires region selection, regional execution, region identification, different regional results, and regional analysis. Multi-region monitoring introduces infrastructure and networking complexity and can be deferred after the core monitoring system.

## US-21 — Deploy and Maintain the Platform Within Hosting Constraints

**Story Points:** 5  
**Priority:** Must Have

The story covers application deployment, background workers, database, storage, CPU/memory, network connectivity, repeatable deployment, and maintainability. The selected environment must support the platform's monitoring workload.

## US-22 — Scale Monitoring Resources as Usage Grows

**Story Points:** 8  
**Priority:** Should Have

The story covers user growth, resource scaling, health-check cost, unnecessary traffic, churn measurement, and satisfaction measurement. Scaling introduces infrastructure complexity and can follow the initial implementation.



## US-24 — Preserve Long-Term Monitoring Data Through Data Rollups

**Story Points:** 8  
**Priority:** Should Have

The story requires recent minute-level data, daily aggregation, information preservation, historical accessibility, protection against required-history loss, and sustainable storage. This requires substantial data-management logic.

## US-25 — Manage Agile Delivery, GitHub Collaboration and Requirement Decisions

**Story Points:** 8  
**Priority:** Must Have

The updated story spans Agile/SCRUM, sprint objectives, work tracking, acceptance-criteria validation, user-story structure, EPIC grouping, sprint organization, GitHub contribution traceability, commit quality, Slack communication, and formal requirement-conflict management.

Because it governs project delivery and traceability throughout development, it is estimated at 8 points and treated as Must Have for the project process.

---

# 7. Priority Distribution

| Priority | Number of Stories | Percentage |
|---|---:|---:|
| **Must Have** | 15 | 62.5% |
| **Should Have** | 7 | 29.2% |
| **Could Have** | 2 | 8.3% |
| **Won't Have** | 0 | 0% |
| **Total** | **24** | **100%** |

### Must Have

US-01, US-02, US-03, US-05, US-06, US-08, US-09, US-10, US-11, US-13, US-16, US-17, US-19, US-21, US-25

### Should Have

US-04, US-07, US-12, US-14, US-18, US-22, US-24

### Could Have

US-15, US-20

### Won't Have

None in the current project scope.

---

# 8. Total Story Points

**Total Story Points = 157**

This represents the relative estimated size of all 25 user stories.

> Story points are not development hours. The total should later be considered together with the team's measured sprint velocity.

---

# 9. Story Point Distribution

| Story Points | Number of Stories |
|---:|---:|
| **1** | 0 |
| **2** | 0 |
| **3** | 2 |
| **5** | 10 |
| **8** | 13 |
| **13** | 0 |
| **Total** | **25** |

The updated project contains a larger number of 8-point stories because the revised requirements introduce response-content validation, RBAC, multi-region monitoring, worker failover, long-term data rollups, and project governance.

---

# 10. Priority vs. Complexity

Priority and story points are independent.

| Story | Complexity | Priority | Main Reason |
|---|---|---|---|
| US-06 | High — 8 pts | Must Have | Core failure detection |
| US-07 | High — 8 pts | Should Have | Advanced response-content validation |
| US-20 | High — 8 pts | Could Have | Multi-region enhancement |

| US-25 | High — 8 pts | Must Have | Project governance and traceability |

A high story-point value does not automatically imply low priority.

---

# 11. Core Product Dependency Flow

```text
US-01
User Onboarding
   ↓
US-02
Register API Endpoint
   ↓
US-05
Schedule Background Health Checks
   ↓
US-06
Detect API Health Failures
   ↓
US-07
Validate Response Content
   ↓
US-08
Record Health-Check Results
   ↓
US-09
Confirm Failure
   ↓
US-10
Manage Incident State
   ↓
US-11
Send Incident Alert
   ↓
US-12
Retry Failed Notification
   ↓
US-13
View Dashboard
   ↓
US-14
View Uptime & History
   ↓
US-15
Generate Monthly Report
```

Supporting and cross-cutting capabilities:

```text
US-03 → Notification Configuration
US-04 → Maintenance Windows

US-16 → Rate Limiting & Backoff
US-17 → Data Protection
US-18 → Audit Logging

US-19 → RBAC
US-20 → Multi-Region Monitoring
US-21 → Deployment & Hosting

US-22 → Scalability

US-24 → Data Rollups

US-25 → Agile / GitHub / Slack / Requirement Governance
```

---

# 12. Dependency Considerations for Sprint Planning

### Monitoring Dependencies

```text
US-02
  ↓
US-05
  ↓
US-06
  ↓
US-08
```

### Incident Dependencies

```text
US-06 / US-07
       ↓
     US-09
       ↓
     US-10
       ↓
     US-11
       ↓
     US-12
```

### Dashboard and Reporting Dependencies

```text
US-08
  ↓
US-13
  ↓
US-14
  ↓
US-15
```

### Security Dependencies

```text
US-17
  ├── US-18
  └── US-19
```



These dependencies should be considered when the team divides stories into sprints.

---

# 13. Estimation Guidelines for the Team

## 3 Points

Use when:

- The functionality is well understood.
- The implementation is relatively small.
- Few components are involved.
- Testing requirements are limited.

## 5 Points

Use when:

- Several components interact.
- Moderate backend/frontend work is required.
- There are multiple acceptance criteria.
- Moderate testing is required.

## 8 Points

Use when:

- Multiple system components are involved.
- External integrations or infrastructure are required.
- The story contains significant system logic.
- There are substantial security, reliability, or testing requirements.
- There is meaningful technical uncertainty.

## 13 Points

Use only when:

- The story is too large or uncertain to handle as one sprint-level item.
- The team should first consider splitting it into smaller stories.

---

# 14. Definition of Done

A user story should be considered complete when:

1. The functionality described by the user story has been implemented.
2. All mandatory acceptance criteria pass.
3. The corresponding FR/NFR/DR requirement remains satisfied.
4. Relevant positive, negative, and edge cases have been tested.
5. Applicable error handling has been implemented.
6. Security and authorization requirements have been verified where applicable.
7. Monitoring, logging, and audit behaviour has been verified where applicable.
8. Existing monitoring, incident, alerting, and reporting behaviour is not broken.
9. Relevant project documentation has been updated.
10. The implementation is reviewed through the project's GitHub workflow.
11. The completed change is integrated into the appropriate project branch.

---

# 15. Traceability

The updated project follows:

```text
Stakeholders
     ↓
Requirements
     ↓
User Stories
     ↓
Acceptance Criteria
     ↓
Story Points + Priority
     ↓
EPICs
     ↓
Sprints
     ↓
Implementation
     ↓
Testing
```

The user story IDs remain unchanged so that story points and priorities can be traced to their acceptance criteria and FR/NFR/DR requirements.

---

# 16. Summary

The updated **24 user stories** have been estimated using Fibonacci-based story points and prioritized using the MoSCoW method.

### Final Summary

- **Total User Stories:** 24
- **Total Story Points:** 152
- **Must Have:** 15
- **Should Have:** 7
- **Could Have:** 2
- **Won't Have:** 0
- **Maximum Story Size:** 8 points

The estimates provide the basis for the next Phase 1 activity: **dividing EPICs and user stories into sprints and preparing the Sprint Plan**.

---

# 17. Reference

The estimation and priority assignment are based on the updated `USER_STORIES.md`, which contains 24 user stories across 8 EPICs with detailed acceptance criteria and FR/NFR/DR traceability.
