# RuangKampus — API Contract

**Backend:** FastAPI under `backend/`. **Base path:** `/api/v1`. Generated OpenAPI is available at `/api/v1/openapi.json`; Swagger UI is at `/api/v1/docs`.

## Response conventions

Most business endpoints use this success envelope:

```json
{
  "success": true,
  "message": "Rooms retrieved",
  "data": [],
  "meta": { "page": 1, "limit": 20, "total": 0, "total_pages": 0 }
}
```

Most errors use:

```json
{
  "success": false,
  "message": "Request validation failed",
  "errors": [{ "code": "VALIDATION_ERROR", "field": "capacity", "message": "Invalid value" }]
}
```

**Frontend compatibility exception:** the active frontend branch's auth client expects direct JSON for auth success responses, so auth responses are not wrapped in `data`. The public API role labels are `Student` and `TU/Admin`, while internal database/RBAC role values remain `STUDENT` and `TU_ADMIN`. Error responses expose a top-level `message`, which the current client helper already reads.

## Conventions

- Send `Authorization: Bearer <access_token>` for protected endpoints.
- Access token lifetime defaults to 15 minutes.
- Refresh token is stored as a hash and delivered only in an HttpOnly cookie scoped to `/api/v1/auth`; default 14-day lifetime and rotation on refresh.
- Campus date and wall-clock time use `Asia/Jakarta` by default. Dates are `YYYY-MM-DD`; times are `HH:MM:SS` or `HH:MM`.
- Overnight reservations are not supported.
- IDs are UUIDs and must be treated as opaque strings.
- Pagination defaults to `page=1`, `limit=20`; max limit is 100.

## Authentication

| Method | Path | Request | Access |
|---|---|---|---|
| POST | `/auth/register` | `{ "name", "email", "password", "phone"?, "student_identifier"? }` | Public; role is assigned as Student |
| POST | `/auth/login` | `{ "email", "password" }` | Public |
| POST | `/auth/logout` | Bearer access token; clears refresh cookie | Authenticated |
| POST | `/auth/refresh` | Refresh HttpOnly cookie, no JSON body | Refresh cookie |
| GET | `/auth/me` | None | Authenticated |
| POST | `/auth/forgot-password` | `{ "email" }` | Public, rate-limited |
| POST | `/auth/reset-password` | `{ "token", "new_password" }` | Public, rate-limited |

Register/login/refresh return the direct object:

```json
{
  "access_token": "<short-lived-access-token>",
  "token_type": "bearer",
  "expires_in": 900,
  "user": {
    "id": "uuid",
    "name": "Student Name",
    "email": "student@example.com",
    "student_identifier": null,
    "phone": null,
    "profile_image_url": null,
    "role": "Student",
    "account_status": "ACTIVE",
    "created_at": "2026-11-25T09:00:00Z"
  }
}
```

This is an illustrative payload, not live user data. `GET /auth/me` returns the direct safe user object. `POST /auth/logout` returns `{ "success": true }`. Refresh tokens and password hashes are never returned in JSON. Unknown registration fields (including role) are rejected.

Forgot-password returns a non-enumerating 202 response regardless of whether an active account matches. In development, `EMAIL_BACKEND=console` writes to a gitignored local mailbox; it is not actual delivery. Production requires configured SMTP. Reset token hashes are stored, tokens expire, and each token is single-use.

## User profile and administration

| Method | Path | Request/query | Access |
|---|---|---|---|
| GET | `/users/me` | None | Authenticated |
| PATCH | `/users/me` | `name`?, `phone`?, `profile_image_url`? | Authenticated; own profile |
| PATCH | `/users/me/password` | `current_password`, `new_password` | Authenticated; own account |
| GET | `/users` | `search`, `role`, `account_status`, `page`, `limit` | TU/Admin |
| PATCH | `/users/{user_id}/status` | `{ "account_status": "ACTIVE" | "DISABLED" }` | TU/Admin |
| PATCH | `/users/{user_id}/role` | `{ "role": "STUDENT" | "TU_ADMIN" }` | TU/Admin |
| DELETE | `/users/{user_id}` | None; soft delete | TU/Admin |

The user object role returned to browser clients is `Student` or `TU/Admin`; role-update request values remain `STUDENT` or `TU_ADMIN`. Disabling, changing role, or soft-deleting an account revokes active sessions. Admins cannot demote/disable/delete themselves or remove the last active TU/Admin.

## Rooms

