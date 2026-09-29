# Roadmap

No calendar dates are set. The sequence follows dependencies and MoSCoW priority from the requirements.

| Phase | Scope | Depends on |
| --- | --- | --- |
| Foundation | Repository, local stack, CI, data and worker foundation, secure configuration (`US-17`, `US-21`, `US-25`) | None |
| Core monitoring | Onboarding, endpoint registration, scheduling, responsible checks, detection, result storage (`US-01`, `US-02`, `US-05`, `US-06`, `US-08`, `US-16`) | Foundation |
| Incidents and alerts | Notification configuration, threshold incidents, state changes, alerts (`US-03`, `US-09`–`US-11`) | Core monitoring |
| Dashboard and access | Dashboard, RBAC, uptime history, and maintenance windows (`US-13`, `US-19`, `US-14`, `US-04`) | Stored results and security |
| Should Have | Assertions, retries, audit, and scale (`US-07`, `US-12`, `US-18`, `US-22`) | Core capabilities |
| Data retention and Could Have | Daily rollups, monthly reports, multi-region probes (`US-24`, `US-15`, `US-20`) | History and incident data |
| Hardening and demo | Security review, performance checks, accessibility, documentation, demo | All selected scope |

Must Have work is prioritized before Should Have and Could Have work. Advanced AI work remains advisory and asynchronous.

