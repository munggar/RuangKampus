import { test, expect, installMockApi, waitForPageReady } from "./support";

const futureDate = (offset = 1) =>
  new Date(Date.now() + offset * 24 * 60 * 60 * 1000).toLocaleDateString("en-CA", { timeZone: "Asia/Jakarta" });

test.describe("Authentication UI — mocked session only", () => {
  test("rejects invalid login credentials and exposes an inline error", async ({ page }) => {
    await installMockApi(page, null);
    await page.goto("/login");
    await waitForPageReady(page);
    await page.getByLabel("NIM").fill("E2E-24000001");
    await page.locator('input[autocomplete="current-password"]').fill("wrong-fixture-password");
    await page.getByRole("button", { name: "Masuk ke RuangKampus" }).click();
    await expect(page.getByRole("alert")).toContainText("Kredensial fixture tidak valid");
    await expect(page).toHaveURL(/\/login$/);
  });

  test("logs in a Student fixture and opens the protected dashboard", async ({ page }) => {
    const api = await installMockApi(page, null);
    await page.goto("/login");
    await waitForPageReady(page);
    await page.getByLabel("NIM").fill("E2E-24000001");
    await page.locator('input[autocomplete="current-password"]').fill("fixture-pass-1234");
    await page.getByRole("button", { name: "Masuk ke RuangKampus" }).click();
    await expect(page).toHaveURL(/\/student\/dashboard$/);
    await expect(page.getByRole("heading", { name: /Selamat (pagi|siang|sore|malam)/ })).toBeVisible();
    expect(api.calls).toContain("POST /auth/login");
  });

  test("public registration creates only a Student fixture", async ({ page }) => {
    const api = await installMockApi(page, null);
    await page.goto("/register");
    await waitForPageReady(page);
    await page.getByLabel("Nama lengkap").fill("Mahasiswa Browser Uji");
    await page.getByLabel("Email kampus").fill("registration-e2e@example.invalid");
    await page.getByLabel("NIM").fill("E2E-REG-001");
    await page.getByLabel("Nomor telepon (opsional)").fill("080000000001");
    await page.getByLabel("Password", { exact: true }).fill("fixture-pass-1234");
    await page.getByLabel("Konfirmasi password").fill("fixture-pass-1234");
    await page.getByRole("button", { name: /Buat akun Student/ }).click();
    await expect(page).toHaveURL(/\/student\/dashboard$/);
    expect(api.calls).toContain("POST /auth/register");
  });

  test("forgot password submits an email without revealing account existence", async ({ page }) => {
    const api = await installMockApi(page, null);
    await page.goto("/forgot-password");
    await waitForPageReady(page);
    await page.getByLabel("Email kampus").fill("forgot-e2e@example.invalid");
    await page.getByRole("button", { name: "Kirim instruksi reset" }).click();
    await expect(page.getByRole("status")).toContainText("Jika email terdaftar");
    expect(api.calls).toContain("POST /auth/forgot-password");
  });

  test("reset-password token state accepts matching new passwords", async ({ page }) => {
    const api = await installMockApi(page, null);
    await page.goto("/reset-password?token=fixture-reset-token");
    await waitForPageReady(page);
    await page.getByLabel("Password baru").fill("fixture-new-password");
    await page.getByLabel("Konfirmasi password").fill("fixture-new-password");
    await page.getByRole("button", { name: "Simpan password baru" }).click();
    await expect(page.getByRole("status")).toContainText("Password berhasil diperbarui");
    expect(api.calls).toContain("POST /auth/reset-password");
  });

  test("unauthenticated protected routes redirect to login", async ({ page }) => {
    await installMockApi(page, null);
    await page.goto("/admin/dashboard");
    await waitForPageReady(page);
    await expect(page).toHaveURL(/\/login$/);
  });

  test("role guards redirect Student away from Admin routes and Admin away from Student routes", async ({ page }) => {
    await installMockApi(page, "Student");
    await page.goto("/admin/schedules");
    await waitForPageReady(page);
    await expect(page).toHaveURL(/\/student\/dashboard$/);

    await page.unroute("**/api/v1/**");
    await installMockApi(page, "Staff Sekretariat");
    await page.goto("/student/reservations");
    await waitForPageReady(page);
    await expect(page).toHaveURL(/\/admin\/dashboard$/);
  });

  test("logout clears the mocked session and returns to login", async ({ page }) => {
    const api = await installMockApi(page, "Student");
    await page.goto("/student/dashboard");
    await waitForPageReady(page);
    await page.getByRole("button", { name: /Mahasiswa Uji Browser/ }).click();
    await page.getByRole("menuitem", { name: "Keluar" }).click();
    await expect(page).toHaveURL(/\/login$/);
    expect(api.calls).toContain("POST /auth/logout");
  });
});

