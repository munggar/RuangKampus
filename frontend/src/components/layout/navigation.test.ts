import { describe, expect, it } from "vitest";
import { adminNavigation, currentPageTitle, navigationForRole, studentNavigation } from "./navigation";

describe("application navigation", () => {
  it("exposes the five student destinations from the project brief", () => {
    expect(studentNavigation.map((item) => item.to)).toEqual([
      "/student/dashboard",
      "/student/rooms",
      "/student/reservations",
      "/student/notifications",
      "/student/profile",
    ]);
  });

  it("exposes the six TU/Admin destinations from the project brief", () => {
    expect(adminNavigation.map((item) => item.to)).toEqual([
      "/admin/dashboard",
      "/admin/reservations",
      "/admin/rooms",
      "/admin/schedule",
      "/admin/notifications",
      "/admin/profile",
    ]);
  });

  it("selects role navigation and resolves the current page title", () => {
    expect(navigationForRole("Student")).toBe(studentNavigation);
    expect(navigationForRole("TU/Admin")).toBe(adminNavigation);
    expect(currentPageTitle("/admin/reservations", "TU/Admin")).toBe("Reservation Requests");
    expect(currentPageTitle("/student/rooms", "Student")).toBe("Find Rooms");
  });
});
