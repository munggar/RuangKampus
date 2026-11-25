# RuangKampus — Development Status

Last updated: 2026-11-25

## Current phase
**Phase 1 — Frontend Foundation.** Repository bootstrap is complete. The initial frontend foundation is on a feature branch and has not been merged into `develop`.

## Verified repository baseline
- [x] GitHub repository `munggar/RuangKampus` exists.
- [x] `main` and `develop` are available.
- [x] Bootstrap commit `86c2fa77480a268a08e86d5d080684d9c731349c` is present on both branches at branch creation.
- [x] Shared project documentation and feature ownership boundaries are present.
- [x] `frontend/` was empty except for its placeholder at the base commit.
- [x] Connected RuangKampus Figma file and earlier audit are available in the working conversation.
- [x] React + TypeScript + Vite frontend foundation added on `feat/frontend-foundation`.
- [x] Design tokens and Student/TU login foundations added.
- [x] API client scaffolding added for the planned API contract.
- [ ] Dependencies installed and lockfile generated.
- [ ] Frontend build and unit tests executed in a provisioned environment.
- [ ] Backend routes implemented and verified against OpenAPI.
- [ ] Authentication and the role/session strategy finalized with Account A.
- [ ] Student booking and TU/Admin workflows implemented.
- [ ] Notifications, schedule import, and AI workflows implemented.

## Frontend implementation notes
- Framework: React 19 + TypeScript.
- Build tool: Vite.
- Package manager: npm.
- Routing: React Router.
- Icons: Lucide React.
- Styling: CSS variables and component CSS derived from the Figma audit; no UI framework was present in the monorepo bootstrap.
- Vite reads environment values from the repository root. The root `.env.example` already defines `VITE_API_BASE_URL`.
- The login screen includes Student and TU/Admin role selection, credential inputs, password visibility, feedback, and a password-recovery route.
- Access tokens are held in memory only. Persistent session and refresh behavior requires agreement with Account A.
- Password recovery is not wired because its endpoint is not in the API contract.
- No backend, database, migrations, or cloud configuration was changed by Account B.

## Figma and asset notes
- The linked Figma file has a mobile-first screen set, Light/Dark variables, Inter typography, blue brand tokens, and reusable component patterns.
- The Figma login designs show campus photography and the official wordmark/logo. These exact image/vector assets have not yet been exported to the repository; the current login hero uses the brand colors and a text wordmark.
- Desktop and tablet artboards remain incomplete; responsive behavior is an implementation requirement to validate with the team.

## API integration status
- `docs/API_CONTRACT.md` is a planning baseline and explicitly states that routes are planned, not implemented.
- The frontend API base path and auth request shape follow that plan but have not been verified against a running service.
- No production API integration is claimed.
- Tokens are not written to localStorage or sessionStorage.
- The login role control is a UI selection only; backend authorization remains authoritative and must be finalized with Account A.
- Password recovery and persistent “remember me” behavior remain unavailable until agreed API/session support exists.

## Next dependencies and tasks
1. Account A to implement backend endpoints and publish tested OpenAPI.
2. Account A and Account B to finalize token/session/refresh behavior and exact role enum.
3. Export/provide approved campus photography and logo artwork.
4. Implement Student dashboard, room catalogue/details, availability, booking, and reservation tracking after contracts are available.
5. Implement TU/Admin workflows, notifications, schedule UI, and AI presentation after corresponding endpoints are verified.
6. Confirm desktop/tablet layout requirements and complete responsive QA.

## Verification status
- GitHub branches, tree, bootstrap commit, README, Master Brief, Architecture, Feature Ownership, API Contract, and environment example were inspected.
- Figma Student and Administrator Login frame metadata was rechecked.
- Dependency installation, build, test execution, browser testing, and end-to-end integration have not been executed in this environment.
- This status file is updated on the frontend feature branch for coordination; merge requires review under the repository workflow.
