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
| `ENCRYPTION_KEY` | Yes | Base64url-encoded 32-byte AES-256 key for secret storage at rest (US-17, US-03). Generate with `python -m app.core.crypto`. |
| `JWT_SECRET_KEY` | Yes | Independent signing key of at least 32 characters for access and refresh tokens. |
| `JWT_ALGORITHM` | No | `HS256`; signing algorithm for JWT tokens. |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | No | `15`; access token lifetime in minutes. |
| `REFRESH_TOKEN_EXPIRE_DAYS` | No | `7`; refresh token lifetime in days. |

The worker sends email through `SMTP_HOST` and `SMTP_PORT` (default 587) with STARTTLS. Set `EMAIL_FROM` and, for authenticated relays, `SMTP_USER` and `SMTP_PASSWORD`. Configure these in the root Compose `.env`. Generic HTTPS webhooks receive incident JSON. Set `WEBHOOK_SECRET` to include a hex HMAC-SHA256 of the request body in `X-Monitoring-Signature`.

## Planned variables

`LLM_PROVIDER`, `LLM_API_KEY`, and deployment settings will be added with their features. They must be documented before use. LLM and notification secrets must never appear in logs.

## Local stack and CI

Docker Compose supplies PostgreSQL with pgvector and Redis. The backend and worker use the same `DATABASE_URL` and `REDIS_URL`. The frontend uses `VITE_API_BASE_URL`, defaulting to `http://localhost:8000` for local development. The Vercel build sets it to an empty string so requests use the site's own domain.

Production must use HTTPS with TLS 1.3 and restrictive CORS. Safe defaults let the API and tests start with AI disabled.

## Hosted monitoring workers

For hosted Celery jobs on Vercel, set the Production `REDIS_URL` to the provider's TCP connection URL. The worker and Beat use certificate-verified TLS for Upstash endpoints with either Redis URL scheme.

## Using Aiven for PostgreSQL

Celery defaults to two concurrent tasks per worker. Its synchronous database sessions release their connections when returned, so idle worker processes do not occupy PostgreSQL connection slots between tasks.

In your Compose environment file, set `DATABASE_URL` to the Aiven service URI with the `postgresql+psycopg://` scheme. Use the Aiven service port and percent-encode special characters in the username or password. For an existing deployment, keep its `ENCRYPTION_KEY` and `JWT_SECRET_KEY`.

The app uses the TLS mode in `DATABASE_URL`. A service URI with `sslmode=require` enables encryption. For certificate and hostname verification, save the service CA from Aiven as `aiven-certs/ca.pem` in the project root, and set `sslmode=verify-full&sslrootcert=/run/aiven/ca.pem`. Compose mounts the certificate directory read-only for both the backend and the worker.

The following PowerShell commands assume you saved the settings in `backend/.env`. Use `.env` in the first line if you saved them in the project root. Run from the project root. The Aiven override requires Docker Compose 2.24.4 or newer.

```powershell
$dc = @('--env-file', 'backend/.env', '-f', 'docker-compose.yml', '-f', 'compose.aiven.yaml')
docker compose @dc config --quiet
docker compose @dc run --rm --no-deps --build backend uv run --no-dev alembic current
```

`alembic current` checks the connection and reports any existing schema revision. A new database has no revision. To move existing records, restore a full PostgreSQL dump into a fresh Aiven database **before** starting the backend. A previously migrated source dump includes `alembic_version`. Compare source and restored row counts before enabling the workers. The Aiven database role needs permission to create the `pgcrypto`, `citext`, and `vector` extensions used by the schema.

Once the database is ready, start the stack and check the applied revision. The backend applies pending migrations on startup.

```powershell
docker compose @dc up -d --build --wait
docker compose @dc exec backend uv run --no-dev alembic current
```
