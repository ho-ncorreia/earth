# EA Workbench

An incremental Enterprise Architecture governance workbench. Increment 1 establishes a React and FastAPI foundation with local authentication, role-based access, persisted users and audit events, and a database-backed dashboard. Ardoq remains the portfolio system of record.

## Start locally

Prerequisites: Python 3.11+ and Node.js 20+. Docker is optional; SQLite is the default local database.

1. Copy `.env.example` to `.env`. Set a random `EA_SECRET_KEY`, a valid `EA_BOOTSTRAP_ADMIN_EMAIL`, and a unique `EA_BOOTSTRAP_ADMIN_PASSWORD` of at least 16 characters. The seed command rejects example placeholders.
2. Install dependencies once:

```powershell
py -m venv .venv
.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
Set-Location frontend
npm.cmd install
Set-Location ..
```

3. From the repository root, start migrations, seed the administrator, and both services with one command:

```powershell
powershell.exe -ExecutionPolicy Bypass -File .\dev.ps1
```

Open `http://127.0.0.1:5173`. The API publishes OpenAPI at `http://127.0.0.1:8000/docs`. The launcher requires `.env`, checks that its ports are free, and writes service logs under `backend` and `frontend`.

After changing role definitions or adding migrations while the services already run, refresh the database without stopping them with `powershell.exe -ExecutionPolicy Bypass -File .\dev.ps1 -SeedOnly`.

PostgreSQL is available in `docker-compose.yml`. For a local PostgreSQL install, set `EA_DATABASE_URL` to a PostgreSQL SQLAlchemy URL before startup. Docker is not required for local SQLite development.

## Increment 1: Foundation

Implemented: bounded package structure; SQLite/PostgreSQL configuration and Alembic migration; bootstrap roles and administrator; Argon2 password hashing; short-lived signed access token in an HTTP-only cookie; CSRF double-submit protection; permission-checked user management and audit APIs; health/readiness endpoints; database-derived dashboard; bilingual responsive shell; theme tokens; backend tests and deployment files.

Local password/JWT authentication is development-only, not production enterprise identity. User creation sets a temporary password; password reset, OIDC, MFA and account lifecycle workflows are later work.

## Increment 2: Core Governance

Implemented: architecture study create/read/update/draft-delete with a controlled status workflow; risk create/read/update with backend score calculation; ADR authoring, considered options, study/risk links, review/accept/reject/supersede rules, immutable accepted versions, optimistic concurrency and comparison; persisted assistant conversations and source references; server-side permission-filtered study/ADR/risk retrieval.

## ADR and assistant configuration

ADR APIs and history are listed in OpenAPI at `/docs`. The assistant uses the Mistral API only from FastAPI. Set `EA_MISTRAL_API_KEY` and optionally `EA_MISTRAL_MODEL`/`EA_MISTRAL_BASE_URL` in the backend environment, then restart the backend. Never put the key in frontend variables. When no authorised source matches, the assistant returns “No reliable source was found in the authorised knowledge base.” When a source matches but Mistral is unconfigured or unavailable, the API reports the integration outage rather than fabricating an answer.

See [docs/architecture.md](docs/architecture.md) for the module map, component and deployment architecture, ER model, permissions matrix, API contracts, integration strategy and security assumptions. See [docs/operations.md](docs/operations.md) for the runbook.

Remaining work: mitigation actions; ADD authoring and versions; Draw.io; Ardoq read-only integration; deviations, reports and notifications. AI draft-artefact generation, embeddings/vector retrieval and source-document authoring are not implemented yet.

Checks: `py -m pytest backend\tests`; frontend production build: from `frontend`, run `npm.cmd run build`. The launcher applies migrations before starting the API; the API itself does not create tables implicitly.
# EA Workbench

An incremental Enterprise Architecture governance workbench. Increment 1 establishes a runnable React and FastAPI foundation with local authentication, role-based access, persisted users and audit events, and a database-backed dashboard. Ardoq remains the portfolio system of record.

## Start locally

Prerequisites: Python 3.11+ and Node.js 20+. Docker is optional. SQLite is the default local database.

1. Copy `.env.example` to `.env`; set `EA_SECRET_KEY` to a random value and set `EA_BOOTSTRAP_ADMIN_EMAIL` and `EA_BOOTSTRAP_ADMIN_PASSWORD` (at least 16 unique characters) to create the first administrator. Placeholder values are rejected.
2. Install the Python and frontend dependencies once:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
py -m pip install -r backend\requirements.txt
Set-Location frontend
npm.cmd install
Set-Location ..
```

3. Start the migrated backend and frontend with one command from the repository root: `.[dev.ps1](dev.ps1)` (PowerShell). Open `http://127.0.0.1:5173`; the API publishes OpenAPI at `http://127.0.0.1:8000/docs`. The launcher requires the `.env` settings from step 1 and writes service logs under `backend` and `frontend`.

PostgreSQL is available in `docker-compose.yml`. For a local PostgreSQL install set `EA_DATABASE_URL` to a PostgreSQL SQLAlchemy URL before migration. Docker is not required for local SQLite development.

## Increment 1

Implemented: bounded package structure; SQLite/PostgreSQL database configuration and Alembic revision; bootstrap roles and administrator; Argon2 password hashing; short-lived signed access token in an HTTP-only cookie; CSRF double-submit protection; permission-checked user management and audit APIs; health/readiness endpoints; database-derived dashboard; bilingual responsive shell; theme tokens; backend tests and deployment files.

Local password/JWT authentication is development-only, not production enterprise identity. User creation sets a temporary password; password reset, OIDC, MFA and account lifecycle workflows are later work.

See [docs/architecture.md](docs/architecture.md) for the requested business/module map, component/deployment architecture, ER model, permission matrix, API contracts, integration strategy and security assumptions. See [docs/operations.md](docs/operations.md) for the runbook.

Next increments: studies/ADRs/risks/mitigations; ADD editor and versions; Draw.io; Ardoq read-only integration; grounded Mistral assistant; deviations, reports and notifications. These are not simulated or represented by fake controls in this foundation.

Checks: `py -m pytest backend\tests`; frontend production build: `npm.cmd --prefix frontend run build` after installing dependencies. Apply migrations before starting the API. Startup does not create tables implicitly.