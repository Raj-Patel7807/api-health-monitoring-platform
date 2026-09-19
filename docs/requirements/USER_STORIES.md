# User Stories & Acceptance Criteria

## Distributed API Health & Incident Monitoring Platform

### 1. Purpose

This document converts the Functional Requirements (FR), Non-Functional Requirements (NFR), and Domain Requirements (DR) of the **Distributed API Health & Incident Monitoring Platform** into user stories with testable acceptance criteria.

The user stories are derived from the existing project requirements and stakeholder/elicitation documents. The intention is to maintain traceability:

```text
Stakeholders
     ↓
Elicitation
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
```

The project requirements identify API developers/API owners, DevOps/deployment-experienced developers, incident responders/on-call developers, team leads/project maintainers, the platform/project development team, notification/integration services, monitored APIs/target services, and hosting/infrastructure providers as relevant stakeholders.

---

## 2. User Story Format

Each user story follows the standard format:

> **As a [stakeholder], I want [capability], so that [benefit].**

Each story contains:

- **Story ID** — unique identifier.
- **EPIC** — larger feature area.
- **Priority** — relative implementation priority for project planning.
- **Source Requirements** — FR/NFR/DR requirements covered.
- **User Story** — requirement from the stakeholder's point of view.
- **Acceptance Criteria** — conditions that must be satisfied for the story to be considered complete.

Acceptance criteria are intentionally written so that they can later be converted into test cases.

## 3. User Story Index

All **23 user stories** are included below in continuous numerical order.

- **US-01 — User Account Onboarding**
- **US-02 — Register an API Endpoint**
- **US-03 — Configure Notification Details**
- **US-04 — Configure an Endpoint Maintenance Window**
- **US-05 — Schedule Continuous Background Health Checks**
- **US-06 — Detect API Health Failures**
- **US-07 — Record Health-Check Results and Response Time**
- **US-08 — Create an Incident Only After Confirmed Failure**
- **US-09 — Avoid Duplicate Alerts for the Same Incident State**
- **US-10 — Send Incident Alerts Through Configured Channels**
- **US-11 — Retry Failed Notification Delivery**
- **US-12 — Represent Incident and Recovery State**
- **US-13 — View Overall API Health Dashboard**
- **US-14 — View Uptime and Historical Performance**
- **US-15 — Generate Monthly Uptime Report**
- **US-16 — Respect Target API Rate Limits and Use Backoff**
- **US-17 — Protect Stored Monitoring and Configuration Data**
- **US-18 — Securely Manage Access to the Platform**
- **US-19 — Scale Monitoring Resources as Usage Grows**
- **US-20 — Deploy and Maintain the Platform Within Hosting Constraints**
- **US-21 — Keep Monitoring Workloads Separate From the User Interface**
- **US-22 — Follow Standard Web Communication Rules**
- **US-23 — Maintain Monitoring Behaviour During Temporary Network Problems**


---

# 4. EPIC Overview

| EPIC ID | EPIC | Main Scope | Requirement Coverage |
|---|---|---|---|
| E1 | User Onboarding & API Registration | Account creation and endpoint registration | FR1, FR11, NFR9 |
| E2 | API Monitoring & Health Checks | Scheduling, checking, failure detection and history | FR2, FR3, FR9, DR1, DR2, DR5 |
| E3 | Incident Detection & Alerting | Incident threshold, state changes and notifications | FR5, FR6, FR7, FR8, FR13, NFR1, NFR3, NFR7 |
| E4 | Dashboard, History & Reporting | Health overview, uptime, history and reports | FR4, FR9, FR10, FR14, NFR2, NFR4, NFR9 |
| E5 | Responsible Monitoring & Maintenance | Rate limiting, backoff and maintenance windows | FR12, FR15, NFR11, DR3, DR4 |
| E6 | Security & Data Protection | Encryption, secure communication and security controls | NFR5, NFR6, DR2 |
| E7 | Scalability, Cost & Operations | Scaling, deployment, maintenance and hosting constraints | NFR8, NFR10, NFR12 |
| E8 | Platform Reliability & Operational Behaviour | Reliable monitoring and notification operation | NFR1, NFR3, NFR7, DR1, DR5 |

---

# 5. User Stories

## E1 — User Onboarding & API Registration

## US-01 — User Account Onboarding

**EPIC:** E1 — User Onboarding & API Registration  
**Primary Actor:** API Developer / API Owner  
**Priority:** High  
**Source Requirements:** FR11, NFR9

### User Story

> **As an API developer, I want a simple onboarding process for creating my account and adding my first API endpoint, so that I can start monitoring an API quickly without a complicated setup process.**

### Acceptance Criteria

