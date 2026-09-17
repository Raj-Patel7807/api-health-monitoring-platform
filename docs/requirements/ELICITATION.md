# Requirements Elicitation Plan

## 1. Purpose

This document explains how requirements will be collected for the **Distributed API Health & Incident Monitoring Platform**.

The system is mainly used by developers and people who maintain deployed APIs. Because of this, a random public survey is not suitable as the main elicitation method. Many general users have never deployed or monitored an API and may not be able to give useful answers about monitoring, incidents, retries, SSL checks, or alerting.

Our main approach is therefore:

**Targeted Interviews + Task Walkthroughs + Document Analysis + Team Requirements Workshop**

A small targeted questionnaire may be used later only to confirm patterns found during interviews.

---

## 2. Elicitation Goals

The elicitation process should help us understand:

- How developers currently check whether an API is healthy.
- What problems they face with manual monitoring.
- What information they need from a monitoring dashboard.
- How failures should be detected and reported.
- What makes an alert useful or annoying.
- What reliability, security, and performance expectations exist.
- What technical limits are imposed by external services and hosting platforms.
- Which features are important for the first version of the project.

The final output should support:

- Functional Requirements (`FR.md`)
- Non-Functional Requirements (`NFR.md`)
- Domain Requirements (`DOMAIN_REQS.md`)
- User Stories (`USER_STORIES.md`)
- EPICs and Sprints

---

## 3. Why We Are Not Using a General Public Survey

A general Google Form sent to random students would give weak results because the product is not intended for normal non-technical users.

For example, a person who has never deployed an API may not be able to answer questions such as:

- How should API failures be confirmed?
- Should a failed request be retried before creating an incident?
- What should an outage alert contain?
- How often should an endpoint be checked?
- How should authenticated endpoints be monitored?
- What information is useful during an incident?

Therefore, participants will be selected based on relevant experience.

A survey is still possible, but it should be **targeted** at people who have built, deployed, or maintained backend APIs.

---

## 4. Techniques We Will Use

| Technique                      | Main Purpose                                                                  | Used With                                                                                               |
| ------------------------------ | ----------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------- |
| Semi-structured interview      | Understand real workflows, problems, needs, and priorities                    | API developers, deployment-experienced developers, incident responders, team leads                      |
| Task walkthrough / observation | See the actual steps used to check and investigate an API                     | API developers and incident responders                                                                  |
| Document analysis              | Find technical constraints and mandatory course requirements                  | Integration services, hosting provider, target API docs, course instructions, existing monitoring tools |
| Targeted questionnaire         | Confirm common patterns with a slightly larger technical group                | Developers with API/backend/deployment experience                                                       |
| Requirements workshop          | Combine findings, remove duplicates, discuss conflicts, and check feasibility | Project development team and database administrator                                                     |
| Prototype review               | Validate dashboard layout and usability after a basic mock-up exists          | API developers and team leads                                                                           |

Not every technique must be used with every stakeholder. We use the technique that best fits the information we need.

---

## 5. Participant Selection

### 5.1 Target Participants

A realistic target for this course project is around **6 to 8 participants**.

Suggested coverage:

- At least **4 people** who have built backend APIs.
- At least **2 people** who have deployed or maintained an API.
- At least **1 person** who has handled a real service failure, deployment issue, or production-like incident.
- At least **1 person** who has maintained a project with multiple services or endpoints.

These groups may overlap. We do not need a different person for every stakeholder role.

### 5.2 Where We Can Find Participants

Possible participants include:

- Senior students with backend projects.
- Programming Club members.
- Students who completed internships.
- Alumni working in software roles.
- Teaching assistants.
- Friends or classmates who have deployed backend APIs.
- Developers known personally by team members.

### 5.3 Participant Screening

Before an interview or questionnaire, ask:

> Have you built, deployed, maintained, or monitored a backend API?

If the answer is no, the person is usually not suitable for detailed product elicitation.

### 5.4 Participant Codes

To keep records simple, participants will be stored using codes:

```text
P1
P2
P3
...
```

We do not need to publish their private information in the repository.

For each participant, record only:

- Participant code
- Date
- Relevant experience
- Stakeholder role(s) represented
- Main findings

Do not record passwords, API keys, tokens, private URLs, or company-confidential information.

---

## 6. Stakeholder–Technique Mapping

