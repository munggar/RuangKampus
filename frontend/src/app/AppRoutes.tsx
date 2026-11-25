import { Link, Navigate, Route, Routes } from "react-router";
import { ArrowLeft } from "lucide-react";
import { LoginPage } from "../pages/LoginPage";
import { PasswordRecoveryPage } from "../pages/PasswordRecoveryPage";

function NotFoundPage() {
  return (
    <main className="simple-page">
      <section className="simple-page__card">
        <p className="eyebrow">404 · Halaman tidak ditemukan</p>
        <h1>Halaman ini belum tersedia.</h1>
        <p>Periksa alamat yang dibuka atau kembali ke halaman masuk RuangKampus.</p>
        <Link className="button button--primary" to="/login">
          <ArrowLeft size={18} aria-hidden="true" />
          Kembali ke login
        </Link>
      </section>
    </main>
  );
}

export function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/forgot-password" element={<PasswordRecoveryPage />} />
      <Route path="*" element={<NotFoundPage />} />
    </Routes>
  );
}