**AC-01.1 — Account creation**

- Given that a new user does not have an account,
- When the user starts the onboarding process,
- Then the system shall provide the required account-registration steps.

**AC-01.2 — First endpoint setup**

- Given that the user has successfully completed registration,
- When the onboarding process continues,
- Then the user shall be guided toward adding their first API endpoint.

**AC-01.3 — Successful completion**

- Given that the user provides valid information,
- When the onboarding process is completed,
- Then the system shall create the account and save the first endpoint configuration.

**AC-01.4 — Time expectation**

- The complete sign-up and first-endpoint setup should be achievable within **5 minutes** under normal operating conditions.

---

## US-02 — Register an API Endpoint

**EPIC:** E1 — User Onboarding & API Registration  
**Primary Actor:** API Developer / API Owner  
**Priority:** High  
**Source Requirements:** FR1

### User Story

> **As an API owner, I want to register an API endpoint by providing its URL, expected status code, and monitoring frequency, so that the platform knows what to monitor and how to determine whether the endpoint is healthy.**

### Acceptance Criteria

**AC-02.1 — Endpoint URL**

- Given that the user is adding an endpoint,
- When the user enters a valid API URL,
- Then the system shall accept the URL for registration.

**AC-02.2 — Expected status code**

- Given that the user is registering an endpoint,
- When the user specifies the expected HTTP status code,
- Then the system shall store that expected status code with the endpoint configuration.

**AC-02.3 — Monitoring frequency**

- Given that the user is registering an endpoint,
- When the user specifies how often it should be checked,
- Then the system shall save the monitoring frequency.

**AC-02.4 — Saved configuration**

- Given that all required endpoint information is valid,
- When the user submits the registration,
- Then the endpoint shall be saved and become available for monitoring.

**AC-02.5 — Invalid configuration**

- Given that required endpoint information is missing or invalid,
- When the user submits the registration,
- Then the system shall reject the invalid configuration and inform the user that correction is required.

---

## US-03 — Configure Notification Details

**EPIC:** E1 — User Onboarding & API Registration  
**Primary Actor:** API Developer / API Owner  
**Priority:** High  
**Source Requirements:** FR13

### User Story

> **As an API owner, I want to configure and manage my notification details, so that incident alerts can be delivered through the notification channel I have selected.**

### Acceptance Criteria

**AC-03.1 — Notification configuration**

- Given that the user has a registered account or endpoint,
- When the user opens notification settings,
- Then the system shall allow the user to configure supported notification details.

**AC-03.2 — Supported details**

- The configuration shall support the notification information required for the selected channel, such as a Slack webhook or email address.

**AC-03.3 — Account or endpoint scope**

- The user shall be able to associate notification details with their account or with an individual endpoint, as supported by the platform configuration.

**AC-03.4 — Update configuration**

- Given that notification details already exist,
- When the user changes them,
- Then the system shall save the updated configuration for future notifications.

**AC-03.5 — Secure handling**

- Sensitive notification information such as webhook URLs or tokens shall not be unnecessarily exposed in the user interface or logs.

---

## US-04 — Configure an Endpoint Maintenance Window

**EPIC:** E1 — User Onboarding & API Registration  
**Primary Actor:** API Developer / API Owner  
**Priority:** Medium  
**Source Requirements:** FR15, DR4

### User Story

> **As an API owner, I want to define a maintenance window for an endpoint, so that planned deployments or maintenance do not create false incidents or unnecessary alerts.**

### Acceptance Criteria

**AC-04.1 — Create maintenance window**

- Given that an endpoint is registered,
- When the user defines a valid planned time range,
- Then the system shall save the maintenance window for that endpoint.

**AC-04.2 — Monitoring continues**

- Given that a maintenance window is active,
- When the scheduled health-check time is reached,
- Then the system shall continue performing the health check.

**AC-04.3 — Suppress incident/alert**

- Given that a monitored endpoint fails during an active maintenance window,
- When the failure is processed,
- Then the system shall not create a normal incident or send a normal incident alert for that planned maintenance period.

**AC-04.4 — End of maintenance**

- Given that the maintenance window has ended,
- When subsequent health checks fail,
- Then normal failure and incident processing shall resume.

---

# E2 — API Monitoring & Health Checks

## US-05 — Schedule Continuous Background Health Checks

**EPIC:** E2 — API Monitoring & Health Checks  
**Primary Actor:** API Developer / API Owner  
**Priority:** High  
**Source Requirements:** FR2, DR1

### User Story

> **As an API owner, I want the platform to check my registered endpoint automatically in the background, so that I do not have to manually check whether my API is working.**

### Acceptance Criteria

**AC-05.1 — Background scheduling**

