# Stakeholders

## 1. Purpose

This document identifies the main stakeholders of the **Distributed API Health & Incident Monitoring Platform**.

The platform is mainly used by technical users who build, deploy, maintain, or monitor APIs. Because of this, stakeholder identification focuses on people and third parties that directly use the platform, depend on its output, are affected by its monitoring traffic, or define important project constraints.

> A single person may represent more than one stakeholder role.  
> For example, a backend developer may also deploy the API and respond to incidents.

---

## 2. Stakeholder Groups

We divide the stakeholders into four groups:

1. **Primary users** — people who directly use the monitoring platform.
2. **Secondary and internal stakeholders** — people who use summaries, manage the platform, or build it.
3. **External third parties** — services or organizations that the platform depends on or affects.
4. **Course/process stakeholders** — people who define mandatory project-process requirements.

---

## 3. Stakeholder Summary

| ID  | Stakeholder                                       | Type                     | Main Relationship with the System                                                       | Priority                |
| --- | ------------------------------------------------- | ------------------------ | --------------------------------------------------------------------------------------- | ----------------------- |
| S1  | API Developer / API Owner                         | Primary user             | Registers APIs, checks health, views history, receives alerts                           | High                    |
| S2  | DevOps / Deployment-Experienced Developer         | Primary/advanced user    | Focuses on reliability, failures, retries, deployment behaviour, and monitoring quality | High                    |
| S3  | Incident Responder / On-call Developer            | Primary operational user | Receives alerts and investigates failures                                               | High                    |
| S4  | Team Lead / Project Maintainer                    | Secondary user           | Wants a quick overview of service health and incidents                                  | Medium                  |
| S5  | Platform Administrator / Project Development Team | Internal stakeholder     | Builds, deploys, configures, secures, and maintains the platform                        | High                    |
| S6  | Notification and Integration Services             | External third party     | Receives alert requests from the platform, such as Slack, Discord, email, or webhooks   | Medium                  |
| S7  | Monitored API Owners / Target Services            | External affected party  | Receives repeated monitoring requests from the platform                                 | Medium                  |
| S8  | Hosting / Infrastructure Provider                 | External dependency      | Provides compute, database, storage, networking, and background-worker support          | Medium                  |
| S9  | Course Instructor / Teaching Team                 | Process stakeholder      | Defines required software-engineering process and project deliverables                  | High for course process |

Priority means how strongly the stakeholder affects the product or the course process. It does **not** mean that lower-priority stakeholders are ignored.

---

## 4. Detailed Stakeholder Analysis

### S1. API Developer / API Owner

**Who they are:**  
A developer or team that owns an API and wants to know whether it is working correctly.

**How they interact with the platform:**

- Register an API endpoint.
- Configure monitoring settings.
- View current health and previous check results.
- View uptime and latency information.
- Receive failure and recovery alerts.

**Main needs to investigate during elicitation:**

- What information they need to define a healthy API.
- How often they expect an endpoint to be checked.
- What information they want on the dashboard.
- What kind of alerts they want.
- How much history is useful.
- How authenticated endpoints should be handled safely.

**Why this stakeholder is important:**  
This is the main end-user group. Their workflow defines the core product.

---

### S2. DevOps / Deployment-Experienced Developer

**Who they are:**  
A person who has experience deploying and maintaining backend applications or APIs.

A formal job title such as "DevOps Engineer" or "SRE" is **not required**. For this student project, a senior, intern, alumnus, or backend developer with real deployment experience can represent this role.

**How they interact with the platform:**

- Monitor multiple deployed endpoints.
- Review failures and reliability information.
- Help define reasonable retry, timeout, and monitoring behaviour.

**Main needs to investigate during elicitation:**

- When a failed check should become an incident.
- Whether failed checks should be retried.
- Which failure types should be shown separately.
- How to avoid unnecessary or duplicate alerts.
- What SSL certificate information is useful.
- What monitoring frequency is reasonable.

**Why this stakeholder is important:**  
They can provide practical feedback about real deployment failures and false alerts.

---

### S3. Incident Responder / On-call Developer

**Who they are:**  
The person who reacts when an API or service fails.

In a small team, this may be the same person as the API owner, but the role is kept separate because their needs are different during an incident.

**How they interact with the platform:**

- Receive an incident alert.
- Check what failed and when it failed.
- Investigate the problem.
- Check whether the service has recovered.
- Review incident history.

**Main needs to investigate during elicitation:**

- What information an alert must contain.
- What information is needed before investigation starts.
- Whether duplicate alerts are useful or annoying.
- Whether a recovery alert is required.
- What information should appear in incident history.

**Why this stakeholder is important:**  
Alerts are only useful if they help someone understand and act on a problem quickly.

---

### S4. Team Lead / Project Maintainer

**Who they are:**  
A person responsible for a project or a group of services.

**How they interact with the platform:**

- View the overall health of several APIs.
- Review uptime and incident history.
- Check which services have frequent problems.

**Main needs to investigate during elicitation:**

- What summary information is useful.
- What time period should be shown.
- What information should be visible without opening every endpoint separately.

