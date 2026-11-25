import { Navigate, Route, Routes, useLocation } from "react-router";
import type { ReactNode } from "react";
import { useAuth } from "./auth";
import { AppShell } from "./layout";
import {
  AdminDashboardPage, AdminRequestsPage, AdminRoomsPage, AdminRoomEditorPage, AdminSchedulesPage,
  AssistantUnavailablePage, ForgotPasswordPage, LoginPage, NotificationsPage, ProfilePage,
  ReservationDetailPage, RoomDirectoryPage, RoomDetailPage, StudentDashboardPage,
  StudentReservationsPage, BookingPage, NotFoundPage,
} from "./pages";

function FullScreenLoading() {
  return <main className="loading-screen"><span className="spinner" /><span>Memuat RuangKampus…</span></main>;
}

function RequireRole({ role, children }: { role: "Student" | "TU/Admin"; children: ReactNode }) {
  const { user, loading } = useAuth();
  const location = useLocation();
  if (loading) return <FullScreenLoading />;
  if (!user) return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  if (user.role !== role) return <Navigate to={user.role === "Student" ? "/student/dashboard" : "/admin/dashboard"} replace />;
  return <>{children}</>;
}

function HomeRedirect() {
  const { user, loading } = useAuth();
  if (loading) return <FullScreenLoading />;
  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "Student" ? "/student/dashboard" : "/admin/dashboard"} replace />;
}

export function App() {
  return (
    <Routes>
      <Route path="/" element={<HomeRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<ForgotPasswordPage />} />

      <Route path="/student" element={<RequireRole role="Student"><AppShell role="Student" /></RequireRole>}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<StudentDashboardPage />} />
        <Route path="rooms" element={<RoomDirectoryPage role="Student" />} />
        <Route path="rooms/:roomId" element={<RoomDetailPage role="Student" />} />
        <Route path="rooms/:roomId/book" element={<BookingPage />} />
        <Route path="reservations" element={<StudentReservationsPage />} />
        <Route path="reservations/:reservationId" element={<ReservationDetailPage role="Student" />} />
        <Route path="notifications" element={<NotificationsPage role="Student" />} />
        <Route path="profile" element={<ProfilePage role="Student" />} />
        <Route path="assistant" element={<AssistantUnavailablePage role="Student" />} />
      </Route>

      <Route path="/admin" element={<RequireRole role="TU/Admin"><AppShell role="TU/Admin" /></RequireRole>}>
        <Route index element={<Navigate to="dashboard" replace />} />
        <Route path="dashboard" element={<AdminDashboardPage />} />
        <Route path="reservations" element={<AdminRequestsPage />} />
        <Route path="reservations/:reservationId" element={<ReservationDetailPage role="TU/Admin" />} />
        <Route path="rooms" element={<AdminRoomsPage />} />
        <Route path="rooms/new" element={<AdminRoomEditorPage />} />
        <Route path="rooms/:roomId/edit" element={<AdminRoomEditorPage />} />
        <Route path="schedules" element={<AdminSchedulesPage />} />
        <Route path="notifications" element={<NotificationsPage role="TU/Admin" />} />
        <Route path="profile" element={<ProfilePage role="TU/Admin" />} />
        <Route path="assistant" element={<AssistantUnavailablePage role="TU/Admin" />} />
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}