test.describe("Student workflows — fixture-backed browser E2E", () => {
  test("checks availability and submits a reservation through the UI", async ({ page }) => {
    const api = await installMockApi(page, "Student");
    await page.goto("/student/rooms/room-e2e-001/book");
    await waitForPageReady(page);

    await page.getByLabel("Tanggal").fill(futureDate(1));
    await page.getByLabel("Jumlah peserta").fill("8");
    await page.getByLabel("Jam mulai").fill("10:00");
    await page.getByLabel("Jam selesai").fill("12:00");
    await page.getByLabel("Tujuan kegiatan").fill("Diskusi implementasi pengujian browser");

    await page.getByRole("button", { name: "Periksa ketersediaan" }).click();
    await expect(page.getByText(/Waktu yang dipilih tercatat tersedia/)).toBeVisible();
    await page.getByRole("button", { name: /Tinjau dan kirim permohonan/ }).click();

    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("heading", { name: "Kirim permohonan reservasi?" })).toBeVisible();
    await dialog.getByRole("button", { name: "Kirim permohonan" }).click();

    await expect(page).toHaveURL(/\/student\/reservations\/reservation-created-e2e/);
    await expect(page.getByRole("heading", { name: "Detail reservasi" })).toBeVisible();
    expect(api.calls).toContain("GET /rooms/room-e2e-001/availability");
    expect(api.calls).toContain("POST /reservations");
    expect(api.calls).toContain("GET /reservations/reservation-created-e2e");
  });

  test("marks an unread notification as read", async ({ page }) => {
    const api = await installMockApi(page, "Student");
    await page.goto("/student/notifications");
    await waitForPageReady(page);
    await expect(page.getByText("Reservation approved")).toBeVisible();
    await page.getByRole("button", { name: "Tandai dibaca" }).click();
    await expect(page.getByText("Dibaca")).toBeVisible();
    expect(api.calls).toContain("PATCH /notifications/notification-e2e-001/read");
  });

  test("sends a message to the Student assistant and renders a fixture reply", async ({ page }) => {
    const api = await installMockApi(page, "Student");
    await page.goto("/student/assistant");
    await waitForPageReady(page);
    await page.getByLabel("Tulis pertanyaan").fill("Saya membutuhkan ruang untuk delapan orang besok.");
    await page.getByRole("button", { name: "Kirim" }).click();
    await expect(page.getByText(/Saya menemukan satu ruangan yang sesuai/)).toBeVisible();
    expect(api.calls).toContain("POST /assistant/chat");
  });

  test("updates profile details using the profile form", async ({ page }) => {
    const api = await installMockApi(page, "Student");
    await page.goto("/student/profile");
    await waitForPageReady(page);
    await page.getByLabel("Nama lengkap").fill("Mahasiswa Browser Diperbarui");
    await page.getByRole("button", { name: "Simpan perubahan" }).click();
    await expect(page.getByRole("status")).toContainText("Profil berhasil diperbarui");
    expect(api.calls).toContain("PATCH /users/me");
  });
});

