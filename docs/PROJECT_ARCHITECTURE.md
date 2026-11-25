# RuangKampus — Project Architecture

## 1. Architecture status
This is the intended architecture for the initial monorepo. The GitHub repository was empty before bootstrap; there was no existing application architecture to preserve or claim as implemented.

## 2. Technology decision

| Layer | Baseline | Why it fits | Status |
|---|---|---|---|
| Frontend | React + TypeScript | Reusable component UI and typed client code | Selected; app not scaffolded |
| Backend | Python + FastAPI | Typed request/response validation and generated OpenAPI | Selected; app not scaffolded |
| Database | PostgreSQL | Relational integrity, transactions, indexes, concurrency primitives | Selected; no RuangKampus instance identified |
| API | Versioned REST under `/api/v1` | Clear frontend/backend integration boundary | Planned |
| Migrations | Alembic proposed if SQLAlchemy is adopted | Versioned, reviewable, repeatable schema changes | Proposed; not configured |
| Frontend build tool | Account B to confirm | Avoid imposing tooling before frontend owner sets up app | Open |

No evidence justifies replacing React + TypeScript, FastAPI, or PostgreSQL. PostgreSQL provider and deployment topology remain unconfirmed; existing projects in other applications must not be repurposed by assumption.

## 3. Monorepo layout

```text
RuangKampus/
├── frontend/       # Account B: React + TypeScript
├── backend/        # Account A: FastAPI
├── docs/           # Shared project and integration documents
└── tests/          # Automated test suites
```

Initial bootstrap has tracked placeholders only in frontend, backend, and tests. No executable application code is included.

## 4. Target logical flow

```text
Student / TU Admin browser
          |
          v
React + TypeScript frontend
          |
          | HTTPS / JSON — versioned REST
          v
FastAPI application
  |       |        |
  |       |        +--> Authentication / role authorization
  |       +-----------> Reservation / availability services
  +-------------------> Room / schedule / notification services
          |
          v
PostgreSQL
```

This is a target logical architecture. Hosting, network topology, and production deployment have not been configured.

## 5. Planned backend boundaries
- API layer: routing, validation, response schemas, dependencies.
- Identity/access: credential verification, session/token validation, role checks, user scoping.
- Room domain: room data, facilities, hours, status, maintenance.
- Schedule domain: lecture schedules and source provenance.
- Availability domain: authoritative evaluation of schedules, reservations, capacity, hours, and status.
- Reservation domain: request creation, transitions, cancellation, and approval transaction.
- Notification domain: in-app records and actual provider-backed email delivery.
- Audit domain: administrator actions and room/schedule changes.

Refine module/file names after implementation starts; do not duplicate existing domain entities if future work adds them.

## 6. Availability and approval integrity
Absence of a lecture schedule is not enough to mark a room available. Evaluate every applicable blocker. Use a clearly documented interval-overlap policy; half-open intervals may allow adjacent reservations such as 09:00–10:00 and 10:00–11:00 without conflict.

Approval must run in a transaction and re-check:
- the request is still Pending;
- the room is active and usable;
- requested time fits operating hours;
- capacity is sufficient;
- lecture schedule, approved reservations, maintenance, and policy-defined blockers do not overlap;
- concurrency protection prevents competing approvals from both succeeding.

Choose appropriate row locking, isolation, or PostgreSQL constraints after the final data model and policy are confirmed.

## 7. Authentication and data access
- Enforce access on the backend, not only in frontend navigation.
- A Student reads/cancels only their own requests, subject to policy.
- Only TU/Admin can maintain rooms/schedules and approve/reject requests.
- Hash local passwords with a modern password-hashing implementation or use an approved external identity provider.
- Keep tokens/session secrets in local ignored environment files or deployment secret storage.
- Do not log passwords, tokens, or unnecessary personal data.

Token/session approach remains an implementation decision to be documented before auth code is written.

## 8. Database/environment strategy
PostgreSQL is the engine baseline. Provider, project, region, and RuangKampus connection are not confirmed. Use separate development, test, staging, and production resources. Run schema changes only through reviewed migrations. Never test against production or copy credentials from unrelated projects.

## 9. API integration
FastAPI OpenAPI becomes the implementation source of truth once routes exist. `docs/API_CONTRACT.md` is the cross-team planning contract. Account A notifies Account B before breaking changes to responses already consumed by the frontend.

## 10. Deployment
Frontend and backend may be deployed separately. Provider, service names, domains, CI/CD, secrets, and database networking remain open. Do not configure or mutate existing cloud resources until a RuangKampus-specific target is confirmed.

## 11. Security and quality baseline
Validate untrusted input server-side; apply least-privilege authorization; enforce critical invariants with transactions/constraints; configure explicit CORS origins; use secure transport and suitable rate limits at deployment; keep secrets and real personal/campus data out of source control; test normal, boundary, invalid, conflict, unauthorized, and concurrency cases.
