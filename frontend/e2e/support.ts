import { mkdir, writeFile } from "node:fs/promises";
import { resolve } from "node:path";
import { test as base, expect, type Page } from "@playwright/test";

type AppRole = "Student" | "Staff Sekretariat";
type NullableRole = AppRole | null;

const isoJakartaDate = (offsetDays = 0) => {
  const date = new Date(Date.now() + offsetDays * 24 * 60 * 60 * 1000);
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Jakarta", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(date);
  const part = (name: string) => parts.find((entry) => entry.type === name)?.value || "00";
  return part("year") + "-" + part("month") + "-" + part("day");
};

export const fixtureUser = (role: AppRole) => ({
  id: role === "Student" ? "user-student-e2e" : "user-admin-e2e",
  name: role === "Student" ? "Mahasiswa Uji Browser" : "Administrator Uji Browser",
  email: role === "Student" ? "student-e2e@example.invalid" : "admin-e2e@example.invalid",
  student_identifier: role === "Student" ? "E2E-24000001" : "admin.uhamka",
  phone: null,
  profile_image_url: null,
  role,
  account_status: "ACTIVE",
  created_at: isoJakartaDate() + "T08:00:00+07:00",
});

export const fixtureRoom = {
  id: "room-e2e-001",
  room_name: "Ruang Diskusi Uji",
  room_code: "RK-E2E-001",
  building: "Gedung Pengujian",
  faculty: "Fakultas Teknologi Informasi",
  floor: "2",
  location_description: "Dekat area laboratorium",
  capacity: 32,
  capacity_estimate: "32",
  description: "Fixture pengujian browser RuangKampus. Bukan data ruangan production.",
  facilities: ["Proyektor", "Wi-Fi", "Whiteboard"],
  operating_hours: {
    monday: [{ start: "08:00", end: "17:00" }],
    tuesday: [{ start: "08:00", end: "17:00" }],
    wednesday: [{ start: "08:00", end: "17:00" }],
    thursday: [{ start: "08:00", end: "17:00" }],
    friday: [{ start: "08:00", end: "17:00" }],
    saturday: [{ start: "08:00", end: "12:00" }],
    sunday: [],
  },
  room_status: "ACTIVE",
  photo_url: null,
  created_at: isoJakartaDate() + "T08:00:00+07:00",
  updated_at: isoJakartaDate() + "T08:00:00+07:00",
};

const makeReservation = (id: string, status: string, offsetDays: number) => ({
  id,
  user_id: fixtureUser("Student").id,
  room_id: fixtureRoom.id,
  purpose: status === "PENDING" ? "Diskusi proyek pengujian" : "Rapat tim pengujian",
  reservation_date: isoJakartaDate(offsetDays),
  start_time: "10:00:00",
  end_time: "12:00:00",
  participant_count: 8,
  notes: "Data fixture E2E; tidak menggunakan record production.",
  status,
  admin_id: status === "PENDING" ? null : fixtureUser("Staff Sekretariat").id,
  rejection_reason: null,
  submitted_at: isoJakartaDate() + "T08:00:00+07:00",
  approved_at: status === "APPROVED" ? isoJakartaDate() + "T09:00:00+07:00" : null,
  cancelled_at: null,
  cancellation_reason: null,
  room: {
    id: fixtureRoom.id,
    room_name: fixtureRoom.room_name,
    building: fixtureRoom.building,
    capacity: fixtureRoom.capacity,
    photo_url: null,
  },
  applicant: {
    id: fixtureUser("Student").id,
    name: fixtureUser("Student").name,
    email: fixtureUser("Student").email,
  },
});

const fixtureSchedule = {
  id: "schedule-e2e-001",
  room_id: fixtureRoom.id,
  course_name: "Praktikum Pengujian Perangkat Lunak",
  schedule_date: isoJakartaDate(1),
  day_of_week: null,
  start_time: "08:00:00",
  end_time: "10:00:00",
  schedule_status: "ACTIVE",
  data_source: "E2E_FIXTURE",
  last_updated_at: isoJakartaDate() + "T08:00:00+07:00",
};

