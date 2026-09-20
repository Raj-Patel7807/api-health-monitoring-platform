# User Stories & Acceptance Criteria

## Distributed API Health & Incident Monitoring Platform

---

## 1. Purpose

This document converts the Functional Requirements (FR), Non-Functional Requirements (NFR), and Domain Requirements (DR) of the **Distributed API Health & Incident Monitoring Platform** into implementation-ready user stories and testable acceptance criteria.

Each user story follows the structure:

> **As a [role], I want [goal], so that [benefit].**

The acceptance criteria are written as clear, direct statements describing the conditions that must be satisfied for a user story to be considered complete.

The document maintains the following traceability:

```text
Stakeholders
    ↓
Requirements
    ↓
User Stories
    ↓
Acceptance Criteria
    ↓
EPICs
    ↓
Sprints
    ↓
Implementation
    ↓
Testing
```

---

# 2. User Story Structure

Every user story contains:

- **Story ID** — unique identifier.
- **EPIC** — larger capability area.
- **Primary Actor** — main stakeholder represented by the story.
- **Priority** — implementation priority.
- **Source Requirements** — FR, NFR, and/or DR requirements represented by the story.
- **User Story** — role, goal, and benefit.
- **Acceptance Criteria** — objective conditions that can be implemented and tested.

The acceptance criteria are intentionally detailed enough to serve as a direct basis for test-case generation.

---

# 3. EPIC Overview

| EPIC ID | EPIC | Scope | User Stories |
|---|---|---|---|
| E1 | User Onboarding & API Configuration | Account setup, endpoint registration, notification configuration, maintenance | US-01 – US-04 |
| E2 | API Monitoring & Health Checks | Background monitoring, failure detection, response validation, history | US-05 – US-08 |
| E3 | Incident Management & Alerting | Incident confirmation, state changes, notifications and retries | US-09 – US-12 |
| E4 | Dashboard, Uptime & Reporting | Dashboard, uptime calculation, historical analysis and reports | US-13 – US-15 |
| E5 | Responsible Monitoring & Security | Rate limiting, backoff, encryption and security | US-16 – US-18 |
| E6 | Access Control & Advanced Monitoring | RBAC, multi-region monitoring and deployment | US-19 – US-21 |
| E7 | Scalability, Reliability & Data Management | Scaling, worker failover and long-term data management | US-22 – US-24 |
| E8 | Project Governance & Requirement Management | Agile/SCRUM, GitHub, Slack, requirement structure and conflict resolution | US-25 |

---

# 4. User Story Index

| ID | User Story | EPIC |
|---|---|---|
| US-01 | User Account Onboarding | E1 |
| US-02 | Register and Configure an API Endpoint | E1 |
| US-03 | Configure Notification Details | E1 |
| US-04 | Configure an Endpoint Maintenance Window | E1 |
| US-05 | Schedule Continuous Background Health Checks | E2 |
| US-06 | Detect API Health Failures | E2 |
| US-07 | Validate Response Body and JSONPath Content | E2 |
| US-08 | Record Health-Check Results and Response Time | E2 |
| US-09 | Create an Incident Only After Confirmed Failure | E3 |
| US-10 | Manage Incident State and Avoid Duplicate Alerts | E3 |
| US-11 | Send Incident Alerts Through Configured Channels | E3 |
| US-12 | Retry Failed Notification Delivery | E3 |
| US-13 | View Overall API Health Dashboard | E4 |
| US-14 | View Uptime and Historical Performance | E4 |
| US-15 | Generate Monthly Uptime Reports | E4 |
| US-16 | Respect Target API Rate Limits and Use Backoff | E5 |
| US-17 | Protect Stored Monitoring and Configuration Data | E5 |
| US-18 | Maintain Tamper-Proof Operational Audit Logs | E5 |
| US-19 | Securely Manage Team Access Through RBAC | E6 |
| US-20 | Monitor APIs From Multiple Geographic Regions | E6 |
| US-21 | Deploy and Maintain the Platform Within Hosting Constraints | E6 |
| US-22 | Scale Monitoring Resources as Usage Grows | E7 |
| US-23 | Automatically Fail Over Monitoring Workers | E7 |
| US-24 | Preserve Long-Term Monitoring Data Through Data Rollups | E7 |
| US-25 | Manage Agile Delivery, Collaboration and Requirement Decisions | E8 |

---

# 5. Detailed User Stories & Acceptance Criteria

# E1 — User Onboarding & API Configuration

## US-01 — User Account Onboarding

**EPIC:** E1 — User Onboarding & API Configuration  
**Primary Actor:** API Developer / API Owner  
**Priority:** High  
**Source Requirements:** FR11, NFR9

### User Story

> **As an API developer, I want a simple onboarding process for creating my account and adding my first API endpoint, so that I can start monitoring an API quickly without unnecessary setup complexity.**

### Acceptance Criteria

**AC-01.1 — Account creation**

- the system shall provide the required account-registration steps.

**AC-01.2 — Required information**

- the system shall validate the required information before continuing.

**AC-01.3 — First endpoint setup**

- the user shall be able to configure their first monitored API endpoint.

**AC-01.4 — Invalid information**

- the system shall reject the invalid input and provide a clear indication that correction is required.

**AC-01.5 — Successful onboarding**

- the account and first endpoint configuration shall be saved successfully.

**AC-01.6 — Onboarding performance**

- The complete sign-up and first-endpoint setup should be achievable within **5 minutes** under normal operating conditions.

---

## US-02 — Register and Configure an API Endpoint

