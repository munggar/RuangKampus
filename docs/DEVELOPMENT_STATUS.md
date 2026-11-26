# RuangKampus — Development Status

Last updated: 2026-11-25

## Current phase

**Backend core API implementation — `backend/core-api`.**

## Repository and branch audit

- Repository: `munggar/RuangKampus`.
- `main` and `develop` remain at bootstrap commit `86c2fa77480a268a08e86d5d080684d9c731349c` during this backend implementation.
- Account A created `backend/core-api` from `develop`.
- A separate `feat/frontend-foundation` branch appeared during this task. Its current head is `2534066161e19f823bfc29db1691d185a5fa4cb5`; it includes React/TypeScript/Vite student and Staff Sekretariat shells, navigation, login UI, API HTTP/auth clients, and dashboard placeholders. This branch was inspected read-only and was not merged or modified.
- Existing project decision remains React + TypeScript, FastAPI, and PostgreSQL. The Node/Express fallback is not applicable because FastAPI was already selected in project documentation.

## Implemented in `backend/`

- FastAPI app, modular routers, OpenAPI/Swagger, health check, CORS, security headers, request-size guard, centralized error handling, and per-process auth endpoint rate limits.
- SQLAlchemy models and Alembic initial migration for users, auth sessions, password reset tokens, rooms, reservations, lecture schedules, room unavailability, notifications, and room update logs.
- Argon2id password hashing, short-lived access JWT, hashed/rotating HttpOnly refresh cookie, logout revocation, protected dependencies, and Student/TU_Admin RBAC.
- Student registration with server-assigned role, login/logout/refresh/me, profile update, password change, forgot/reset password, and CLI bootstrap for first Staff Sekretariat.
- Admin user listing, role/status updates, and soft deactivation. Last active Staff Sekretariat cannot be removed/demoted through management routes.
- Room list/detail/create/update/soft-delete, search/building/capacity/facility/status filters, pagination/sort, room constraints, and audit snapshots.
- Availability checks for operating hours, capacity, room state, one-time/recurring lecture schedules, maintenance blocks, and overlapping `PENDING`/`APPROVED` reservations.
- Reservation create/list/detail/cancel/approve/reject/complete, owner scoping, transaction-bound room row locks for writes/approvals, and decision notifications/audit.
- Admin lecture schedule and room-unavailability endpoints; in-app notifications and read tracking; SMTP/local-mailbox status; role-scoped dashboard; room statistics; admin activity log.

## Frontend compatibility review

The `feat/frontend-foundation` branch was inspected without modification. Its existing `frontend/src/api/auth.ts` expects direct login payloads (`access_token`, `token_type`, `expires_in`, `user`), public role labels `Student` / `Staff Sekretariat`, direct `/auth/me` user data, and `{ success: true }` from logout. Its HTTP client sends bearer access tokens and `credentials: include`. Backend auth serialization was adjusted to these expectations while database/RBAC role values remain `STUDENT` and `TU_ADMIN`. Other business endpoints continue using the general success envelope.

The frontend currently does not call `/auth/refresh` or restore sessions after a full page reload. Its password-recovery page is a placeholder and is not yet wired to the backend reset endpoints. Dashboard and other feature pages remain scaffolds, not verified end-to-end integrations.

## Tests and validation

- `python -m compileall -q src tests alembic`: passed.
- `PYTHONPATH=src pytest -q`: **24 tests passed** using a fresh in-memory SQLite database per test.
- Initial Alembic migration upgrade, model/migration drift check, and downgrade: validated against a disposable SQLite database; no cloud DB used.
- Local Uvicorn smoke check: health endpoint and generated OpenAPI were checked; OpenAPI exposed 33 paths.
- Credential scan of generated source/config/docs: no populated API key, password, database credential, or populated `.env` was included.
- No RuangKampus PostgreSQL provider/connection was available; PostgreSQL driver connectivity and lock concurrency have not been integration-tested.

