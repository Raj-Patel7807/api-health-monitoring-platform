# Testing Strategy

Tests must be deterministic, isolated, and independent of order. Do not use real paid or external APIs. Avoid `sleep()` when a controlled clock or polling assertion can be used. Coverage is a signal, not a reason to write empty tests. The initial backend coverage target is 80% for application code.

## Backend

Use unit tests for pure logic and service behavior. Use integration tests for repositories, PostgreSQL, Redis, API boundaries, and Celery tasks. Test retries and idempotency. Use fake notification and LLM providers. Test failure thresholds, state transitions, and recovery.

Monitoring tests must cover HTTP 200, wrong status, timeout, connection or DNS failure, SSL failure or expiry, response-body assertions, one transient failure, threshold incident creation, duplicate-alert prevention, recovery, maintenance windows, notification retry/final failure, rate limiting, uptime, monthly reports, RBAC, audit logs, worker restart/failover, and an unavailable AI provider while monitoring continues.

## Frontend

Use Vitest and Testing Library for components, hooks, utilities, routes, and mocked API states. Use Playwright for a small smoke or critical-flow test when the environment can run it. Do not call a live backend in unit tests.

## Commands

Backend: `uv sync --frozen`, `uv run ruff format --check .`, `uv run ruff check .`, `uv run mypy app`, and `uv run pytest --cov=app --cov-report=term-missing`.

Frontend: `npm ci`, `npm run format:check`, `npm run lint`, `npm run typecheck`, `npm run test`, and `npm run build`.

Use `docker compose config` for compose validation. Integration CI starts PostgreSQL and Redis before migration and integration checks.
