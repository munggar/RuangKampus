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
- AI recommendation provider/endpoint.
- Media upload/storage.
- Push/WebSocket notifications.
