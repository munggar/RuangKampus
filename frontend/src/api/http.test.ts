import { describe, expect, it } from "vitest";
import { buildApiUrl, extractApiErrorMessage } from "./http";

describe("buildApiUrl", () => {
  it("joins base URL and path without duplicate slashes", () => {
    expect(buildApiUrl("http://localhost:8000/api/v1/", "/auth/login")).toBe(
      "http://localhost:8000/api/v1/auth/login",
    );
  });
});

describe("extractApiErrorMessage", () => {
  it("reads the documented error response", () => {
    expect(extractApiErrorMessage({
      error: { code: "VALIDATION_ERROR", message: "Data tidak valid." },
    }, 422)).toBe("Data tidak valid.");
  });

  it("returns a safe fallback for an unknown response", () => {
    expect(extractApiErrorMessage(null, 503)).toBe(
      "Permintaan gagal (HTTP 503). Silakan coba kembali.",
    );
  });
});