const fixtureNotification = {
  id: "notification-e2e-001",
  notification_type: "RESERVATION_APPROVED",
  title: "Reservasi disetujui",
  message: "Reservasi Ruang Diskusi Uji telah disetujui. Ini adalah notifikasi fixture.",
  read_at: null,
  delivery_status: "IN_APP_CREATED",
  email_delivery_status: "SENT",
  email_attempt_count: 1,
  email_sent_at: isoJakartaDate() + "T09:01:00+07:00",
  action_url: "/student/reservations/reservation-approved-e2e",
  created_at: isoJakartaDate() + "T09:00:00+07:00",
};

const fixtureImportBatch = {
  batch_id: "import-e2e-001",
  status: "PREVIEWED",
  source_filename: "ruangan-e2e.xlsx",
  row_count: 1,
  valid_count: 1,
  invalid_count: 0,
  row_results: [{
    row_number: 2,
    room_name: "Ruang Diskusi Uji",
    room_code: "RK-E2E-001",
    capacity_estimate: "32",
    status: "VALID",
    errors: [],
    has_photo: false,
    floor: "2",
  }],
  preview_rows: [],
  created_at: isoJakartaDate() + "T09:00:00+07:00",
  completed_at: null,
};

export const SCREEN_ROUTES: Array<{
  id: string;
  group: "auth" | "student" | "admin";
  role: NullableRole;
  path: string;
}> = [
  { id: "login", group: "auth", role: null, path: "/login" },
  { id: "register", group: "auth", role: null, path: "/register" },
  { id: "forgot-password", group: "auth", role: null, path: "/forgot-password" },
  { id: "reset-password", group: "auth", role: null, path: "/reset-password?token=fixture-reset-token" },

  { id: "student-dashboard", group: "student", role: "Student", path: "/student/dashboard" },
  { id: "student-rooms", group: "student", role: "Student", path: "/student/rooms" },
  { id: "student-availability", group: "student", role: "Student", path: "/student/availability" },
  { id: "student-alternatives", group: "student", role: "Student", path: "/student/alternatives" },
  { id: "student-room-detail", group: "student", role: "Student", path: "/student/rooms/room-e2e-001" },
  { id: "student-booking", group: "student", role: "Student", path: "/student/rooms/room-e2e-001/book" },
  { id: "student-reservations", group: "student", role: "Student", path: "/student/reservations" },
  { id: "student-reservation-detail", group: "student", role: "Student", path: "/student/reservations/reservation-pending-e2e" },
  { id: "student-notifications", group: "student", role: "Student", path: "/student/notifications" },
  { id: "student-profile", group: "student", role: "Student", path: "/student/profile" },
  { id: "student-assistant", group: "student", role: "Student", path: "/student/assistant" },

  { id: "admin-dashboard", group: "admin", role: "Staff Sekretariat", path: "/admin/dashboard" },
  { id: "admin-reservations", group: "admin", role: "Staff Sekretariat", path: "/admin/reservations" },
  { id: "admin-reservation-detail", group: "admin", role: "Staff Sekretariat", path: "/admin/reservations/reservation-pending-e2e" },
  { id: "admin-rooms", group: "admin", role: "Staff Sekretariat", path: "/admin/rooms" },
  { id: "admin-data-imports", group: "admin", role: "Staff Sekretariat", path: "/admin/data-imports" },
  { id: "admin-room-create", group: "admin", role: "Staff Sekretariat", path: "/admin/rooms/new" },
  { id: "admin-room-edit", group: "admin", role: "Staff Sekretariat", path: "/admin/rooms/room-e2e-001/edit" },
  { id: "admin-schedules-maintenance", group: "admin", role: "Staff Sekretariat", path: "/admin/schedules" },
  { id: "admin-notifications", group: "admin", role: "Staff Sekretariat", path: "/admin/notifications" },
  { id: "admin-profile", group: "admin", role: "Staff Sekretariat", path: "/admin/profile" },
  ];

export const STUDENT_PATHS = SCREEN_ROUTES.filter((screen) => screen.role === "Student");
export const ADMIN_PATHS = SCREEN_ROUTES.filter((screen) => screen.role === "Staff Sekretariat");

export type MockApiResult = {
  calls: string[];
  unmatched: string[];
};

