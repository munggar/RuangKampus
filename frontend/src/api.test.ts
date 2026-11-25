import { describe, expect, it, vi } from "vitest";
import {
  availabilityReasonLabel,
  authApi,
  buildApiUrl,
  formatTime,
  statusLabel,
} from "./api";

describe("frontend API display helpers", () => {
  it("formats API time values without changing their timezone meaning", () => {
    expect(formatTime("09:30:00")).toBe("09:30");
    expect(formatTime(null)).toBe("—");
  });

  it("maps reservation states to Indonesian labels", () => {
    expect(statusLabel("PENDING")).toBe("Menunggu");
    expect(statusLabel("APPROVED")).toBe("Disetujui");
    expect(statusLabel("COMPLETED")).toBe("Selesai");
  });

  it("explains backend availability blockers in user-friendly Indonesian", () => {
    expect(availabilityReasonLabel("CAPACITY_EXCEEDED")).toContain("kapasitas");
    expect(availabilityReasonLabel("RESERVATION_CONFLICT")).toContain("reservasi");
    expect(availabilityReasonLabel("UNKNOWN_REASON")).toBe("UNKNOWN_REASON");
  });
});

describe("Student registration API", () => {
  it("posts registration data to the public auth endpoint and reads the new session", async () => {
    const originalFetch = globalThis.fetch;
    const payload = {
      name: "Student Example",
      email: "student@example.test",
      password: "StrongPassword123!",
      student_identifier: "2403045007",
      phone: "081234567890",
    };
    const session = {
      access_token: "test-access-token",
      token_type: "bearer",
      expires_in: 900,
      user: {
        id: "student-id",
        name: "Student Example",
        email: "student@example.test",
        student_identifier: "2403045007",
        phone: "081234567890",
        profile_image_url: null,
        role: "Student",
        account_status: "ACTIVE",
        created_at: "2026-11-25T00:00:00Z",
      },
    };
    const fetchMock = vi.fn<typeof fetch>().mockResolvedValue(new Response(JSON.stringify(session), {
      status: 201,
      headers: { "Content-Type": "application/json" },
    }));
    globalThis.fetch = fetchMock;

    try {
      const result = await authApi.register(payload);
      expect(result.access_token).toBe(session.access_token);
      expect(fetchMock).toHaveBeenCalledTimes(1);
      const [url, init] = fetchMock.mock.calls[0] || [];
      expect(String(url)).toBe(buildApiUrl("/auth/register"));
      expect(init?.method).toBe("POST");
      expect(init?.credentials).toBe("include");
      expect(JSON.parse(String(init?.body))).toEqual(payload);
    } finally {
      globalThis.fetch = originalFetch;
    }
  });
});
