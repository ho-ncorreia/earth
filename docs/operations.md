# Operations Runbook (Foundation)

## Local start

Follow the root README. Apply `py -m alembic -c backend\alembic.ini upgrade head` before starting FastAPI. Vite proxies `/api` to the API process, keeping browser API traffic same-origin for cookie and CSRF handling.

## Configuration

`EA_DATABASE_URL` defaults to a local SQLite file. `EA_SECRET_KEY` must be a unique random secret (at least 32 characters outside development). Set `EA_COOKIE_SECURE=true` outside local development and only behind HTTPS. `EA_CORS_ORIGINS` is a comma-separated allowlist; keep empty for same-origin ingress. Bootstrap credentials are read only by the seed command. Never commit `.env`, database files, tokens or integration keys.

The optional `EA_MISTRAL_API_KEY`, `EA_MISTRAL_BASE_URL`, and `EA_MISTRAL_MODEL` are backend-only settings. Do not define them in frontend build variables. After role or schema changes with servers already running, `powershell.exe -ExecutionPolicy Bypass -File .\dev.ps1 -SeedOnly` reapplies migrations and role permissions without starting duplicate listeners.

Mitigation attachments are stored under `EA_ATTACHMENT_STORAGE_PATH` (default `backend/uploads/mitigations`). Uploads are limited to 10 MB and PDF, PNG, JPEG, TXT, or DOCX files. Docker Compose stores them in the persistent `mitigation_files` volume; include that volume in backup and restore procedures alongside the database. Jira JPD and Confluence values are validated HTTP(S) links only. Live CMA CGM API integration requires approved endpoints, authentication, and secret-management configuration.

Optional Ardoq lookup uses backend-only `EA_ARDOQ_API_TOKEN`, `EA_ARDOQ_ORG_LABEL`, and `EA_ARDOQ_API_HOST` (default `https://app.ardoq.com`). Configure the Ardoq root workspace ID and each component type ID under Architecture settings. The token must be least-privilege and must never be placed in frontend settings or committed files. Search uses Ardoq API v2 `GET /api/v2/components` with `name`, `rootWorkspace`, and `typeId` filters.

## Assistant knowledge sources

The assistant currently ranks stored studies, decisions, and risks by lexical overlap with each question, after permission and restricted-study checks. It considers the latest 200 records per source type and sends up to five relevant excerpts (up to 1,000 characters each) to Mistral with source references `[R1]`, `[R2]`, etc. The prompt requires source-grounded factual claims and an explicit no-evidence answer when context is insufficient. This supplies context per request; it does not train or fine-tune Mistral, and prompt instructions do not guarantee factual accuracy.

Saving or updating authorized workbench records makes them eligible for subsequent retrieval. Ardoq component lookup only fills a risk's object reference; it does not import Ardoq content into the assistant. Confluence and Jira links do not import their target documents either. Enriching retrieval with those systems requires an approved ingestion/synchronization pipeline, permission-aware indexing, and source citations. Semantic/vector retrieval is not implemented. Configure the Mistral key on the backend, restart the API after environment changes, and approve external processing of the selected excerpts before production use.

## Migrations, tests, backup

Run `py -m alembic -c backend\alembic.ini upgrade head` to upgrade, and back up production data before migrations. Run `py -m pytest backend\tests`; build frontend with `npm.cmd --prefix frontend run build`. For local SQLite, stop the API and copy the database and attachment directory. For PostgreSQL use `pg_dump --format=custom` and restore with `pg_restore` into a clean database, restore the `mitigation_files` volume, then migrate and verify `/health/ready`. Production cadence, encryption, retention, RPO/RTO and restore testing require operations approval.

## Health and gaps

`/health/live` reports process liveness; `/health/ready` checks database connectivity. Increment 1 uses standard Uvicorn logs. Structured logs/correlation, external integrations and background jobs are future work. Before enterprise production configure OIDC, TLS, secure cookies, trusted proxies, CSP, rate limiting, centralized secrets, audit retention, observability, backup policy and security review. Docker/Compose could not be exercised where Docker is absent.