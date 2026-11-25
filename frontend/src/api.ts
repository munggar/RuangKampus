import type { AppNotification, AuthUser, AvailabilityResult, PageMeta, PageResult, Reservation, Room, RoomUnavailability, Schedule, TokenResponse } from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;
  constructor(message: string, status: number, code?: string) {
    super(message); this.name = "ApiError"; this.status = status; this.code = code;
  }
}

const configuredApiBase = import.meta.env.VITE_API_BASE_URL?.trim();
const API_BASE_URL = (configuredApiBase || (import.meta.env.DEV ? "http://localhost:8000/api/v1" : "")).replace(/\/+$/, "");

export function isApiConfigured() {
  return API_BASE_URL.length > 0;
}
let accessToken: string | null = null;
let refreshPromise: Promise<TokenResponse | null> | null = null;

export function setAccessToken(token: string | null) { accessToken = token; }
export function buildApiUrl(path: string) {
  if (!API_BASE_URL) {
    throw new ApiError("Backend belum dikonfigurasi. Tampilan frontend bisa dilihat, tetapi login dan data belum aktif.", 0, "API_NOT_CONFIGURED");
  }
  return API_BASE_URL + "/" + path.replace(/^\/+/, "");
}

function isRecord(value: unknown): value is Record<string, unknown> {
  return typeof value === "object" && value !== null;
}
async function readPayload(response: Response): Promise<unknown> {
  if (response.status === 204) return undefined;
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json")
    ? response.json().catch(() => null)
    : response.text().catch(() => "");
}
function messageFrom(payload: unknown, status: number): string {
  if (typeof payload === "string" && payload.trim()) return payload;
  if (isRecord(payload) && typeof payload.message === "string" && payload.message.trim()) return payload.message;
  if (isRecord(payload) && typeof payload.detail === "string" && payload.detail.trim()) return payload.detail;
  return "Permintaan gagal (HTTP " + status + "). Silakan coba kembali.";
}

async function refreshAccessToken(): Promise<TokenResponse | null> {
  if (!API_BASE_URL) {
    setAccessToken(null);
    return null;
  }
  if (refreshPromise) return refreshPromise;
  refreshPromise = (async () => {
    try {
      const response = await fetch(buildApiUrl("/auth/refresh"), {
        method: "POST", credentials: "include", headers: { Accept: "application/json" },
      });
      const payload = await readPayload(response);
      if (!response.ok || !isRecord(payload) || typeof payload.access_token !== "string") {
        setAccessToken(null); return null;
      }
      const session = payload as unknown as TokenResponse;
      setAccessToken(session.access_token);
      return session;
    } catch {
      setAccessToken(null); return null;
    } finally {
      refreshPromise = null;
    }
  })();
  return refreshPromise;
}

interface RequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown; noRefresh?: boolean; rawResponse?: boolean;
}
async function rawRequest<T>(path: string, options: RequestOptions = {}, retried = false): Promise<T> {
  if (!API_BASE_URL) {
    throw new ApiError("Backend belum dikonfigurasi. Atur VITE_API_BASE_URL setelah API dipublikasikan.", 0, "API_NOT_CONFIGURED");
  }
  const { body, headers: initialHeaders, noRefresh = false, rawResponse = false, ...rest } = options;
  const headers = new Headers(initialHeaders);
  headers.set("Accept", "application/json");
  if (accessToken) headers.set("Authorization", "Bearer " + accessToken);

  const init: RequestInit = { ...rest, headers, credentials: "include" };
  if (body !== undefined) {
    if (typeof FormData !== "undefined" && body instanceof FormData) init.body = body;
    else { headers.set("Content-Type", "application/json"); init.body = JSON.stringify(body); }
  }

  let response: Response;
  try { response = await fetch(buildApiUrl(path), init); }
  catch { throw new ApiError("Layanan API belum dapat dijangkau. Pastikan backend berjalan dan alamat API benar.", 0, "NETWORK_ERROR"); }

  if (response.status === 401 && !noRefresh && !retried && !path.startsWith("/auth/")) {
    const renewed = await refreshAccessToken();
    if (renewed) return rawRequest<T>(path, options, true);
  }

  const payload = await readPayload(response);
  if (!response.ok) {
    const code = isRecord(payload) && typeof payload.code === "string" ? payload.code : undefined;
    throw new ApiError(messageFrom(payload, response.status), response.status, code);
  }
  if (rawResponse) return payload as T;
  if (isRecord(payload) && Object.prototype.hasOwnProperty.call(payload, "data")) return payload.data as T;
  return payload as T;
}
export function apiRequest<T>(path: string, options: RequestOptions = {}) { return rawRequest<T>(path, options); }