| Stakeholder                               | Primary Technique                                     | Supporting Technique                                       | Reason                                                                      |
| ----------------------------------------- | ----------------------------------------------------- | ---------------------------------------------------------- | --------------------------------------------------------------------------- |
| API Developer / API Owner                 | Interview                                             | Task walkthrough, prototype review, targeted questionnaire | They directly use the core product                                          |
| DevOps / Deployment-Experienced Developer | Interview                                             | Document analysis, workshop                                | Their experience helps with reliability and failure behaviour               |
| Incident Responder / On-call Developer    | Task walkthrough                                      | Interview, scenarios                                       | Their incident-response process is easier to understand by seeing the steps |
| Team Lead / Project Maintainer            | Interview                                             | Prototype review                                           | Their main need is service-level summary and history                        |
| Platform Administrator / Development Team | Requirements workshop                                 | Security analysis, document analysis                       | The team combines evidence and checks feasibility                           |
| Database Administrator                    | Requirements workshop                                 | Document analysis, technical testing                       | They identify database reliability, security, backup, and retention needs   |
| Notification / Integration Services       | Document analysis                                     | Integration test                                           | Their rules are defined in official API/webhook documentation               |
| Monitored API Owners / Target Services    | Interview where possible, otherwise document analysis | Scenario analysis                                          | Their limits depend on the specific target service                          |
| Course Instructor / Teaching Team         | Document analysis                                     | Clarification discussion                                   | Course requirements are already written in the project instructions         |
| Hosting / Infrastructure Provider         | Document analysis                                     | Technical testing where needed                             | Deployment limits are mainly documented by the provider                     |

---

## 7. Semi-Structured Interview Plan

### 7.1 Format

- Duration: around **15 to 25 minutes**.
- Interviewers: preferably **2 team members**.
- One person asks questions.
- One person takes notes.
- Questions are guides, not a strict script.
- Follow-up questions are allowed when an answer is useful.

The interview should focus on the participant's real experience, not on convincing them to approve features we already decided.

---

## 8. Interview Questions

### A. Current Workflow

1. Have you built or deployed a backend API before?
2. How do you currently check whether your API is working?
3. What do you usually check first when you think the API may be down?
4. Have you ever found an API failure later than you wanted? What happened?
5. Which tools do you normally use when checking a problem?

### B. Health Monitoring

6. What information is most useful when checking API health?
7. Do status code and response time give enough information, or do you normally check something else?
8. How often would you want an important API to be checked?
9. If one monitoring request fails, should the system immediately create an incident, or should it confirm the failure first?
10. Should different failures such as timeout, HTTP error, DNS error, or SSL error be shown separately?

### C. Alerts and Incidents

11. How would you prefer to receive an outage alert?
12. What information should an alert contain?
13. Should the system notify you when the API recovers?
14. What makes monitoring alerts annoying or easy to ignore?
15. If an incident is already open, should the system continue sending the same alert?

### D. Dashboard and History

16. What information would you want to see first when opening the dashboard?
17. How much previous uptime or latency history would be useful to you?
18. What should an incident-history entry contain?
19. If you monitor several APIs, what summary would help you most?

### E. Reliability, Security, and Performance

20. How quickly should the platform detect a failure for the alert to still be useful?
21. What would make you stop trusting a monitoring platform?
22. Would you have concerns about giving the platform authentication headers or credentials for a protected API?
23. Are there any API endpoints that a monitoring system should not be allowed to access?
24. What should happen if the monitoring platform itself cannot perform scheduled checks?

### F. Priority

25. If we could build only three features first, which three would be most useful?
26. Which features would be useful but not necessary for the first version?
27. Is there anything important we have not asked about?

---

## 9. Task Walkthrough / Observation

### Prompt

Ask the participant:

> Suppose one of your deployed APIs may be down right now. Show or explain the steps you would follow to confirm the problem and decide what to do next.

During the first part, let the participant explain or demonstrate the process without interrupting too much.

### Record

- Steps followed.
- Tools used.
- Information checked.
- Information that was difficult to find.
- Repeated manual steps.
- How they decide whether the failure is real.
- How they know the API has recovered.
- Information they wish had been available automatically.

### Important Rule

Do not request:

- passwords,
- private API keys,
- tokens,
- confidential URLs,
- private company data.

---

## 10. Document Analysis

Document analysis is used for requirements that come from technical rules instead of user preference.

### Sources to Study

| Source                         | What We Study                                                                           |
| ------------------------------ | --------------------------------------------------------------------------------------- |
| Course project instructions    | Mandatory SCRUM, documentation, GitHub, Slack, user-story, and elicitation requirements |
| Slack documentation            | Webhook/message format, authentication, rate-limit/error behaviour                      |
| Discord documentation          | Webhook format and message constraints                                                  |
| Email provider documentation   | Authentication, sending limits, and error behaviour                                     |
| Hosting provider documentation | Compute, database, storage, networking, background-worker, and sleep limits             |
| Target API documentation       | Authentication, rate limits, expected responses, and usage restrictions                 |
| Existing monitoring products   | Common terminology and possible features to validate with users                         |

### Important Rule About Existing Products

Existing monitoring tools are used only to learn:

