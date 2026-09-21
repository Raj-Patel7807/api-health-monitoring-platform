# Code Rules

## Core ideas

**No code is better than unnecessary code.**

**Ten clear lines are better than fifty clever lines.**

**Use a trusted library for a solved problem, but not for something trivial.**

Use KISS (keep it simple) and YAGNI (build only what is needed now). Use DRY carefully. Two repeated lines do not always need an abstraction.

## General rules

Use meaningful names, small focused functions and modules, clear responsibilities, explicit types, and clear input/output contracts. Validate early and handle errors explicitly. Do not silently swallow exceptions, keep hidden mutable global state, use unexplained business numbers, duplicate business logic, leave dead or commented-out code, commit debug prints, secrets, or production URLs.

Use UTC timestamps. Make retryable worker tasks idempotent where needed. Use safe retry limits and database transactions for work that must succeed together. Services and workers should shut down cleanly. Use useful structured logging, but never log passwords, tokens, keys, webhook URLs, authorization headers, or private response bodies.

Comments explain why, a rule, or a non-obvious edge case; they do not restate syntax. Add docstrings when a public module, class, or function needs a clearer contract.

## Python

Use Ruff formatting and linting, mypy, type hints at public and important internal boundaries, Pydantic for request, response, and configuration validation, SQLAlchemy 2.x style, and Alembic for schema changes. Prefer FastAPI dependency injection over hidden globals. Keep routes thin and put feature behavior in a feature module when it is added. Use HTTPX with explicit timeouts for outbound checks. Celery tasks must name their queue and must not own permanent business truth.

## TypeScript and React

Use TypeScript strict mode. Keep components small and accessible. Use React Router for pages and TanStack Query for server state when API-backed pages are added. Use native `fetch` through one small API helper. Validate uncertain external data with Zod where useful. Do not keep server data in unrelated client state. Use semantic HTML, visible focus states, labels, keyboard support, and meaningful error states.

## API and data

Use `/api/v1` for product endpoints and keep `/health` small. Return documented error shapes. Validate input at the API boundary. Database changes require a committed Alembic migration; do not edit shared migrations. PostgreSQL is the source of truth. Redis is for queues, locks, caches, and short-lived coordination only. Never let an LLM decide health, incidents, or uptime.

## Quality gate

Run formatter, lint, type checks, tests, and the relevant build before committing. Update docs for behavior, schema, configuration, architectural, and deployment changes.
