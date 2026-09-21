# Distributed API Health & Incident Monitoring Dashboard

A course project for monitoring API endpoints, recording health results, opening confirmed incidents, and sending useful alerts. It is a modular monolith: one FastAPI service, a React web app, PostgreSQL, Redis, and separate Celery worker processes.

The repository currently provides a runnable foundation. Product features such as accounts, endpoint registration, incident rules, and notifications are planned work; they are not claimed as complete here.

## Quick start

Install Docker, Docker Compose, Node.js 22, and [uv](https://docs.astral.sh/uv/). Copy `backend/.env.example` to `backend/.env` and `frontend/.env.example` to `frontend/.env` if local overrides are needed.

```bash
docker compose up --build
```

Open `http://localhost:5173`. The API health check is at `http://localhost:8000/health` and API documentation is at `http://localhost:8000/docs`.

For host-based development, use `cd backend && uv sync` then `uv run uvicorn app.main:app --reload`, and `cd frontend && npm ci && npm run dev`.

## Checks

```bash
cd backend
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run pytest --cov=app
```

```bash
cd frontend
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run build
```

Read `AGENT.md` before contributing. The design, configuration, tests, and sprint plan are in `docs/`.
