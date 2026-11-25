# RuangKampus

RuangKampus is a campus room discovery and reservation platform. Students can discover rooms, check availability, submit reservation requests, and track their own requests. Authorized TU/Admin staff maintain rooms and schedules, review requests, and manage campus room resources.

## Current implementation status

The backend core API is implemented under `backend/` using Python, FastAPI, SQLAlchemy, Alembic, and PostgreSQL as the target database engine. Automated tests run against isolated in-memory SQLite for portability; PostgreSQL-specific row-lock/concurrency behavior still requires a dedicated PostgreSQL integration test.

The frontend foundation exists on a separate `feat/frontend-foundation` branch. Account B (Adil Muslim Saputra) owns frontend implementation and UI/UX. Account A (Munggar Fajar Muharram) owns backend source, database schema/migrations, API contracts, and backend tests. The frontend feature branch remains separate; Account A did not modify it.

## Monorepo layout

```text
frontend/   React + TypeScript application (Account B ownership)
backend/    FastAPI backend, SQLAlchemy models, Alembic migrations (Account A ownership)
docs/       Shared brief, architecture, API contract, schema, and development status
tests/      Shared/end-to-end test space; backend tests currently live in backend/tests/
```

## Technology baseline

- Frontend: React + TypeScript.
- Backend: Python + FastAPI.
- ORM: SQLAlchemy 2.x.
- Migrations: Alembic.
- Database engine: PostgreSQL for shared/staging/production deployments. Isolated SQLite is used for fast local/API tests only.
- API: versioned REST under `/api/v1`, with generated OpenAPI and Swagger UI.

This follows the existing Master Project Brief and repository architecture decision. No RuangKampus-specific cloud PostgreSQL resource has been identified; do not reuse unrelated databases.

## Quick start — backend

See [backend/README.md](backend/README.md) for full setup, environment variables, migrations, admin bootstrap, testing, and endpoint groups.

```bash
cd backend
python -m venv .venv
# Windows: .venv\\Scripts\\Activate.ps1
# macOS/Linux: source .venv/bin/activate
pip install -r requirements.txt
# Copy backend/.env.example to backend/.env and configure private values.
PYTHONPATH=src alembic upgrade head
PYTHONPATH=src uvicorn ruangkampus.main:app --reload --host 127.0.0.1 --port 8000
```

API docs: `http://127.0.0.1:8000/api/v1/docs`  
OpenAPI JSON: `http://127.0.0.1:8000/api/v1/openapi.json`  
Health: `http://127.0.0.1:8000/health`

For tests, use only isolated databases:

```bash
cd backend
PYTHONPATH=src pytest -q
```

## Security rules

- Never commit `.env`, populated credentials, API keys, SMTP passwords, private keys, tokens, or connection strings containing credentials.
- `.env.example` files contain placeholders only; generate secrets locally or in the hosting provider's secret manager.
- Public registration always creates a Student; role assignment is server-controlled.
- Students can only access their own reservations and notifications.
- Only TU/Admin can maintain rooms/schedules and approve/reject reservations.
- Reservation approval re-checks availability in a database transaction.
- Email is only reported delivered after a configured SMTP operation is confirmed. Local mailbox mode is not actual email delivery.
- Never use production data or a production database for automated tests.

## Git workflow

- `main`: stable reviewed baseline.
- `develop`: integration branch.
- `backend/<feature>`: Account A feature branches.
- `frontend/<feature>`: Account B feature branches.
- Do not commit directly to `main`, force-push, or automatically merge feature branches. Use pull requests and coordinate cross-owner changes.

## Documentation

- [Master Project Brief](docs/MASTER_BRIEF.md)
- [Feature Ownership](docs/FEATURE_OWNERSHIP.md)
- [Project Architecture](docs/PROJECT_ARCHITECTURE.md)
- [API Contract](docs/API_CONTRACT.md)
- [Database Schema](docs/DATABASE_SCHEMA.md)
- [Development Status](docs/DEVELOPMENT_STATUS.md)

## Release readiness

Not production-ready until a RuangKampus PostgreSQL resource is provisioned, migration and concurrency tests pass against PostgreSQL, Account B's full frontend contracts are reviewed, SMTP is configured, and deployment/operations are validated. CSV/XLSX schedule import, AI recommendations, and media upload are not implemented in this API slice.
