# Architecture

## Overview

The project is a modular monolith. It has one FastAPI API, one React web app, PostgreSQL, Redis, and separate Celery worker and scheduler processes. This supports `DR1` without introducing microservices too early.

```text
React web app -> FastAPI API -> PostgreSQL + pgvector
                         -> Redis <- Celery worker / Celery Beat
Celery worker -> monitored endpoint / notification provider / later LLM provider
```

PostgreSQL stores durable product facts: users, monitors, health results, incidents, alert deliveries, configuration, audit records, and later AI analysis. pgvector stays in PostgreSQL for later embeddings. Redis holds queue messages, short-lived coordination, locks, and justified cache data. It is never the only copy of important domain data.

## Module boundaries

`app/api` owns HTTP boundaries. `app/core` owns configuration, logging, and cross-cutting error handling. `app/db` owns database setup and migrations. Future `app/modules/<feature>` folders own each domain's router, schemas, service, repository, and models where useful. `app/integrations` will hold HTTP, notification, and LLM providers. `app/workers` owns Celery setup and tasks.

Workers use logical queues: `monitoring`, `notifications`, `ai`, and `maintenance`. Beat schedules work; workers perform it. Deterministic code evaluates status, timeout, SSL, assertions, failure thresholds, incidents, and uptime. AI receives small structured incident context through the `ai` queue and returns validated advisory text only. It never decides monitoring truth.

## Scaling later

Scale the API and worker processes independently. Add worker replicas and queue-specific concurrency before considering separate services. PostgreSQL indexes and rollups support recent and historical queries. Worker resilience relies on Celery's built-in queue durability and idempotent tasks; standby-worker high-availability is out of scope for this project.

## Health

`/health` is a liveness endpoint and must not fail because an LLM, notification provider, database, or Redis is temporarily unavailable. A future `/ready` endpoint may check dependencies for traffic readiness.