## Not implemented / not verified

- No RuangKampus cloud PostgreSQL project, SMTP provider, or deployment service has been configured.
- No Figma file URL/file key was available for direct design inspection. The frontend branch README refers to mobile-sized Figma artboards, but the design resource itself was not opened.
- CSV/XLSX academic schedule import preview/commit is not implemented.
- AI recommendation is not implemented; no verified frontend specification or provider configuration exists.
- Media upload/storage is not implemented; room/profile image attributes accept URLs only.
- Full historical refresh-token replay-family detection is not implemented; the current refresh token hash is rotated and stored.
- Rate limiting is per-process; production multi-worker deployment requires shared API gateway/WAF rate limiting.
- PostgreSQL row-lock concurrency has not been proven by a dedicated concurrent integration test.

## Open dependencies before staging/production

1. Confirm/provision a dedicated RuangKampus PostgreSQL project and credentials.
2. Run the initial Alembic migration against a disposable PostgreSQL integration database, not production.
3. Test two concurrent same-room/time create requests and approval races on PostgreSQL.
4. Coordinate with Account B to test auth payloads, refresh cookie behavior, error handling, CORS origin, and page-level API contracts against the actual frontend branch.
5. Wire frontend password recovery and session restoration to the implemented endpoints.
6. Configure SMTP and validate delivery with a controlled mailbox.
7. Configure shared rate limiting at the API gateway/WAF.
8. Implement schedule import after the authorized campus schedule source and actual file format are confirmed.

## Release readiness

**Not production-ready yet.** Core backend APIs and automated tests exist, but production PostgreSQL connection, concurrency test evidence, full frontend integration, real email provider, deployment, and security/operational review remain outstanding.


## Phase 2 implementation additions

- Schedule import: CSV/XLSX upload, parser limits, row preview, room/date/time validation, duplicate/overlap checks, persisted batch history, 24-hour preview expiry, atomic commit with deterministic room-row locking and conflict revalidation.
- Notifications: deterministic unique event keys, recipient-scoped reads, one-attempt SMTP delivery records, admin notification when a student cancels, HTML/plain-text messages.
- Operations: liveness `/health`, DB readiness `/ready`, structured JSON logs, streamed request-size cap, HSTS in production.
- Deployment artifacts: non-root backend Docker image, local PostgreSQL Compose file, isolated GitHub Actions PostgreSQL service, dependency audit and image build.
- Tests added for schedule CSV/XLSX workflows, late conflicts at import commit, SMTP mock/HTML escaping/local mailbox permissions, event dedupe, notifications access control, PostgreSQL schema constraints, and real concurrent reservation create/approval paths.

## Phase 2 validation status

- Local disposable SQLite tests: 45 passed.
- PostgreSQL-only integration tests: 9 passed on the GitHub Actions PostgreSQL 18 service (schema/FK/check constraints plus reservation concurrency and rollback). They were skipped only on the local workstation.
- SQLite Alembic validation: upgrade to head, `alembic check`, downgrade to base, re-upgrade to head, second `alembic check`: passed against an isolated temporary SQLite database.
- Neon PostgreSQL test project: a separate isolated project/branch was provisioned and a read-only query confirmed PostgreSQL 18.7. Migration/concurrency proof below comes from an ephemeral GitHub Actions PostgreSQL 18 service, not the Neon test branch.
- Existing Neon `RuangKampus/production` branch was not used or modified.
- GitHub Actions run #19 completed successfully on commit 3959f51d0740f2786751c1213f37fe004dcd5e3c: SQLite tests, PostgreSQL migrations/integration, dependency audit, and Docker image build all passed.
- Docker, Ruff, and pip-audit binaries were not available locally. Their CI equivalents passed: Ruff lint/format, pip-audit (no known vulnerabilities), and Docker image build.

## Remaining Phase 2/production blockers