- Given that an endpoint is registered and monitoring is enabled,
- When its configured check time is reached,
- Then the system shall schedule the endpoint for a health check through the background job system.

**AC-05.2 — Job queue**

- The monitoring process shall use the project's background job queue mechanism (**BullMQ**) for scheduled health-check jobs.

**AC-05.3 — Repeated monitoring**

- Given that a health check has completed,
- When monitoring remains enabled,
- Then the system shall schedule the next check according to the endpoint's configured monitoring frequency.

**AC-05.4 — User-facing application remains responsive**

- Health-check execution shall run in the background and shall not block the main user-facing application.

**AC-05.5 — Monitoring failure**

- If a background monitoring job fails internally, the platform shall record/log the operational failure so that the development/administration team can investigate it.

---

## US-06 — Detect API Health Failures

**EPIC:** E2 — API Monitoring & Health Checks  
**Primary Actor:** API Developer / API Owner  
**Priority:** High  
**Source Requirements:** FR3, DR2, DR5

### User Story

> **As an API owner, I want the platform to identify different types of endpoint failures, so that I can understand whether the problem is a timeout, incorrect response, connection problem, or SSL problem.**

### Acceptance Criteria

**AC-06.1 — Expected status code**

- Given that the endpoint returns the configured expected status code,
- When the response is analyzed,
- Then the health check shall be considered successful unless another configured health condition fails.

**AC-06.2 — Wrong status code**

- Given that the endpoint returns a status code different from the configured expected status code,
- When the response is analyzed,
- Then the health check shall be recorded as failed.

**AC-06.3 — Timeout**

- Given that the endpoint does not respond within the configured/requested timeout,
- When the health check completes,
- Then the check shall be recorded as a timeout failure.

**AC-06.4 — Connection failure**

- Given that the system cannot establish the required connection,
- When the check is processed,
- Then the check shall be recorded as a connection failure.

**AC-06.5 — SSL failure**

- Given that the monitored HTTPS endpoint has an invalid/bad SSL certificate condition,
- When the certificate is checked,
- Then the health check shall be recorded as an SSL-related failure.

---

## US-07 — Record Health-Check Results and Response Time

**EPIC:** E2 — API Monitoring & Health Checks  
**Primary Actor:** API Developer / API Owner  
**Priority:** High  
**Source Requirements:** FR9, NFR2, NFR4

### User Story

> **As an API owner, I want the platform to store health-check results and response-time information, so that I can investigate the endpoint's behaviour later.**

### Acceptance Criteria

**AC-07.1 — Successful check record**

- Given that a health check succeeds,
- When the check is completed,
- Then the system shall record the result and relevant response-time information.

**AC-07.2 — Failed check record**

- Given that a health check fails,
- When the check is completed,
- Then the system shall record the failure result and relevant failure information.

**AC-07.3 — Historical access**

- Given that historical monitoring data exists,
- When the user requests it,
- Then the system shall provide the available historical uptime/response-time information.

**AC-07.4 — Recent data performance**

- Monitoring data from the most recent 30 days should be retrievable within **5 seconds**.

**AC-07.5 — Older data**

- Older/archived data shall remain reachable even if retrieval takes longer, with the stated target of up to **5 minutes**.

**AC-07.6 — No monitoring-data deletion**

- Monitoring data shall not be intentionally deleted as part of normal system operation.

---

# E3 — Incident Detection & Alerting

## US-08 — Create an Incident Only After Confirmed Failure

**EPIC:** E3 — Incident Detection & Alerting  
**Primary Actor:** Incident Responder / On-call Developer  
**Priority:** High  
**Source Requirements:** FR5, DR5, NFR1

### User Story

> **As an incident responder, I want the platform to confirm repeated failures before opening an incident, so that temporary network problems do not create false incidents.**

### Acceptance Criteria

**AC-08.1 — First failure**

- Given that an endpoint is healthy,
- When the first health check fails,
- Then the system shall record the failure but shall not immediately create an incident.

**AC-08.2 — Failure threshold**

- Given that failures continue,
- When the configured failure threshold is crossed,
- Then the system shall create an incident.

**AC-08.3 — Example threshold**

- The current requirement uses a threshold such as **3 consecutive failures** as an example; the final threshold should follow the finalized project configuration.

**AC-08.4 — Temporary failure**

- Given that a failure is temporary and the endpoint returns to the expected healthy state before the incident threshold is reached,
- Then the system shall not create a normal incident for that temporary failure.

**AC-08.5 — Failure detection performance**

- The system should detect failures within **2 minutes for at least 95 out of 100 incidents**, measured over the stated 30-day period.

---

## US-09 — Avoid Duplicate Alerts for the Same Incident State

