# Functional Requirements (FR)

## 1. Definition and Purpose

**Definition:** Functional Requirements (FR) define what the system must explicitly perform—including system capabilities, user inputs, automated execution behaviors, data processing, and outward responses.

**Overall Purpose:** The primary purpose of functional requirements is to construct an unambiguous operational blueprint for the platform. By clearly specifying how target endpoints are registered, monitored, evaluated, and reported on, functional requirements bridge user needs with software architecture. Specifically, they serve to:
* **Guide Technical Architecture:** Provide developers with exact specifications for constructing background job queues, failure detection mechanisms, and alert dispatch services.
* **Ensure Operational Integrity:** Guarantee that health checks, state transitions, and incident logs operate predictably without manual intervention.
* **Prevent Silent Failures:** Establish strict evaluation criteria (such as status codes, timeouts, and payload assertions) so that faulty endpoint behavior is immediately detected.
* **Form Testable Criteria:** Provide Quality Assurance (QA) and software engineering teams with clear baseline logic for creating unit, integration, and end-to-end automated test suites.

---

## 2. Functional Requirements List

| ID | Requirement |
| :--- | :--- |
| **FR1** | User can add (register) an API endpoint by giving its URL, the status code it should return, and how often it should be checked. |
| **FR2** | System keeps checking each saved endpoint again and again using a background job queue (BullMQ). After every check it schedules the next one. |
| **FR3** | System can tell when an endpoint has failed - this includes timeout, wrong status code, connection error, or bad SSL certificate. |
| **FR4** | System calculates uptime percentage for each endpoint and gives it through a reporting API. |
| **FR5** | System does not create an incident on the very first failure. It waits and only creates an incident once failures cross a set limit (like 3 in a row). |
| **FR6** | System sends only one alert per change of state (healthy to failing), not one alert per failed check, so the user does not get spammed. |
| **FR7** | System sends incident alerts through Slack, Discord, Email or a webhook, whichever the user has set up. |
| **FR8** | If sending a notification fails, system tries again up to 3 times with growing wait time between tries, then marks it failed and logs it. |
| **FR9** | System stores old uptime and response-time data so it can be looked up later. Recent data should be fast to fetch, older data can be a bit slower. |
| **FR10** | System shows a dashboard where a team lead can see, at one glance, how all their endpoints are doing and which ones have an open incident. |
| **FR11** | New user gets a simple onboarding flow to sign up and add their first endpoint quickly. |
| **FR12** | When checking someone else's API, system should not hit it too often, should back off if it keeps failing, and should identify itself properly in the request. |
| **FR13** | User can set up and manage their notification details (Slack webhook link, email address, etc.) for their account or for a single endpoint. |
| **FR14** | System can generate a monthly uptime report per user, which can be downloaded or fetched through the API. |
| **FR15** | User can set a maintenance window for an endpoint (a planned time range) during which checks still happen but no alert/incident is raised, so planned deployments do not trigger false alarms. |
| **FR16** | Response Body & JSONPath Assertions: Users can set rules to check specific text strings, regex patterns, or JSONPath values inside the response body. |
| **FR17** | Role-Based Access Control (RBAC): Admins can grant granular permissions (e.g., Admin, Operator, Read-Only) to team members. |
| **FR18** | Multi-Region Probe Selection: Allowing users to pick geographic origin regions (e.g., US-East, EU-Central, AP-South) to detect localized network routing issues. |

---

## 3. Requirement Purposes

* **FR1 Purpose:** Enables users to onboard new API endpoints into the platform and define target parameters (HTTP URL, expected status code, check frequency) required for automated monitoring workflows. This establishes the baseline configuration data needed by the system to begin health tracking.
* **FR2 Purpose:** Guarantees continuous, asynchronous health monitoring executed via background job queues (BullMQ). By automatically scheduling the next check after every completed task, it ensures non-blocking, periodic execution without impacting main application performance.
* **FR3 Purpose:** Accurately diagnoses and isolates different technical failure modes—such as timeouts, HTTP status mismatches, connection drops, and bad SSL certificates. This provides developers with clear, actionable diagnostic data whenever an endpoint fails.
* **FR4 Purpose:** Computes historical availability metrics based on standardized uptime calculation formulas and exposes them via a reporting API. This enables users and external tooling to track long-term service stability and verify Service Level Agreement (SLA) compliance.
* **FR5 Purpose:** Acts as a failure-threshold filter to absorb transient network glitches or temporary delay spikes. By delaying incident creation until consecutive failures cross a defined threshold (such as 3 consecutive fails), it prevents false alarms and noisy notifications.
* **FR6 Purpose:** Enforces state-transition alerting logic so notifications are dispatched only when an endpoint transitions between states (healthy to failing or vice versa). This prevents alert fatigue by avoiding repetitive notifications for every single failed check during an extended outage.
* **FR7 Purpose:** Integrates directly with essential communication channels (Slack, Discord, Email, Webhooks) preferred by the user. This guarantees that outage events are delivered instantly to active developer communication workflows.
* **FR8 Purpose:** Implements resilient notification delivery with exponential backoff retries (up to 3 attempts). This ensures that temporary outages in third-party notification services do not cause critical incident alerts to be lost silently.
* **FR9 Purpose:** Establishes a multi-tiered data storage structure where recent monitoring data is optimized for rapid dashboard retrieval, while older historical metrics remain accessible for long-term auditing. This balances operational speed with historical auditability.
* **FR10 Purpose:** Delivers a consolidated operational view for team leads, offering a single visual dashboard that immediately displays global system health and highlights active incidents. This reduces time-to-awareness during major infrastructure failures.
* **FR11 Purpose:** Streamlines user account creation and initial endpoint configuration through a simplified onboarding workflow. This reduces user setup friction and accelerates time-to-value for new platform adopters.
* **FR12 Purpose:** Practices standard web etiquette by enforcing rate limiting, exponential backoff on repeated failures, and proper user-agent identification. This prevents the monitoring platform from overloading monitored target APIs or getting blacklisted as abusive traffic.
* **FR13 Purpose:** Grants granular control over notification settings at both the account level and individual endpoint level. This allows teams to route alerts from specific APIs directly to responsible individuals or dedicated channels.
* **FR14 Purpose:** Automates the generation of structured monthly uptime summaries that can be downloaded or fetched via API. This simplifies compliance reporting, stakeholder communications, and periodic SLA verification.
* **FR15 Purpose:** Allows users to define scheduled maintenance windows during which health checks continue but alert creation is suppressed. This prevents false alarms and unnecessary incident records during planned system updates or server migrations.
* **FR16 Purpose:** Enables detailed content verification using text matching, regular expressions, or JSONPath expressions against response bodies. This detects "silent failures" where a compromised server returns an HTTP 200 OK code but outputs empty, corrupted, or structurally invalid payload data.
* **FR17 Purpose:** Implements Role-Based Access Control (RBAC) to grant granular permissions (e.g., Admin, Operator, Read-Only) across organization members. This secures system configurations, prevents unauthorized modifications, and ensures proper operational governance.
* **FR18 Purpose:** Provides global visibility into API performance by executing health checks from multiple geographic origin regions (e.g., US-East, EU-Central, AP-South). This enables early detection of localized network routing issues, regional CDN drops, and geo-specific outages.