**EPIC:** E1 — User Onboarding & API Configuration  
**Primary Actor:** API Developer / API Owner  
**Priority:** High  
**Source Requirements:** FR1

### User Story

> **As an API owner, I want to register an API endpoint by providing its URL, expected HTTP status code, and monitoring frequency, so that the platform knows what to monitor and how frequently to check it.**

### Acceptance Criteria

**AC-02.1 — Endpoint URL**

- the system shall accept the URL for endpoint configuration.

**AC-02.2 — Expected status code**

- the system shall store the expected status code with the endpoint configuration.

**AC-02.3 — Monitoring frequency**

- the system shall store the configured frequency.

**AC-02.4 — Configuration validation**

- the system shall reject the configuration and identify the invalid information.

**AC-02.5 — Successful registration**

- the endpoint shall be saved successfully.

**AC-02.6 — Monitoring eligibility**

- the endpoint shall become eligible for scheduled background health checks.

---

## US-03 — Configure Notification Details

**EPIC:** E1 — User Onboarding & API Configuration  
**Primary Actor:** API Developer / API Owner  
**Priority:** High  
**Source Requirements:** FR7, FR13, NFR3

### User Story

> **As an API owner, I want to configure and manage notification destinations for my account or endpoint, so that incident alerts can reach the appropriate people and communication channels.**

### Acceptance Criteria

**AC-03.1 — Notification settings**

- the system shall allow supported notification details to be configured.

**AC-03.2 — Supported notification channels**

- The platform shall support the notification channels defined by the project, including **Slack, Discord, Email, and Webhook**.

**AC-03.3 — Account-level configuration**

- the configured account notification destination shall be available to the alerting workflow.

**AC-03.4 — Endpoint-level configuration**

- the endpoint-specific notification configuration shall be used according to the platform's routing rules.

**AC-03.5 — Update configuration**

- the updated configuration shall be saved for future notifications.

**AC-03.6 — Secure handling**

- Sensitive information such as webhook URLs, tokens, or credentials shall not be unnecessarily exposed in the user interface or application logs.

---

## US-04 — Configure an Endpoint Maintenance Window

**EPIC:** E1 — User Onboarding & API Configuration  
**Primary Actor:** API Developer / API Owner  
**Priority:** Medium  
**Source Requirements:** FR15, DR4

### User Story

> **As an API owner, I want to define a planned maintenance window for an endpoint, so that planned deployments or maintenance do not create false incidents or unnecessary alerts.**

### Acceptance Criteria

**AC-04.1 — Create maintenance window**

- the system shall save the maintenance window for that endpoint.

**AC-04.2 — Monitoring continues**

- the system shall continue performing health checks.

**AC-04.3 — Incident suppression**

- the system shall not create a normal incident for that planned maintenance period.

**AC-04.4 — Alert suppression**

- the system shall not send a normal incident alert for that planned maintenance period.

**AC-04.5 — Resume normal monitoring behaviour**

- normal failure, incident, and alert processing shall resume.

---

# E2 — API Monitoring & Health Checks

## US-05 — Schedule Continuous Background Health Checks

**EPIC:** E2 — API Monitoring & Health Checks  
**Primary Actor:** API Developer / API Owner  
**Priority:** High  
**Source Requirements:** FR2, DR1

### User Story

> **As an API owner, I want my registered endpoint to be checked automatically in the background, so that I do not have to manually check whether my API is working.**

### Acceptance Criteria

**AC-05.1 — Background scheduling**

- the system shall schedule a health-check job through the background job mechanism.

**AC-05.2 — Job queue**

- The monitoring workflow shall use the project's background job queue mechanism, **BullMQ**, for scheduled health-check jobs.

**AC-05.3 — Repeated monitoring**

- the system shall schedule the next check according to the configured monitoring frequency.

**AC-05.4 — No manual trigger required**

- the system shall perform the check without requiring manual user action.

**AC-05.5 — Non-blocking behaviour**

- Health-check execution shall run in the background and shall not block the main user-facing application.

**AC-05.6 — Worker/job failure visibility**

- the platform shall record or log the operational failure so that it can be investigated.

---

## US-06 — Detect API Health Failures

**EPIC:** E2 — API Monitoring & Health Checks  
**Primary Actor:** API Developer / API Owner  
**Priority:** High  
**Source Requirements:** FR3, DR2, DR5

### User Story

> **As an API owner, I want the platform to identify different types of endpoint failures, so that I can understand whether an API is failing because of its response, timeout, connection, or SSL/TLS condition.**

### Acceptance Criteria

**AC-06.1 — Expected response**

- the status-code check shall be considered successful unless another configured health condition fails.

**AC-06.2 — Wrong status code**

- the health check shall be recorded as a failure.

**AC-06.3 — Timeout**

- the result shall be recorded as a timeout failure.

**AC-06.4 — Connection failure**

- the result shall be recorded as a connection failure.

**AC-06.5 — SSL/TLS failure**

- the health check shall be recorded as an SSL/TLS-related failure.

**AC-06.6 — Temporary failure handling**

- A single temporary failure shall not automatically be treated as a confirmed incident.

---

## US-07 — Validate Response Body and JSONPath Content

**EPIC:** E2 — API Monitoring & Health Checks  
**Primary Actor:** API Developer / API Owner  
**Priority:** High  
**Source Requirements:** FR16

### User Story

> **As an API developer, I want to define response-body assertions, so that the platform can detect silent API failures even when the API returns a technically successful HTTP response.**

### Acceptance Criteria

