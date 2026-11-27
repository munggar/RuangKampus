import { test, expect, installMockApi, waitForPageReady } from "./support";

const futureDate = (offset: number) =>
  new Date(Date.now() + offset * 24 * 60 * 60 * 1000).toLocaleDateString("en-CA", { timeZone: "Asia/Jakarta" });

test("admin dashboard summary API failure is shown instead of zero statistics", async ({ page }) => {
  const api = await installMockApi(page, "Staff Sekretariat");
  await page.route("**/api/v1/dashboard/summary", (route) => route.fulfill({
    status: 503,
    contentType: "application/json",
    body: JSON.stringify({ detail: "Ringkasan sementara tidak dapat dimuat." }),
  }));
  await page.goto("/admin/dashboard");
  await waitForPageReady(page);

  await expect(page.getByText("Ringkasan sementara tidak dapat dimuat.")).toBeVisible();
  await expect(page.getByText(/Ringkasan status dan inventaris tidak ditampilkan/)).toBeVisible();
  await expect(page.locator(".admin-stat-grid")).toHaveCount(0);
  await expect(page.getByText("Distribusi status tidak dapat ditampilkan")).toBeVisible();
  expect(api.unmatched).toEqual([]);
});

test("admin reservation date filters are sent to the API and reset together", async ({ page }) => {
  const api = await installMockApi(page, "Staff Sekretariat");
  const reservationQueries: URLSearchParams[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname === "/api/v1/reservations" && request.method() === "GET") {
      reservationQueries.push(url.searchParams);
    }
  });
  await page.goto("/admin/reservations");
  await waitForPageReady(page);

  const from = futureDate(1);
  const to = futureDate(2);
  await page.getByLabel("Dari tanggal").fill(from);
  await page.getByLabel("Sampai tanggal").fill(to);
  await expect.poll(() => reservationQueries.some((query) => query.get("dateFrom") === from && query.get("dateTo") === to)).toBe(true);
  await expect(page.getByText("Diskusi proyek pengujian")).toBeVisible();

  await page.getByRole("button", { name: "Reset filter" }).click();
  await expect(page.getByLabel("Dari tanggal")).toHaveValue("");
  await expect(page.getByLabel("Sampai tanggal")).toHaveValue("");
  await expect.poll(() => reservationQueries.some((query) => !query.has("dateFrom") && !query.has("dateTo"))).toBe(true);
  expect(api.unmatched).toEqual([]);
});

test("student reservation status filters fit the mobile content width", async ({ page }) => {
  await installMockApi(page, "Student");
  await page.setViewportSize({ width: 390, height: 844 });
  await page.goto("/student/reservations");
  await waitForPageReady(page);
  const layout = await page.locator(".segmented-tabs").evaluate((element) => {
    const rect = element.getBoundingClientRect();
    return {
      shell: element.closest(".app-shell")?.className,
      display: getComputedStyle(element).display,
      width: rect.width,
      columns: getComputedStyle(element).gridTemplateColumns,
      mainWidth: document.querySelector("main.main-content")?.scrollWidth,
    };
  });
  expect(layout.display, JSON.stringify(layout)).toBe("grid");
  expect(layout.mainWidth, JSON.stringify(layout)).toBeLessThanOrEqual(391);
});