| Method | Path | Request/query | Access |
|---|---|---|---|
| GET | `/rooms` | `search`, `building`, `capacity` (minimum), `min_capacity`, `max_capacity`, repeated `facilities`, `status`, `sortBy`, `sortOrder`, `page`, `limit` | Public for active rooms; TU/Admin can filter status |
| GET | `/rooms/{room_id}` | None | Public active room; TU/Admin can read inactive/maintenance |
| GET | `/rooms/{room_id}/availability` | `date`, `startTime`, `endTime`, `participantCount` | Public |
| POST | `/rooms` | Room create payload | TU/Admin |
| PATCH | `/rooms/{room_id}` | Partial Room payload | TU/Admin |
| DELETE | `/rooms/{room_id}` | Soft delete | TU/Admin |

Create/update fields: `room_name`, `room_code`?, `building`, `floor`?, `capacity`, `description`?, `facilities: string[]`, `operating_hours`, `room_status`, `photo_url`?. Valid statuses: `ACTIVE`, `INACTIVE`, `MAINTENANCE`. Operating-hours keys are weekdays `monday`–`sunday`, each with one or more `{ start, end }` windows. Empty/unconfigured hours do not imply availability. Future pending/approved reservations prevent room deactivation/deletion; capacity cannot be reduced below booked participant count.

Availability blocker codes include `PAST_OR_CURRENT_START_TIME`, `ROOM_NOT_ACTIVE`, `CAPACITY_EXCEEDED`, `OUTSIDE_OPERATING_HOURS_OR_NOT_CONFIGURED`, `LECTURE_SCHEDULE_CONFLICT`, `ROOM_UNAVAILABLE`, and `RESERVATION_CONFLICT`.

## Reservations

| Method | Path | Request/query | Access |
|---|---|---|---|
| POST | `/reservations` | `room_id`, `purpose`, `date`, `start_time`, `end_time`, `participant_count`, `notes`? | Student |
| GET | `/reservations` | `status`, `dateFrom`, `dateTo`, `page`, `limit` | Student own records; TU/Admin all |
| GET | `/reservations/{reservation_id}` | None | Owner Student or TU/Admin |
| PATCH | `/reservations/{reservation_id}/cancel` | `reason`? | Owner or TU/Admin, policy permitting |
| PATCH | `/reservations/{reservation_id}/approve` | No body | TU/Admin |
| PATCH | `/reservations/{reservation_id}/reject` | `{ "rejection_reason": "..." }` | TU/Admin |
| PATCH | `/reservations/{reservation_id}/complete` | No body | TU/Admin; after end time |

Statuses: `PENDING`, `APPROVED`, `REJECTED`, `CANCELLED`, `COMPLETED`. Pending/approved overlaps block a room; rejected/cancelled/completed do not. Create and approval re-check room state, capacity, hours, lecture schedules, maintenance, and reservations. Room row locks serialize conflicting write/approval flows on PostgreSQL. Conflict/state responses use HTTP 409. Cancellation is only allowed for pending/approved reservations before the start time.

## Schedules and room unavailability

| Method | Path | Request/query | Access |
|---|---|---|---|
| GET | `/admin/schedules` | `room_id`?, `date`? | TU/Admin |
| POST | `/admin/schedules` | room, course, times, exactly one of `schedule_date` or `day_of_week`, `data_source`? | TU/Admin |
| DELETE | `/admin/schedules/{schedule_id}` | None; marks CANCELLED | TU/Admin |
| GET | `/admin/room-unavailability` | `room_id`?, `date`? | TU/Admin |
| POST | `/admin/room-unavailability` | room, date, times, reason | TU/Admin |
| PATCH | `/admin/room-unavailability/{block_id}/deactivate` | No body | TU/Admin |
| GET | `/admin/activity` | `entity_type`, `action`, `page`, `limit` | TU/Admin |

Recurring schedule `day_of_week` uses Monday=0 through Sunday=6. Overlapping schedule/maintenance blocks are rejected where detected.

## Notifications and dashboard

| Method | Path | Request/query | Access |
|---|---|---|---|
| GET | `/notifications` | `unreadOnly`, `page`, `limit` | Authenticated; own |
| PATCH | `/notifications/{notification_id}/read` | No body | Recipient only |
| GET | `/dashboard/summary` | None | Role-scoped |
| GET | `/dashboard/recent-reservations` | `limit` (1–50) | Student own; TU/Admin all |
| GET | `/dashboard/room-statistics` | `dateFrom`, `dateTo` | TU/Admin |

Email delivery state is recorded separately from in-app notification creation: `NOT_CONFIGURED`, `LOCAL_MAILBOX_WRITTEN`, `SENT`, or `FAILED`. Console mode is not actual email delivery. Dashboard figures are calculated from database queries, not hard-coded.

