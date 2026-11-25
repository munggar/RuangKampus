# RuangKampus Frontend

React 19 + TypeScript + Vite 8 frontend for the RuangKampus monorepo.

## Requirements and local setup

- Node.js 22.12.0 or newer.
- npm 10 or newer.
- A running RuangKampus FastAPI service.

From this directory:

```bash
npm install
```

Create a private `.env` file in this directory (do not commit it) and set `VITE_API_BASE_URL=http://localhost:8000/api/v1`. Run `npm run dev` to start Vite on port 5173. Use `npm run test` and `npm run build` before merging.

Never place credentials, signing keys, database URLs, SMTP credentials, or service-role secrets in variables prefixed with `VITE_`; they are exposed to browser code.

## Architecture

- `src/api.ts`: versioned REST client, response envelope handling, bearer access token, HttpOnly refresh-cookie flow.
- `src/auth.tsx`: in-memory authentication context and session restoration.
- `src/App.tsx`: public, Student, and TU/Admin routes.
- `src/layout.tsx`: shared responsive shells, mobile navigation, theme selector.
- `src/pages.tsx`: Student and TU/Admin workflows.
- `src/styles/`: light/dark tokens and responsive UI.
- `server.mjs`: production static-file server with SPA route fallback.

The browser stores the access token in memory only. On reload, the app calls `POST /auth/refresh` to rotate the HttpOnly refresh cookie and restore the session. The backend remains authoritative for every role and reservation rule.

## API integration

- API base path: `/api/v1`.
- Auth success payloads are direct objects. Business endpoints use `{ success, message, data, meta }`.
- Dates and times use `Asia/Jakarta` by default.
- Availability checks on the client are advisory; the backend revalidates reservation creation and approval.
- Room operating hours must be configured before the backend treats a room as reservable.
- The Student room assistant uses the backend's stateless, database-grounded `RULE_BASED` search endpoint. It is not a generative LLM. The TU/Admin page provides operational shortcuts because that endpoint is Student-only.
- Alternative-slot responses are suggestions only; they do not create reservations.
- Room image upload is not supported by the backend; the interface only renders API-provided photo URLs.
- Desktop/tablet layouts adapt the mobile-first design and still require viewport QA.

## Production deployment

The Railway frontend service uses the repository root directory `/frontend`, runs `npm run build`, then `npm run start`. The included Node server serves `dist/` and falls back to `index.html` for React Router deep links.

Set `VITE_API_BASE_URL` on the Railway frontend service to the public backend URL including `/api/v1`. Because Vite embeds this value at build time, changing it triggers a frontend rebuild.

The frontend is served from the domain root (`/`) by default. The optional GitHub Pages workflow sets `GITHUB_PAGES=true` to use its project path `/RuangKampus/`.

Backend configuration must allow the exact frontend origin in `CORS_ORIGINS`; use secure refresh cookies (`COOKIE_SECURE=true`). With the Railway-provided frontend and API domains, both use HTTPS. Keep `VITE_API_BASE_URL` free of secrets.

## GitHub Pages preview

GitHub Pages hosts only the static frontend, not FastAPI, PostgreSQL, migrations, or SMTP. The Pages workflow is separate from the Railway deployment and requires the repository Pages source to be set to GitHub Actions and `ENABLE_GITHUB_PAGES=true`.
