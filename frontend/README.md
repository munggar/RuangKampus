# RuangKampus Frontend

React 19 + TypeScript + Vite frontend. This directory contains the Railway production web source and is deployed from `deploy/frontend-audit-remediation`.

## Production source

- Railway service: `ruangkampus-web`
- Source branch: `deploy/frontend-audit-remediation`
- Production URL: https://ruangkampus-web-production.up.railway.app/

Railway builds this directory with `npm install --no-audit --no-fund && npm run build`, then starts `npm run start`. The Node server in `server.mjs` serves `dist/` and provides SPA fallback for application routes.

## Requirements

- Node.js 22.12 or newer.
- npm 10 or newer.
- A running RuangKampus backend API.

## Local development

```powershell
cd frontend
Copy-Item .env.example .env
npm install
npm run dev
```

The Vite dev server runs at http://localhost:5173. Set `VITE_API_BASE_URL` in `frontend/.env` to the backend API base including `/api/v1`, for example `http://localhost:8000/api/v1`.

## Tests and build

```powershell
npm run test
npm run build
```

Browser E2E tests use Playwright:

```powershell
npx playwright install chromium
npm run test:e2e
```

## Features and architecture

- `src/api.ts`: versioned REST client and response handling.
- `src/auth.tsx`: authentication/session context.
- `src/App.tsx`: public, Student, and Staff Sekretariat routes.
- `src/layout.tsx`: responsive shells, navigation, profile, and theme controls.
- `src/student-pages.tsx`: student room discovery, assistant, bookings, profile, and notification workflows.
- `src/admin-pages.tsx`: Staff Sekretariat workflows.
- `src/admin-data-imports.tsx`: room and campus data import UI.
- `src/styles.css` and `src/styles/tokens.css`: application styling and responsive tokens.

RUKKA AI is the Student-facing assistant. It uses backend-verified room and availability results. An optional backend-side OpenRouter/Gemma layer can shape conversational responses when configured; its key must never be placed in browser code. Staff Sekretariat uses separate management pages and does not receive the Student assistant route.

## Production configuration and security

Set `VITE_API_BASE_URL` before building. Vite embeds this public API URL into generated JavaScript, so changing it requires a rebuild. It is not a secret. Never place JWT keys, database credentials, SMTP passwords, or OpenRouter/Brevo API keys in any `VITE_*` variable.

The backend must allow the exact frontend origin in `CORS_ORIGINS`. Production uses HTTPS and secure refresh cookies. For the complete local stack, use the repository-root [Docker Compose instructions](../README.md).
