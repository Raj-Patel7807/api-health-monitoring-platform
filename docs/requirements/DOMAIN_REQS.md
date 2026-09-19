# Domain Requirements (DR)

## 1. Definition and Purpose

**Definition:** Domain Requirements (DR) define constraints, specialized formulas, business rules, and operational conventions derived directly from the underlying domain—in this case, API monitoring and agile software execution—rather than from general user feature requests.

**Overall Purpose:** The primary purpose of domain requirements is to embed industry-standard domain knowledge, network protocols, mathematical formulas, and project management practices directly into the application and its development process. Specifically, they serve to:
* **Ensure Industry-Standard Integrity:** Align calculation methods (like uptime percentages) with recognized monitoring industry formulas.
* **Guarantee Network Courtesy & Compliance:** Embed web etiquette rules to protect system reputation and prevent target API blocks.
* **Filter Transient False Positives:** Incorporate domain-specific network understanding into incident management logic to handle transient internet glitches gracefully.
* **Standardize Governance & Delivery:** Maintain formal Agile requirements structuring and systematic conflict resolution across all development sprints.

---

## 2. Domain Requirements List

| ID | Requirement |
| :--- | :--- |
| **DR1** | Since this is a monitoring system, all health checks must run in the background (through the job queue) and must never block or slow down the main user-facing part of the app. |
| **DR2** | All communication with endpoints and between system parts must follow standard HTTP/HTTPS rules, and TLS 1.3 must be used wherever data is sent over the network. |
| **DR3** | Uptime percentage must be calculated using the standard formula used across the monitoring industry: (Total Time - Downtime) / Total Time x 100. |
| **DR4** | Checking someone else's API again and again is a sensitive thing to do. The system must follow general web etiquette (reasonable intervals, backoff on repeated failure) so that our platform's IP does not get blocked. |
| **DR5** | Because failures on the internet are sometimes just a temporary blip (a slow network, a one-off timeout), the system must not treat a single failed check as a real incident. |
| **DR6** | Project requirements must be structured into user stories featuring both a front (role, goal, benefit) and a back (acceptance criteria), grouped into EPICs, and organized into Sprints. |
| **DR7** | Conflicting requirements across stakeholders or EPICs must be formally identified and their resolutions documented. |

---

## 3. Requirement Purposes

* **DR1 Purpose:** Enforces strict architectural separation by executing monitoring tasks asynchronously in job queues, ensuring the core user interface and API server remain fast, responsive, and unaffected by heavy background monitoring traffic.
* **DR2 Purpose:** Mandates standardized protocol adherence and TLS 1.3 encryption across all network communication paths to ensure data privacy, payload integrity, and compliance with web security standards.
* **DR3 Purpose:** Aligns system availability metrics with the industry-standard formula `(Total Time - Downtime) / Total Time x 100`, delivering uniform, trustworthy, and audit-ready uptime metrics across dashboard and reporting channels.
* **DR4 Purpose:** Embeds responsible probing behaviors (configurable intervals, automatic backoff during outages, proper User-Agent headers) to avoid overloading target servers and prevent system probe IP addresses from being blacklisted.
* **DR5 Purpose:** Incorporates fundamental network domain knowledge into incident creation logic, filtering out transient network anomalies or single-second timeouts so teams are alerted only to genuine, confirmed outages.
* **DR6 Purpose:** Guarantees that product specifications are formatted using formal Agile user story templates (Role-Goal-Benefit and Backing Acceptance Criteria), organized systematically into EPICs and Sprints for efficient engineering execution.
* **DR7 Purpose:** Establishes a formal process to identify, document, and resolve conflicting stakeholder expectations or requirement overlaps, maintaining structural clarity and preventing scope drift throughout the development lifecycle.
