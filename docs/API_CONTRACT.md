# RuangKampus — API Contract (Planning Baseline)

## Status and rules
**Every route below is planned, not implemented.** These contracts give Account B an initial integration reference and must be reconciled with FastAPI OpenAPI after endpoint implementation and tests.

- Base path: `/api/v1`.
- Transport: HTTPS in deployed environments.
- Content type: `application/json`, except file uploads.
- Date: ISO calendar date `YYYY-MM-DD`.
- Time: local campus wall-clock time `HH:MM`; Asia/Jakarta is the working assumption pending institutional confirmation.
- IDs: opaque; clients must not assume database integer sequences.
- Protected endpoints require the agreed session/token credential.
- Roles: Student and TU/Admin; exact enum string will be finalized with the identity model.
- Backend is authoritative for data ownership, availability, and state transitions.

## Proposed common error shape

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "The request could not be processed.",
    "details": []
  }
}
```

Use suitable HTTP status codes: 400/422 invalid input, 401 missing/invalid authentication, 403 insufficient role/access, 404 unavailable/non-visible resource, 409 state/conflict error, 5xx unexpected failure. Do not expose stack traces or secrets.

## Authentication

| Method | Path | Request | Response | Access |
|---|---|---|---|---|
| POST | `/auth/login` | `{ "email": "...", "password": "..." }` | `{ "access_token": "...", "token_type": "bearer", "expires_in": 1800, "user": { "id": "...", "name": "...", "role": "Student" } }` | Public |
| POST | `/auth/logout` | Credential/session context | `{ "success": true }` | Authenticated |
| GET | `/auth/me` | None | Current profile; never include password/hash | Authenticated |

Token/session shape and refresh strategy must be finalized during auth design. Example values are illustrative.

## Rooms

| Method | Path | Request/query | Response | Access |
|---|---|---|---|---|
| GET | `/rooms` | Optional q, building, min_capacity, max_capacity, facilities, status, pagination | `{ "items": [Room], "page": 1, "page_size": 20, "total": 0 }` | Authenticated or public-by-policy |
| GET | `/rooms/{room_id}` | None | Room | Authenticated or public-by-policy |
| POST | `/rooms` | Room creation payload | Created Room | TU/Admin |
| PATCH | `/rooms/{room_id}` | Partial Room payload | Updated Room | TU/Admin |
| POST | `/rooms/{room_id}/deactivate` | Optional reason | Updated room status | TU/Admin |

Proposed Room fields: id, room_name, building, floor, capacity, facilities, location, operating_hours, room_status, description, last_updated_at.

## Availability

| Method | Path | Request/query | Response | Access |
|---|---|---|---|---|
| GET | `/rooms/{room_id}/availability` | date, start_time, end_time, participant_count | `{ "room_id": "...", "available": false, "reasons": [], "checked_at": "..." }` | Authenticated |

This response is advisory for selection only. Creation and TU/Admin approval must independently revalidate. Reasons should identify blocker categories without disclosing another student's private reservation details.

## Reservations — Student

| Method | Path | Request | Response | Access |
|---|---|---|---|---|
| POST | `/reservations` | room_id, reservation_date, start_time, end_time, purpose, participant_count | Created Reservation with Pending status | Student |
| GET | `/reservations/me` | Optional status/date filters and pagination | Own reservation list | Student |
| GET | `/reservations/{reservation_id}` | None | Own detail | Owner Student or TU/Admin |
| POST | `/reservations/{reservation_id}/cancel` | Optional cancellation reason | Updated Cancelled reservation | Owner Student subject to policy |

A Student must never read another student's request by changing the identifier.

## Reservations — TU/Admin

| Method | Path | Request | Response | Access |
|---|---|---|---|---|
| GET | `/admin/reservations` | Optional status/date/building filters and pagination | Filtered list | TU/Admin |
| GET | `/admin/reservations/{reservation_id}` | None | Request, applicant summary, conflict review data | TU/Admin |
| POST | `/admin/reservations/{reservation_id}/approve` | Optional administrative note | Approved reservation if transaction succeeds | TU/Admin |
| POST | `/admin/reservations/{reservation_id}/reject` | `{ "rejection_reason": "..." }` | Rejected reservation | TU/Admin |

Approval atomically re-checks authorization, Pending state, room status, hours, capacity, lecture schedule, maintenance, and reservation conflicts. Return 409 if the request is no longer approvable or a conflict exists. Rejection requires a non-empty reason.

## Academic schedules

| Method | Path | Request | Response | Access |
|---|---|---|---|---|
| GET | `/admin/schedules` | Date/building/room filters | Schedule list | TU/Admin |
| POST | `/admin/schedules/import/preview` | CSV/XLSX multipart file | Row preview and validation report; no persistence | TU/Admin |
| POST | `/admin/schedules/import/commit` | Validated preview reference | Import summary and row-level result | TU/Admin |

Validate room references, date/time, duplicates, and source metadata. Do not assume direct academic-system integration exists.

## Notifications

| Method | Path | Request | Response | Access |
|---|---|---|---|---|
| GET | `/notifications` | Optional unread_only and pagination | Own notification list | Authenticated |
| PATCH | `/notifications/{notification_id}/read` | `{ "read_status": true }` | Updated notification | Recipient only |

Delivery status must distinguish queued, sent, failed, and not configured based on actual provider results.

## Proposed response concepts
- **Reservation:** id, user_id, room_id, reservation_date, start_time, end_time, purpose, participant_count, status, admin_id, rejection_reason, submitted_at, approved_at, updated_at.
- **Notification:** id, recipient_id, notification_type, title, message, read_status, delivery_status, created_at.

## Contract change process
Account A maintains the backend/OpenAPI contract. Before changing a response already consumed by Account B, notify Account B, document compatibility impact, and agree on the migration path. Update this document with implementation status only after endpoint tests pass.
