# Distributed API Health & Incident Monitoring Dashboard

A course project for monitoring API endpoints, recording health results, opening confirmed incidents, and sending useful alerts. It is a modular monolith: one FastAPI service, a React web app, PostgreSQL, Redis, and separate Celery worker processes.

Accounts, team roles, monitors, check history, incident tracking, the dashboard, and incident notifications are implemented. The platform also includes API documentation import (`api.md` or OpenAPI JSON/YAML) with SSRF-safe candidate extraction, and advisory AI-powered incident assistance with root-cause analysis and remediation steps.

When you sign in, the browser remembers your session for that site. Reopening the same address in the same browser profile takes you to the dashboard. By default the app renews a 15-minute access token using a refresh token valid for seven days after sign-in or the last successful renewal. Choose **Log out** to end the session in that browser.

## Quick start

Install Docker with Compose and Python 3. From the repository root, generate independent local signing and encryption keys once, then start the stack. Keep the generated `.env` for subsequent starts. For an existing database, reuse its encryption and signing keys.

```bash
python scripts/init_env.py
docker compose up --build
```

Open `http://localhost:5173`. The API health check is at `http://localhost:8000/health` and API documentation is at `http://localhost:8000/docs`.

For host-based development, copy the generated root `.env` to `backend/.env`, and install Node.js 22 and uv. Run `cd backend && uv sync` then `uv run uvicorn app.main:app --reload`, and `cd frontend && npm ci && npm run dev`.

## Deploy to Vercel

Link the repository root to one Vercel project. The root `vercel.json` routes the dashboard and API on the same domain. In the project's Production environment, set `DATABASE_URL` to the Aiven PostgreSQL URI using `postgresql+psycopg://`, and reuse the deployment's `ENCRYPTION_KEY` and `JWT_SECRET_KEY`. Enter these as server-side sensitive variables. The frontend build uses relative API URLs. For a new release with database changes, apply `alembic upgrade head` to the target database before promoting the release.

```powershell
npx vercel login
npx vercel link
npx vercel deploy --prod
```

Check `/health`, open `/login` and sign in with an existing account. Set the Production `REDIS_URL` to the broker’s TCP connection URL for scheduled checks and alerts. The deployment runs one Celery worker and one Beat scheduler in `iad1`. When moving from a local stack, stop the local Beat scheduler at cutover so only one scheduler queues checks.

## Checks

```bash
cd backend
uv run ruff format --check .
uv run ruff check .
uv run mypy app
uv run pytest tests/unit --cov=app --cov-fail-under=80
```

```bash
cd frontend
npm run format:check
npm run lint
npm run typecheck
npm run test
npm run build
```

New monitors default to a 30-second schedule and open an incident after three consecutive failures. The scheduler polls every 10 seconds. During normal operation, the next check stays on its planned schedule even if the previous probe took several seconds. Queue and network latency can shift individual completion times. Exponential backoff starts at confirmation. Existing monitor intervals are preserved.

For database integration tests, start disposable PostgreSQL with pgvector and a Redis broker, apply `uv run alembic upgrade head` with `DATABASE_URL` and `REDIS_URL` set, then run `uv run pytest tests/integration`. CI sets this up automatically.

Read `AGENT.md` before contributing. The design, configuration, tests, and sprint plan are in `docs/`.
