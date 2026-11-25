# RuangKampus — Development Status

Last updated: 2026-11-25

## Current phase

**Backend core API implementation — `backend/core-api`.**

## Repository and branch audit

- Repository: `munggar/RuangKampus`.
- `main` and `develop` remain at bootstrap commit `86c2fa77480a268a08e86d5d080684d9c731349c` during this backend implementation.
- Account A created `backend/core-api` from `develop`.
- A separate `feat/frontend-foundation` branch appeared during this task. Its current head is `2534066161e19f823bfc29db1691d185a5fa4cb5`; it includes React/TypeScript/Vite student and TU/Admin shells, navigation, login UI, API HTTP/auth clients, and dashboard placeholders. This branch was inspected read-only and was not merged or modified.
- Existing project decision remains React + TypeScript, FastAPI, and PostgreSQL. The Node/Express fallback is not applicable because FastAPI was already selected in project documentation.

## Implemented in `backend/`

- FastAPI app, modular routers, OpenAPI/Swagger, health check, CORS, security headers, request-size guard, centralized error handling, and per-process auth endpoint rate limits.
- SQLAlchemy models and Alembic initial migration for users, auth sessions, password reset tokens, rooms, reservations, lecture schedules, room unavailability, notifications, and room update logs.
- Argon2id password hashing, short-lived access JWT, hashed/rotating HttpOnly refresh cookie, logout revocation, protected dependencies, and Student/TU_Admin RBAC.
- Student registration with server-assigned role, login/logout/refresh/me, profile update, password change, forgot/reset password, and CLI bootstrap for first TU/Admin.
- Admin user listing, role/status updates, and soft deactivation. Last active TU/Admin cannot be removed/demoted through management routes.
- Room list/detail/create/update/soft-delete, search/building/capacity/facility/status filters, pagination/sort, room constraints, and audit snapshots.
- Availability checks for operating hours, capacity, room state, one-time/recurring lecture schedules, maintenance blocks, and overlapping `PENDING`/`APPROVED` reservations.
- Reservation create/list/detail/cancel/approve/reject/complete, owner scoping, transaction-bound room row locks for writes/approvals, and decision notifications/audit.
- Admin lecture schedule and room-unavailability endpoints; in-app notifications and read tracking; SMTP/local-mailbox status; role-scoped dashboard; room statistics; admin activity log.

## Frontend compatibility review

The `feat/frontend-foundation` branch was inspected without modification. Its existing `frontend/src/api/auth.ts` expects direct login payloads (`access_token`, `token_type`, `expires_in`, `user`), public role labels `Student` / `TU/Admin`, direct `/auth/me` user data, and `{ success: true }` from logout. Its HTTP client sends bearer access tokens and `credentials: include`. Backend auth serialization was adjusted to these expectations while database/RBAC role values remain `STUDENT` and `TU_ADMIN`. Other business endpoints continue using the general success envelope.

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
