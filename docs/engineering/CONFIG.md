# Configuration

Use local, test, staging, and production environments. `.env.example` files contain names and safe examples only. Never commit real keys or passwords.

## Current backend variables

| Variable | Secret | Default / purpose |
| --- | --- | --- |
| `APP_ENV` | No | `development`; environment name. |
| `LOG_LEVEL` | No | `INFO`; application log level. |
| `CORS_ORIGINS` | No | `http://localhost:5173`; comma-separated browser origins. |
| `DATABASE_URL` | Yes | PostgreSQL connection URL. |
| `REDIS_URL` | Yes in production | Redis broker and result backend URL. |
| `LLM_ENABLED` | No | `false`; keeps the optional AI capability disabled. |

## Planned variables

`LLM_PROVIDER`, `LLM_API_KEY`, notification provider settings, SMTP credentials, and deployment settings will be added with their features. They must be documented before use. LLM and notification secrets must never appear in logs.

## Local stack and CI

Docker Compose supplies PostgreSQL with pgvector and Redis. The backend and worker use the same `DATABASE_URL` and `REDIS_URL`. The frontend uses `VITE_API_BASE_URL`, defaulting to `http://localhost:8000`. GitHub Actions reads repository secrets only when a later deployment needs them. GHCR publishing uses `GITHUB_TOKEN`; no cloud provider is selected yet.

Production must use HTTPS/TLS and restrictive CORS. Safe defaults let the API and tests start with AI disabled.
