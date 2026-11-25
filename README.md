# RuangKampus

RuangKampus is a campus room discovery and reservation platform. It helps students find rooms that fit their needs and submit reservation requests, while authorized TU/Admin staff manage rooms, schedules, and reservation decisions.

> **Project status:** repository bootstrap only. This repository initially had no source code. Application endpoints, frontend screens, database migrations, and production integrations are not implemented by this bootstrap.

## Planned technology

- **Frontend:** React + TypeScript.
- **Backend:** Python + FastAPI.
- **Database:** PostgreSQL.
- **API style:** versioned REST API, initially under `/api/v1`.
- **Database migrations:** Alembic is proposed if SQLAlchemy is adopted.

The stack follows the Master Project Brief and supports a typed web client, validated API contracts, relational integrity, and transactional reservation approval. The database provider and deployment topology remain open until a RuangKampus-specific resource is confirmed.

## Repository layout

```text
frontend/   React + TypeScript application owned by Account B
backend/    FastAPI application and backend services owned by Account A
docs/       Product brief, ownership, architecture, API and database planning
tests/      Automated test suites
```

See [Project Architecture](docs/PROJECT_ARCHITECTURE.md), [Feature Ownership](docs/FEATURE_OWNERSHIP.md), [API Contract](docs/API_CONTRACT.md), and [Database Schema](docs/DATABASE_SCHEMA.md).

## Local development

The bootstrap intentionally does not install dependencies or generate application code. After the application owners add their scaffolds:

1. Copy `.env.example` to a local `.env` and fill it with locally provisioned values.
2. Install dependencies using instructions maintained by each application owner.
3. Start the backend and frontend using their respective development commands.
4. Use only a dedicated development/test database for automated tests.

Never commit `.env`, API keys, passwords, connection strings, private certificates, or other credentials. Use hosting-provider secret/environment-variable facilities for deployed environments.

## Git workflow

- `main`: stable, reviewed project baseline.
- `develop`: integration branch for accepted work.
- Feature branches start from `develop`:
  - `backend/<feature>` for Account A work.
  - `frontend/<feature>` for Account B work.
  - `docs/<topic>` for coordinated documentation changes.

Do not commit directly to `main`. Open a pull request to `develop`, provide test evidence, and coordinate cross-owner changes before merging.

## Project rules

- Do not replace existing architecture without technical evidence and agreement.
- Do not use production data or production databases for tests.
- Do not treat sample values, mockups, or unverified campus information as official data.
- Re-check room availability when TU/Admin approves a reservation.
- Approval must be transactional and protected against concurrent conflicting approvals.
- AI recommendations may only use facts returned by the backend and may never approve reservations.

## Ownership and status

Account A (Munggar Fajar Muharram) owns backend implementation, database schema/migrations, API, authorization, reservation logic, notifications, and backend tests.

Account B (Adil Muslim Saputra) owns frontend implementation and UI/UX. The frontend folder is reserved for Account B; backend work must not overwrite frontend files.

See [Development Status](docs/DEVELOPMENT_STATUS.md) for verified progress and open dependencies.