export async function apiPage<T>(path: string, options: RequestOptions = {}): Promise<PageResult<T>> {
  const payload = await rawRequest<unknown>(path, { ...options, rawResponse: true });
  if (isRecord(payload) && Array.isArray(payload.data)) {
    return { items: payload.data as T[], meta: isRecord(payload.meta) ? payload.meta as unknown as PageMeta : undefined };
  }
  return Array.isArray(payload) ? { items: payload as T[] } : { items: [] };
}

export const authApi = {
  login: (email: string, password: string) => apiRequest<TokenResponse>("/auth/login", {
    method: "POST", noRefresh: true, body: { email, password },
  }),
  refresh: () => refreshAccessToken(),
  logout: () => apiRequest<{ success: boolean }>("/auth/logout", { method: "POST", noRefresh: true }),
  forgotPassword: (email: string) => apiRequest<unknown>("/auth/forgot-password", {
    method: "POST", noRefresh: true, body: { email },
  }),
  resetPassword: (token: string, newPassword: string) => apiRequest<unknown>("/auth/reset-password", {
    method: "POST", noRefresh: true, body: { token, new_password: newPassword },
  }),
};

export const profileApi = {
  me: () => apiRequest<AuthUser>("/users/me"),
  update: (payload: { name?: string; phone?: string | null; profile_image_url?: string | null }) =>
    apiRequest<AuthUser>("/users/me", { method: "PATCH", body: payload }),
  changePassword: (current_password: string, new_password: string) =>
    apiRequest<unknown>("/users/me/password", { method: "PATCH", body: { current_password, new_password } }),
};

export const roomApi = {
  list: (params: URLSearchParams) => apiPage<Room>("/rooms?" + params.toString()),
  get: (id: string) => apiRequest<Room>("/rooms/" + encodeURIComponent(id)),
  availability: (id: string, params: URLSearchParams) =>
    apiRequest<AvailabilityResult>("/rooms/" + encodeURIComponent(id) + "/availability?" + params.toString()),
  create: (payload: Partial<Room>) => apiRequest<Room>("/rooms", { method: "POST", body: payload }),
  update: (id: string, payload: Partial<Room>) =>
    apiRequest<Room>("/rooms/" + encodeURIComponent(id), { method: "PATCH", body: payload }),
  remove: (id: string) => apiRequest<unknown>("/rooms/" + encodeURIComponent(id), { method: "DELETE" }),
};

export const reservationApi = {
  list: (params: URLSearchParams) => apiPage<Reservation>("/reservations?" + params.toString()),
  get: (id: string) => apiRequest<Reservation>("/reservations/" + encodeURIComponent(id)),
  create: (payload: { room_id: string; purpose: string; date: string; start_time: string; end_time: string; participant_count: number; notes?: string }) =>
    apiRequest<Reservation>("/reservations", { method: "POST", body: payload }),
  cancel: (id: string, reason?: string) => apiRequest<Reservation>("/reservations/" + encodeURIComponent(id) + "/cancel", {
    method: "PATCH", body: reason ? { reason } : {},
  }),
  approve: (id: string) => apiRequest<Reservation>("/reservations/" + encodeURIComponent(id) + "/approve", { method: "PATCH" }),
  reject: (id: string, rejection_reason: string) => apiRequest<Reservation>("/reservations/" + encodeURIComponent(id) + "/reject", {
    method: "PATCH", body: { rejection_reason },
  }),
};

export const notificationApi = {
  list: (params: URLSearchParams) => apiPage<AppNotification>("/notifications?" + params.toString()),
  markRead: (id: string) => apiRequest<AppNotification>("/notifications/" + encodeURIComponent(id) + "/read", { method: "PATCH" }),
};

