# Production source release — 27 November 2026

## Purpose

This release snapshot makes the code that is actually running in the two Railway application services available from one GitHub `main` branch and one ZIP download. It is a source snapshot, not a database backup.

## Verified Railway source at release time

| Service | Railway source branch | Deployed commit | Source directory |
|---|---|---|---|
| `ruangkampus-api` | `develop` | `b9443b173d7898b4647219d239c52dbf8c2a7c76` | `/backend` |
| `ruangkampus-web` | `deploy/frontend-audit-remediation` | `0b6dfb0f5a0351dd542b231af83d83a1753d751c` | `/frontend` |

Railway project: `RuangKampus`, production environment. The backend uses the production PostgreSQL service and mounts persistent storage at `/data`. Frontend and backend remain independently deployed services.

## How this repository snapshot was assembled

- The complete `backend/` directory and shared backend-side project files were sourced from the backend production commit.
- The complete `frontend/` directory was sourced from the frontend production commit.
- The GitHub Actions `backend-ci.yml` workflow was retained from the backend snapshot.
- The `frontend-ci.yml` workflow file was taken from the deployed frontend branch so the repository contains its browser/unit test workflow.
- The official `RuangKampus-Brand-Assets (1).zip` archive is retained at the repository root because the frontend build script verifies and extracts these official assets.
- The root documentation and local Docker Compose instructions were updated for this combined source release.

The branch pointers used by Railway were not changed by this snapshot operation.

## Run the full app locally

Use the root `README.md` and `.env.example`. Docker Compose provisions a disposable local PostgreSQL instance, runs the Alembic migrations against that local database, starts the FastAPI service, builds the frontend with the local API URL, and serves the frontend on port 5173.

Do not point this Compose stack at the Railway production database. Do not use production secrets in local configuration.

## What is intentionally not included

- Railway environment variable values, API keys, signing keys, SMTP credentials, access tokens, or database credentials.
- Production database, user accounts, room records, bookings, notifications, or audit history.
- Persistent room photos from Railway's volume.
- Local `.env` files, virtual environments, `node_modules`, build artifacts, and local SQLite/PostgreSQL databases.

## Reproducibility notes

The root README includes local Docker and native setup commands. Frontend branding is verified by the build script against the checked-in official brand archive. Backend migrations are under `backend/alembic/versions/`. GitHub Actions workflows run backend and frontend validation on pushes and pull requests.
