import { test, expect, installMockApi, waitForPageReady } from "./support";

test("student dashboard summarizes all real reservation states and exposes key destinations", async ({ page }) => {
  const api = await installMockApi(page, "Student");
  await page.goto("/student/dashboard");
  await waitForPageReady(page);

  for (const label of ["Reservasi aktif", "Menunggu", "Disetujui", "Ditolak", "Dibatalkan", "Selesai"]) {
    await expect(page.getByText(label, { exact: true }).first()).toBeVisible();
  }
  await expect(page.getByRole("link", { name: /Jelajahi ruang/ })).toHaveAttribute("href", "/student/rooms");
  await expect(page.getByRole("link", { name: "Cek ketersediaan", exact: true })).toHaveAttribute("href", "/student/availability");
  await expect(page.getByRole("link", { name: /Ngobrol dengan RUKKA/ })).toHaveAttribute("href", "/student/assistant");
  expect(api.calls).toContain("GET /dashboard/summary");
  expect(api.calls).toContain("GET /dashboard/recent-reservations");
});

test("student can clear one applied room filter from its chip", async ({ page }) => {
  const api = await installMockApi(page, "Student");
  const roomQueries: string[] = [];
  page.on("request", (request) => {
    const url = new URL(request.url());
    if (url.pathname === "/api/v1/rooms") roomQueries.push(url.search);
  });
  await page.goto("/student/rooms");
  await waitForPageReady(page);
  await page.getByLabel("Gedung").fill("Gedung Pengujian");
  await page.getByRole("button", { name: "Terapkan filter" }).click();
  await expect(page.getByRole("button", { name: /Gedung: Gedung Pengujian/ })).toBeVisible();
  await page.getByRole("button", { name: /Gedung: Gedung Pengujian/ }).click();
  await expect(page.getByText("Filter aktif")).toHaveCount(0);
  await expect(page.getByLabel("Gedung")).toHaveValue("");
  expect(roomQueries.some((query) => query.includes("building=Gedung+Pengujian"))).toBe(true);
  expect(api.unmatched).toEqual([]);
});

test("student discovers a room, opens its detail, and continues to booking", async ({ page }) => {
  const api = await installMockApi(page, "Student");
  await page.goto("/student/rooms");
  await waitForPageReady(page);
  await page.getByRole("link", { name: "Lihat detail", exact: true }).click();
  await expect(page).toHaveURL(/\/student\/rooms\/room-e2e-001$/);
  await expect(page.getByRole("heading", { name: "Ruang Diskusi Uji" })).toBeVisible();
  await expect(page.getByText("Kapasitas")).toBeVisible();
  await page.getByRole("link", { name: "Ajukan reservasi" }).click();
  await expect(page).toHaveURL(/\/student\/rooms\/room-e2e-001\/book$/);
  await expect(page.getByRole("heading", { name: "Ajukan reservasi" })).toBeVisible();
  expect(api.calls).toContain("GET /rooms/room-e2e-001");
  expect(api.unmatched).toEqual([]);
});

test("unavailable booking slot opens alternatives with the selected criteria", async ({ page }) => {
  const api = await installMockApi(page, "Student");
  await page.route("**/api/v1/rooms/room-e2e-001/availability**", (route) => route.fulfill({
    status: 200,
    contentType: "application/json",
    body: JSON.stringify({ room_id: "room-e2e-001", available: false, reasons: ["RESERVATION_CONFLICT"], checked_at: new Date().toISOString() }),
  }));
  const date = new Date(Date.now() + 24 * 60 * 60 * 1000).toLocaleDateString("en-CA", { timeZone: "Asia/Jakarta" });
  await page.goto(`/student/rooms/room-e2e-001/book?date=${date}&startTime=10%3A00&endTime=12%3A00&participantCount=8`);
  await waitForPageReady(page);
  await page.getByRole("button", { name: "Periksa ketersediaan" }).click();
  const alternativeLink = page.getByRole("link", { name: "Cari waktu atau ruang alternatif" });
  await expect(alternativeLink).toBeVisible();
  await alternativeLink.click();
  await expect(page).toHaveURL(/\/student\/alternatives\?.*durationMinutes=120.*participantCount=8/);
  await expect(page.getByLabel("Jumlah peserta")).toHaveValue("8");
  await page.getByRole("button", { name: "Temukan slot alternatif" }).click();
  await expect(page.getByText("0 rekomendasi ditemukan")).toBeVisible();
  expect(api.calls).toContain("POST /rooms/alternative-slots");
  expect(api.unmatched).toEqual([]);
});

test("RUKKA error retry keeps the failed message in the composer", async ({ page }) => {
  const api = await installMockApi(page, "Student");
  let shouldFail = true;
  await page.route("**/api/v1/assistant/chat", async (route) => {
    if (shouldFail) {
      shouldFail = false;
      await route.fulfill({ status: 503, contentType: "application/json", body: JSON.stringify({ detail: "Asisten sedang sibuk. Coba kembali." }) });
      return;
    }
    await route.fallback();
  });
  await page.goto("/student/assistant");
  await waitForPageReady(page);
  const composer = page.getByLabel("Tulis pertanyaan");
  await composer.fill("Cari ruang diskusi untuk kelompok saya");
  await page.getByRole("button", { name: "Kirim" }).click();
  await expect(page.getByRole("alert")).toContainText("Asisten sedang sibuk");
  await expect(composer).toHaveValue("Cari ruang diskusi untuk kelompok saya");
  await page.getByRole("button", { name: "Kirim" }).click();
  await expect(page.getByText(/Saya menemukan satu ruangan yang sesuai/)).toBeVisible();
  await expect(composer).toHaveValue("");
  expect(api.calls.filter((call) => call === "POST /assistant/chat")).toHaveLength(1);
});