**Why this stakeholder is important:**  
They help define summary and reporting needs, but they do not define the core monitoring flow.

---

### S5. Platform Administrator / Project Development Team

**Who they are:**  
The nine-member project team that develops and operates the platform.

For this project, the team is also responsible for deploying and maintaining the system.

**Responsibilities:**

- Build and test the platform.
- Maintain monitoring workers and scheduled jobs.
- Manage deployment and configuration.
- Protect stored secrets and credentials.
- Handle errors and logs.
- Keep data growth under control.
- Make sure monitoring jobs are actually running.

**Important areas to analyse:**

- Authentication and authorization.
- Secure storage of secrets.
- Validation of user-supplied URLs.
- Background-worker failures.
- Logging and error handling.
- Database growth and data retention.
- Deployment limits.

**Important note:**  
The project team should not invent user requirements only from its own assumptions. User-facing requirements should first be supported by interviews, observation, or other evidence.

---

### S6. Notification and Integration Services

**Examples:**

- Slack
- Discord
- Email provider
- Generic webhook receiver

**Relationship with the platform:**  
The platform sends alert messages to these services.

**Main constraints to study:**

- Required payload format.
- Authentication or webhook URL format.
- Rate limits.
- Error responses.
- Retry behaviour.
- Security of tokens and webhook URLs.

**How requirements will be collected:**  
Mainly through official documentation and small integration tests.

---

### S7. Monitored API Owners / Target Services

**Who they are:**  
The APIs being monitored and the people or teams that own them.

**Relationship with the platform:**  
The monitoring system repeatedly sends requests to their APIs.

**Important concerns to investigate:**

- Monitoring should not create unnecessary load.
- Timeouts should be reasonable.
- Rate-limit responses should be handled correctly.
- Authentication may be required.
- Custom request headers may be required.

**How requirements will be collected:**

- Interview the owner when they are available.
- Otherwise, use the target API's documentation.

---

### S8. Hosting / Infrastructure Provider

**Examples:**  
The service used to host the frontend, backend, background workers, database, or storage.

**Relationship with the platform:**  
Its limits affect how the system can be deployed and operated.

**Important constraints to study:**

- CPU and memory limits.
- Background-worker support.
- Database and storage limits.
- Network limits.
- Idle/sleep behaviour.
- Deployment restrictions.

**How requirements will be collected:**  
Through official provider documentation.

---

### S9. Course Instructor / Teaching Team

**Who they are:**  
The faculty or teaching team responsible for the Software Engineering course.

**Relationship with the project:**  
They are not normal users of the monitoring platform, but they define mandatory project-process requirements.

**Important requirements from this stakeholder include:**

- Follow Agile/SCRUM.
- Identify stakeholders and end users.
- Select and justify elicitation techniques.
- Actually apply the elicitation techniques.
- Collect functional, non-functional, and domain requirements.
- Write user stories with acceptance criteria.
- Organize work into EPICs and Sprints.
- Identify and resolve requirement conflicts.
- Use GitHub for development.
- Use Slack for project communication.

**How requirements will be collected:**  
Mainly through document analysis of the official project instructions. Direct clarification can be requested if any instruction is unclear.

---

## 5. Stakeholder Priority

### High Priority

- API Developer / API Owner
- DevOps / Deployment-Experienced Developer
- Incident Responder / On-call Developer
- Platform Administrator / Project Development Team

These stakeholders directly affect the main monitoring and incident-management flow.

The Course Instructor / Teaching Team is also high priority for **project-process requirements**, but does not decide normal product features.

### Medium Priority

- Team Lead / Project Maintainer
- Notification and Integration Services
- Monitored API Owners / Target Services
- Hosting / Infrastructure Provider

These stakeholders affect important but more focused areas such as reporting, integrations, monitoring traffic, and deployment constraints.

---

## 6. Important Assumptions

- One participant may represent multiple stakeholder roles.
- We will record the participant's real experience instead of assigning a job title they do not have.
- Existing monitoring products are **not stakeholders**. They are sources used during document analysis.
- External services such as Slack or hosting providers are treated as external third parties that impose technical constraints.
- Exact values such as retry count, check interval, alert delay, and data-retention period should not be treated as final until they are supported by elicitation, technical testing, or documented infrastructure limits.

---

## 7. Related Documents

The following repository documents are connected to this stakeholder analysis:

- `ELICITATION.md` — techniques, participant plan, interview questions, and execution process.
- `ELICITATION_RESULTS.md` — actual evidence collected from interviews, observation, documents, and workshops.
- `FR.md` — final functional requirements.
- `NFR.md` — final non-functional requirements.
- `DOMAIN_REQS.md` — final domain requirements.
- `USER_STORIES.md` — user stories and acceptance criteria.

The expected flow is:

```text
STAKEHOLDERS.md
        ↓
ELICITATION.md
        ↓
ELICITATION_RESULTS.md
        ↓
FR.md + NFR.md + DOMAIN_REQS.md
        ↓
USER_STORIES.md
        ↓
EPICs and Sprints
```
