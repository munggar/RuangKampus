import { test, expect, installMockApi, saveScreenshot, waitForPageReady } from "./support";

const capture = (page: Parameters<typeof saveScreenshot>[0], name: string) =>
  saveScreenshot(page, "test-results/screenshots/final/states/" + name + "-1440-light.png");

test("state screenshot: Student room directory with active search filter", async ({ page }) => {
  await installMockApi(page, "Student");
  await page.goto("/student/rooms");
  await waitForPageReady(page);

  await page.getByLabel("Cari ruangan").fill("Ruang Diskusi");
  await page.getByRole("button", { name: /Terapkan filter/ }).click();
  await expect(page.getByText("1 ruangan", { exact: true })).toBeVisible();
  await expect(page.getByRole("link", { name: "Lihat detail", exact: true })).toBeVisible();
  await capture(page, "student-room-directory-filter-active");
});

test("state screenshot: Student directory empty state", async ({ page }) => {
  await installMockApi(page, "Student");
  await page.route("**/api/v1/rooms?*", (route) =>
    route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [], meta: { page: 1, limit: 100, total: 0, total_pages: 0 } }),
    }),
  );
  await page.goto("/student/rooms");
  await waitForPageReady(page);
  await expect(page.getByText("Tidak ada ruangan yang cocok")).toBeVisible();
  await capture(page, "student-room-directory-empty");
});

test("state screenshot: Student directory loading state", async ({ page }) => {
  await installMockApi(page, "Student");
  let releaseRequest!: () => void;
  const pending = new Promise<void>((resolve) => { releaseRequest = resolve; });
  await page.route("**/api/v1/rooms?*", async (route) => {
    await pending;
    await route.fulfill({
      status: 200,
      contentType: "application/json",
      body: JSON.stringify({ data: [], meta: { page: 1, limit: 100, total: 0, total_pages: 0 } }),
    });
  });

  await page.goto("/student/rooms");
  await page.locator("h1").first().waitFor({ state: "visible" });
  await expect(page.getByText("Memuat direktori ruangan…")).toBeVisible();
  await capture(page, "student-room-directory-loading");
  releaseRequest();
  await waitForPageReady(page);
});

test("state screenshot: Student directory API error", async ({ page }) => {
  await installMockApi(page, "Student");
  await page.route("**/api/v1/rooms?*", (route) =>
    route.fulfill({
      status: 503,
      contentType: "application/json",
      body: JSON.stringify({ detail: "API fixture intentionally unavailable for this visual state." }),
    }),
  );
  await page.goto("/student/rooms");
  await waitForPageReady(page);
  await expect(page.getByRole("alert")).toContainText("API fixture intentionally unavailable");
  await capture(page, "student-room-directory-error");
});

test("state screenshot: account dropdown expanded", async ({ page }) => {
  await installMockApi(page, "Student");
  await page.goto("/student/dashboard");
  await waitForPageReady(page);

  const trigger = page.locator(".account-trigger");
  await trigger.click();
  await expect(trigger).toHaveAttribute("aria-expanded", "true");
  await expect(page.getByRole("menuitem", { name: "Keluar" })).toBeVisible();
  await capture(page, "student-account-dropdown-open");
});

test("state screenshot: Admin approval dialog open", async ({ page }) => {
  await installMockApi(page, "Staff Sekretariat");
  await page.goto("/admin/reservations");
  await waitForPageReady(page);

  await page.getByRole("button", { name: "Setujui", exact: true }).first().click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("heading", { name: "Setujui permohonan?" })).toBeVisible();
  await capture(page, "admin-reservation-approval-dialog");
});

test("state screenshot: booking validation error", async ({ page }) => {
  await installMockApi(page, "Student");
  await page.goto("/student/rooms/room-e2e-001/book");
  await waitForPageReady(page);

  await page.getByLabel("Jam mulai").fill("12:00");
  await page.getByLabel("Jam selesai").fill("10:00");
  await page.getByRole("button", { name: "Periksa ketersediaan" }).click();
  await expect(page.getByRole("alert")).toContainText("Jam selesai harus lebih akhir dari jam mulai");
  await capture(page, "student-booking-validation-error");
});

test("state screenshot: import workbook preview", async ({ page }) => {
  await installMockApi(page, "Staff Sekretariat");
  await page.goto("/admin/data-imports");
  await waitForPageReady(page);

  await page.locator('input[type="file"]').setInputFiles({
    name: "rooms-preview-fixture.xlsx",
    mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    buffer: Buffer.from("browser-fixture-not-a-real-xlsx-workbook"),
  });
  await page.getByRole("button", { name: "Pratinjau & validasi" }).click();
  await expect(page.getByText("Hasil pratinjau")).toBeVisible();
  await expect(page.getByText("Ruang Diskusi Uji").first()).toBeVisible();
  await capture(page, "admin-import-preview");
});