export async function installMockApi(page: Page, initialRole: NullableRole): Promise<MockApiResult> {
  let currentRole = initialRole;
  let rooms = [{ ...fixtureRoom }];
  let reservations = [
    makeReservation("reservation-pending-e2e", "PENDING", 1),
    makeReservation("reservation-approved-e2e", "APPROVED", 2),
    makeReservation("reservation-rejected-e2e", "REJECTED", 3),
  ];
  let notifications = [{ ...fixtureNotification }];
  let schedules = [{ ...fixtureSchedule }];
  let unavailability: Array<Record<string, unknown>> = [];
  let importHistory: Array<Record<string, unknown>> = [];
  let currentBatch = { ...fixtureImportBatch };

  const calls: string[] = [];
  const unmatched: string[] = [];

  const respond = (route: Parameters<Parameters<Page["route"]>[1]>[0], payload: unknown, status = 200) =>
    route.fulfill({ status, contentType: "application/json; charset=utf-8", body: JSON.stringify(payload) });
  const data = (route: Parameters<Parameters<Page["route"]>[1]>[0], payload: unknown, status = 200) =>
    respond(route, { data: payload }, status);
  const paged = (route: Parameters<Parameters<Page["route"]>[1]>[0], items: unknown[]) =>
    respond(route, { data: items, meta: { page: 1, limit: 100, total: items.length, total_pages: 1 } });
  const sessionPayload = () => ({
    access_token: "fixture-access-token-not-a-real-credential",
    token_type: "bearer",
    expires_in: 3600,
    user: fixtureUser(currentRole || "Student"),
  });

  await page.route("**/api/v1/**", async (route) => {
    const request = route.request();
    const url = new URL(request.url());
    const path = url.pathname.replace(/^\/api\/v1/, "") || "/";
    const method = request.method();
    calls.push(method + " " + path);

    const body = (): Record<string, unknown> => {
      try {
        const value = request.postDataJSON();
        return value && typeof value === "object" ? value as Record<string, unknown> : {};
      } catch {
        return {};
      }
    };

    if (path === "/auth/refresh" && method === "POST") {
      if (!currentRole) return respond(route, { detail: "No fixture session" }, 401);
      return respond(route, sessionPayload());
    }
    if (path === "/auth/login" && method === "POST") {
      const payload = body();
      const identifier = String(payload.identifier || "");
      if (payload.password !== "fixture-pass-1234") {
        return respond(route, { detail: "Kredensial fixture tidak valid." }, 401);
      }
      currentRole = identifier === "admin.uhamka" ? "Staff Sekretariat" : "Student";
      return respond(route, sessionPayload());
    }
    if (path === "/auth/register" && method === "POST") {
      currentRole = "Student";
      return respond(route, sessionPayload());
    }
    if (path === "/auth/logout" && method === "POST") {
      currentRole = null;
      return data(route, { success: true });
    }
    if (path === "/auth/forgot-password" && method === "POST") {
      return data(route, { accepted: true });
    }
    if (path === "/auth/reset-password" && method === "POST") {
      return data(route, { success: true });
    }

    if (path === "/users/me" && method === "GET") {
      if (!currentRole) return respond(route, { detail: "Unauthenticated fixture" }, 401);
      return data(route, fixtureUser(currentRole));
    }
    if (path === "/users/me" && method === "PATCH") {
      const user = fixtureUser(currentRole || "Student");
      return data(route, { ...user, ...body() });
    }
    if (path === "/users/me/password" && method === "PATCH") {
      return data(route, { success: true });
    }

    if (path === "/dashboard/summary" && method === "GET") {
      return data(route, {
        role: currentRole || "Student",
        total_rooms: rooms.length,
        active_rooms: rooms.filter((room) => room.room_status === "ACTIVE").length,
        total_users: 3,
        total_reservations: reservations.length,
        pending: reservations.filter((item) => item.status === "PENDING").length,
        approved: reservations.filter((item) => item.status === "APPROVED").length,
        rejected: reservations.filter((item) => item.status === "REJECTED").length,
        cancelled: reservations.filter((item) => item.status === "CANCELLED").length,
        completed: reservations.filter((item) => item.status === "COMPLETED").length,
      });
    }
    if (path.startsWith("/dashboard/recent-reservations") && method === "GET") {
      return paged(route, reservations.slice(0, 8));
    }
    if (path.startsWith("/dashboard/room-statistics") && method === "GET") {
      return data(route, [{ room_id: fixtureRoom.id, room_name: fixtureRoom.room_name, building: fixtureRoom.building, reservation_count: reservations.length }]);
    }
    if (path.startsWith("/admin/activity") && method === "GET") {
      return paged(route, []);
    }

    if (path === "/rooms" && method === "GET") {
      const term = (url.searchParams.get("search") || "").toLowerCase();
      const filtered = rooms.filter((room) => !term || room.room_name.toLowerCase().includes(term));
      return paged(route, filtered);
    }
    if (path === "/rooms" && method === "POST") {
      const payload = body();
      const created = {
        ...fixtureRoom,
        ...payload,
        id: "room-created-e2e",
        room_name: String(payload.room_name || "Ruang Baru Fixture"),
        room_status: String(payload.room_status || "ACTIVE"),
      };
      rooms = [created, ...rooms];
      return data(route, created);
    }
    const availabilityMatch = path.match(/^\/rooms\/([^/]+)\/availability$/);
    if (availabilityMatch && method === "GET") {
      return data(route, {
        room_id: availabilityMatch[1],
        available: true,
        reasons: [],
        checked_at: new Date().toISOString(),
      });
    }
    const roomMatch = path.match(/^\/rooms\/([^/]+)$/);
    if (roomMatch && method === "GET") {
      const room = rooms.find((item) => item.id === decodeURIComponent(roomMatch[1]));
      return room ? data(route, room) : respond(route, { detail: "Room fixture not found" }, 404);
    }
    if (roomMatch && method === "PATCH") {
      const id = decodeURIComponent(roomMatch[1]);
      rooms = rooms.map((item) => item.id === id ? { ...item, ...body() } : item);
      return data(route, rooms.find((item) => item.id === id) || fixtureRoom);
    }
    if (roomMatch && method === "DELETE") {
      rooms = rooms.filter((item) => item.id !== decodeURIComponent(roomMatch[1]));
      return data(route, { success: true });
    }
    if (path === "/rooms/bulk-status" && method === "PATCH") {
      const payload = body();
      const ids = Array.isArray(payload.room_ids) ? payload.room_ids : [];
      rooms = rooms.map((item) => ids.includes(item.id) ? { ...item, room_status: payload.room_status } : item);
      return data(route, { updated_count: ids.length, unchanged_count: 0, rooms });
    }
    if (path === "/rooms/bulk-operating-hours" && method === "PATCH") {
      const payload = body();
      const ids = Array.isArray(payload.room_ids) ? payload.room_ids : [];
      return data(route, { updated_count: ids.length, unchanged_count: 0, rooms });
    }
    if (path === "/rooms/alternative-slots" && method === "POST") {
      const payload = body();
      return data(route, {
        items: [],
        criteria: {
          requested_date: payload.date || isoJakartaDate(1),
          duration_minutes: payload.duration_minutes || 120,
          participant_count: payload.participant_count || 1,
          search_days: payload.search_days || 7,
          slot_step_minutes: payload.slot_step_minutes || 30,
        },
        availability_note: "Hasil fixture pengujian; backend availability tidak dipanggil.",
      });
    }

    if (path === "/reservations" && method === "GET") {
      let filtered = [...reservations];
      const status = url.searchParams.get("status");
      if (status) filtered = filtered.filter((item) => item.status === status);
      const dateTo = url.searchParams.get("dateTo");
      if (dateTo) filtered = filtered.filter((item) => item.reservation_date <= dateTo);
      return paged(route, filtered);
    }
    if (path === "/reservations" && method === "POST") {
      const payload = body();
      const created = {
        ...makeReservation("reservation-created-e2e", "PENDING", 1),
        ...payload,
        id: "reservation-created-e2e",
        room_id: String(payload.room_id || fixtureRoom.id),
        reservation_date: String(payload.date || isoJakartaDate(1)),
        start_time: String(payload.start_time || "10:00:00"),
        end_time: String(payload.end_time || "12:00:00"),
        participant_count: Number(payload.participant_count || 1),
        purpose: String(payload.purpose || "Reservasi fixture"),
      };
      reservations = [created, ...reservations];
      return data(route, created);
    }
    const reservationAction = path.match(/^\/reservations\/([^/]+)\/(cancel|approve|reject|complete)$/);
    if (reservationAction && method === "PATCH") {
      const id = decodeURIComponent(reservationAction[1]);
      const action = reservationAction[2];
      let updated: Record<string, unknown> | undefined;
      reservations = reservations.map((item) => {
        if (item.id !== id) return item;
        const nextStatus = action === "approve" ? "APPROVED"
          : action === "reject" ? "REJECTED"
          : action === "cancel" ? "CANCELLED" : "COMPLETED";
        updated = {
          ...item,
          status: nextStatus,
          approved_at: action === "approve" ? new Date().toISOString() : item.approved_at,
          rejection_reason: action === "reject" ? String(body().rejection_reason || "Ditolak pada fixture.") : item.rejection_reason,
          cancelled_at: action === "cancel" ? new Date().toISOString() : item.cancelled_at,
        };
        return updated;
      });
      return updated ? data(route, updated) : respond(route, { detail: "Reservation fixture not found" }, 404);
    }
    const reservationMatch = path.match(/^\/reservations\/([^/]+)$/);
    if (reservationMatch && method === "GET") {
      const reservation = reservations.find((item) => item.id === decodeURIComponent(reservationMatch[1]));
      return reservation ? data(route, reservation) : respond(route, { detail: "Reservation fixture not found" }, 404);
    }

    if (path === "/notifications" && method === "GET") {
      const unreadOnly = url.searchParams.get("unreadOnly") === "true";
      const filtered = unreadOnly ? notifications.filter((item) => !item.read_at) : notifications;
      return paged(route, filtered);
    }
    if (path === "/notifications/read-all" && method === "PATCH") {
      const readAt = new Date().toISOString();
      const updatedCount = notifications.filter((item) => !item.read_at).length;
      notifications = notifications.map((item) => ({ ...item, read_at: item.read_at || readAt }));
      return data(route, { updated_count: updatedCount, read_at: readAt });
    }
    const retryMatch = path.match(/^\\/notifications\\/([^/]+)\\/retry-email$/);
    if (retryMatch && method === "POST") {
      const id = decodeURIComponent(retryMatch[1]);
      notifications = notifications.map((item) => item.id === id ? { ...item, email_delivery_status: "SENT", email_attempt_count: Number(item.email_attempt_count || 0) + 1, email_sent_at: new Date().toISOString() } : item);
      return data(route, notifications.find((item) => item.id === id) || fixtureNotification);
    }
    const notificationMatch = path.match(/^\/notifications\/([^/]+)\/read$/);
    if (notificationMatch && method === "PATCH") {
      const id = decodeURIComponent(notificationMatch[1]);
      notifications = notifications.map((item) => item.id === id ? { ...item, read_at: new Date().toISOString() } : item);
      return data(route, notifications.find((item) => item.id === id) || fixtureNotification);
    }

    if (path === "/assistant/chat" && method === "POST") {
      return data(route, {
        engine: "fixture",
        intent: "ROOM_SEARCH",
        message: "Saya menemukan satu ruangan yang sesuai berdasarkan data fixture.",
        filters: {
          faculty: null, building: null, min_capacity: null, facilities: [],
          date: null, start_time: null, end_time: null, participant_count: 1,
        },
        rooms,
        alternative_slots: [],
        follow_up_questions: ["Apakah Anda membutuhkan slot waktu tertentu?"],
        reservation_action: "NONE",
        privacy: "Fixture only",
      });
    }

    if (path === "/admin/schedules" && method === "GET") {
      return paged(route, schedules);
    }
    if (path === "/admin/schedules" && method === "POST") {
      const payload = body();
      const created = {
        ...fixtureSchedule,
        ...payload,
        id: "schedule-created-e2e",
        schedule_date: String(payload.schedule_date || isoJakartaDate(1)),
      };
      schedules = [created, ...schedules];
      return data(route, created);
    }
    const scheduleMatch = path.match(/^\/admin\/schedules\/([^/]+)$/);
    if (scheduleMatch && method === "DELETE") {
      schedules = schedules.filter((item) => item.id !== decodeURIComponent(scheduleMatch[1]));
      return data(route, { success: true });
    }
    if (path === "/admin/room-unavailability" && method === "GET") {
      return data(route, unavailability);
    }
    if (path === "/admin/room-unavailability" && method === "POST") {
      const created = { id: "unavailability-created-e2e", is_active: true, ...body() };
      unavailability = [created, ...unavailability];
      return data(route, created);
    }
    const unavailableMatch = path.match(/^\/admin\/room-unavailability\/([^/]+)\/deactivate$/);
    if (unavailableMatch && method === "PATCH") {
      const id = decodeURIComponent(unavailableMatch[1]);
      unavailability = unavailability.map((item) => item.id === id ? { ...item, is_active: false } : item);
      return data(route, unavailability.find((item) => item.id === id) || { id, is_active: false });
    }

    if (path === "/admin/rooms/imports" && method === "GET") {
      return data(route, importHistory);
    }
    if (path === "/admin/rooms/imports/preview" && method === "POST") {
      currentBatch = { ...fixtureImportBatch };
      return data(route, currentBatch);
    }
    if (path === "/admin/rooms/imports/commit" && method === "POST") {
      const completed = {
        ...currentBatch,
        status: "COMPLETED",
        completed_at: new Date().toISOString(),
      };
      importHistory = [completed, ...importHistory];
      return data(route, {
        batch_id: currentBatch.batch_id,
        status: "COMPLETED",
        inserted: currentBatch.valid_count,
        row_count: currentBatch.row_count,
        invalid_count: currentBatch.invalid_count,
      });
    }

    unmatched.push(method + " " + path);
    return respond(route, { detail: "No E2E mock defined for " + method + " " + path }, 501);
  });

  return { calls, unmatched };
}