- common monitoring concepts,
- common terminology,
- possible features,
- common user flows.

A feature should **not** become a final requirement only because another monitoring product has it.

---

## 11. Optional Targeted Questionnaire

The questionnaire is a **supporting technique**, not the main technique.

It should be sent only to people with backend/API/deployment experience.

A simple screening question should be placed first:

> Have you built, deployed, maintained, or monitored a backend API?

People without relevant experience should not be asked detailed monitoring questions.

The questionnaire should mainly confirm patterns already seen during interviews, for example:

- preferred alert channels,
- useful health information,
- need for recovery alerts,
- preferred history period,
- common problems with manual monitoring.

Avoid asking very technical questions that require detailed discussion, such as exact retry policies, only through multiple-choice questions.

---

## 12. Requirements Workshop

After the first interviews, observations, and document analysis, the nine-member project team will hold one requirements workshop, including database-administration input where needed.

### Workshop Goals

1. Present the collected findings.
2. Remove duplicate findings.
3. Separate facts from team assumptions.
4. Convert findings into candidate requirements.
5. Classify them as:
    - Functional Requirement
    - Non-Functional Requirement
    - Domain Requirement
6. Identify conflicts.
7. Check technical feasibility.
8. Decide what belongs in the first project scope.
9. Record the source of every accepted requirement.

### Important Rule

A user-facing requirement should have a clear source such as:

```text
P1 interview
P3 walkthrough
DOC-SLACK-01
TEAM-WORKSHOP-01
```

This gives us requirement traceability.

---

## 13. Handling Requirement Conflicts

Different stakeholders may ask for different behaviour.

Example:

- One participant may want checks every 10 seconds.
- Another may consider that too frequent.
- The hosting platform may have resource limits.

We should not simply choose one opinion.

For every important conflict, record:

| Field                    | Meaning                        |
| ------------------------ | ------------------------------ |
| Conflict ID              | Unique ID such as `C-01`       |
| Requirement / Topic      | What the disagreement is about |
| Sources                  | Who or what produced each view |
| Options Considered       | Possible solutions             |
| Decision                 | Final decision                 |
| Reason                   | Why the decision was selected  |
| Affected Requirement IDs | FR/NFR/Domain requirement IDs  |

The decision should consider user need, technical feasibility, safety, course scope, and documented external limits.

---

## 14. Elicitation Execution Order

We will follow this order:

### Step 1 — Prepare

- Finalize stakeholders.
- Select participants.
- Prepare interview questions.
- Prepare note template.

### Step 2 — Run Developer Interviews

Interview API developers and deployment-experienced developers first.

### Step 3 — Run Task Walkthroughs

Ask 2–3 suitable participants to explain or demonstrate how they investigate an API failure.

### Step 4 — Perform Document Analysis

Review:

- course instructions,
- notification-service documentation,
- hosting documentation,
- database documentation and operational constraints,
- target API rules,
- existing monitoring products.

### Step 5 — Optional Targeted Questionnaire

Use it only if we want to confirm patterns across a larger technical group.

### Step 6 — Requirements Workshop

The full team reviews evidence and creates candidate requirements.

### Step 7 — Validate Important Findings

Where needed:

- show a simple dashboard prototype,
- run an integration test,
- ask a short follow-up question.

### Step 8 — Write Final Requirement Documents

Update:

```text
FR.md
NFR.md
DOMAIN_REQS.md
USER_STORIES.md
```

Only after the elicitation evidence is available.

---

## 15. Evidence We Will Keep

To show that the techniques were actually applied, the repository should contain an `ELICITATION_RESULTS.md` file with:

- participant codes,
- dates,
- represented stakeholder roles,
- interview findings,
- observation findings,
- document-analysis findings,
- workshop decisions,
- requirement-source mapping,
- conflict-resolution records.

Screenshots or raw private notes do not need to be public if they contain personal or confidential information.

---

## 16. What We Should Avoid

We should **not**:

- Send a random technical survey to people who have no API experience.
- Create fake interview results.
- Call someone an SRE/DevOps engineer if that is not their real background.
- Treat features from another monitoring product as our requirements without validation.
- Decide exact retry counts, monitoring intervals, retention periods, or alert-delay targets before we have evidence.
- Store interviewees' confidential credentials or company information.
- Let the development team replace user feedback with its own assumptions.

---

## 17. Expected Output

After completing this plan, we should be able to show a clear chain:

```text
Stakeholder
    ↓
Elicitation Technique
    ↓
Collected Finding / Evidence
    ↓
FR / NFR / Domain Requirement
    ↓
User Story + Acceptance Criteria
    ↓
EPIC
    ↓
Sprint
```

This makes the requirement process easy to explain during review, viva, and final presentation.
