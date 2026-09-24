# Decisions

| ID | Date | Decision | Reason | Status |
| --- | --- | --- | --- | --- |
| D-001 | 2026-09-22 | Use a monorepo. | The course team can find web, API, docs, and infrastructure in one place. | Accepted |
| D-002 | 2026-09-22 | Use React, TypeScript, and Vite. | A small typed web foundation with low setup cost. | Accepted |
| D-003 | 2026-09-22 | Use FastAPI with Python. | It is the approved backend stack. | Accepted |
| D-004 | 2026-09-22 | Use PostgreSQL with pgvector. | One durable source of truth and future embedding storage. | Accepted |
| D-005 | 2026-09-22 | Use Redis with Celery and Celery Beat. | Background checks need queue workers and scheduling (`DR1`). | Accepted |
| D-006 | 2026-09-22 | Start as a modular monolith with separate workers. | It is simpler than microservices and can scale workers independently. | Accepted |
| D-007 | 2026-09-22 | Use SQLAlchemy and Alembic. | Typed ORM access and tracked schema changes. | Accepted |
| D-008 | 2026-09-22 | Use uv for Python and npm for frontend packages. | Both give repeatable lockfile-based installs. | Accepted |
| D-009 | 2026-09-22 | Use Docker Compose, GitHub Actions, and GHCR. | Local stack, automated checks, and container delivery without choosing hosting. | Accepted |
| D-010 | 2026-09-22 | Make LLM work advisory and asynchronous. | Deterministic code remains responsible for health, incidents, and uptime. | Accepted |
| D-011 | 2026-09-22 | Do not add an AI service or vector database yet. | The modular monolith and pgvector meet current needs. | Accepted |
| D-012 | 2026-09-22 | Use deterministic monitoring rules. | This protects `FR3`–`FR6` and `DR3`–`DR5`. | Accepted |
| D-013 | 2026-09-22 | Use Celery instead of BullMQ wording in `FR2`. | The approved Python backend uses Celery + Redis. Required behavior remains asynchronous monitoring. | Accepted — `FR.md` aligned 2026-09-24 |
| D-014 | 2026-09-24 | Remove NFR13 (worker failover) and US-23. | NFR13's 10-second standby-worker SLA is infrastructure-heavy for a course project. Worker resilience relies on Celery's built-in queue durability and idempotent tasks. US-23 lost its primary source requirement. | Accepted |
| D-015 | 2026-09-24 | Rebalance sprint plan from 7 sprints to 6. | Sprint load was uneven (13–34 pts). Moved US-08 to Sprint 3, pulled US-14 and US-04 into Sprint 4, moved US-22 to Sprint 5, and merged Could Have work into Sprint 6. Average load is now ~25 pts/sprint. | Accepted |

Add a short row for every future major architecture or technology decision.
