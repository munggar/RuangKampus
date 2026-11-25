import { Link, Navigate, Route, Routes } from "react-router";
import { ArrowLeft } from "lucide-react";
import { useAuth } from "../auth/AuthContext";
import { RequireRole } from "../auth/RequireRole";
import { AppShell } from "../components/layout/AppShell";
import { AdminDashboardPage } from "../pages/AdminDashboardPage";
import { LoginPage } from "../pages/LoginPage";
import { PasswordRecoveryPage } from "../pages/PasswordRecoveryPage";
import { PlaceholderPage } from "../pages/PlaceholderPage";
import { StudentDashboardPage } from "../pages/StudentDashboardPage";

function RootRedirect() {
  const { user } = useAuth();

  if (!user) return <Navigate to="/login" replace />;
  return <Navigate to={user.role === "Student" ? "/student/dashboard" : "/admin/dashboard"} replace />;
}

function NotFoundPage() {
  return (
    <main className="simple-page">
      <section className="simple-page__card">
        <p className="eyebrow">404 · HALAMAN TIDAK DITEMUKAN</p>
        <h1>Halaman ini belum tersedia.</h1>
        <p>Periksa alamat yang dibuka atau kembali ke halaman utama akun Anda.</p>
        <Link className="button button--primary" to="/">
          <ArrowLeft size={18} aria-hidden="true" />
          Kembali
        </Link>
      </section>
    </main>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<PasswordRecoveryPage />} />

      <Route element={<RequireRole allowedRole="Student" />}>
        <Route path="/student" element={<AppShell role="Student" />}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<StudentDashboardPage />} />
          <Route path="rooms" element={<PlaceholderPage role="Student" title="Find Rooms" description="Temukan ruangan berdasarkan lokasi, kapasitas, fasilitas, dan ketersediaan." />} />
          <Route path="reservations" element={<PlaceholderPage role="Student" title="My Reservations" description="Pantau status dan riwayat permohonan reservasi Anda." />} />
          <Route path="notifications" element={<PlaceholderPage role="Student" title="Notifications" description="Lihat pembaruan mengenai permohonan dan aktivitas akun Anda." />} />
          <Route path="profile" element={<PlaceholderPage role="Student" title="Profile" description="Informasi akun mahasiswa yang disediakan oleh layanan RuangKampus." />} />
        </Route>
      </Route>

      <Route element={<RequireRole allowedRole="TU/Admin" />}>
        <Route path="/admin" element={<AppShell role="TU/Admin" />}>
          <Route index element={<Navigate to="dashboard" replace />} />
          <Route path="dashboard" element={<AdminDashboardPage />} />
          <Route path="reservations" element={<PlaceholderPage role="TU/Admin" title="Reservation Requests" description="Tinjau detail dan status permohonan reservasi mahasiswa." />} />
          <Route path="rooms" element={<PlaceholderPage role="TU/Admin" title="Room Management" description="Kelola inventaris ruangan sesuai hak akses yang diberikan backend." />} />
          <Route path="schedule" element={<PlaceholderPage role="TU/Admin" title="Schedule Management" description="Tinjau jadwal penggunaan ruangan setelah endpoint schedule tersedia." />} />
          <Route path="notifications" element={<PlaceholderPage role="TU/Admin" title="Notifications" description="Pembaruan permohonan dan informasi operasional untuk staf TU." />} />
          <Route path="profile" element={<PlaceholderPage role="TU/Admin" title="Profile" description="Informasi akun administrator yang disediakan backend." />} />
        </Route>
      </Route>

      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