- Provision and authorize the actual staging/production PostgreSQL target; the verified CI migration/concurrency run used ephemeral PostgreSQL 18.
- Configure a real SMTP account/credentials in the hosting secret manager and run controlled delivery tests. No SMTP credentials or production email was used.
- Deploy backend to an approved hosting target and run /health and /ready checks.
- Full page-by-page frontend integration remains pending; current frontend branch provides auth integration scaffolding while room/reservation/dashboard pages are placeholders.
- AI Recommendation, Room Image Upload, and WebSocket/SSE are intentionally deferred: no verified frontend flow or provider/storage requirement exists in the current Master Brief/frontend branch. The master brief positions AI as a later phase.
- Shared distributed rate limiting remains a deployment-layer requirement for multi-worker/multi-instance production; the current application limiter is per-process.


## Verified Phase 2 CI evidence

GitHub Actions run #19 completed with conclusion SUCCESS for commit 3959f51d0740f2786751c1213f37fe004dcd5e3c on 2026-11-25.

- Ruff lint, CI workspace formatting, and Python compile checks passed.
- SQLite unit/API suite: 45 passed.
- PostgreSQL 18 integration suite: 9 passed, covering schema/index/FK/check constraints, concurrent overlapping reservation creation, duplicate concurrent approval, approval-versus-overlapping-create serialization, and transaction rollback.
- PostgreSQL migration database: all migrations upgraded to head, alembic check passed, downgraded to base, upgraded to head again, and second alembic check passed.
- pip-audit: No known vulnerabilities found.
- Backend Docker image build: passed.
- Workflow: https://github.com/munggar/RuangKampus/actions/runs/45596818058.

These checks ran against ephemeral GitHub Actions PostgreSQL 18 databases. They do not mean a production database was migrated or a backend hosting provider was deployed.

## Primary 15-feature backend implementation update

Backend implementation now maps each of the 15 primary features to an API/data flow. Added in this update:
- Room metadata: nullable `faculty` and `location_description` fields, output schemas, audit snapshots, faculty/location search filters, and migration `d4e8b71c2f90`.
- Room search: exact date/time search parameters invoke the same availability service before pagination.
- Alternative slots: Student-only `POST /api/v1/rooms/alternative-slots` enumerates slots inside operating hours and returns only candidates passing the availability engine.
- Room assistant: Student-only `POST /api/v1/assistant/chat` returns records from the database, parsed filters, alternatives, and clarifying questions. It is explicitly `RULE_BASED` at this stage, does not create reservations, does not persist chat messages, and does not transmit chat messages to an external AI provider.
- API rate limiting was added to assistant and alternative-slot endpoints.

The core flows for features 1–10 and 12–14 already exist in the Phase 1/2 routers and services. Feature 11 has a functioning backend chat/search contract but does not yet use a generative LLM provider. Feature 15 now has a deterministic availability-based recommendation endpoint. All candidate recommendations are revalidated when a student actually submits a reservation.

The frontend branch was not modified. Frontend work should be based on these final request/response contracts after backend review and CI passes.

## Verified 15-feature backend CI result

GitHub Actions run #43 completed successfully for backend commit `1e80718e283ce5060ad5375e020a79c71320a930` on 2026-11-25:
- SQLite unit/API suite: **50 tests passed**.
- PostgreSQL 18 schema/concurrency integration suite: **9 tests passed**.
- PostgreSQL Alembic upgrade, drift check, downgrade-to-base, re-upgrade, and second drift check: passed.
- Ruff lint, formatting in CI workspace, and Python compile: passed.
- `pip-audit`: no known vulnerabilities found.
- Backend Docker image build: passed.

Run: https://github.com/munggar/RuangKampus/actions/runs/45607354793.

This validates the backend source and migrations against isolated CI databases only. No production database was migrated and no hosting provider was deployed. Frontend sources were not modified. The room assistant API currently uses a deterministic rule-based engine; an external generative LLM provider remains unconfigured.