## HTTP status codes

- `200` success.
- `201` created.
- `202` forgot-password accepted without account enumeration.
- `401` unauthenticated/invalid session.
- `403` insufficient role.
- `404` missing or non-visible record.
- `409` state/uniqueness/reservation conflict.
- `413` request too large.
- `422` input validation.
- `429` rate-limited.
- `500` unexpected failure; `503` database unavailable for health.

## Frontend compatibility and known gaps

The current separate `feat/frontend-foundation` branch calls login and expects the direct auth payload above, reads public role labels as `Student` / `TU/Admin`, and expects direct `/auth/me` data. Its HTTP helper sends bearer tokens and `credentials: include`. Backend auth serialization is aligned with this contract; no frontend file has been modified.

The frontend currently does not call refresh/session restoration after a hard reload. Its password recovery view is still a placeholder and does not yet submit to the implemented endpoints. Dashboard and feature pages beyond login remain scaffolds/placeholders and are not yet end-to-end wired.

## Not implemented in this API slice

- CSV/XLSX schedule import preview/commit.
- Generative LLM provider for the room assistant; the current stateless rule-based assistant endpoint is documented below.
- Media upload/storage.
- Push/WebSocket notifications.


## Phase 2 — schedule import endpoints

All routes below require TU/Admin and retain the `/api/v1` prefix.

| Method | Path | Request/query | Behavior |
|---|---|---|---|
| POST | `/admin/schedules/imports/preview` | multipart form field `file` | Parse CSV/XLSX, validate each row, check conflicts, persist preview batch |
| POST | `/admin/schedules/imports/commit` | `{ "batch_id": "uuid" }` | Revalidate and atomically insert preview-valid rows |
| GET | `/admin/schedules/imports` | `limit` (1–100, default 20) | Current administrator's import history |
| GET | `/admin/schedules/imports/{batch_id}` | None | Current administrator's batch details |

Accepted headers are `course_name`, `start_time`, `end_time`, plus `room_code` or `room_id`, plus exactly one of `schedule_date` or `day_of_week`. Headers are case-insensitive; spaces and hyphens normalize to underscores. Date uses ISO `YYYY-MM-DD`; time uses `HH:MM` or `HH:MM:SS`; weekday accepts Monday–Sunday or integer 0–6 (Monday=0).

Limits: 5 MiB upload, 5,000 non-empty rows, XLSX expanded ZIP payload at most 25 MiB. CSV must be UTF-8. XLSX is parsed using read-only/data-only mode; XLS/XLSM and unsupported MIME/signatures are rejected. Only the first active worksheet is parsed.

Preview returns `batch_id`, source filename, SHA-256 digest, row/valid/invalid counts, row-level status/errors, and up to 50 normalized valid rows. A preview is valid for 24 hours and is scoped to the administrator who created it. Commit locks all affected room rows in sorted UUID order, rechecks current room status and schedule/reservation/maintenance conflicts, and inserts the batch in one transaction. New conflicts after preview produce HTTP 409 and zero inserted rows. No file binary is retained.

## Phase 2 — notification idempotency and email states

Notification rows now carry an optional unique `event_key`, `email_attempted_at`, and `email_attempt_count`. Reservation event keys are deterministic per reservation, event type, and recipient. This prevents duplicate in-app records when the same event handler is invoked more than once.

Email delivery is attempted once per notification record. SMTP errors are recorded as `FAILED`; a network timeout is not automatically retried because delivery may have been accepted despite the lost response. Plain-text and HTML alternatives are sent; HTML content is escaped. `LOCAL_MAILBOX_WRITTEN` is still development-only and is not actual SMTP delivery.

## Phase 2 — operations

| Method | Path | Access | Meaning |
|---|---|---|---|
| GET | `/health` | Public | Liveness only; process is running |
| GET | `/ready` | Public | Executes database `SELECT 1`; 503 if DB is unavailable |

CORS uses explicit configured origins. Request size is limited to 6 MiB, including streamed requests without Content-Length. Production responses receive HSTS; structured JSON logs do not serialize request bodies or exception messages. Docker images run as a non-root user. Database migrations must be run explicitly as an operator/CI step.

## Backend flow for the 15 primary features

The following is the backend contract that the frontend must follow. The backend owns authorization, validation, availability decisions, and reservation state transitions; the browser must not treat client-side checks as authoritative.

