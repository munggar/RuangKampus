export class ApiError extends Error {
  readonly status: number;
  readonly code?: string;

  constructor(message: string, status: number, code?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.code = code;
  }
}

const API_BASE_URL = (import.meta.env.VITE_API_BASE_URL ?? "").trim();
let accessToken: string | null = null;

export function setAccessToken(token: string | null) {
  accessToken = token;
}

export function buildApiUrl(baseUrl: string, path: string) {
  return `${baseUrl.replace(/\/+$/, "")}/${path.replace(/^\/+/, "")}`;
}

export function extractApiErrorMessage(payload: unknown, status: number) {
  if (typeof payload === "string" && payload.trim()) return payload;

  if (payload && typeof payload === "object") {
    const record = payload as Record<string, unknown>;
    const error = record.error;

    if (error && typeof error === "object") {
      const nested = error as Record<string, unknown>;
      if (typeof nested.message === "string" && nested.message.trim()) {
        return nested.message;
      }
    }

    if (typeof record.detail === "string" && record.detail.trim()) return record.detail;
    if (typeof record.message === "string" && record.message.trim()) return record.message;
  }

  return `Permintaan gagal (HTTP ${status}). Silakan coba kembali.`;
}

interface ApiRequestOptions extends Omit<RequestInit, "body"> {
  body?: unknown;
}

export async function apiRequest<T>(
  path: string,
  options: ApiRequestOptions = {},
): Promise<T> {
  if (!API_BASE_URL) {
    throw new ApiError(
      "VITE_API_BASE_URL belum dikonfigurasi. Atur variabel tersebut pada file .env lokal.",
      0,
      "API_BASE_URL_MISSING",
    );
  }

  const { body, headers: initialHeaders, ...requestOptions } = options;
  const headers = new Headers(initialHeaders);

  if (accessToken) headers.set("Authorization", `Bearer ${accessToken}`);

  const requestInit: RequestInit = {
    ...requestOptions,
    headers,
    credentials: "include",
  };

  if (body !== undefined) {
    const isFormData = typeof FormData !== "undefined" && body instanceof FormData;
    if (isFormData) {
      requestInit.body = body;
    } else {
      headers.set("Content-Type", "application/json");
      requestInit.body = JSON.stringify(body);
    }
  }

  let response: Response;
  try {
    response = await fetch(buildApiUrl(API_BASE_URL, path), requestInit);
  } catch {
    throw new ApiError(
      "Layanan API belum dapat dijangkau. Pastikan backend berjalan dan alamat API sudah benar.",
      0,
      "NETWORK_ERROR",
    );
  }

  if (response.status === 204) return undefined as T;

  const contentType = response.headers.get("content-type") ?? "";
  const payload: unknown = contentType.includes("application/json")
    ? await response.json().catch(() => null)
    : await response.text().catch(() => "");

  if (!response.ok) {
    const errorValue =
      payload && typeof payload === "object"
        ? (payload as Record<string, unknown>).error
        : undefined;
    const code =
      errorValue && typeof errorValue === "object"
        ? (errorValue as Record<string, unknown>).code
        : undefined;

    throw new ApiError(
      extractApiErrorMessage(payload, response.status),
      response.status,
      typeof code === "string" ? code : undefined,
    );
  }

  return payload as T;
}
