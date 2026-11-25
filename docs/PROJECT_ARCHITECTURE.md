# RuangKampus — Project Architecture

## Selected technology

| Layer | Choice | Current status |
|---|---|---|
| Frontend | React + TypeScript | Scaffolded on separate `feat/frontend-foundation` branch; Account B owns implementation |
| Backend | Python + FastAPI | Core API implemented on `backend/core-api` |
| ORM | SQLAlchemy 2 | Models and DB access layer implemented |
| Migrations | Alembic | Initial migration included; SQLite validation only |
| Database | PostgreSQL | Selected; no RuangKampus cloud project or connection confirmed |
| API | REST `/api/v1` | Implemented; FastAPI OpenAPI/Swagger available |

The alternate Node/Express/Prisma stack is not used because the existing project documents already selected FastAPI. A frontend foundation branch was created separately during this task; Account A inspected it read-only and did not modify it.

## Monorepo and ownership boundaries

```text
RuangKampus/
├── frontend/       # Account B — React + TypeScript and UI/UX
├── backend/        # Account A — FastAPI, SQLAlchemy, Alembic, services, tests
├── docs/           # Shared architecture, API, ownership, schema, status
└── tests/          # Shared/end-to-end tests may be added later
```

Account A changes only `backend/` and Account A-owned documentation. No frontend component, style, layout, route, animation, or Figma file was changed. The `feat/frontend-foundation` branch remains separate and unmerged.

## Backend modules

```text
backend/
├── alembic/versions/       # Versioned schema migrations
├── src/ruangkampus/
│   ├── routers/            # auth, users, rooms, reservations, schedules, notifications, dashboard
│   ├── services/           # availability and email delivery
│   ├── config.py           # environment configuration and production guards
│   ├── database.py         # SQLAlchemy engine/session
│   ├── dependencies.py     # authenticated user and role dependencies
│   ├── models.py           # ORM models
│   ├── schemas.py          # Pydantic request/response schemas
│   ├── security.py         # Argon2id, JWT, opaque token hashing
│   ├── rate_limit.py       # per-process auth endpoint rate limiter
│   └── main.py             # FastAPI app, middleware, error handlers, OpenAPI
└── tests/                  # isolated SQLite API tests
```

## Logical request flow

```text
Browser (Student / TU Admin)
          |
          v
React + TypeScript (Account B)
          | HTTPS JSON + bearer access token; HttpOnly refresh cookie
          v
FastAPI /api/v1 (Account A)
  |         |          |
  |         |          +--> auth / RBAC / user scope
  |         +-------------> availability / reservation transactions
  +-----------------------> rooms / schedules / notifications / dashboard
          |
          v
SQLAlchemy 2 + Alembic
          |
          v
PostgreSQL (provider not yet confirmed)
```

## Frontend authentication contract

The existing frontend auth client expects direct JSON bodies for login/register/refresh (`access_token`, `token_type`, `expires_in`, `user`), direct safe user data from `/auth/me`, and `{ success: true }` for logout. The browser uses `Authorization: Bearer` and `credentials: include`. Public role labels are `Student` / `TU/Admin`; internal DB/RBAC values remain `STUDENT` / `TU_ADMIN`. Backend auth serializers follow this contract without editing frontend source.

## Availability and reservation integrity

- No schedule row does not automatically mean available; operating hours, active room status, capacity, lecture schedules, maintenance blocks, and pending/approved reservation overlaps are evaluated.
- `PENDING` and `APPROVED` reservations both block a room. `REJECTED`, `CANCELLED`, and `COMPLETED` do not block future availability.
- Create and approval flows re-check availability. The room row is locked inside the database transaction to serialize writes for a specific room on PostgreSQL.
- The current test suite uses SQLite for portable rules/API tests; it does not prove PostgreSQL lock concurrency.

## Authentication and access

- Local passwords use Argon2id.
- Access JWT is short-lived; refresh token is long-lived, stored as a hash in `auth_sessions`, and delivered as an HttpOnly cookie.
- Every protected request checks the session row and the user's current database role/status.
- Registration creates `STUDENT` only. Admin creation uses a local CLI command.
- Student data queries are scoped by authenticated user ID; non-owned reservation detail returns 404.

## Notifications and external services

- In-app notifications are persisted in PostgreSQL. Email is attempted after the associated business transaction commits; email delivery state is recorded separately.
- Email delivery is attempted only through a configured SMTP provider. Local development `console` writes to ignored `.local_mailbox/`; status is `LOCAL_MAILBOX_WRITTEN`, never reported as real email send.
- No AI provider, academic-system integration, or cloud storage is configured.

## Deployment and environment strategy

- Use separate local/development, test, staging, and production databases/secrets.
- Production requires PostgreSQL, strong JWT key, secure cookies, explicit CORS origins, and a configured real email backend.
- Rate limiting is per process. Multi-worker/multi-instance deployments must add shared rate limiting at API gateway/WAF.
- Never commit populated `.env` files or secrets.

## Remaining work

- Confirm cloud PostgreSQL and SMTP resources.
- Validate initial migration against disposable PostgreSQL and run concurrency tests.
- Reconcile API fields and flows with the full frontend as Account B implements pages beyond the current shell.
- Wire session restoration/refresh and the password-recovery page in frontend.
- Implement schedule import after the authorized data source/file format is provided.
- Consider AI only after core backend/availability integration and a confirmed functional requirement.


## Phase 2 backend hardening

Schedule imports are a dedicated backend module and use a two-stage preview/commit process. The preview parser rejects unsupported formats, limits upload size and row count, resolves room references, validates date/time/weekdays, and reports row-specific errors. Commit locks all target room rows in deterministic order and revalidates conflicts before a single transaction writes the schedule rows and audit records.

Notification event handlers use deterministic unique event keys for in-app idempotency. SMTP sends a multipart message with a shared HTML template and escaped content. Delivery is attempted once per notification record and recorded separately from in-app creation; automatic retries are intentionally disabled when provider acceptance is ambiguous.

Operational endpoints separate liveness (`/health`) from readiness (`/ready`). Structured logs omit request bodies and exception messages. A non-root container, local Compose PostgreSQL, and CI PostgreSQL service have been added. Migrations are explicitly run in CI/operator steps, not on application worker startup.

The current release workflow separates SQLite tests from PostgreSQL integration tests. Its PostgreSQL service validates Alembic upgrade/check/downgrade/re-upgrade, schema constraints, foreign keys, concurrent reservation creation/approval, rollback, and container build. The workflow result—not local SQLite output—is the required evidence for PostgreSQL readiness.