export const dashboardApi = {
  summary: () => apiRequest<Record<string, number | string>>("/dashboard/summary"),
  recent: (limit = 8) => apiPage<Reservation>("/dashboard/recent-reservations?limit=" + limit),
  roomStatistics: (params = new URLSearchParams()) =>
    apiRequest<Array<{ room_id: string; room_name: string; building: string; reservation_count: number }>>("/dashboard/room-statistics?" + params.toString()),
};

export const scheduleApi = {
  list: (params = new URLSearchParams()) => apiPage<Schedule>("/admin/schedules?" + params.toString()),
  create: (payload: { room_id: string; course_name: string; schedule_date?: string; day_of_week?: number; start_time: string; end_time: string; data_source?: string }) =>
    apiRequest<Schedule>("/admin/schedules", { method: "POST", body: payload }),
  cancel: (id: string) => apiRequest<unknown>("/admin/schedules/" + encodeURIComponent(id), { method: "DELETE" }),
  listUnavailability: (params = new URLSearchParams()) => apiRequest<RoomUnavailability[]>("/admin/room-unavailability?" + params.toString()),
  createUnavailability: (payload: { room_id: string; unavailable_date: string; start_time: string; end_time: string; reason: string }) =>
    apiRequest<RoomUnavailability>("/admin/room-unavailability", { method: "POST", body: payload }),
  deactivateUnavailability: (id: string) => apiRequest<Pick<RoomUnavailability, "id" | "is_active">>("/admin/room-unavailability/" + encodeURIComponent(id) + "/deactivate", { method: "PATCH" }),
};

export const adminApi = {
  activity: (params = new URLSearchParams()) => apiPage<Record<string, unknown>>("/admin/activity?" + params.toString()),
  roomStatistics: (params = new URLSearchParams()) => dashboardApi.roomStatistics(params),
};

export function localToday(): string {
  const parts = new Intl.DateTimeFormat("en-CA", {
    timeZone: "Asia/Jakarta", year: "numeric", month: "2-digit", day: "2-digit",
  }).formatToParts(new Date());
  const get = (type: string) => parts.find((item) => item.type === type)?.value || "00";
  return get("year") + "-" + get("month") + "-" + get("day");
}
export function formatDate(value: string | null | undefined, options?: Intl.DateTimeFormatOptions): string {
  if (!value) return "—";
  const date = new Date(value.length === 10 ? value + "T00:00:00+07:00" : value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("id-ID", { day: "numeric", month: "short", year: "numeric", timeZone: "Asia/Jakarta", ...options }).format(date);
}
export function formatTime(value: string | null | undefined): string { return value ? value.slice(0, 5) : "—"; }
export function statusLabel(status: string): string {
  const labels: Record<string, string> = {
    PENDING: "Menunggu", APPROVED: "Disetujui", REJECTED: "Ditolak", CANCELLED: "Dibatalkan",
    COMPLETED: "Selesai", ACTIVE: "Aktif", INACTIVE: "Nonaktif", MAINTENANCE: "Pemeliharaan",
  };
  return labels[status] || status;
}
export function availabilityReasonLabel(reason: string): string {
  const labels: Record<string, string> = {
    PAST_OR_CURRENT_START_TIME: "Waktu mulai harus berada di masa mendatang.",
    ROOM_NOT_ACTIVE: "Ruangan sedang tidak aktif.",
    CAPACITY_EXCEEDED: "Jumlah peserta melebihi kapasitas ruangan.",
    OUTSIDE_OPERATING_HOURS_OR_NOT_CONFIGURED: "Waktu di luar jam operasional atau jam operasional belum diatur.",
    LECTURE_SCHEDULE_CONFLICT: "Terdapat jadwal perkuliahan pada waktu tersebut.",
    ROOM_UNAVAILABLE: "Ruangan memiliki jadwal pemeliharaan atau tidak tersedia.",
    RESERVATION_CONFLICT: "Terdapat permohonan reservasi lain pada waktu tersebut.",
  };
  return labels[reason] || reason;
}