# RuangKampus browser QA

## What this suite verifies

Run the production Vite preview in Chromium with Playwright. The suite captures the 25 leaf routes actually present in src/App.tsx:

- Public: login, registration, forgot password, reset password.
- Student (11): dashboard, room directory, availability, alternative slots, room detail, booking, reservation list/detail, notifications, profile, assistant.
- Staff Sekretariat (10): dashboard, reservation list/detail, room list, data imports, room create/edit, schedules and maintenance, notifications and profile.

There is no separate maintenance route: maintenance is a workflow inside /admin/schedules.

The suite captures every route in light and dark theme, checks all protected routes at 1440x900, 1024x768, 820x1180, 768x1024, 390x844 and 320x800, and saves responsive captures for every Student and Staff Sekretariat route.

It also covers browser interactions for Student and Staff login, registration/password flows, role redirects, Student availability and reservation submission, notifications, the Student assistant, profile editing, Staff approval/rejection, room create/edit, academic schedule and maintenance forms, workbook preview/commit UI, keyboard behavior, reduced motion, axe accessibility, console/network diagnostics and navigation/asset timing.

## Run locally

From frontend/:

    npm install
    npx playwright install --with-deps chromium
    VITE_API_BASE_URL=http://127.0.0.1:4173/api/v1 npm run build
    npm run test:e2e

On Windows PowerShell, set the environment variable for the current process before building:

    $env:VITE_API_BASE_URL = "http://127.0.0.1:4173/api/v1"
    npm run build
    npm run test:e2e

Playwright starts vite preview on loopback port 4173 using playwright.config.ts.

## Data boundary and limits

ALL current E2E workflows use deterministic in-memory API fixtures. They do not call a real backend, staging environment, Railway, or production database. Fixture identities use the reserved .example.invalid domain. The fixture login password is intentionally fake and must never be used as an application credential.

The workbook upload test sends a small browser fixture named .xlsx to a mocked preview endpoint. It verifies the file control, validation feedback, preview state and confirmation interaction; it does not verify the backend Excel parser, file-storage pipeline or import database transaction.

Role redirects and protected-page visibility are client UI checks. They are not proof of server-side RBAC. Real authentication, token refresh against the live API, backend authorization, reservation conflict rules, persistence, email delivery, assistant service behavior and staging cleanup remain NOT TESTED until a dedicated staging URL and non-production test accounts/secrets are configured.

No test mutates production data. The browser workflow does not require or print passwords, cookies, access tokens or refresh tokens.

## Evidence output

- test-results/screenshots/: page and responsive screenshots.
- test-results/results.json: machine-readable Playwright results.
- test-results/playwright/: traces, failure screenshots and per-test browser diagnostics.
- playwright-report/: HTML report with test details and attached axe/performance/diagnostic JSON.
- test-results/diagnostics/performance.json: browser navigation and asset timing/transfer sample.

First-run baseline evidence is retained in the run #182 artifact. Reviewed and corrected captures are written under screenshots/final/; all 25 leaf routes are captured in both themes and at all six target viewports. GitHub Actions uploads reports and screenshots as a 14-day artifact.

Performance figures are browser timing and resource-transfer measurements from the Chromium run. They are not Lighthouse scores or Core Web Vitals certification.