**EPIC:** E3 — Incident Detection & Alerting  
**Primary Actor:** Incident Responder / On-call Developer  
**Priority:** High  
**Source Requirements:** FR6, NFR7

### User Story

> **As an incident responder, I want to receive an alert when an endpoint changes from healthy to failing without receiving an alert for every failed check, so that monitoring notifications remain useful and actionable.**

### Acceptance Criteria

**AC-09.1 — State transition alert**

- Given that an endpoint changes from healthy to a confirmed failing state,
- When the incident is created,
- Then the system shall send an incident alert.

**AC-09.2 — No repeated alert for every failed check**

- Given that the endpoint remains in the same failing state,
- When additional checks fail,
- Then the system shall not send a new duplicate incident alert for every failed check.

**AC-09.3 — New failure state**

- Given that an endpoint has returned to a healthy state and later becomes failing again,
- When a new confirmed failure state is reached,
- Then the system shall be able to generate a new incident alert for the new state change.

**AC-09.4 — Actionable alerts**

- The project target is that at least **90 out of 100 alerts** represent real, actionable problems.

---

## US-10 — Send Incident Alerts Through Configured Channels

**EPIC:** E3 — Incident Detection & Alerting  
**Primary Actor:** Incident Responder / On-call Developer  
**Priority:** High  
**Source Requirements:** FR7, FR13, NFR3

### User Story

> **As an incident responder, I want confirmed incidents to be delivered through my configured notification channel, so that I can react to API failures without continuously watching the dashboard.**

### Acceptance Criteria

**AC-10.1 — Slack**

- Given that a Slack notification destination is configured,
- When a confirmed incident is created,
- Then the system shall attempt to send the incident notification through the configured Slack integration.

**AC-10.2 — Discord**

- Given that a Discord notification destination is configured,
- When a confirmed incident is created,
- Then the system shall attempt to send the incident notification through Discord.

**AC-10.3 — Email**

- Given that an email destination is configured,
- When a confirmed incident is created,
- Then the system shall attempt to send the incident notification to the configured email address.

**AC-10.4 — Webhook**

- Given that a generic webhook destination is configured,
- When a confirmed incident is created,
- Then the system shall send the appropriate notification payload to the configured webhook.

**AC-10.5 — Delivery reliability**

- At least **99 out of 100** notification/webhook deliveries should succeed.
- Successful notification delivery should be acknowledged within **5 seconds**.

---

## US-11 — Retry Failed Notification Delivery

**EPIC:** E3 — Incident Detection & Alerting  
**Primary Actor:** Incident Responder / On-call Developer  
**Priority:** High  
**Source Requirements:** FR8, NFR3

### User Story

> **As an incident responder, I want the platform to retry a failed notification delivery, so that a temporary failure in Slack, email, Discord, or a webhook does not immediately prevent me from receiving the incident alert.**

### Acceptance Criteria

**AC-11.1 — Detect delivery failure**

- Given that the system attempts to send a notification,
- When the external notification service reports a delivery failure,
- Then the system shall mark the delivery attempt as failed.

**AC-11.2 — Retry**

- The system shall retry a failed notification up to **3 times**.

**AC-11.3 — Growing wait time**

- The retry attempts shall use a growing wait time between attempts rather than immediately sending all retries together.

**AC-11.4 — Final failure**

- Given that all configured retry attempts fail,
- Then the system shall mark the notification delivery as failed and log the failure.

**AC-11.5 — No unnecessary retries**

- Given that a notification is successfully delivered,
- Then no further retry for that notification shall be performed.

---

## US-12 — Represent Incident and Recovery State

**EPIC:** E3 — Incident Detection & Alerting  
**Primary Actor:** Incident Responder / On-call Developer  
**Priority:** High  
**Source Requirements:** FR5, FR6, FR9, DR5

### User Story

> **As an incident responder, I want the system to maintain the current incident state and historical incident information, so that I can understand when a problem started and whether the service has recovered.**

### Acceptance Criteria

**AC-12.1 — Open incident**

- Given that an endpoint crosses the confirmed failure threshold,
- Then the system shall record an open incident associated with that endpoint.

**AC-12.2 — Incident history**

- The incident shall retain the relevant start/failure information needed for later investigation.

**AC-12.3 — Recovery detection**

- Given that an endpoint with an open incident returns to its expected healthy state,
- Then the system shall update the endpoint's state to healthy/recovered.

**AC-12.4 — Historical state**

- Previous incident information shall remain available as historical data.

---

# E4 — Dashboard, History & Reporting

## US-13 — View Overall API Health Dashboard

**EPIC:** E4 — Dashboard, History & Reporting  
**Primary Actor:** Team Lead / Project Maintainer  
**Priority:** High  
**Source Requirements:** FR10, NFR9, NFR10

