# RuangKampus Backend

Backend API for RuangKampus. This implementation uses **Python, FastAPI, SQLAlchemy 2, Alembic, and PostgreSQL**. Backend source, migrations, API contracts, and backend tests are owned by Account A (Munggar Fajar Muharram).

## Current status

Core API modules are implemented for authentication/session management, user/profile administration, room management, room availability, reservation requests and decisions, lecture schedules/maintenance blocks, in-app/email notifications, dashboard summaries, and administrator activity.

No RuangKampus cloud database or deployment has been connected. No migration has been applied to a cloud database. PostgreSQL integration/concurrency tests remain a staging prerequisite.

## Requirements and local setup

- Python 3.11+ (Python 3.12 recommended)
- PostgreSQL 15+ for shared development/staging/production
- pip
- SMTP provider for real email delivery (optional in local development)

From the repository root:

```bash
cd backend
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS/Linux
# source .venv/bin/activate

python -m pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
# macOS/Linux: cp .env.example .env
```

Set a private `JWT_SECRET_KEY` (32+ random bytes in production) and set `DATABASE_URL` to a **dedicated development PostgreSQL database**:

```dotenv
DATABASE_URL=postgresql+psycopg://USERNAME:PASSWORD@HOST:5432/ruangkampus_dev
JWT_SECRET_KEY=replace-with-a-long-random-local-secret
CORS_ORIGINS=http://localhost:5173
```

An isolated SQLite database can be used for quick local smoke tests only:

```dotenv
DATABASE_URL=sqlite:///./ruangkampus_local.db
```

SQLite does not verify PostgreSQL row-level lock behavior.

## Environment variables

| Variable | Purpose |
|---|---|
| `APP_ENV` | `development` or `production` |
| `APP_NAME`, `API_V1_PREFIX` | API title and prefix |
| `DATABASE_URL` | SQLAlchemy connection URL |
| `JWT_SECRET_KEY`, `JWT_ALGORITHM` | Access-token signing |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | Access token lifetime; default 15 |
| `REFRESH_TOKEN_EXPIRE_DAYS` | Refresh session lifetime; default 14 |
| `PASSWORD_RESET_EXPIRE_MINUTES` | Reset-token expiry; default 30 |
| `CORS_ORIGINS` | Exact comma-separated trusted frontend origins |
| `COOKIE_SECURE`, `COOKIE_SAMESITE` | Refresh cookie security attributes |
| `CAMPUS_TIMEZONE` | Defaults to `Asia/Jakarta` |
| `EMAIL_BACKEND` | `console` (local only), `smtp`, or `disabled` |
| `LOCAL_MAILBOX_DIR` | Gitignored local mailbox for development messages |
| `PASSWORD_RESET_BASE_URL` | Frontend reset-page URL |
| `SMTP_HOST`, `SMTP_PORT`, `SMTP_USERNAME`, `SMTP_PASSWORD`, `SMTP_FROM_EMAIL`, `SMTP_USE_TLS` | SMTP provider configuration |

Do not commit populated `.env` files or share secrets. Production settings require PostgreSQL, a strong JWT key, secure cookies, explicit CORS origins, and real SMTP configuration. Never place secrets in `VITE_*` variables.

## Migrations

The initial Alembic migration is under `alembic/versions/`. Account A owns schema and migration changes.

```bash
# Confirm DATABASE_URL points to a disposable/development database first.
PYTHONPATH=src alembic upgrade head
PYTHONPATH=src alembic check
```

Review each migration. Never run test or local migration commands against production. The current migration was validated on disposable SQLite; PostgreSQL migration validation remains outstanding.

## First administrator

Public registration always assigns `STUDENT`; clients cannot set role. Create the first TU/Admin account using a trusted operator shell after applying the development migration:

```bash
PYTHONPATH=src python -m ruangkampus.cli create-admin
```

The command prompts for email, name, and password. No default administrator or official campus seed data is included.

## Run and inspect the API

```bash
PYTHONPATH=src uvicorn ruangkampus.main:app --reload --host 127.0.0.1 --port 8000
```

- Health: `GET /health`
- Swagger UI: `http://127.0.0.1:8000/api/v1/docs`
- OpenAPI JSON: `http://127.0.0.1:8000/api/v1/openapi.json`
- ReDoc: `http://127.0.0.1:8000/api/v1/redoc`

## Authentication and frontend compatibility

