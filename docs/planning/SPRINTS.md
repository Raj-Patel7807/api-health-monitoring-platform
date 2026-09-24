# Sprint Plan

The project follows Scrum. Sprint length and dates are agreed by the team, so none are invented here. `US-25` is continuous governance work in every sprint. Total planning uses the source values (152 points) after removing US-23 (worker failover, 8 points) with NFR13.

| Sprint | Goal | Stories | Points | Demo / dependency |
| --- | --- | --- | ---: | --- |
| 1 | Establish a safe foundation. | US-17, US-21, US-25 | 21 | Local stack and CI; no product feature claim. |
| 2 | Register and run a basic monitored endpoint. | US-01, US-02, US-05, US-06, US-08, US-16 | 34 | Monitor-and-record loop; depends on Sprint 1. |
| 3 | Confirm incidents and notify users. | US-03, US-09, US-10, US-11 | 29 | One useful alert per state transition; depends on Sprint 2. |
| 4 | Provide visibility and access control. | US-13, US-19 | 13 | Dashboard and protected team actions; depends on results/security. |
| 5 | Add selected refinements. | US-04, US-07, US-12, US-14, US-18 | 29 | Maintenance, assertions, retries, history, audit. |
| 6 | Improve resilience and retention. | US-22, US-24 | 16 | Scale/rollup evidence. |
| 7 | Consider Could Have work and harden demo. | US-15, US-20 | 13 | Only if Must/Should scope is stable. |

The displayed points are planning capacity signals, not a promise. Split work if measured team velocity needs it. Each sprint goal needs a usable increment where practical.

## Definition of Done

- Acceptance criteria are satisfied.
- Code is reviewed through a pull request.
- Relevant tests are added and pass.
- Lint, type checks, and CI are green.
- Documentation is updated.
- There is no known critical bug.
- The change is merged through the approved process.
