# RuangKampus Frontend

React + TypeScript application for the RuangKampus monorepo.

## Requirements

- Node.js 22.12.0 or newer.
- npm 10 or newer.

## Setup

From this directory:

```bash
npm install
npm run dev
```

Vite runs on port `5173`. Its configuration reads environment variables from the repository root.

Copy the root `.env.example` to a private root `.env` and configure `VITE_API_BASE_URL`, for example:

```env
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

Never put credentials, signing keys, database URLs, or service-role secrets in variables prefixed with `VITE_`; they are exposed to browser code.

## Commands

```bash
npm run dev
npm run build
npm run test
npm run preview
```

## Current implementation

- React 19 + TypeScript + Vite 8.
- React Router 7 is used to preserve compatibility with the current Node 22.16 development runtime while Vite 8 requires Node 22.12 or newer.
- Lucide React provides interface icons.
- Student and TU/Admin application shells have separate navigation and responsive layouts.
- Dashboard cards intentionally show an unavailable state until verified API data exists. No campus statistics or reservations are fabricated.
- Non-dashboard Student and TU/Admin destinations are explicit scaffold placeholders.
- Client-side role routing is for navigation UX only. Backend authorization remains authoritative.
- Access tokens are held in memory only. Persistent session and refresh behavior must be agreed with Account A.
- Login calls the planned `POST /auth/login` route; end-to-end authentication is not verified until Account A implements and tests the API.
- Password recovery is presented but not submitted because no recovery endpoint is documented in the API contract.
- Campus photograph and official logo artwork have not been exported into this repository. The current hero uses the documented brand colors and a text wordmark.

## Responsive behavior

- Desktop: fixed sidebar and workspace topbar.
- Tablet/mobile: compact brand topbar and fixed bottom navigation.
- Layout adaptation is a frontend implementation decision because the available Figma artboards are predominantly mobile-sized; it requires viewport QA after dependencies can be installed.

## Verification

Run `npm install`, `npm run build`, and `npm run test` before merging. The repository bootstrap's API contract remains a planning document; verify implemented routes with Account A before claiming production integration.