### User Story

> **As a team lead, I want to see the health of all monitored endpoints in one dashboard, so that I can quickly identify unhealthy services and open incidents without opening every endpoint individually.**

### Acceptance Criteria

**AC-13.1 — Endpoint overview**

- Given that the user has multiple registered endpoints,
- When the dashboard is opened,
- Then the dashboard shall provide an overview of their monitored endpoints.

**AC-13.2 — Health state**

- The dashboard shall show the current health/state of each endpoint.

**AC-13.3 — Open incidents**

- The dashboard shall identify which endpoints currently have an open incident.

**AC-13.4 — Service-level summary**

- The dashboard shall provide summary information useful for understanding overall service health.

**AC-13.5 — Dashboard performance**

- The dashboard should load within **3 seconds** under the stated target conditions.


---

## US-14 — View Uptime and Historical Performance

**EPIC:** E4 — Dashboard, History & Reporting  
**Primary Actor:** API Developer / API Owner  
**Priority:** High  
**Source Requirements:** FR4, FR9, NFR2, NFR4, DR3

### User Story

> **As an API owner, I want to view uptime and historical response-time information, so that I can understand the reliability and performance of my endpoint over time.**

### Acceptance Criteria

**AC-14.1 — Uptime percentage**

- Given that monitoring data is available for an endpoint,
- When uptime is requested,
- Then the system shall calculate and provide the endpoint's uptime percentage.

**AC-14.2 — Uptime calculation**

- Uptime shall follow the project domain formula:

```text
Uptime % = ((Total Time - Downtime) / Total Time) × 100
```

**AC-14.3 — Response-time history**

- The user shall be able to access stored response-time history for the endpoint.

**AC-14.4 — Reporting API**

- The uptime result shall be available through the project's reporting API.

**AC-14.5 — Historical availability**

- Historical monitoring information shall remain accessible according to the project's data-retention requirements.

---

## US-15 — Generate Monthly Uptime Report

**EPIC:** E4 — Dashboard, History & Reporting  
**Primary Actor:** Team Lead / Project Maintainer  
**Priority:** Medium  
**Source Requirements:** FR14

### User Story

> **As a team lead, I want to generate a monthly uptime report for my monitored endpoints, so that I can review service reliability over a defined reporting period.**

### Acceptance Criteria

**AC-15.1 — Monthly report**

- Given that monitoring data exists for a user,
- When a monthly report is requested,
- Then the system shall generate a report containing the available monthly uptime information.

**AC-15.2 — User-specific data**

- The report shall contain only the monitoring information associated with the requesting user's endpoints.

**AC-15.3 — Download**

- The generated report shall be available for download.

**AC-15.4 — API access**

- The report shall also be retrievable through the reporting API.

---

# E5 — Responsible Monitoring & Maintenance

## US-16 — Respect Target API Rate Limits and Use Backoff

**EPIC:** E5 — Responsible Monitoring & Maintenance  
**Primary Actor:** Monitored API Owner / Target Service  
**Priority:** High  
**Source Requirements:** FR12, NFR11, DR4

### User Story

> **As an owner of a monitored API, I want the monitoring platform to control the frequency of health-check requests and back off after repeated failures, so that monitoring does not create unnecessary or abusive traffic to my service.**

### Acceptance Criteria

**AC-16.1 — Configurable check frequency**

- Health-check frequency shall be configurable according to the endpoint monitoring configuration.

**AC-16.2 — Rate limiting**

- Health-check requests sent to monitored external APIs shall be rate-limited.

**AC-16.3 — Backoff**

- Given that an endpoint continues to fail,
- Then the monitoring system shall back off rather than continuously sending requests at the same frequency.

**AC-16.4 — Request identification**

- Monitoring requests shall identify the monitoring system appropriately.

**AC-16.5 — No unnecessary traffic**

- The system shall avoid generating unnecessary monitoring traffic that could cause the monitored service to treat the platform as abusive traffic.

---

# E6 — Security & Data Protection

## US-17 — Protect Stored Monitoring and Configuration Data

**EPIC:** E6 — Security & Data Protection  
**Primary Actor:** Platform Administrator / Project Development Team  
**Priority:** High  
**Source Requirements:** NFR5, NFR6

### User Story

> **As a platform administrator, I want stored monitoring and configuration data to be encrypted and protected, so that sensitive information is not exposed if stored data is accessed improperly.**

### Acceptance Criteria

**AC-17.1 — Stored-data encryption**

- Stored sensitive/project data shall use **AES-256** encryption as specified by the current NFR.

**AC-17.2 — Network encryption**