| No. | Feature | Backend flow and contract |
|---:|---|---|
| 1 | Authentication & Authorization | `POST /auth/register` (Student-only role assignment), `POST /auth/login`, `POST /auth/refresh`, `POST /auth/logout`, `GET /auth/me`; current-user and Student/TU_Admin dependencies enforce RBAC on every protected route. |
| 2 | Student Dashboard | `GET /dashboard/summary` and `GET /dashboard/recent-reservations`; returns counts and only the authenticated student's records. |
| 3 | TU Dashboard | The same summary/recent endpoints are role-scoped; `GET /dashboard/room-statistics` is TU/Admin-only. |
| 4 | Room Management | TU/Admin-only `POST/PATCH/DELETE /rooms`; soft deletion and room changes are audited. |
| 5 | Smart Room Availability | `GET /rooms/{room_id}/availability`; checks active state, capacity, operating hours, one-time/recurring lectures, maintenance blocks, and pending/approved reservations. Creation and approval repeat this check transactionally. |
| 6 | Room Search & Filter | `GET /rooms` supports text, faculty, building, location, capacity/min/max capacity, repeated facilities, status (TU/Admin), sorting, and paging. Optional `date`, `startTime`, `endTime`, and `participantCount` filter to rooms available for that exact slot before pagination. |
| 7 | Online Room Reservation | Student-only `POST /reservations`; server validates inputs and rechecks availability while holding the room row lock. |
| 8 | TU Approval System | TU/Admin-only `PATCH /reservations/{id}/approve` and `/reject`; validates status transitions, rechecks the current room slot, writes an audit event, and notifies the student. |
| 9 | Conflict Detection | One shared availability service checks schedules, maintenance, and PENDING/APPROVED bookings; PostgreSQL room-row locking serializes create/approval races. Conflicts return HTTP 409. |
| 10 | Reservation Tracking | `GET /reservations` and `GET /reservations/{id}` apply student ownership scoping and return PENDING/APPROVED/REJECTED/CANCELLED/COMPLETED states. |
| 11 | Chatbot / AI Room Assistant | Student-only `POST /assistant/chat`; accepts a message and optional structured filters, returns grounded room records and follow-up questions, never creates a reservation, and does not persist or forward chat content. The first engine is deterministic/rule-based; a generative LLM provider is not yet configured. |
| 12 | Notification System | `GET /notifications` and `PATCH /notifications/{id}/read`; recipient scoping, event-key deduplication, and explicit email delivery states. |
| 13 | Room Location Information | Room payload now includes `faculty`, `building`, `floor`, and `location_description`; existing `photo_url` remains an optional URL. |
| 14 | Room Facility Information | Room payload includes capacity, facilities, description, operating hours, and status; these values are returned in search/detail and used by availability validation. |
| 15 | Alternative Slot Recommendation | Student-only `POST /rooms/alternative-slots`; enumerates operating-hour slots in the requested date window and returns only slots that pass the same availability engine. It returns candidate suggestions, not a reservation; booking revalidates. |

### Alternative-slot request

`POST /api/v1/rooms/alternative-slots` accepts `date`, `duration_minutes`, `participant_count`, optional `room_id`, `faculty`, `building`, `facilities`, `preferred_start_time`, `search_days` (0–14), `slot_step_minutes` (5–120), and `limit` (1–50). Suggestions are ranked by date proximity, time proximity, same-room preference, and capacity slack. Each result carries `availability_source: LIVE_AVAILABILITY_CHECK`. Availability may change after the response, so the reservation endpoint always rechecks.

### Assistant request

`POST /api/v1/assistant/chat` accepts `message` plus optional `faculty`, `building`, `min_capacity`, `facilities`, `date`, `start_time`, `end_time`, and `participant_count`. Date and time filters must be complete as a group. The response includes `engine`, `intent`, `filters`, `rooms`, `alternative_slots`, `follow_up_questions`, and `reservation_action: NOT_CREATED`. `engine=RULE_BASED` identifies the current non-LLM implementation accurately; no external provider receives user chat messages.

### Room search time filter

`GET /api/v1/rooms` accepts `faculty`, `building`, `location`, `capacity`, `min_capacity`, `max_capacity`, repeated `facilities`, and `date` + `startTime` + `endTime` + optional `participantCount`. The date/time trio must be supplied together. When present, availability filtering is performed before pagination so `meta.total` counts matching available rooms only.

### Schema migration

Alembic revision `d4e8b71c2f90` adds nullable `rooms.faculty` and `rooms.location_description` columns and a faculty/building/status index. Existing room rows remain valid with null metadata; administrators should populate faculty and location details before relying on those filters.
