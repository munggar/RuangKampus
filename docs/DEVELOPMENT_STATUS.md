# RuangKampus — Development Status

Last updated: 2026-11-26

## Repository and production source

- Repository: `munggar/RuangKampus`.
- Production deployment is connected to branch `develop`.
- Audit remediation is being prepared on a separate branch so production is not changed without review.
- Stack: React 19, TypeScript, Vite, FastAPI, SQLAlchemy, Alembic, and PostgreSQL.

## Implemented application capabilities

- Student: room directory/search, availability checks, room details, booking requests, reservation tracking/cancellation, notifications, profile/password management, alternative slots, and a rule-based room assistant.
- TU/Admin: dashboard, reservation approval/rejection/completion, room management, per-day operating hours with multiple time windows, schedules and maintenance periods, user management, schedule import preview/commit, activity history, notifications, and profile/password management.
- Backend checks room capacity, operating hours, recurring and date-specific schedules, maintenance periods, and overlapping pending/approved reservations.
- Reservation creation and approval re-check availability while database locks are held.
- Authentication uses Argon2id password hashes, short-lived access tokens, rotating HttpOnly refresh cookies, and server-side session revocation.
- Database schema changes use Alembic migrations.

## Changes prepared from the technical/product audit

- Logout can revoke a browser session through its HttpOnly refresh cookie even after the access token has expired.
- Public Student self-registration is disabled until NIM can be checked against an authorized campus roster. TU/Admin can create accounts only after manually checking the official record.
- Admin account creation, status changes, role changes, and deactivation are recorded in the existing activity log.
- Assistant search carries participant count parsed from natural-language messages into alternative-slot search.
- Alternative-slot search has stricter day/time/result bounds and a maximum of 500 availability checks per request.
- Admin screens provide account management, schedule import preview/commit/history, activity history, and a reservation completion action after its booked end time.
- Student/Admin room, reservation, notification, and schedule lists now use 20-item pages with navigation controls rather than silently stopping at the first 100 records.
- Admin login accepts more than one Admin username.
- Frontend CI runs on pushes to `develop`, `main`, and `frontend/**`.
- Profile identity labels, unavailable-room messages, and the inactive “Ingat saya” checkbox were corrected.
- Room opening hours can be set separately by weekday and can contain multiple time windows.

## Remaining work requiring external data, credentials, or broader validation

1. **Official student roster:** the campus data owner must provide a current, authorized NIM/contact list. Admin must manually compare records until an approved import or integration exists.
2. **Email recovery:** a real sender mailbox and SMTP credentials are required. Production email delivery was disabled during the audit; code changes cannot create valid provider credentials or an operational Admin mailbox.
3. **Official room and timetable data:** the authorized campus unit must validate room codes, capacities, facilities, opening hours, lecture timetables, and maintenance windows.
4. **Schedule import format:** the new screen uses the backend's existing CSV/XLSX parser. Validate the actual campus timetable file/template before importing operational data.
5. **End-to-end and load tests:** cover login/refresh/logout, room search, booking, approval/completion, user management, schedule import, mobile layouts, and concurrent usage in staging.
6. **Shared rate limiting:** current API limits are process-local. Use a trusted proxy setup and a shared gateway/WAF or Redis before increasing workers/replicas.
7. **Branch release policy:** production follows `develop`. Document merge and rollback rules and deliberately synchronize `main`.
8. **Pagination across other lists:** some Student/Admin lists still need consistent navigation after records exceed the current fetch limit. New user and activity screens have pagination.
9. **Production verification:** after review and merge, verify Alembic migrations, Railway health, SMTP delivery, real-user workflows, and data correctness. CI success is not proof of full browser readiness.
10. **Profile image storage and generative AI:** direct file upload and generative AI are not included; photo URL support and rule-based assistance remain current scope.

## Release recommendation

Use a limited pilot only after the campus data owner validates student identities and official room/schedule data, and after email recovery is configured or a secure manual recovery process is documented. Passing a build or automated test suite is not a substitute for browser-based pilot and operational checks.