- Data transmitted over the network shall use **TLS 1.3** as specified by the current requirement.

**AC-17.3 — Sensitive credentials**

- Authentication credentials, tokens, webhook secrets, and similar sensitive values shall not be stored or logged in an unnecessarily exposed form.

**AC-17.4 — Security incidents**

- The system should operate with a target of zero critical/high-severity security incidents over a 12-month period.

**AC-17.5 — Compliance**

- The system shall satisfy applicable required compliance checks identified for the project.

---

## US-18 — Securely Manage Access to the Platform

**EPIC:** E6 — Security & Data Protection  
**Primary Actor:** Platform Administrator / Project Development Team  
**Priority:** High  
**Source Requirements:** NFR5, NFR6, stakeholder security requirements

### User Story

> **As a platform administrator, I want access to platform resources and sensitive configuration to be protected, so that users cannot access data or functions they are not authorized to use.**

### Acceptance Criteria

**AC-18.1 — Authentication**

- Users shall authenticate before accessing protected platform functionality.

**AC-18.2 — Authorization**

- Access to user-specific monitoring information and configuration shall be restricted to authorized users.

**AC-18.3 — Sensitive configuration**

- Sensitive configuration such as notification credentials shall be protected from unauthorized access.

**AC-18.4 — Logging**

- Security-relevant failures shall be recorded appropriately without exposing secrets.

---

# E7 — Scalability, Cost & Operations

## US-19 — Scale Monitoring Resources as Usage Grows

**EPIC:** E7 — Scalability, Cost & Operations  
**Primary Actor:** Platform Administrator / Project Development Team  
**Priority:** Medium  
**Source Requirements:** NFR8, NFR10

### User Story

> **As a platform administrator, I want the monitoring system to scale its resources as the number of users and health checks grows, so that the platform can continue operating without unnecessary cost or performance degradation.**

### Acceptance Criteria

**AC-19.1 — Active-user growth**

- The system should be capable of growing toward the current target of **200 active users within 3 months**.

**AC-19.2 — Auto-scaling**

- Where supported by the final hosting environment, monitoring resources should be able to scale according to workload.

**AC-19.3 — Health-check cost**

- The target cost of a single health check should remain below **$0.01 for at least 95% of checks**.

**AC-19.4 — User retention target**

- The current requirement includes a target of user churn below **5%**.

**AC-19.5 — Satisfaction target**

- The current requirement includes a target average satisfaction rating of **4.5/5 or higher**.


---

## US-20 — Deploy and Maintain the Platform Within Hosting Constraints

**EPIC:** E7 — Scalability, Cost & Operations  
**Primary Actor:** Platform Administrator / Project Development Team  
**Priority:** Medium  
**Source Requirements:** NFR12, NFR8, S8 stakeholder constraints

### User Story

> **As a platform administrator, I want the application to be deployable and maintainable within the selected hosting environment, so that the monitoring platform can run reliably without exceeding infrastructure limitations.**

### Acceptance Criteria

**AC-20.1 — Deployment**

- The system shall be deployable using the compute, database, storage, networking, and background-worker facilities available from the selected hosting provider.

**AC-20.2 — Background workers**

- The selected hosting setup shall support the background monitoring workload required by the platform.

**AC-20.3 — Resource constraints**

- Deployment configuration shall account for the provider's CPU, memory, storage, database, and network limits.

**AC-20.4 — Maintenance**

- The application should be maintainable without requiring unsupported infrastructure capabilities.

**AC-20.5 — Hosting-specific configuration**

- Hosting-specific limits and configuration values shall be defined according to the selected hosting provider and deployment architecture.


---

# E8 — Platform Reliability & Operational Behaviour

## US-21 — Keep Monitoring Workloads Separate From the User Interface

**EPIC:** E8 — Platform Reliability & Operational Behaviour  
**Primary Actor:** Platform Administrator / Project Development Team  
**Priority:** High  
**Source Requirements:** DR1, FR2

### User Story

> **As a platform administrator, I want health checks to execute through background workers rather than the main user-facing request flow, so that monitoring activity does not make the dashboard or application slow or unresponsive.**

### Acceptance Criteria

**AC-21.1 — Background execution**

- Health checks shall execute through the background job mechanism.

**AC-21.2 — Non-blocking user interface**

- A long-running or slow health check shall not block the main user-facing request handling.

**AC-21.3 — Repeated scheduling**

- Background workers shall continue scheduling health checks while monitoring remains enabled.

**AC-21.4 — Operational failure visibility**

- Failure of a monitoring worker/job shall be logged or otherwise made visible to the platform administration team.

---

## US-22 — Follow Standard Web Communication Rules