**AC-07.1 — Text assertion**

- the system shall evaluate whether the required text is present according to the configured rule.

**AC-07.2 — Regular-expression assertion**

- the system shall evaluate the response against the configured regular expression.

**AC-07.3 — JSONPath assertion**

- the system shall evaluate the configured JSONPath value according to the expected assertion.

**AC-07.4 — Failed assertion**

- the health check shall be recorded as failed.

**AC-07.5 — HTTP 200 with invalid content**

- the platform shall be able to classify the health check as unhealthy.

**AC-07.6 — Incident integration**

- A response-content assertion failure shall be eligible for the normal failure-threshold, incident, and alert workflow.

---

## US-08 — Record Health-Check Results and Response Time

**EPIC:** E2 — API Monitoring & Health Checks  
**Primary Actor:** API Developer / API Owner  
**Priority:** High  
**Source Requirements:** FR9, NFR2, NFR4

### User Story

> **As an API owner, I want health-check results, response times, and failure information stored, so that I can investigate current and historical API behaviour.**

### Acceptance Criteria

**AC-08.1 — Successful result**

- the system shall store the result and relevant response-time information.

**AC-08.2 — Failed result**

- the system shall store the failure result and relevant failure information.

**AC-08.3 — Response time**

- Response-time information shall be stored for applicable health checks.

**AC-08.4 — Historical access**

- the system shall return the available historical monitoring information.

**AC-08.5 — Recent-data performance**

- Monitoring data from the most recent **30 days** should be retrievable in **under 5 seconds**.

**AC-08.6 — Older data**

- Older/archived monitoring data shall remain reachable, with retrieval allowed to take up to **5 minutes**.

**AC-08.7 — Retention**

- Monitoring data shall not be deleted through normal system operation.

---

# E3 — Incident Management & Alerting

## US-09 — Create an Incident Only After Confirmed Failure

**EPIC:** E3 — Incident Management & Alerting  
**Primary Actor:** Incident Responder / On-call Developer  
**Priority:** High  
**Source Requirements:** FR5, NFR1, DR5

### User Story

> **As an incident responder, I want the platform to confirm repeated failures before creating an incident, so that temporary network problems do not create false incidents.**

### Acceptance Criteria

**AC-09.1 — First failure**

- the system shall record the failure but shall not immediately create a confirmed incident.

**AC-09.2 — Failure threshold**

- the system shall create a confirmed incident.

**AC-09.3 — Threshold consistency**

- The configured failure threshold shall be applied consistently to the endpoint's monitoring results.

**AC-09.4 — Recovery before threshold**

- the system shall not create a normal confirmed incident for that temporary failure.

**AC-09.5 — Temporary internet failure**

- A single timeout, connection problem, or other temporary network blip shall not automatically become a confirmed incident.

**AC-09.6 — Detection target**

- The platform shall target failure detection within **2 minutes for at least 95 out of 100 qualifying incidents**, measured over the specified 30-day period.

---

## US-10 — Manage Incident State and Avoid Duplicate Alerts

**EPIC:** E3 — Incident Management & Alerting  
**Primary Actor:** Incident Responder / On-call Developer  
**Priority:** High  
**Source Requirements:** FR6, NFR7, DR5

### User Story

> **As an incident responder, I want incident state changes to be tracked and alerts to be generated only for meaningful state changes, so that I receive actionable information without repeated alerts for the same outage.**

### Acceptance Criteria

**AC-10.1 — Healthy-to-failing transition**

- the endpoint shall transition to a confirmed failing state and an incident shall be opened.

**AC-10.2 — No repeated alert**

- the system shall not generate a new incident alert for every failed check.

**AC-10.3 — Recovery**

- the endpoint shall transition to the healthy/recovered state.

**AC-10.4 — New failure after recovery**

- the system shall be able to create a new incident and corresponding state-change alert.

**AC-10.5 — Actionable alert target**

- At least **90 out of 100 alerts** should represent real, actionable problems.

**AC-10.6 — Resolution target**

- The average time to resolve actionable alerts should be **under 30 minutes**.

---

## US-11 — Send Incident Alerts Through Configured Channels

**EPIC:** E3 — Incident Management & Alerting  
**Primary Actor:** Incident Responder / On-call Developer  
**Priority:** High  
**Source Requirements:** FR7, FR13, NFR3

### User Story

> **As an incident responder, I want confirmed incidents delivered through configured communication channels, so that I can respond to API failures without continuously monitoring the dashboard.**

### Acceptance Criteria

**AC-11.1 — Slack notification**

- the system shall attempt to send the incident notification through the configured Slack integration.

**AC-11.2 — Discord notification**

- the system shall attempt to send the incident notification through Discord.

**AC-11.3 — Email notification**

- the system shall attempt to send the notification to the configured email destination.

**AC-11.4 — Webhook notification**

- the system shall send the appropriate notification payload to the configured webhook.

**AC-11.5 — Alert content**

- The notification shall identify the affected endpoint and the relevant incident/failure condition.

**AC-11.6 — Delivery success**

- At least **99 out of 100** notification/webhook deliveries should succeed.

**AC-11.7 — Acknowledgement**

- Successful notification deliveries should be acknowledged within **5 seconds**, where acknowledgement is supported by the delivery mechanism.

---

## US-12 — Retry Failed Notification Delivery

**EPIC:** E3 — Incident Management & Alerting  
**Primary Actor:** Incident Responder / On-call Developer  
**Priority:** High  
**Source Requirements:** FR8, NFR3