- Passwords use Argon2id.
- Access JWTs default to 15 minutes. Refresh token is stored as a hash in `auth_sessions`, delivered in an HttpOnly cookie scoped to `/api/v1/auth`, rotated on refresh, and revoked on logout/password change/reset.
- Protected endpoints reload the user/session from the database and enforce current role/account status.
- Student signup always creates `STUDENT`. Internal database/RBAC role values are `STUDENT` and `TU_ADMIN`.
- Public user role labels in API responses match the current frontend AuthContext: `Student` and `TU/Admin`.

The existing separate `feat/frontend-foundation` branch was reviewed read-only. Its `frontend/src/api/auth.ts` expects:
- `POST /auth/login`: direct response object `{ access_token, token_type, expires_in, user }` (not wrapped in `data`);
- `GET /auth/me`: direct safe user object;
- `POST /auth/logout`: `{ success: true }`;
- bearer access tokens in `Authorization` and `credentials: include` for the HttpOnly refresh cookie.

The backend auth serializers were adapted to this contract without changing frontend files. Other business endpoints use the shared `{ success, message, data, meta }` envelope. Error responses expose a top-level `message`, which the frontend HTTP helper already reads.

The frontend currently keeps the access token in memory and does not yet call refresh/session restoration after a full page reload. Its password-recovery page remains a placeholder even though backend forgot/reset endpoints exist. Dashboard and other non-auth pages remain placeholders and are not end-to-end integrated.

## Password recovery and notifications

`POST /auth/forgot-password` returns a non-enumerating 202 response. Reset token hashes are stored, tokens expire, and a token is single-use; successful reset revokes active sessions. In local development `EMAIL_BACKEND=console` writes a message to the gitignored `.local_mailbox/`. This is not actual email delivery. Only a successful configured SMTP provider operation is marked `SENT`.

## Roles and reservation rules

- `STUDENT`: active room discovery, availability check, own reservation history/detail/cancellation, own profile and notifications.
- `TU_ADMIN`: room/user/schedule/maintenance management, all reservation reviews, approval/rejection/cancellation/completion, dashboard and audit access.
- Backend authorization is authoritative; client role selection is only a UX consistency check.
- Dates and operating times use `Asia/Jakarta` by default. Overnight bookings are not supported.
- Rooms without configured operating hours are not assumed to be available.
- Availability checks room status, capacity, operating hours, one-time/recurring lecture schedules, maintenance blocks, and overlapping `PENDING`/`APPROVED` reservations.
- Creation and approval re-check conflicts inside a transaction and lock the room row. PostgreSQL is required to validate cross-worker concurrency.
- Adjacent half-open intervals (09:00–10:00 and 10:00–11:00) do not overlap.

## API groups

All paths except health include the `/api/v1` prefix.

| Group | Routes | Access |
|---|---|---|
| Auth | register, login, logout, refresh, me, forgot-password, reset-password | Mixed |
| Profile | GET/PATCH `/users/me`, PATCH `/users/me/password` | Authenticated |
| User administration | GET `/users`, PATCH role/status, DELETE soft-deactivate | TU/Admin |
| Rooms | GET list/detail/availability; POST/PATCH/DELETE | Read active rooms public; mutations TU/Admin |
| Reservations | GET list/detail, POST create, PATCH cancel/approve/reject/complete | Owner Student or TU/Admin |
| Schedules | GET/POST/DELETE `/admin/schedules` | TU/Admin |
| Room unavailability | GET/POST `/admin/room-unavailability`, PATCH deactivate | TU/Admin |
| Notifications | GET, PATCH read | Recipient only |
| Dashboard | summary, recent reservations, room statistics | Role-scoped |

See `docs/API_CONTRACT.md` and the generated OpenAPI document for schemas and query parameters.

## Tests

```bash
PYTHONPATH=src pytest -q
python -m compileall -q src tests alembic
```

The automated unit/API suite contains **45 passing SQLite tests** using isolated in-memory databases. A separate **9-test PostgreSQL 18 integration suite** is run by GitHub Actions against an ephemeral PostgreSQL service. It covers schema/index/FK/check constraints, migration lifecycle, concurrent overlapping creates, duplicate concurrent approval, approval-versus-create serialization, and rollback. CI run #19 passed both suites and PostgreSQL migration upgrade/check/downgrade/re-upgrade: https://github.com/munggar/RuangKampus/actions/runs/45596818058.

This is actual PostgreSQL integration evidence, not an inference from SQLite. It is still an ephemeral CI database; no production or campus database was changed.

## Known limitations

