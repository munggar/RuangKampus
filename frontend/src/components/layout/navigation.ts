import {
  Bell,
  Building2,
  CalendarDays,
  CalendarRange,
  ClipboardList,
  LayoutDashboard,
  Search,
  UserRound,
  type LucideIcon,
} from "lucide-react";
import type { AppRole } from "../../auth/AuthContext";

export interface NavigationItem {
  label: string;
  mobileLabel: string;
  to: string;
  icon: LucideIcon;
}

export const studentNavigation: NavigationItem[] = [
  { label: "Dashboard", mobileLabel: "Home", to: "/student/dashboard", icon: LayoutDashboard },
  { label: "Find Rooms", mobileLabel: "Rooms", to: "/student/rooms", icon: Search },
  { label: "My Reservations", mobileLabel: "Bookings", to: "/student/reservations", icon: CalendarDays },
  { label: "Notifications", mobileLabel: "Alerts", to: "/student/notifications", icon: Bell },
  { label: "Profile", mobileLabel: "Profile", to: "/student/profile", icon: UserRound },
];

export const adminNavigation: NavigationItem[] = [
  { label: "Dashboard", mobileLabel: "Home", to: "/admin/dashboard", icon: LayoutDashboard },
  { label: "Reservation Requests", mobileLabel: "Requests", to: "/admin/reservations", icon: ClipboardList },
  { label: "Room Management", mobileLabel: "Rooms", to: "/admin/rooms", icon: Building2 },
  { label: "Schedule Management", mobileLabel: "Schedule", to: "/admin/schedule", icon: CalendarRange },
  { label: "Notifications", mobileLabel: "Alerts", to: "/admin/notifications", icon: Bell },
  { label: "Profile", mobileLabel: "Profile", to: "/admin/profile", icon: UserRound },
];

export function navigationForRole(role: AppRole) {
  return role === "Student" ? studentNavigation : adminNavigation;
}

export function currentPageTitle(pathname: string, role: AppRole) {
  return navigationForRole(role).find((item) => pathname.startsWith(item.to))?.label ?? "Dashboard";
}