### User Story

> **As an incident responder, I want failed notification deliveries retried automatically, so that temporary failures in external notification services do not silently prevent important alerts from reaching me.**

### Acceptance Criteria

**AC-12.1 — Delivery failure**

- the system shall record the delivery attempt as failed.

**AC-12.2 — Retry count**

- The system shall retry a failed notification **up to 3 times**.

**AC-12.3 — Growing wait**

- The retry mechanism shall use a growing wait time between attempts.

**AC-12.4 — Successful retry**

- the system shall stop further retries for that notification.

**AC-12.5 — Final failure**

- the system shall mark the notification as failed and log the failure.

---

# E4 — Dashboard, Uptime & Reporting

## US-13 — View Overall API Health Dashboard

**EPIC:** E4 — Dashboard, Uptime & Reporting  
**Primary Actor:** Team Lead / Project Maintainer  
**Priority:** High  
**Source Requirements:** FR10, NFR9, NFR10

### User Story

> **As a team lead, I want a consolidated dashboard showing the health of all monitored endpoints and their open incidents, so that I can understand the overall operational state at a glance.**

### Acceptance Criteria

**AC-13.1 — Endpoint overview**

- the dashboard shall provide an overview of the monitored endpoints.

**AC-13.2 — Current health state**

- The dashboard shall display the current health state of each monitored endpoint.

**AC-13.3 — Open incidents**

- The dashboard shall clearly identify endpoints with open incidents.

**AC-13.4 — Consolidated view**

- The dashboard shall provide a consolidated operational view without requiring the user to inspect every endpoint individually.

**AC-13.5 — Current monitoring data**

- Dashboard health information shall be based on current monitoring and incident state data.

**AC-13.6 — Dashboard performance**

- The dashboard should load in **under 3 seconds** under the defined operating conditions.

---

## US-14 — View Uptime and Historical Performance

**EPIC:** E4 — Dashboard, Uptime & Reporting  
**Primary Actor:** API Developer / API Owner  
**Priority:** High  
**Source Requirements:** FR4, FR9, NFR2, NFR4, DR3

### User Story

> **As an API owner, I want to view uptime and historical response-time information, so that I can evaluate the reliability and performance of my endpoint over time.**

### Acceptance Criteria

**AC-14.1 — Uptime percentage**

- the system shall calculate and return the endpoint's uptime percentage.

**AC-14.2 — Standard formula**

The uptime calculation shall use:

```text
Uptime % = ((Total Time - Downtime) / Total Time) × 100
```

**AC-14.3 — Response-time history**

- The user shall be able to access stored response-time history.

**AC-14.4 — Reporting API**

- Uptime information shall be available through the reporting API.

**AC-14.5 — Historical availability**

- Historical monitoring information shall remain accessible according to the project's retention and storage strategy.

---

## US-15 — Generate Monthly Uptime Reports

**EPIC:** E4 — Dashboard, Uptime & Reporting  
**Primary Actor:** Team Lead / Project Maintainer  
**Priority:** Medium  
**Source Requirements:** FR14

### User Story

> **As a team lead, I want to generate a monthly uptime report for monitored endpoints, so that I can review API reliability over a defined reporting period.**

### Acceptance Criteria

**AC-15.1 — Generate report**

- the system shall generate the monthly uptime report.

**AC-15.2 — Correct reporting period**

- The generated report shall represent the requested monthly period.

**AC-15.3 — Relevant information**

- The report shall contain the relevant uptime information for the user's monitored endpoints.

**AC-15.4 — Download**

- The generated report shall be available for download.

**AC-15.5 — API access**

- The report shall also be retrievable through the reporting API.

**AC-15.6 — Authorization**

- A user shall only be able to access reports for endpoints and monitoring data they are authorized to access.

---

# E5 — Responsible Monitoring & Security

## US-16 — Respect Target API Rate Limits and Use Backoff

**EPIC:** E5 — Responsible Monitoring & Security  
**Primary Actor:** Monitored API Owner / Target Service  
**Priority:** High  
**Source Requirements:** FR12, NFR11, DR4

### User Story

> **As an owner of a monitored API, I want monitoring traffic to be controlled and respectful, so that the monitoring platform does not overload my API or appear as abusive traffic.**

### Acceptance Criteria

**AC-16.1 — Configurable frequency**

- Health-check frequency shall be configurable according to the endpoint monitoring configuration.

**AC-16.2 — Rate limiting**

- Health-check requests sent to external monitored APIs shall be rate-limited according to configured limits.

**AC-16.3 — Backoff**

- the system shall apply backoff behaviour where configured instead of continuously sending requests at the normal rate.

**AC-16.4 — Reasonable intervals**

- The system shall use reasonable intervals between repeated health checks.

**AC-16.5 — Request identification**

- Monitoring requests shall identify the monitoring platform appropriately.

**AC-16.6 — Avoid abusive traffic**

- The monitoring system shall avoid unnecessary repeated requests that could overload a target service, cause rate limiting, or result in the monitoring source being blocked.

---

## US-17 — Protect Stored Monitoring and Configuration Data

**EPIC:** E5 — Responsible Monitoring & Security  
**Primary Actor:** Platform Administrator / Project Development Team  
**Priority:** High  
**Source Requirements:** NFR5, NFR6, DR2

### User Story

> **As a platform administrator, I want monitoring data and sensitive configuration information protected with appropriate encryption and security controls, so that unauthorized parties cannot access or intercept sensitive information.**

### Acceptance Criteria

**AC-17.1 — Encryption at rest**

