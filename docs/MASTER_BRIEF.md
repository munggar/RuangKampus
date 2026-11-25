# RuangKampus — Master Project Brief

## Product overview
RuangKampus is a web application for discovering campus rooms and managing room reservations. Students discover rooms, check availability, submit requests, and track their own requests. Authorized TU/Admin staff maintain room and schedule information and review reservation decisions.

Only verified and authorized campus information may be treated as official. Direct integration with UHAMKA academic systems must not be assumed until an authorized interface and permission are confirmed.

## Target technology
- Frontend: React + TypeScript.
- Backend: Python + FastAPI.
- Database: PostgreSQL.
- Integration: versioned REST API with OpenAPI documentation.

These are project technology decisions, not claims that an application or cloud service is already deployed. Database provider, deployment topology, and operational configuration require separate confirmation.

## Functional scope

### Authentication and authorization
- Login and logout; secure password hashing or an approved external identity reference.
- Session/token lifecycle and protected endpoints.
- Roles: Student and TU/Admin.
- Students can access only their own reservation records.
- Only authorized TU/Admin users can modify rooms/schedules and approve or reject requests.

### Room management
- List rooms and view details.
- Search and filter by building, capacity, facilities, and status.
- Create, update, and deactivate rooms.
- Maintain capacity, facilities, location, operating hours, description, and room status.
- Represent maintenance and unavailable periods explicitly.

### Smart availability
The backend must evaluate lecture schedules, approved reservations, policy-defined pending-request conflicts, capacity, operating hours, room status, and maintenance/unavailability. Absence of a lecture schedule alone must never imply availability.

Check actual time-range overlap. Revalidate during TU/Admin approval. Use a database transaction and concurrency control so overlapping requests cannot both be approved.

### Reservation lifecycle
Planned states: Pending, Approved, Rejected, Cancelled.
- Create request and retrieve a student's own history/details.
- Cancellation follows a documented policy.
- TU/Admin can inspect, approve, or reject.
- Rejection requires a reason.
- A request becomes Approved only after authorization, fresh conflict validation, and transaction commit succeed.

### TU/Admin operations
- List/filter requests, inspect applicant/request details, and review conflicts.
- Approve/reject requests.
- Manage rooms and academic schedules.
- Inspect approval history and administrator activity.

### Notifications
- In-app notification feed and read state.
- Notify TU/Admin of new requests.
- Notify students of approval, rejection, and cancellation.
- Optional email delivery with provider-backed status tracking.

Never report an email as sent unless a configured provider confirms successful delivery/acceptance. Keep in-app and email delivery states distinguishable.

### Academic schedule import
Support CSV/Excel where feasible: validate format, room references, dates, times, and duplicates; preview before persistence; provide row-level import results; record data source and update time. Do not fabricate official data or assume a direct academic-system integration.

### AI recommendation (later phase)
Recommend rooms based on capacity, facilities, time, and user requirements; suggest alternatives; use only backend-verified facts. AI must never invent availability, capacity, or source data, bypass validation, or approve reservations. Core search and reservation must work without AI.

## Non-functional requirements
- Server-side input validation and backend authorization.
- Student data isolation.
- Transactions/concurrency controls for approval invariants.
- No sensitive data leakage or secrets in source control.
- Versioned, repeatable, reviewed database migrations.
- Automated tests use isolated test resources, never production databases.
- OpenAPI/API contracts documented for frontend integration.
- Responsive and accessible frontend experiences.

## Collaboration
- Account A — Munggar Fajar Muharram: backend, database/migrations, API, authentication/authorization, business logic, notifications, integration, and backend tests.
- Account B — Adil Muslim Saputra: frontend and UI/UX, including Figma design ownership.
- Coordinate API changes and cross-owner work. Account A must not independently replace frontend or Figma work.

## Bootstrap exclusions
Repository bootstrap does not implement application features, provision cloud infrastructure, configure external providers, create migrations, import campus data, or build AI features. Those tasks require separate verification and approval.
