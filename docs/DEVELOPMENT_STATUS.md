# RuangKampus — Development Status

Last updated: 2026-11-25

## Current phase
**Phase 1.1 — Foundation Verification & Application Shell.** Work is on `feat/frontend-foundation`; PR #1 remains open as Draft and has not been merged.

## Verified repository baseline
- [x] GitHub repository `munggar/RuangKampus` exists.
- [x] `main` and `develop` are available.
- [x] Latest checked `develop` commit is `86c2fa77480a268a08e86d5d080684d9c731349c`.
- [x] Feature branch base is current `develop`; feature branch was one commit ahead before Phase 1.1 changes.
- [x] Shared project documentation and ownership boundaries are present.
- [x] Existing frontend scaffold and login foundation inspected before modification.
- [x] Application shell, Student/TU navigation, dashboards, and placeholder destinations added.
- [x] Navigation config tests added.
- [ ] Dependency installation and lockfile generation.
- [ ] Frontend build and automated tests executed.
- [ ] Browser testing and responsive viewport QA.
- [ ] Backend routes implemented and verified against OpenAPI.
- [ ] Authentication and role/session strategy finalized with Account A.

## Frontend technology
- Framework: React 19 + TypeScript.
- Build tool: Vite 8.
- Package manager: npm.
- Routing: React Router 7 (selected for Node 22.16 compatibility; React Router 8 requires Node 22.22 or newer).
- Icons: Lucide React.
- Styling: CSS variables and component styles based on the Figma audit; no UI framework was present in the repository bootstrap.
- Vite reads environment values from the repository root. The root `.env.example` defines `VITE_API_BASE_URL`.

## Phase 1.1 implementation
- Student layout: sidebar navigation for desktop; bottom navigation for tablet/mobile.
- TU/Admin layout: separate six-item navigation, with compact mobile labels.
- Shared topbar, page title, notification route link, profile menu, logout action, and light/dark toggle.
- Student dashboard scaffold: quick room-search action, unavailable reservation summary states, upcoming reservation and recent activity empty states.
- TU/Admin dashboard scaffold: unavailable summary cards, pending request, upcoming room use, and activity empty states.
- Student and Admin non-dashboard routes currently use explicit "not implemented" placeholders.
- Dashboard placeholders do not contain invented reservations, counts, names, or campus data.
- Client-side role route guard is only a navigation UX control and does not replace backend authorization.
- Login now navigates after server response only when the returned role matches the role selected at sign-in.

## Design notes
- Colors, typography, spacing, and radii use the prior Figma audit tokens.
- Exact official wordmark/logo and campus photo artwork have not yet been exported; text brand treatment and brand-color hero remain fallback.
- Desktop/sidebar composition is an implementation adaptation because Figma's verified screens are predominantly 390 × 844 mobile frames; it needs design review and responsive browser QA.
- Manual theme toggle applies audited Light/Dark variables. Theme persistence is not implemented.

## API integration status
- `docs/API_CONTRACT.md` is a planning baseline and explicitly states that routes are planned, not implemented.
- The API client and login response shape follow that planning document and are not verified against a running service.
- No production API integration is claimed.
- Access tokens are not written to localStorage or sessionStorage.
- Session persistence, refresh strategy, exact role enum, and notification APIs need confirmation from Account A.
- Password recovery is not wired because no recovery endpoint is documented.
- Dashboard metrics and reservation data are not mocked; the UI identifies their unavailable API state.

## Verification and blockers
- GitHub repository, branch refs, PR #1, compare status, frontend source, README, API contract, ownership and project documentation inspected.
- Before Phase 1.1, branch comparison showed one feature commit ahead of `develop` and no commits behind; no new Munggar changes were observed on `develop`.
- Runtime Node version is `v22.16.0`; Vite 8's Node requirement is satisfied. React Router 8's Node 22.22 minimum is not satisfied, so the dependency is moved to React Router 7.
- Git clone and npm registry access failed because this environment could not resolve `github.com`; dependency installation, lockfile generation, build, unit test execution, browser testing, and responsive QA could not be run.
- GitHub tree and commit verification are available, but runtime correctness remains unverified until commands above are run in a network-enabled development environment.
- No backend source, database schema, migration, cloud configuration, or secret file was modified.

## Next dependencies and tasks
1. Run `npm install`, commit generated `package-lock.json`, and run build/tests in a network-enabled local environment.
2. Perform browser QA for login, Student/TU application shell, navigation, profile menu, theme toggle, mobile, tablet, and desktop.
3. Account A to publish tested OpenAPI and confirm token/session behavior and exact role enum.
4. Provide approved campus photograph and official logo assets.
5. Once Phase 1.1 passes QA, begin Phase 2 — Student Room Catalogue & Room Discovery.
