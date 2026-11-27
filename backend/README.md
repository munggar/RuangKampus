# RuangKampus Backend

FastAPI service for RuangKampus. The backend source snapshot in this release matches the Railway production API deployment on **27 November 2026**.

## Production source

- Railway service: `ruangkampus-api`
- Source branch: `develop`
- Source commit: `b9443b173d7898b4647219d239c52dbf8c2a7c76`
- Production URL: https://ruangkampus-api-production.up.railway.app/
- OpenAPI/Swagger: https://ruangkampus-api-production.up.railway.app/api/v1/docs

Production runs on Railway with PostgreSQL, an Alembic pre-deploy migration command, and persistent storage mounted at `/data` for imported room photos. The source ZIP does **not** contain production environment variables, secrets, database content, users, or uploaded media.

## Stack and capabilities

- Python 3.12, FastAPI, Pydantic Settings.
- SQLAlchemy 2 and PostgreSQL.
- Alembic migrations.
- JWT access tokens and refresh-cookie sessions.
- Role-aware endpoints for Student and Staff Sekretariat (`TU_ADMIN` internally).
- Room inventory, capacity/facility filtering, photos and location descriptions.
- Availability checks, reservation creation/approval/rejection/cancellation.
- Schedule and maintenance blocks.
- In-app notifications and transactional email integration.
- Two-step .xlsx room and schedule imports.
- Student RUKKA assistant endpoints with deterministic room-data checks and optional server-side OpenRouter language responses.
- Audit/activity logging, health/readiness endpoints, and rate limiting.

## Requirements

- Python 3.12 recommended (3.11+ may work depending on dependency support).
- PostgreSQL 15 or newer for shared development and production-like testing.
- pip.

For the complete stack, the easiest option is Docker Compose from the repository root; see [../README.md](../README.md).

## Local setup without Docker

From the repository root:

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

Edit `backend/.env` and set:
- `DATABASE_URL` to a dedicated local PostgreSQL database.
- `JWT_SECRET_KEY` to a random value of at least 32 bytes.
- `CORS_ORIGINS=http://localhost:5173`.
- `EMAIL_BACKEND=console` for local development.

Then run:

```powershell
$env:PYTHONPATH = "src"
alembic upgrade head
uvicorn ruangkampus.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: http://127.0.0.1:8000/api/v1/docs  
Health: http://127.0.0.1:8000/health  
Readiness: http://127.0.0.1:8000/ready

## Environment configuration

The authoritative local template is [`.env.example`](.env.example). Important variables:

| Variable | Purpose |
|---|---|
| `APP_ENV` | `development` or `production` |
| `DATABASE_URL` | SQLAlchemy PostgreSQL connection string |
| `JWT_SECRET_KEY` | Private signing key; at least 32 bytes |
| `CORS_ORIGINS` | Exact, comma-separated trusted frontend origins |
| `COOKIE_SECURE`, `COOKIE_SAMESITE` | Refresh-cookie security attributes |
| `PUBLIC_APP_URL` | Public frontend base URL used in links |
| `PASSWORD_RESET_BASE_URL` | Frontend password reset page |
| `EMAIL_BACKEND` | `console` local only, `smtp`, `brevo`, or `disabled` in production |
| `BREVO_API_KEY`, `BREVO_SENDER_EMAIL` | Optional Brevo transactional email |
| `ROOM_MEDIA_DIR` | Writable directory for photos extracted from room inventory workbooks |
| `ASSISTANT_AI_ENABLED` | Enables the optional AI language layer when a server-side key is configured |
| `OPENROUTER_API_KEY` | Optional secret for RUKKA response generation; backend only |
| `OPENROUTER_MODEL` / `ASSISTANT_AI_MODEL` | Provider model selection |
| `ASSISTANT_AI_ENDPOINT_URL` | OpenRouter-compatible chat completions endpoint |

Never expose provider secrets through frontend `VITE_*` variables. In production, use Railway service variables, a strong signing key, PostgreSQL, secure cookies, an explicit CORS allowlist, and persistent storage for room photos. Do not copy production values into local files.

RUKKA's verified room facts and availability are derived from backend data and checks; the optional model is a response layer, not an authority for room or reservation state. See [RUKKA AI API Contract](../docs/AI_ASSISTANT_API_CONTRACT.md) and [provider setup](../docs/RAKA_OPENROUTER_SETUP.md).

## Database migrations

Migration files are under `alembic/versions/`. Apply migrations only to the development/test database selected by `DATABASE_URL`:

```powershell
$env:PYTHONPATH = "src"
alembic upgrade head
alembic check
```

Railway runs `alembic upgrade head` as a pre-deploy command for the production API. Do not run local tests or migration experiments against production.

## First administrator

Public registration creates Student accounts; it does not let a caller choose an administrator role. A trusted operator can create a Staff Sekretariat account from a controlled shell after applying the development migration:

```powershell
$env:PYTHONPATH = "src"
python -m ruangkampus.cli create-admin
```

Follow the interactive prompts. Never store administrator credentials in source control or the ZIP archive.

## Tests and quality checks

```powershell
cd backend
python -m pip install -r requirements.txt
python -m pip install pytest ruff
$env:PYTHONPATH = "src"
pytest -q
ruff check src tests alembic
ruff format --check src tests alembic
```

PostgreSQL schema, migration, and concurrency tests are in `tests/postgres/` and require isolated disposable PostgreSQL databases. Use the GitHub Actions workflows as the canonical CI path.

## Operational notes

- `/health` is the liveness endpoint; `/ready` verifies readiness including database connectivity.
- Room photos extracted by Excel import are stored under `ROOM_MEDIA_DIR`; on Railway a persistent volume is mounted at `/data`.
- Room inventory import supports .xlsx with six-column inventory mapping and embedded photos; imported rooms remain inactive until the required building/operating-hours details are completed by Staff Sekretariat.
- The API never accepts a Student-supplied identity as authorization evidence. Backend RBAC is authoritative.