- Stored sensitive/project data shall use **AES-256** encryption as specified by the security requirement.

**AC-17.2 — Encryption in transit**

- Data transmitted over the network shall use **TLS 1.3**.

**AC-17.3 — Sensitive secrets**

- Credentials, tokens, webhook secrets, and similar sensitive values shall not be unnecessarily exposed in application output or logs.

**AC-17.4 — Secure communication**

- Sensitive information shall not be intentionally transmitted through an insecure communication channel.

**AC-17.5 — Security incident target**

- The platform shall target **zero critical or high-severity security incidents over a 12-month period**.

**AC-17.6 — Compliance**

- Required security/compliance checks applicable to the deployed platform shall be capable of being performed and passed.

---

## US-18 — Maintain Tamper-Proof Operational Audit Logs

**EPIC:** E5 — Responsible Monitoring & Security  
**Primary Actor:** Platform Administrator  
**Priority:** High  
**Source Requirements:** NFR15

### User Story

> **As a platform administrator, I want important administrative and configuration changes recorded in tamper-resistant audit logs, so that operational actions can be traced and investigated.**

### Acceptance Criteria

**AC-18.1 — Configuration changes**

- Important monitoring and configuration changes shall generate audit records.

**AC-18.2 — Administrative actions**

- Administrative actions affecting monitoring behaviour or platform configuration shall be traceable.

**AC-18.3 — Event details**

- Each audit record shall contain sufficient information to identify what operation occurred and when it occurred.

**AC-18.4 — Tamper resistance**

- Audit records shall not be casually modified through normal application operations.

**AC-18.5 — Deletion protection**

- Audit records shall not be casually deleted through normal application operations.

**AC-18.6 — Audit access**

- Audit information shall be protected from unauthorized access.

**AC-18.7 — Investigation**

- Authorized administrators shall be able to review audit records when investigating operational or security events.

---

# E6 — Access Control & Advanced Monitoring

## US-19 — Securely Manage Team Access Through RBAC

**EPIC:** E6 — Access Control & Advanced Monitoring  
**Primary Actor:** Platform Administrator  
**Priority:** High  
**Source Requirements:** FR17, NFR5, NFR6

### User Story

> **As a platform administrator, I want to assign roles and granular permissions to team members, so that each member can access only the platform operations appropriate to their role.**

### Acceptance Criteria

**AC-19.1 — Role assignment**

- the system shall store the assigned role and permissions.

**AC-19.2 — Admin role**

- Admin users shall be able to perform the administrative operations permitted by the platform.

**AC-19.3 — Operator role**

- Operator users shall be able to perform the monitoring operations permitted by their role.

**AC-19.4 — Read-Only role**

- Read-Only users shall be able to view permitted information without modifying protected configuration.

**AC-19.5 — Unauthorized action**

- the system shall reject the operation.

**AC-19.6 — Consistent authorization**

- Permission checks shall be enforced consistently across protected resources and operations.

**AC-19.7 — Sensitive configuration**

- Endpoint credentials, notification credentials, and other sensitive configuration shall not be accessible to users without the required permission.

---

## US-20 — Monitor APIs From Multiple Geographic Regions

**EPIC:** E6 — Access Control & Advanced Monitoring  
**Primary Actor:** API Developer / API Owner  
**Priority:** Medium  
**Source Requirements:** FR18

### User Story

> **As an API developer, I want to select geographic monitoring regions, so that I can identify localized network routing issues, regional outages, and geo-specific API failures.**

### Acceptance Criteria

**AC-20.1 — Region selection**

- The user shall be able to select from the geographic monitoring regions supported by the deployment.

**AC-20.2 — Example regions**

- Supported infrastructure may provide regions such as **US-East, EU-Central, and AP-South**.

**AC-20.3 — Regional execution**

- the check shall be executable from the selected geographic origin.

**AC-20.4 — Region identification**

- Each regional monitoring result shall identify the region from which the check originated.

**AC-20.5 — Regional difference**

- The system shall be able to represent different health results for the same endpoint when different regions produce different results.

**AC-20.6 — Regional analysis**

- Regional monitoring results shall be available for analysis and reporting.

---

## US-21 — Deploy and Maintain the Platform Within Hosting Constraints

**EPIC:** E6 — Access Control & Advanced Monitoring  
**Primary Actor:** Platform Administrator / Project Development Team; DevOps / Deployment-Experienced Developer  
**Priority:** Medium  
**Source Requirements:** NFR12

### User Story

> **As a platform administrator, I want the platform to be deployable and maintainable within the selected hosting environment, so that the monitoring system can operate reliably without exceeding infrastructure limitations.**

### Acceptance Criteria

**AC-21.1 — Application deployment**

- The application shall be deployable using the compute, networking, database, storage, and worker capabilities provided by the selected hosting environment.

**AC-21.2 — Background workers**

- The hosting environment shall support the background worker workload required for continuous monitoring.

**AC-21.3 — Database resources**

- Required database capacity and connectivity shall be available for monitoring, incident, configuration, and historical data.

**AC-21.4 — Storage resources**

- Required storage capacity shall support the project's monitoring-data retention strategy.

**AC-21.5 — Compute and memory**

- Deployment shall account for the available CPU and memory resources.

**AC-21.6 — Network resources**

- Deployment shall account for the network connectivity required for outbound health checks and platform communication.

**AC-21.7 — Repeatable deployment**

- Deployment and maintenance procedures shall be repeatable for the selected hosting environment.

**AC-21.8 — Maintainability**