export async function waitForPageReady(page: Page) {
  await page.locator("h1").first().waitFor({ state: "visible", timeout: 15000 });
  await page.waitForFunction(
    () => !document.querySelector("#boot-splash") &&
      !document.querySelector(".loading-inline") &&
      document.fonts.status === "loaded",
    null,
    { timeout: 15000 },
  );
  await page.evaluate(async () => {
    await document.fonts.ready;
    await Promise.all(Array.from(document.images).map((image) =>
      image.decode().catch(() => undefined),
    ));
    await new Promise<void>((resolve) => requestAnimationFrame(() => requestAnimationFrame(() => resolve())));
  });
}

export async function saveScreenshot(page: Page, filePath: string) {
  const { mkdir } = await import("node:fs/promises");
  const { dirname } = await import("node:path");
  await mkdir(dirname(filePath), { recursive: true });
  await page.screenshot({ path: filePath, fullPage: true, animations: "disabled" });
}

export { expect };

export const test = base.extend({
  page: async ({ page }, use, testInfo) => {
    const diagnostics: Array<Record<string, string | number>> = [];
    const expectedHttpStatuses = new Set<number>();
    page.on("console", (message) => {
      if (message.type() === "error") {
        const text = message.text().slice(0, 1000);
        const expected = Array.from(expectedHttpStatuses).some((status) => text.includes(String(status)));
        diagnostics.push({ type: "console-error", expected: expected ? "true" : "false", message: text });
      }
    });
    page.on("pageerror", (error) => {
      diagnostics.push({ type: "page-error", message: error.message.slice(0, 1000) });
    });
    page.on("requestfailed", (request) => {
      diagnostics.push({
        type: "request-failed",
        method: request.method(),
        path: new URL(request.url()).pathname,
        reason: (request.failure()?.errorText || "unknown").slice(0, 300),
      });
    });
    page.on("response", (response) => {
      if (response.status() >= 400) {
        const path = new URL(response.url()).pathname;
        const status = response.status();
        const expected =
          (status === 401 && path === "/api/v1/auth/refresh") ||
          (status === 401 && path === "/api/v1/auth/login" && /invalid login/i.test(testInfo.title)) ||
          (status === 503 && path === "/api/v1/rooms" && /API error/i.test(testInfo.title));
        if (expected) expectedHttpStatuses.add(status);
        diagnostics.push({
          type: "http-response-error", expected: expected ? "true" : "false",
          status, method: response.request().method(), path,
        });
      }
    });
    await use(page);
    const diagnosticJson = JSON.stringify(diagnostics, null, 2);
    const diagnosticDirectory = resolve("test-results/diagnostics/browser");
    await mkdir(diagnosticDirectory, { recursive: true });
    const safeTestId = testInfo.testId.replace(/[^a-zA-Z0-9_-]+/g, "-");
    await writeFile(resolve(diagnosticDirectory, safeTestId + ".json"), diagnosticJson, "utf8");
    await testInfo.attach("browser-diagnostics.json", {
      body: Buffer.from(diagnosticJson), contentType: "application/json",
    });
    const unexpected = diagnostics.filter((item) =>
      item.type === "page-error" ||
      (item.expected === "false" && ["console-error", "http-response-error", "request-failed"].includes(String(item.type))),
    );
    expect(unexpected, "Unexpected browser diagnostics on " + testInfo.title).toEqual([]);
  },
});