test.describe("Staff Sekretariat workflows — fixture-backed browser E2E", () => {
  test("approves a pending reservation from the review list", async ({ page }) => {
    const api = await installMockApi(page, "Staff Sekretariat");
    await page.goto("/admin/reservations");
    await waitForPageReady(page);
    await expect(page.getByText("Diskusi proyek pengujian")).toBeVisible();
    await page.getByRole("button", { name: "Setujui", exact: true }).first().click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByRole("heading", { name: "Setujui permohonan?" })).toBeVisible();
    await dialog.getByRole("button", { name: "Setujui permohonan" }).click();
    await expect(page.getByText("Tidak ada permohonan yang cocok")).toBeVisible();
    expect(api.calls).toContain("PATCH /reservations/reservation-pending-e2e/approve");
  });

  test("rejects a pending reservation with a recorded reason", async ({ page }) => {
    const api = await installMockApi(page, "Staff Sekretariat");
    await page.goto("/admin/reservations");
    await waitForPageReady(page);
    await page.getByRole("button", { name: "Tolak", exact: true }).first().click();
    const dialog = page.getByRole("dialog");
    await dialog.getByLabel("Alasan penolakan").fill("Ruangan digunakan untuk agenda fakultas.");
    await dialog.getByRole("button", { name: "Kirim penolakan" }).click();
    await expect(page.getByText("Tidak ada permohonan yang cocok")).toBeVisible();
    expect(api.calls).toContain("PATCH /reservations/reservation-pending-e2e/reject");
  });

  test("creates a room using the Admin room editor", async ({ page }) => {
    const api = await installMockApi(page, "Staff Sekretariat");
    await page.goto("/admin/rooms/new");
    await waitForPageReady(page);
    await page.getByLabel("Nama ruangan").fill("Ruang Kolaborasi E2E");
    await page.getByLabel("Gedung").fill("Gedung Pengujian");
    await page.getByLabel("Kapasitas").fill("24");
    await page.getByRole("button", { name: "Simpan ruangan" }).click();
    await expect(page).toHaveURL(/\/admin\/rooms$/);
    expect(api.calls).toContain("POST /rooms");
  });

  test("edits an existing room using the Admin room editor", async ({ page }) => {
    const api = await installMockApi(page, "Staff Sekretariat");
    await page.goto("/admin/rooms/room-e2e-001/edit");
    await waitForPageReady(page);
    await expect(page.getByLabel("Nama ruangan")).toHaveValue("Ruang Diskusi Uji");
    await page.getByLabel("Nama ruangan").fill("Ruang Diskusi Diperbarui");
    await page.getByRole("button", { name: "Simpan ruangan" }).click();
    await expect(page).toHaveURL(/\/admin\/rooms$/);
    expect(api.calls).toContain("PATCH /rooms/room-e2e-001");
  });

  test("creates an academic schedule and a maintenance block", async ({ page }) => {
    const api = await installMockApi(page, "Staff Sekretariat");
    await page.goto("/admin/schedules");
    await waitForPageReady(page);

    const scheduleForm = page.locator("form").nth(0);
    await scheduleForm.getByLabel("Ruangan").selectOption("room-e2e-001");
    await scheduleForm.getByLabel("Nama mata kuliah / kegiatan").fill("Jadwal fixture untuk E2E");
    await scheduleForm.getByLabel("Tanggal", { exact: true }).fill(futureDate(2));
    await scheduleForm.getByRole("button", { name: "Simpan jadwal" }).click();
    await expect(page.getByRole("status")).toContainText("Jadwal berhasil ditambahkan");

    const maintenanceForm = page.locator("form").nth(1);
    await maintenanceForm.getByLabel("Ruangan").selectOption("room-e2e-001");
    await maintenanceForm.getByLabel("Alasan").fill("Pemeliharaan fixture E2E");
    await maintenanceForm.getByRole("button", { name: "Simpan periode" }).click();
    await expect(page.getByRole("status")).toContainText("Periode tidak tersedia berhasil ditambahkan");
    expect(api.calls).toContain("POST /admin/schedules");
    expect(api.calls).toContain("POST /admin/room-unavailability");
  });

  test("previews and commits a workbook-shaped file through the import workspace", async ({ page }) => {
    const api = await installMockApi(page, "Staff Sekretariat");
    await page.goto("/admin/data-imports");
    await waitForPageReady(page);

    await page.locator('input[type="file"]').setInputFiles({
      name: "rooms-e2e.xlsx",
      mimeType: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
      buffer: Buffer.from("browser-fixture-not-a-real-xlsx-workbook"),
    });
    await page.getByRole("button", { name: "Pratinjau & validasi" }).click();
    await expect(page.getByText("Ruang Diskusi Uji").first()).toBeVisible();
    await expect(page.getByText("Hasil pratinjau")).toBeVisible();

    page.once("dialog", (dialog) => dialog.accept());
    await page.getByRole("button", { name: "Konfirmasi & impor 1" }).click();
    await expect(page.getByText("1 ruangan berhasil disimpan")).toBeVisible();
    expect(api.calls).toContain("POST /admin/rooms/imports/preview");
    expect(api.calls).toContain("POST /admin/rooms/imports/commit");
  });

  test("Staff mobile navigation exposes schedule and data import workspaces", async ({ page }) => {
    await installMockApi(page, "Staff Sekretariat");
    await page.setViewportSize({ width: 390, height: 844 });
    await page.goto("/admin/dashboard");
    await waitForPageReady(page);
    const mobileNavigation = page.locator(".mobile-nav-shell");
    await expect(mobileNavigation.getByRole("link", { name: "Jadwal" })).toBeVisible();
    await mobileNavigation.getByRole("link", { name: "Jadwal" }).click();
    await expect(page).toHaveURL(new RegExp("/admin/schedules$"));
    await waitForPageReady(page);
    await expect(page.getByRole("heading", { name: "Jadwal & pemeliharaan" })).toBeVisible();
    await mobileNavigation.getByRole("link", { name: "Impor" }).click();
    await expect(page).toHaveURL(new RegExp("/admin/data-imports$"));
    await waitForPageReady(page);
    await expect(page.getByRole("heading", { name: "Impor data kampus", exact: true })).toBeVisible();
  });
});