- Routine maintenance shall be possible without redesigning the monitoring workflow.

---

# E7 — Scalability, Reliability & Data Management

## US-22 — Scale Monitoring Resources as Usage Grows

**EPIC:** E7 — Scalability, Reliability & Data Management  
**Primary Actor:** Platform Administrator / Project Development Team  
**Priority:** Medium  
**Source Requirements:** NFR8, NFR10

### User Story

> **As a platform administrator, I want monitoring resources to scale as users and monitored endpoints increase, so that the platform remains reliable and cost-efficient as usage grows.**

### Acceptance Criteria

**AC-22.1 — Active-user growth**

- The platform should support growth toward **200 active users within 3 months**.

**AC-22.2 — Resource scaling**

- monitoring resources should be scalable according to workload.

**AC-22.3 — Health-check cost**

- The cost of running a single health check should remain below **$0.01 for at least 95% of health checks**.

**AC-22.4 — Scaling without unnecessary traffic**

- Scaling the monitoring infrastructure shall not intentionally increase unnecessary requests to monitored APIs.

**AC-22.5 — Churn target**

- User churn shall be measurable against the project target of **less than 5%**.

**AC-22.6 — Satisfaction target**

- User satisfaction shall be measurable against the project target of **4.5 out of 5 or higher**.

---

## US-23 — Automatically Fail Over Monitoring Workers

**EPIC:** E7 — Scalability, Reliability & Data Management  
**Primary Actor:** Platform Administrator / Project Development Team; DevOps / Deployment-Experienced Developer  
**Priority:** High  
**Source Requirements:** NFR13, DR1

### User Story

> **As a platform administrator, I want a standby monitoring worker to automatically take over when a primary worker fails, so that health monitoring continues without a prolonged interruption.**

### Acceptance Criteria

**AC-23.1 — Standby worker**

- A standby worker configuration shall be available when high availability is enabled.

**AC-23.2 — Failure detection**

- the system shall initiate the failover process.

**AC-23.3 — Automatic takeover**

- an available standby worker shall take over the required monitoring workload.

**AC-23.4 — Failover time**

- Standby takeover shall occur within **10 seconds** of detecting the primary worker crash.

**AC-23.5 — Job continuity**

- A single worker failure shall not permanently lose monitoring jobs.

**AC-23.6 — Failover logging**

- Failover events shall be recorded for operational diagnosis.

**AC-23.7 — Duplicate execution**

- Worker coordination shall avoid duplicate execution of the same monitoring job during failover where the job-queue architecture supports such coordination.

---

## US-24 — Preserve Long-Term Monitoring Data Through Data Rollups

**EPIC:** E7 — Scalability, Reliability & Data Management  
**Primary Actor:** API Developer / API Owner; Database Administrator  
**Priority:** Medium  
**Source Requirements:** NFR4, NFR14

### User Story

> **As an API owner, I want older granular monitoring data rolled into daily summaries while remaining historically accessible, so that long-term monitoring information is preserved without requiring unlimited minute-by-minute storage.**

### Acceptance Criteria

**AC-24.1 — Minute-level data**

- Recent monitoring data shall remain available at the required resolution for active operational analysis.

**AC-24.2 — Daily rollup**

- Older minute-by-minute monitoring data shall be capable of being aggregated into daily summaries according to the retention strategy.

**AC-24.3 — Information preservation**

- Daily summaries shall preserve the information required for long-term reporting and trend analysis.

**AC-24.4 — Historical accessibility**

- the corresponding historical information shall remain reachable.

**AC-24.5 — No loss of required history**

- Rollup processing shall not remove information required by the platform's long-term reporting and analysis requirements.

**AC-24.6 — Storage sustainability**

- The storage strategy shall support long-term retention without requiring unlimited minute-level raw storage.

---

# E8 — Project Governance & Requirement Management

## US-25 — Manage Agile Delivery, GitHub Collaboration and Requirement Decisions

**EPIC:** E8 — Project Governance & Requirement Management  
**Primary Actor:** Project Team / Project Maintainer  
**Priority:** High  
**Source Requirements:** NFR16, NFR17, NFR18, DR6, DR7

### User Story

> **As a project team member, I want development work, requirements, collaboration, and requirement decisions to follow a structured process, so that the project remains organized, traceable, and consistent throughout development.**

### Acceptance Criteria

### A. Agile / SCRUM

**AC-25.1 — Sprint-based development**

- Development work shall be organized into defined Agile/SCRUM iterations or sprints.

**AC-25.2 — Sprint objectives**

- Each sprint shall have clearly identified objectives, scope, or deliverables.

**AC-25.3 — Work tracking**

- Project work items shall be trackable from planning through completion.

**AC-25.4 — Acceptance-criteria validation**

- Completed work shall be evaluated against the acceptance criteria of the corresponding user stories.

### B. Requirement Structure

**AC-25.5 — User story format**

- Implementation-oriented requirements shall be represented using a clear user story structure containing a role, goal, and benefit.

**AC-25.6 — Acceptance criteria**

- Each implementation-oriented user story shall contain explicit acceptance criteria.

**AC-25.7 — EPIC grouping**

- Related user stories shall be grouped into EPICs.

**AC-25.8 — Sprint organization**

- User stories shall be capable of being assigned to appropriate implementation sprints.

### C. GitHub Development

**AC-25.9 — Repository development**

- Source code and project documentation shall be maintained in the project's GitHub repository.

**AC-25.10 — Individual contribution**

- Team members shall contribute using their own GitHub identities so that individual contributions remain traceable.

