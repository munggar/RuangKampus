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

## Current implementation boundary

- Login screen follows the connected Figma Student and Administrator login patterns.
- Login calls the planned `POST /auth/login` route.
- The API contract currently documents planned routes only; a running backend and verified OpenAPI contract are required for end-to-end authentication.
- Access tokens are held in memory only. Persistent session and refresh behavior must be agreed with Account A.
- Password recovery is presented but not submitted because no recovery endpoint is documented in the API contract.
- The campus photograph and official logo artwork have not been exported into this repository. The current hero uses the documented brand colors and a text wordmark rather than invented assets.

## Design tokens

Values in `src/styles/tokens.css` are based on the connected Figma audit. Where a semantic token or responsive behavior was not explicitly defined in Figma, the implementation is an identified frontend foundation decision and must be reviewed during UI QA.