**EPIC:** E8 — Platform Reliability & Operational Behaviour  
**Primary Actor:** Platform Administrator / Project Development Team  
**Priority:** High  
**Source Requirements:** DR2, NFR5

### User Story

> **As a platform administrator, I want communication between the monitoring platform and monitored endpoints to follow standard HTTP/HTTPS and TLS requirements, so that monitoring communication remains compatible and secure.**

### Acceptance Criteria

**AC-22.1 — HTTP/HTTPS communication**

- Endpoint health checks shall use the standard HTTP/HTTPS communication mechanisms required by the target API.

**AC-22.2 — Secure network traffic**

- Network communication carrying project data shall use TLS 1.3 according to the current domain/security requirement.

**AC-22.3 — HTTPS certificate handling**

- Invalid/bad SSL certificate conditions for HTTPS endpoints shall be detected as part of health checking.

---

## US-23 — Maintain Monitoring Behaviour During Temporary Network Problems

**EPIC:** E8 — Platform Reliability & Operational Behaviour  
**Primary Actor:** Incident Responder / On-call Developer  
**Priority:** High  
**Source Requirements:** DR5, FR5, FR6

### User Story

> **As an incident responder, I want temporary network problems to be distinguished from confirmed service failures, so that the platform does not generate unnecessary false incidents and alerts.**

### Acceptance Criteria

**AC-23.1 — Single temporary failure**

- A single failed health check shall not automatically create a confirmed incident.

**AC-23.2 — Failure confirmation**

- The platform shall evaluate subsequent checks/failure threshold rules before opening an incident.

**AC-23.3 — Recovery before threshold**

- If the endpoint becomes healthy again before the configured failure threshold is reached, the platform shall not open a normal incident for that temporary failure.

**AC-23.4 — Confirmed outage**

- If failures continue beyond the configured threshold, the platform shall create the appropriate incident and alert according to the incident-handling requirements.

---

# 6. Cross-Cutting Acceptance Criteria for Non-Functional Requirements

The following criteria provide direct traceability for NFRs that apply across multiple user stories rather than representing one independent user-facing feature.

| NFR | Acceptance / Validation Target | Covered By |
|---|---|---|
| NFR1 | Failure detected within 2 minutes for at least 95/100 incidents over the stated 30-day measurement period | US-08, US-23 |
| NFR2 | Recent-data lookup under 5 seconds; older archived lookup may take up to 5 minutes | US-07, US-14 |
| NFR3 | At least 99/100 notification deliveries succeed and are acknowledged within 5 seconds | US-10, US-11 |
| NFR4 | Monitoring data is retained; recent data remains fast and older data remains reachable | US-07, US-14 |
| NFR5 | Stored data uses AES-256 and network traffic uses TLS 1.3 | US-17, US-22 |
| NFR6 | Zero critical/high security incidents over the stated 12-month target period and required compliance checks pass | US-17, US-18 |
| NFR7 | At least 90/100 alerts are real/actionable and average resolution target is under 30 minutes | US-09, US-12 |
| NFR8 | 95% of health checks target a cost below $0.01; scaling supports workload | US-19 |
| NFR9 | Sign-up + first endpoint under 5 minutes; dashboard load under 3 seconds | US-01, US-13 |
| NFR10 | Target of 200 active users in 3 months, churn below 5%, satisfaction at least 4.5/5 | US-19 |
| NFR11 | Health-check traffic is rate-limited and configurable | US-16 |
| NFR12 | System is deployable and maintainable within the selected hosting environment | US-20 |

---

# 7. Domain Requirement Traceability

| DR | Domain Rule | Covered By |
|---|---|---|
| DR1 | Health checks run in the background and do not block the user-facing application | US-05, US-21 |
| DR2 | Communication follows HTTP/HTTPS rules and TLS 1.3 is used for network transmission | US-06, US-17, US-22 |
| DR3 | Uptime uses `(Total Time - Downtime) / Total Time × 100` | US-14 |
| DR4 | Monitoring another service must use reasonable intervals/backoff to avoid abusive traffic | US-04, US-16 |
| DR5 | A single temporary failure must not automatically become a real incident | US-08, US-23 |

---

# 8. Functional Requirement Traceability