**AC-25.11 — Commit traceability**

- Commits shall identify the individual contributor responsible for the change.

**AC-25.12 — Descriptive commits**

- Commit messages shall describe the actual work performed rather than using meaningless generic descriptions.

**AC-25.13 — Version history**

- Project changes shall remain traceable through the repository's version-control history.

### D. Slack Communication

**AC-25.14 — Centralized communication**

- Project communication shall use the designated Slack workspace/channels.

**AC-25.15 — Decisions**

- Important project and technical decisions shall be communicated through the appropriate Slack channel.

**AC-25.16 — Project updates**

- Relevant project progress, updates, and coordination information shall be shared with the team through Slack.

### E. Requirement Conflict Management

**AC-25.17 — Conflict identification**

- Conflicting or overlapping requirements shall be identifiable during requirements review.

**AC-25.18 — Conflict documentation**

- The affected requirements and stakeholder expectations shall be documented.

**AC-25.19 — Conflict description**

- The nature and impact of the identified conflict shall be documented clearly.

**AC-25.20 — Resolution**

- A resolution shall be agreed through the project's requirements decision process.

**AC-25.21 — Resolution traceability**

- The agreed resolution shall be documented and traceable to the affected requirements.

**AC-25.22 — Update affected stories**

- If a requirement decision changes system behaviour, the related user stories and acceptance criteria shall be updated.

**AC-25.23 — No unresolved implementation contradiction**

- The final approved requirement set shall not contain unresolved contradictions that prevent consistent implementation.

---

# 6. Cross-Cutting Non-Functional Requirement Traceability

The following table shows where the NFRs are represented in the user stories and acceptance criteria.

| NFR | Requirement | Covered By |
|---|---|---|
| NFR1 | Failure detection within 2 minutes for 95/100 incidents over 30 days | US-09 |
| NFR2 | Recent 30-day data under 5 seconds; older data up to 5 minutes | US-08, US-14 |
| NFR3 | 99/100 notification deliveries succeed and acknowledgement within 5 seconds | US-11, US-12 |
| NFR4 | Monitoring data retained; recent data fast and older data accessible | US-08, US-14, US-24 |
| NFR5 | AES-256 for stored data and TLS 1.3 for network data | US-17, US-19, US-21 |
| NFR6 | Zero critical/high security incidents over 12 months and required compliance checks | US-17, US-19 |
| NFR7 | 90/100 alerts actionable and average resolution under 30 minutes | US-10 |
| NFR8 | Health-check cost below $0.01 for 95% of checks and scaling support | US-22 |
| NFR9 | Onboarding under 5 minutes and dashboard under 3 seconds | US-01, US-13 |
| NFR10 | 200 active users in 3 months, churn below 5%, satisfaction ≥4.5/5 | US-22 |
| NFR11 | Configurable and rate-limited outbound health-check traffic | US-16 |
| NFR12 | Deployable and maintainable within selected hosting environment | US-21 |
| NFR13 | Standby worker takeover within 10 seconds | US-23 |
| NFR14 | Roll up old minute-level data into daily summaries | US-24 |
| NFR15 | Tamper-proof operational traceability for configuration changes | US-18 |
| NFR16 | Agile/SCRUM development | US-25 |
| NFR17 | GitHub development with traceable individual contribution | US-25 |
| NFR18 | Team communication, discussions, decisions and updates through Slack | US-25 |

---

# 7. Domain Requirement Traceability

| DR | Requirement | Covered By |
|---|---|---|
| DR1 | Health checks run in the background and do not block the user-facing application | US-05, US-23 |
| DR2 | Communication follows HTTP/HTTPS rules and TLS 1.3 is used for network transmission | US-06, US-17, US-21 |
| DR3 | Uptime uses `(Total Time - Downtime) / Total Time × 100` | US-14 |
| DR4 | Reasonable intervals and backoff are used when monitoring external APIs | US-04, US-16 |
| DR5 | A single temporary failure is not automatically treated as a real incident | US-06, US-09, US-10 |
| DR6 | Requirements are structured into user stories with acceptance criteria, grouped into EPICs and organized into sprints | US-25 |
| DR7 | Conflicting requirements are formally identified and their resolutions documented | US-25 |

---

# 8. Functional Requirement Traceability

| FR | Requirement | Covered By |
|---|---|---|
| FR1 | Register endpoint URL, expected status code and check frequency | US-02 |
| FR2 | Repeated background checking using BullMQ/job queue | US-05 |
| FR3 | Detect timeout, wrong status code, connection error and bad SSL certificate | US-06 |
| FR4 | Calculate uptime percentage and provide it through reporting API | US-14 |
| FR5 | Create incident only after failures cross the configured threshold | US-09 |
| FR6 | Send one alert per state change rather than every failed check | US-10 |
| FR7 | Send alerts through Slack, Discord, Email or Webhook | US-11 |
| FR8 | Retry failed notifications up to 3 times with growing wait time | US-12 |
| FR9 | Store uptime and response-time history | US-08, US-14 |
| FR10 | Dashboard showing endpoint health and open incidents | US-13 |
| FR11 | Simple onboarding and first-endpoint setup | US-01 |
| FR12 | Avoid excessive requests, use backoff and identify monitoring traffic | US-16 |
| FR13 | Configure and manage notification details | US-03, US-11 |
| FR14 | Generate monthly uptime reports and provide/download them through the API | US-15 |
| FR15 | Maintenance window suppresses normal incidents and alerts | US-04 |
| FR16 | Response-body text, regex and JSONPath assertions | US-07 |
| FR17 | Role-Based Access Control with granular permissions | US-19 |
| FR18 | Multi-region monitoring probe selection | US-20 |

