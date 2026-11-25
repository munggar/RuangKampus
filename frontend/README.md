# RuangKampus Frontend

React 19 + TypeScript + Vite 8 frontend for the RuangKampus monorepo.

## Requirements
- Node.js 22.12.0 or newer.
- npm 10 or newer.
- A running RuangKampus FastAPI service.

## Setup
Run npm install from this directory. Create a private .env at the repository root (do not commit it) and set VITE_API_BASE_URL=http://localhost:8000/api/v1. Run npm run dev to start Vite on port 5173. Use npm run build and npm run test before merging.

Never place credentials, signing keys, database URLs, SMTP credentials, or service-role secrets in variables prefixed with VITE_; they are exposed to browser code.

## Architecture
- src/api.ts: versioned REST client, response envelope handling, bearer access token, HttpOnly refresh-cookie flow.
- src/auth.tsx: in-memory authentication context and session restoration.
- src/App.tsx: public, Student, and TU/Admin routes.
- src/layout.tsx: shared responsive shells, Liquid Glass mobile navigation, theme selector.
- src/pages.tsx: Student and TU/Admin workflows.
- src/styles/: Figma-derived light/dark tokens and responsive UI.

The browser stores the access token in memory only. On reload, the app calls POST /auth/refresh to rotate the HttpOnly refresh cookie and restore the session. The backend remains authoritative for every role and reservation rule.

## Integration notes
- API base path: /api/v1.
- Auth success payloads are direct objects. Business endpoints use { success, message, data, meta }.
- Dates and times use Asia/Jakarta by default.
- Availability checks on the client are advisory; the backend revalidates reservation creation and approval.
- Room operating hours are required for rooms to become reservable. The room form exposes them even though the initial mobile Figma form does not.
- The AI tab intentionally opens a not-yet-available notice. The current backend has no AI endpoint/provider, so no synthetic chatbot or recommendation responses are generated.
- Room image upload is not supported by the backend; the interface only renders API-provided photo URLs.
- Figma artboards are primarily 390x844 mobile screens. Desktop/tablet layouts adapt these screens and require viewport QA.

Only frontend/ is changed by this branch. Backend source, database schema, migrations, environment secrets, and cloud services remain under the backend owner's control.

## GitHub Pages preview

The production Vite build uses the project-site base path `/RuangKampus/` and React Router uses Vite's `BASE_URL`. The Pages workflow copies `index.html` to `404.html` so SPA deep links can load after refresh.

GitHub Pages hosts only the static frontend. It does not run FastAPI, PostgreSQL, migrations, or SMTP. Until a public backend URL is configured, the deployed site runs in preview mode and shows a notice that login/data are unavailable.

After deploying the backend to a separate HTTPS host and applying its reviewed migrations:
- Set the repository Actions variable `VITE_API_BASE_URL` to the public API base URL, including `/api/v1`.
- Configure backend `CORS_ORIGINS` to include `https://munggar.github.io`.
- Because the API and Pages site use different sites, configure the refresh cookie as `COOKIE_SECURE=true` and `COOKIE_SAMESITE=none`; browser third-party-cookie restrictions can still affect refresh sessions.
- Set `PASSWORD_RESET_BASE_URL` to `https://munggar.github.io/RuangKampus/reset-password`.
- Production backend startup also requires a dedicated PostgreSQL URL, a strong JWT secret, and the SMTP provider required by its production settings.

To enable Pages, a repository administrator must open Settings -> Pages and set Build and deployment -> Source to GitHub Actions. Then set the repository Actions variable `ENABLE_GITHUB_PAGES` to `true`. The Pages workflow deploys on pushes to `main`; it can also be run manually from a selected branch for a preview.
