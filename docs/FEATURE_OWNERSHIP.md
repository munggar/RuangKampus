# Feature Ownership and Collaboration

## Account A — Munggar Fajar Muharram
**Role:** Backend Lead and System Integration Lead.

Owns:
- Backend source code and architecture.
- Database schema, migrations, constraints, and data-access layer.
- Authentication, sessions/tokens, and backend authorization.
- Student and Staff Sekretariat role enforcement.
- Room Management API and business rules.
- Smart Availability Engine and conflict detection.
- Reservation state machine and transactional approvals.
- Staff Sekretariat backend operations and audit history.
- In-app notifications and provider-backed email services.
- Academic schedule import pipeline.
- AI recommendation backend after core availability/reservation is stable.
- OpenAPI/API documentation, backend tests, and backend deployment configuration.

Branch namespace: `backend/<feature>`.

## Account B — Adil Muslim Saputra
**Role:** Frontend Lead and UI/UX Lead.

Owns:
- Frontend source code and application structure.
- React + TypeScript pages, layouts, components, and client routing.
- Responsive behavior and accessibility.
- UI state, presentation validation, and API-client integration.
- Figma screens, design system, reusable components, colors, typography, and prototypes.
- Frontend tests and frontend build/lint configuration.

Branch namespace: `frontend/<feature>`.

## Shared responsibilities
- Agree on request/response contracts before integration.
- Coordinate breaking API changes before implementation.
- Verify role-based journeys and loading/empty/error/unauthorized states.
- Review pull requests crossing ownership boundaries.
- Maintain feature status and known limitations.

## File/resource boundaries

| Resource | Primary owner | Rule |
|---|---|---|
| `backend/` | Account A | Account B coordinates before backend edits |
| DB schema and migrations | Account A | Account B consumes documented contracts |
| Backend tests | Account A | End-to-end scenarios planned jointly |
| `frontend/` | Account B | Account A must not overwrite or redesign |
| Figma files/design system | Account B | Account A may inspect, not edit |
| `docs/API_CONTRACT.md` | Account A maintains | Contract changes coordinated with Account B |
| `docs/MASTER_BRIEF.md` | Shared; Account A maintains repository copy | Scope changes require agreement |
| `docs/FEATURE_OWNERSHIP.md` | Shared | Update by agreement |
| `docs/PROJECT_ARCHITECTURE.md` | Account A maintains | Coordinate frontend architecture changes |

## Git collaboration
- `main` is the stable reviewed branch; `develop` is the integration branch.
- Feature branches start from `develop`.
- No direct commits to `main`, no force-push, and no automatic merges.
- Use pull requests with test evidence.
- Never overwrite another owner's unreviewed work.
- Never commit credentials, populated local environment files, or private data.
