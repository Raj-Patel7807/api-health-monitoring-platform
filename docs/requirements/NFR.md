# Non-Functional Requirements (NFR)

## 1. Definition and Detailed Purpose

**Definition:** Non-Functional Requirements (NFR) define how the system operates, specifying quality attributes, performance bounds, security constraints, reliability thresholds, and operational standards rather than specific end-user features.

**Overall Purpose:** The primary purpose of non-functional requirements is to establish the operational constraints, quality standards, performance metrics, and governance processes that govern how the platform behaves under load, recovers from failure, protects data, and maintains long-term sustainability. Specifically, they serve to:
* **Define Quality & Performance Benchmarks:** Specify acceptable thresholds for system latency, response times, throughput, and operational efficiency under varying loads.
* **Ensure Reliability & Resiliency:** Mandate high-availability structures and data protection mechanisms to maintain uninterrupted service.
* **Protect System Security & Compliance:** Guarantee data privacy through strict encryption standards, tamper-proof logging, and vulnerability prevention.
* **Guide System Process & Development Governance:** Align team development practices with established software engineering methodologies, structured source control, and centralized communication workflows.

---

## 2. Non-Functional Requirements List

| ID | Requirement |
| :--- | :--- |
| **NFR1** | System should detect a failure within 2 minutes for 95 out of 100 incidents, checked over the last 30 days. |
| **NFR2** | Looking up recent data (last 30 days) should take under 5 seconds. Looking up older, archived data can take up to 5 minutes. |
| **NFR3** | At least 99 out of 100 webhook/notification deliveries should succeed, and they should be acknowledged within 5 seconds. |
| **NFR4** | No monitoring data should be deleted. Recent data (30 days) must load fast, and older data must still be reachable, just a bit slower. |
| **NFR5** | All stored data must be encrypted (AES-256) and all data sent over the network must use TLS 1.3. |
| **NFR6** | Over any 12-month period, there should be zero critical or high severity security incidents, and the system should pass all required compliance checks. |
| **NFR7** | At least 90 out of 100 alerts sent should be real, actionable problems, and the average time to resolve them should be under 30 minutes. |
| **NFR8** | Cost of running one health check should stay under $0.01 for 95% of checks, helped by auto-scaling of resources. |
| **NFR9** | Signing up and adding the first endpoint should take under 5 minutes. The dashboard should load in under 3 seconds. |
| **NFR10** | System should be able to grow to support 200 active users in 3 months, keep user drop-off (churn) under 5%, and keep satisfaction rating at 4.5 out of 5 or higher. |
| **NFR11** | Health-check requests sent to other people's APIs should be rate-limited and configurable, so our platform is not seen as abusive traffic. |
| **NFR12** | The whole system should be easy to deploy and maintain within whatever hosting setup (compute, database, storage, background workers) we finally choose. |

| **NFR14** | Smart Storage vs. Infinite Retention (Data Retention): Roll up old minute-by-minute data into daily summaries. |
| **NFR15** | Tamper-Proof Audit Logging: Strict operational traceability for configuration changes. |
| **NFR16** | Process: The project development must strictly follow the Agile (SCRUM) methodology. |
| **NFR17** | Process: All development must occur on GitHub, with commits reflecting actual individual contribution. |
| **NFR18** | Process: All team communication, discussions, decisions, and updates must happen over Slack. |

---

## 3. Elaborated Requirement Purposes

* **NFR1 Purpose:** Ensures rapid failure detection so that developers and incident responders are alerted to outages almost immediately, minimizing mean time to detect (MTTD) during system downtime.
* **NFR2 Purpose:** Balances fast database performance for active daily operations with cost-effective long-term data archiving strategies, ensuring active screens remain responsive.
* **NFR3 Purpose:** Guarantees high notification delivery reliability and low-latency acknowledgment so on-call personnel are promptly notified without dropping or delaying critical incident alerts.
* **NFR4 Purpose:** Enforces permanent data preservation and structured retrieval speed, allowing compliance audits and historic trend analyses without degrading active dashboard responsiveness.
* **NFR5 Purpose:** Protects sensitive system data, database records, and user endpoint credentials against unauthorized interception or breach by enforcing industry-standard encryption in transit and at rest.
* **NFR6 Purpose:** Ensures systemic operational integrity, legal compliance, and customer trust by maintaining a zero-vulnerability security baseline across annual operation cycles.
* **NFR7 Purpose:** Maintains high alert accuracy and actionability, reducing alert fatigue among incident responders and driving faster average resolution times (MTTR).
* **NFR8 Purpose:** Controls platform operational overhead through dynamic resource auto-scaling, ensuring health monitoring remains financially sustainable and cost-efficient as scale grows.
* **NFR9 Purpose:** Delivers an effortless user experience with sub-3-second load times and fast onboarding to drive user adoption, retention, and satisfaction.
* **NFR10 Purpose:** Ensures platform scalability, user retention, and customer satisfaction goals are met as the user base expands over initial deployment quarters.
* **NFR11 Purpose:** Establishes responsible outbound traffic behavior to prevent target host throttling, IP blacklisting, or unintentional Denial of Service (DoS) conditions on monitored APIs.
* **NFR12 Purpose:** Promotes maintainability and infrastructure flexibility across varied deployment targets (cloud compute, containers, managed databases) to simplify DevOps management and upgrades.

* **NFR14 Purpose:** Optimizes database storage utilization over time by aggregating granular minute-by-minute metrics into daily rollups, preserving storage capacity while maintaining infinite retention.
* **NFR15 Purpose:** Guarantees strict operational accountability and security auditability by maintaining non-rewritable, tamper-proof event logs for all administrative actions and configuration updates.
* **NFR16 Purpose:** Standardizes the software development lifecycle using structured Agile (SCRUM) iterations to ensure consistent project velocity, predictability, and team coordination.
* **NFR17 Purpose:** Ensures code transparency, clean version control management, and verifiable individual developer accountability throughout the shared GitHub repository.
* **NFR18 Purpose:** Streamlines team communication, centralizes architectural decision-making, and maintains transparent project updates across all project members through dedicated Slack channels.