- No RuangKampus cloud PostgreSQL, deployment, or SMTP provider has been confirmed; no cloud migration has been run.
- The Figma file itself is not yet accessible for direct inspection; frontend branch and API client code were reviewed read-only.
- CSV/XLSX schedule import preview/commit is implemented for TU/Admin through /api/v1/admin/schedules/imports/*.
- AI recommendations are intentionally not implemented without a verified specification/provider.
- Media upload/storage is not implemented; room/profile image attributes accept URLs only.
- Historical refresh-token replay-family detection is not implemented.
- Rate limiting is an in-process guard; production multi-worker/multi-instance deployments require shared API gateway/WAF rate limiting.


## Phase 2 — CSV/XLSX schedule import

TU/Admin can import campus lecture schedules through a two-step preview/commit process. The endpoint accepts CSV and XLSX only; maximum upload size is 5 MiB, maximum non-empty records is 5,000, and XLSX expanded archive size is limited. Macro-enabled formats are rejected. The XLSX reader uses read-only/data-only mode and does not execute macros.

Accepted header names are case-insensitive and whitespace/hyphens are normalized to underscores. Required columns are:
- `course_name`
- `start_time`
- `end_time`
- either `room_code` or `room_id`
- exactly one of `schedule_date` or `day_of_week`

One-time dates use ISO `YYYY-MM-DD`. Recurring weekdays accept Monday–Sunday or integers 0–6 (Monday=0). Time accepts `HH:MM` or `HH:MM:SS`. Empty rows are ignored.

Workflow:
1. `POST /api/v1/admin/schedules/imports/preview` with multipart field `file`.
2. Inspect `data.row_results`, counts, and returned `batch_id`.
3. `POST /api/v1/admin/schedules/imports/commit` with `{ "batch_id": "..." }`.
4. Read `GET /api/v1/admin/schedules/imports` or `GET /api/v1/admin/schedules/imports/{batch_id}` for history.

Preview results are persisted for the creating administrator for 24 hours. Commit re-locks the affected rooms in deterministic UUID order, re-checks existing schedules, maintenance, reservations, and room status, then inserts all valid preview rows in one transaction. If any conflict appears after preview, the entire batch is rejected and no schedule rows are inserted. Invalid rows are reported individually during preview; valid rows can still be committed as an atomic batch. File binary content is not retained; source filename, SHA-256 digest, normalized preview, and row results are retained.

### Phase 2 — Notifications and email

In-app events now have deterministic event keys protected by a unique index to prevent duplicate event rows when processing is repeated. Each email notification records an attempt timestamp and count. Automatic retry is intentionally disabled: SMTP cannot guarantee exactly-once delivery after an ambiguous network timeout, and silently retrying can send duplicates. Failed deliveries are visible as `FAILED`; they are not claimed as sent.

SMTP sends multipart plain-text and HTML alternatives. User-controlled content in email HTML is escaped. Production configuration requires SMTP with STARTTLS; credentials remain in environment variables. Development `EMAIL_BACKEND=console` writes to the ignored local mailbox and is not real email delivery.

### Phase 2 — Operations, Docker, and CI

- `GET /health` is the liveness probe and does not require the database.
- `GET /ready` executes `SELECT 1` and returns 503 if the database is unavailable.
- `backend/Dockerfile` uses a non-root runtime image. Migrations remain a separate operator step and do not run automatically at worker startup.
- `docker-compose.yml` starts an isolated local PostgreSQL service and the API.
- GitHub Actions starts a PostgreSQL 18 service, runs SQLite unit/API tests separately from PostgreSQL integration tests, performs PostgreSQL Alembic upgrade/drift/downgrade/re-upgrade, runs concurrency/schema tests, dependency audit, and a Docker build.

PostgreSQL CI evidence must be checked from the GitHub Actions run attached to the backend commit. Local SQLite tests do not prove PostgreSQL row-lock semantics.


## Verified Phase 2 CI result

GitHub Actions run #19 completed successfully on 2026-11-25: 45 SQLite API/unit tests passed; 9 PostgreSQL 18 schema/concurrency integration tests passed; Alembic PostgreSQL upgrade, drift check, downgrade, re-upgrade, and second drift check passed; Ruff lint and CI workspace formatting passed; pip-audit reported no known vulnerabilities; and the non-root backend Docker image built successfully. See https://github.com/munggar/RuangKampus/actions/runs/45596818058.

## Run with Docker Compose (local development)

Copy root .env.example to .env and replace local placeholder values. From repository root:

```bash
docker compose up --build -d
docker compose exec api alembic upgrade head
```

API readiness: http://localhost:8000/ready. Stop services with docker compose down. Use docker compose down -v only when intentionally deleting the disposable local database volume. Example passwords are local-only.