| FR | Requirement Summary | User Story |
|---|---|---|
| FR1 | Register endpoint with URL, expected status code and check frequency | US-02 |
| FR2 | Repeated background checking using BullMQ/job queue | US-05, US-21 |
| FR3 | Detect timeout, wrong status, connection and SSL failures | US-06 |
| FR4 | Calculate uptime and expose it through reporting API | US-14 |
| FR5 | Create incident only after failure threshold is crossed | US-08, US-23 |
| FR6 | One alert per state change instead of one per failed check | US-09 |
| FR7 | Send alerts through Slack, Discord, Email or webhook | US-10 |
| FR8 | Retry failed notification up to 3 times with growing wait time | US-11 |
| FR9 | Store uptime and response-time history | US-07, US-14 |
| FR10 | Dashboard showing endpoint health and open incidents | US-13 |
| FR11 | Simple onboarding and first-endpoint setup | US-01 |
| FR12 | Avoid excessive requests, use backoff and identify monitoring requests | US-16 |
| FR13 | Configure/manage notification details | US-03 |
| FR14 | Generate monthly uptime report and expose/download it | US-15 |
| FR15 | Maintenance window suppresses incident/alert during planned maintenance | US-04 |

---

# 9. Stakeholder Traceability

| Stakeholder | Main User Stories |
|---|---|
| S1 — API Developer / API Owner | US-01, US-02, US-03, US-04, US-05, US-06, US-07, US-14 |
| S2 — DevOps / Deployment-Experienced Developer | US-05, US-06, US-08, US-19, US-20, US-21 |
| S3 — Incident Responder / On-call Developer | US-08, US-09, US-10, US-11, US-12, US-23 |
| S4 — Team Lead / Project Maintainer | US-13, US-14, US-15 |
| S5a — Platform Administrator | US-17, US-18, US-19, US-20, US-21, US-22 |
| S5b — Project Development Team | US-05, US-17, US-18, US-19, US-20, US-21, US-22 |
| S6 — Notification & Integration Services | US-03, US-10, US-11 |
| S7 — Target Service Operators / Monitored APIs | US-04, US-16 |
| S8 — Hosting / Infrastructure Provider | US-05, US-19, US-20 |

---

# 10. Requirement-to-User-Story Traceability Matrix

| Requirement | User Story IDs |
|---|---|
| FR1 | US-02 |
| FR2 | US-05, US-21 |
| FR3 | US-06 |
| FR4 | US-14 |
| FR5 | US-08, US-23 |
| FR6 | US-09 |
| FR7 | US-10 |
| FR8 | US-11 |
| FR9 | US-07, US-14 |
| FR10 | US-13 |
| FR11 | US-01 |
| FR12 | US-16 |
| FR13 | US-03 |
| FR14 | US-15 |
| FR15 | US-04 |
| NFR1 | US-08, US-23 |
| NFR2 | US-07, US-14 |
| NFR3 | US-10, US-11 |
| NFR4 | US-07, US-14 |
| NFR5 | US-17, US-22 |
| NFR6 | US-17, US-18 |
| NFR7 | US-09, US-12 |
| NFR8 | US-19 |
| NFR9 | US-01, US-13 |
| NFR10 | US-19 |
| NFR11 | US-16 |
| NFR12 | US-20 |
| DR1 | US-05, US-21 |
| DR2 | US-06, US-17, US-22 |
| DR3 | US-14 |
| DR4 | US-04, US-16 |
| DR5 | US-08, US-23 |

---

# 11. Definition of Done for a User Story

A user story can be considered ready for completion when:

1. The functionality described by the user story has been implemented.
2. All mandatory acceptance criteria for the story pass.
3. The corresponding FR/NFR/DR requirement remains satisfied.
4. Relevant error and edge cases have been tested.
5. Sensitive data such as credentials, tokens and webhook secrets are not exposed.
6. Relevant monitoring/logging behaviour is implemented where required.
7. The change does not break existing monitoring, incident or notification behaviour.
8. The story is traceable back to its requirement source.
9. The implementation is committed to the project Git repository according to the team's version-control and contribution standards.

---

# 12. Overall Flow

The user stories represent the complete product flow:

```text
User
  ↓
US-01: Create account / onboarding
  ↓
US-02: Register API endpoint
  ↓
US-03: Configure notifications
  ↓
US-04: Configure maintenance window
  ↓
US-05: Schedule background health checks
  ↓
US-06: Check API health
  ↓
US-07: Store health/response-time history
  ↓
US-08: Confirm repeated failures
  ↓
US-09: Avoid duplicate alerts
  ↓
US-10: Send incident notification
  ↓
US-11: Retry failed notification delivery
  ↓
US-12: Maintain incident/recovery state
  ↓
US-13: View dashboard
  ↓
US-14: View uptime/history
  ↓
US-15: Generate monthly report

Parallel technical behaviour:
  ├── US-16: Rate limiting and backoff
  ├── US-17: Data protection
  ├── US-18: Access control
  ├── US-19: Scaling and cost
  ├── US-20: Hosting/deployment
  ├── US-21: Background processing
  ├── US-22: HTTP/HTTPS/TLS
  └── US-23: Temporary-failure handling
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
