# RuangKampus browser QA

## Route inventory

The inventory is derived from the current `frontend/src/App.tsx` route definitions (25 leaf routes):

- Public/authentication (4): `/login`, `/register`, `/forgot-password`, and `/reset-password` (the last route uses the token-aware reset state).
- Student (11): dashboard, room directory, availability, alternative slots, room detail, booking, reservation list/detail, notifications, profile, and assistant.
- Staff Sekretariat (10): dashboard, reservation list/detail, room list, data imports, room create/edit, schedules/maintenance, notifications, and profile.

There is no standalone maintenance route. Maintenance is a workflow inside `/admin/schedules`. The current source has no Staff AI Assistant route.

## Latest verified CI evidence

**GitHub Actions run #192 — successful on commit `b6ef173ad5744ec8d951448166dd75e6cc6121c1`.**

- Playwright Chromium: **134 passed, 0 failed, 0 skipped, 0 flaky**.
- Unit tests: **8 passed**.
- TypeScript `tsc --noEmit`: passed as part of the production build.
- Vite production build: passed; 14 original brand assets verified/extracted.
- Browser target: Ubuntu GitHub Actions runner; the browser navigated to the production Vite preview over loopback HTTP (not `file://`).
- CI run: https://github.com/munggar/RuangKampus/actions/runs/45839852350
- Complete browser artifact (screenshots, HTML report, result JSON, browser diagnostics and performance JSON; 14-day retention): https://github.com/munggar/RuangKampus/actions/runs/45838979092/artifacts/15127670187

## Screenshot coverage

The successful run produced **208 application screenshots**:

| Folder | Coverage | Count |
|---|---|---:|
| `test-results/screenshots/baseline/` | 25 routes × 1440×900 × light/dark | 50 |
| `test-results/screenshots/final/responsive/` | 25 routes × six target viewports in light mode | 150 |
| `test-results/screenshots/final/states/` | Search/filter active, empty, loading, API error, account menu, approval dialog, booking validation, import preview | 8 |
| **Total** | | **208** |

The six responsive viewports are 1440×900, 1024×768, 820×1180, 768×1024, 390×844, and 320×800. Screenshots are taken after the page heading is visible, the boot splash/loading state has cleared, fonts are loaded, images have decoded, and layout has settled for two animation frames.

## What the browser suite verifies

- Authentication UI: invalid credentials, Student and Staff fixture login, public Student registration, forgot/reset password, unauthenticated protected-route redirect, role-based route redirect, and logout.
- Student UI workflow: availability check, reservation submission and detail, notification read state, assistant fixture response, and profile update.
- Staff UI workflow: approval, rejection with reason, room creation/editing, academic schedule, maintenance/unavailability, import preview/confirmation, and mobile access to Jadwal and Impor.
- Theme: light/dark route rendering and theme persistence across navigation and public authentication pages.
- Responsive behavior: all 25 routes are rendered at the six target viewport sizes; page/body overflow and the main mobile navigation layout are checked. Jadwal and Impor are explicitly checked in Staff mobile navigation.
- Accessibility: 50 axe scans (25 routes × two themes), scoped to WCAG 2.0/2.1 A/AA tags; **zero axe violations across all impact levels**. Keyboard checks cover skip-link/main landmark focus, account-menu Escape handling, approval-dialog focus trap/restoration, and reduced-motion CSS behavior.
- Browser diagnostics: per-test console, page-error, failed-request, and HTTP-response diagnostics are attached and written as JSON; unexpected errors fail the test run.
- Performance sample: navigation, first paint/FCP, LCP when available, layout shifts, long tasks, loaded/broken images, and transferred resources are recorded in `test-results/diagnostics/performance.json`.

The #198 performance sample was captured against a local preview and in-memory fixtures: load event end 98.7 ms, FCP 92 ms, observed LCP 92 ms, CLS estimate 0.03, zero observed long tasks, two of two images loaded, zero broken images, and 401,513 bytes of measured resource transfer. This is a repeatable local fixture sample, **not** production user telemetry, a Lighthouse score, or Core Web Vitals certification.

The production build emitted 405.73 kB JavaScript (118.49 kB gzip) and 82.68 kB CSS (14.73 kB gzip). These are build artifact sizes, not full-page transfer totals.

## Run locally

From `frontend/`:

    npm install
    npx playwright install --with-deps chromium
    VITE_API_BASE_URL=http://127.0.0.1:4173/api/v1 npm run build
    npm run test:e2e

On Windows PowerShell:

    $env:VITE_API_BASE_URL = "http://127.0.0.1:4173/api/v1"
    npm run build
    npm run test:e2e

Playwright starts the Vite preview server on loopback port 4173 using `playwright.config.ts`.

## Data boundary and limitations

All browser E2E flows use deterministic in-memory API fixtures. They do not call a real backend, staging environment, Railway, or production database. Fixture identities use the reserved `.example.invalid` domain and the fixture password is fake; it is not an application credential.

The workbook upload test submits a small browser fixture named `.xlsx` to a mocked preview endpoint. It verifies the file control, UI validation, preview and confirmation flow, but not the backend Excel parser, file-storage pipeline, or database transaction.

Client role redirects and protected-page visibility are frontend checks, **not proof of server-side RBAC**. Real authentication/session refresh against a backend, server-side authorization, reservation conflict enforcement, database persistence, email delivery, actual assistant-provider behavior, import parsing/storage/transaction, and staging cleanup remain **NOT TESTED** until a dedicated staging URL and non-production accounts/secrets are available.

The axe gate explicitly fails on critical/serious findings; the successful #198 artifact was also inspected and contained zero moderate/minor findings. Automated axe scans do not replace manual screen-reader testing or a full WCAG conformance audit. Keyboard coverage is limited to the named flows above.

No test mutates production data. No real credentials, passwords, access tokens, refresh tokens, or cookies are printed or included in artifacts. Traces are retained on test failure; the successful #192 run had no failing tests and therefore no failure trace files.

## Evidence paths inside the browser artifact

- `playwright-report/index.html`: Playwright HTML report.
- `test-results/results.json`: machine-readable results.
- `test-results/screenshots/`: all 208 application screenshots.
- `test-results/diagnostics/browser/`: per-test browser diagnostics.
- `test-results/diagnostics/performance.json`: navigation and resource metrics.
- `test-results/playwright/`: per-test attachments and traces on failure.
