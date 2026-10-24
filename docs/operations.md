# Operations Runbook (Foundation)

## Local start

Follow the root README. Apply `py -m alembic -c backend\alembic.ini upgrade head` before starting FastAPI. Vite proxies `/api` to the API process, keeping browser API traffic same-origin for cookie and CSRF handling.

## Configuration

`EA_DATABASE_URL` defaults to a local SQLite file. `EA_SECRET_KEY` must be a unique random secret (at least 32 characters outside development). Set `EA_COOKIE_SECURE=true` outside local development and only behind HTTPS. `EA_CORS_ORIGINS` is a comma-separated allowlist; keep empty for same-origin ingress. Bootstrap credentials are read only by the seed command. Never commit `.env`, database files, tokens or integration keys.

The optional `EA_MISTRAL_API_KEY`, `EA_MISTRAL_BASE_URL`, and `EA_MISTRAL_MODEL` are backend-only settings. Do not define them in frontend build variables. After role or schema changes with servers already running, `powershell.exe -ExecutionPolicy Bypass -File .\dev.ps1 -SeedOnly` reapplies migrations and role permissions without starting duplicate listeners.

## Migrations, tests, backup

Run `py -m alembic -c backend\alembic.ini upgrade head` to upgrade, and back up production data before migrations. Run `py -m pytest backend\tests`; build frontend with `npm.cmd --prefix frontend run build`. For local SQLite, stop the API and copy the database. For PostgreSQL use `pg_dump --format=custom` and restore with `pg_restore` into a clean database, then migrate and verify `/health/ready`. Production cadence, encryption, retention, RPO/RTO and restore testing require operations approval.

## Health and gaps

`/health/live` reports process liveness; `/health/ready` checks database connectivity. Increment 1 uses standard Uvicorn logs. Structured logs/correlation, external integrations and background jobs are future work. Before enterprise production configure OIDC, TLS, secure cookies, trusted proxies, CSP, rate limiting, centralized secrets, audit retention, observability, backup policy and security review. Docker/Compose could not be exercised where Docker is absent.