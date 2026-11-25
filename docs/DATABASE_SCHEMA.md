# RuangKampus — Database Schema (Conceptual Baseline)

## Status
This is a conceptual target model derived from the Master Project Brief. It is **not** an existing schema, migration, or claim that a RuangKampus database has been provisioned.

No database migration was run during repository bootstrap. No connected cloud database resource was changed.

## Engine
PostgreSQL is the relational database baseline because the domain needs foreign keys, transactions, constraints, indexes, and concurrency control for reservation approval. Hosting provider and RuangKampus-specific project are not yet identified.

## Proposed entities

### Users
| Field | Conceptual type | Notes |
|---|---|---|
| id | UUID | Primary key |
| name | VARCHAR | Display name |
| email | VARCHAR/CITEXT | Unique according to identity policy |
| student_identifier | VARCHAR, nullable | Student identifier when applicable |
| password_hash | TEXT, nullable | Only for local password auth |
| external_auth_reference | VARCHAR, nullable | Alternative external identity |
| role | ENUM/VARCHAR | Student or TU/Admin |
| account_status | ENUM/VARCHAR | Active/disabled/pending; final policy TBD |
| created_at | TIMESTAMPTZ | Creation time |
| updated_at | TIMESTAMPTZ | Last update |

Do not use local hashes and external credentials without a clear identity strategy. Never return password hashes.

### Rooms
| Field | Conceptual type | Notes |
|---|---|---|
| id | UUID | Primary key |
| room_name | VARCHAR | Display name |
| building | VARCHAR | Building label |
| floor | VARCHAR | Floor label; final type TBD |
| capacity | INTEGER | Positive |
| facilities | JSONB or normalized relation | Decide based on search/filter needs |
| location | TEXT/JSONB | Structure to be finalized |
| operating_hours | JSONB or normalized relation | Must consider exceptions |
| room_status | ENUM/VARCHAR | Active/inactive/maintenance/etc. |
| description | TEXT | Optional |
| last_updated_at | TIMESTAMPTZ | Last update |

### LectureSchedules
| Field | Conceptual type | Notes |
|---|---|---|
| id | UUID | Primary key |
| room_id | UUID | Foreign key to Rooms |
| course_name | VARCHAR | Course label |
| day/date | DATE or recurrence fields | Choose after inspecting actual source format |
| start_time | TIME | Campus-local time |
| end_time | TIME | Must be later than start_time |
| schedule_status | ENUM/VARCHAR | Active/cancelled/etc. |
| data_source | VARCHAR | Authorized source/provenance |
| last_updated_at | TIMESTAMPTZ | Last update |

The final model must explicitly support one-off dates or recurring weekly schedules; retain import provenance.

### Reservations
| Field | Conceptual type | Notes |
|---|---|---|
| id | UUID | Primary key |
| user_id | UUID | Foreign key to Users |
| room_id | UUID | Foreign key to Rooms |
| reservation_date | DATE | Campus-local date |
| start_time | TIME | Start |
| end_time | TIME | Must be later than start_time |
| purpose | TEXT | Request purpose |
| participant_count | INTEGER | Positive and <= room capacity |
| status | ENUM/VARCHAR | Pending/Approved/Rejected/Cancelled |
| admin_id | UUID, nullable | TU/Admin decision actor |
| rejection_reason | TEXT, nullable | Required when Rejected |
| submitted_at | TIMESTAMPTZ | Request time |
| approved_at | TIMESTAMPTZ, nullable | Approval time |
| updated_at | TIMESTAMPTZ | Last update |

Record cancellation actor/time as additional fields or audit events when workflow is finalized.

### Notifications
| Field | Conceptual type | Notes |
|---|---|---|
| id | UUID | Primary key |
| recipient_id | UUID | Foreign key to Users |
| notification_type | VARCHAR | Typed event |
| title | VARCHAR | Display title |
| message | TEXT | Display message |
| read_status | BOOLEAN | Default false |
| delivery_status | VARCHAR | Define channel-specific status semantics |
| created_at | TIMESTAMPTZ | Creation time |

Consider a separate delivery table if multiple channels, retries, or provider message IDs are required.

### RoomUpdateLogs
| Field | Conceptual type | Notes |
|---|---|---|
| id | UUID | Primary key |
| admin_id | UUID | Foreign key to Users |
| entity_type | VARCHAR | Room/schedule/etc. |
| entity_id | UUID | Polymorphic reference; audit strategy required |
| action | VARCHAR | Create/update/deactivate/etc. |
| previous_value | JSONB, nullable | Before snapshot |
| new_value | JSONB, nullable | After snapshot |
| created_at | TIMESTAMPTZ | Event time |

## Relationships
- Users 1-to-many Reservations.
- Rooms 1-to-many Reservations.
- Rooms 1-to-many LectureSchedules.
- Users 1-to-many Notifications.
- TU/Admin Users 1-to-many RoomUpdateLogs as administrator actor.

## Integrity/index requirements to design during implementation
- Unique email and applicable student_identifier constraints.
- Foreign keys for user, room, recipient, and administrator references.
- Checks for positive capacity/participant count and valid time ranges.
- Index Reservations by room/date/status and by user/date.
- Index LectureSchedules by room/date/time.
- Index Notifications by recipient/read state/created time.
- Rejected requests must have a reason.
- Enforce allowed transitions and approvals transactionally.
- Prevent concurrent conflicting approvals with appropriate locks, isolation, or PostgreSQL range/exclusion constraints after the real policy/schema is known.

## Migration policy
Account A owns schema changes and migrations. Migrations must be versioned, reviewed, repeatable, and safe to apply. Do not edit already-applied production migrations; create corrective migrations. Test against isolated disposable/test databases only. Back up and obtain approval before any production schema change.

## Open schema decisions
1. Identity source: local password hashes or external identity reference.
2. Official schedule source and recurrence representation.
3. Whether Pending reservations block availability or are advisory.
4. Cancellation cutoff and administrator override policy.
5. Whether facilities and operating hours should be normalized.
6. Notification channel/delivery tracking and audit retention.