---

# 9. Stakeholder Traceability

| Stakeholder | Relevant User Stories |
|---|---|
| API Developer / API Owner | US-01, US-02, US-03, US-04, US-05, US-06, US-07, US-08, US-14, US-15, US-20, US-24 |
| DevOps / Deployment-Experienced Developer | US-05, US-06, US-16, US-21, US-22, US-23, US-24 |
| Incident Responder / On-call Developer | US-09, US-10, US-11, US-12, US-13 |
| Team Lead / Project Maintainer | US-13, US-14, US-15, US-18, US-25 |
| Platform Administrator / Project Development Team | US-05, US-17, US-18, US-19, US-21, US-22, US-23, US-24, US-25 |
| Notification and Integration Services | US-03, US-11, US-12 |
| Monitored API Owners / Target Services | US-04, US-06, US-16, US-20 |
| Hosting / Infrastructure Provider | US-21, US-22, US-23, US-24 |
| Course Instructor / Teaching Team | US-25 |
| Database Administrator | US-08, US-14, US-15, US-18, US-24 |

---

# 10. Requirement-to-User-Story Traceability Matrix

| Requirement | User Story |
|---|---|
| FR1 | US-02 |
| FR2 | US-05 |
| FR3 | US-06 |
| FR4 | US-14 |
| FR5 | US-09 |
| FR6 | US-10 |
| FR7 | US-11 |
| FR8 | US-12 |
| FR9 | US-08, US-14 |
| FR10 | US-13 |
| FR11 | US-01 |
| FR12 | US-16 |
| FR13 | US-03, US-11 |
| FR14 | US-15 |
| FR15 | US-04 |
| FR16 | US-07 |
| FR17 | US-19 |
| FR18 | US-20 |
| NFR1 | US-09 |
| NFR2 | US-08, US-14 |
| NFR3 | US-11, US-12 |
| NFR4 | US-08, US-14, US-24 |
| NFR5 | US-17, US-19, US-21 |
| NFR6 | US-17, US-19 |
| NFR7 | US-10 |
| NFR8 | US-22 |
| NFR9 | US-01, US-13 |
| NFR10 | US-22 |
| NFR11 | US-16 |
| NFR12 | US-21 |
| NFR13 | US-23 |
| NFR14 | US-24 |
| NFR15 | US-18 |
| NFR16 | US-25 |
| NFR17 | US-25 |
| NFR18 | US-25 |
| DR1 | US-05, US-23 |
| DR2 | US-06, US-17, US-21 |
| DR3 | US-14 |
| DR4 | US-04, US-16 |
| DR5 | US-06, US-09, US-10 |
| DR6 | US-25 |
| DR7 | US-25 |

---

# 11. Definition of Done

A user story is considered complete when all applicable conditions below are satisfied:

1. The functionality described by the user story has been implemented.
2. All mandatory acceptance criteria for the story pass.
3. The corresponding FR/NFR/DR requirement remains satisfied.
4. Relevant positive, negative, and edge-case scenarios have been tested.
5. Error handling has been implemented for applicable failure conditions.
6. Security and authorization requirements have been verified where applicable.
7. Monitoring, logging, and audit behaviour has been verified where applicable.
8. The implementation does not break existing monitoring, incident, alerting, or reporting behaviour.
9. Relevant documentation has been updated.
10. The implementation is reviewed through the project's GitHub workflow.
11. The completed change is integrated into the appropriate project branch.

---

# 12. Overall Product Flow

The user stories represent the following product flow:

```text
User
  ↓
US-01: Create account / onboarding
  ↓
US-02: Register API endpoint
  ↓
US-03: Configure notification details
  ↓
US-04: Configure maintenance window
  ↓
US-05: Schedule background health checks
  ↓
US-06: Detect API health/failure
  ↓
US-07: Validate response content
  ↓
US-08: Store health-check and response-time history
  ↓
US-09: Confirm repeated failures
  ↓
US-10: Manage incident state and alert transitions
  ↓
US-11: Send incident notification
  ↓
US-12: Retry failed notification delivery
  ↓
US-13: View dashboard
  ↓
US-14: View uptime and historical performance
  ↓
US-15: Generate monthly uptime report
```

Cross-cutting platform behaviour:

```text
US-16 → Responsible monitoring / rate limiting / backoff
US-17 → Encryption and security
US-18 → Tamper-resistant audit logging
US-19 → RBAC and access control
US-20 → Multi-region monitoring
US-21 → Hosting and deployment
US-22 → Scalability and cost
US-23 → Worker failover
US-24 → Long-term data rollups
US-25 → Agile, GitHub, Slack and requirement governance
```

---


# 13. Summary

The user stories translate the project's requirements into stakeholder-oriented work items, while the acceptance criteria define how each story can be verified.

The main traceability chain is:

```text
Stakeholder
    ↓
Elicitation Finding
    ↓
FR / NFR / DR
    ↓
User Story
    ↓
Acceptance Criteria
    ↓
Test Case
    ↓
EPIC
    ↓
Sprint
```

This document is intended to be maintained together with:

- `STAKEHOLDERS.md`
- `ELICITATION.md`
- `ELICITATION_RESULTS.md`
- `FR.md`
- `NFR.md`
- `DOMAIN_REQS.md`

and then used as the basis for EPIC and Sprint planning.
