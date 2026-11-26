import { describe, expect, it } from "vitest";
import { initialsFromName } from "./ui";
import {
  availabilityReasonLabel,
  canCancelReservation,
  authApi,
  apiAssetUrl,
  buildApiUrl,
  formatTime,
  formatDateTime,
  statusLabel,
} from "./api";

describe("frontend API display helpers", () => {
  it("exposes a registration endpoint using the public Student payload", () => {
    expect(buildApiUrl("/auth/register")).toContain("/api/v1/auth/register");
    expect(typeof authApi.register).toBe("function");
  });
  it("resolves imported relative room photo paths against the API origin", () => {
    expect(apiAssetUrl("/media/rooms/room-photo.jpg")).toContain("/media/rooms/room-photo.jpg");
    expect(apiAssetUrl("https://cdn.example.com/room.jpg")).toBe("https://cdn.example.com/room.jpg");
  });

  it("formats API time values without changing their timezone meaning", () => {
    expect(formatTime("09:30:00")).toBe("09:30");
    expect(formatTime(null)).toBe("—");
  });

  it("shows notification timestamps in the campus timezone (WIB)", () => {
    expect(formatDateTime("2026-11-26T10:00:00Z")).toBe("26 Nov 2026 · 17:00 WIB");
    expect(formatDateTime(null)).toBe("—");
  });

  it("allows cancellation only for pending or approved reservations on current or future dates", () => {
    expect(canCancelReservation("PENDING", "2026-11-26", "2026-11-26")).toBe(true);
    expect(canCancelReservation("APPROVED", "2026-11-27", "2026-11-26")).toBe(true);
    expect(canCancelReservation("REJECTED", "2026-11-27", "2026-11-26")).toBe(false);
    expect(canCancelReservation("CANCELLED", "2026-11-27", "2026-11-26")).toBe(false);
    expect(canCancelReservation("COMPLETED", "2026-11-27", "2026-11-26")).toBe(false);
    expect(canCancelReservation("APPROVED", "2026-11-25", "2026-11-26")).toBe(false);
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

describe("shared UI helpers", () => {
  it("builds initials from whitespace-separated names", () => {
    expect(initialsFromName("Adil Muslim Saputra")).toBe("AM");
    expect(initialsFromName("  Adil   Saputra ")).toBe("AS");
    expect(initialsFromName("Adil")).toBe("A");
    expect(initialsFromName("")).toBe("RK");
  });
});
