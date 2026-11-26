import { useState, type FormEvent } from "react";
import { ArrowRight, Eye, EyeOff, ShieldCheck } from "lucide-react";
import { Link, useNavigate, useSearchParams } from "react-router";
import { ApiError, authApi, isApiConfigured } from "./api";
import { useAuth } from "./auth";
import type { AppRole } from "./types";
import { Button, Field, Notice } from "./ui";

function BrandHero() {
  return <aside className="auth-hero">
    <div className="auth-brand"><span className="brand-mark__symbol"><span /></span><span><b>RuangKampus</b><small>Find the Room. Book the Space.</small></span></div>
    <div className="auth-hero__text">
      <p className="eyebrow">CAMPUS FACILITY RESERVATIONS</p>
      <h1>Make room for great ideas.</h1>
      <p>Temukan ruang kampus yang sesuai dan ajukan reservasi dalam satu tempat.</p>
    </div>
    <small className="auth-hero__copyright">© {new Date().getFullYear()} RuangKampus</small>
  </aside>;
}

export function LoginPage() {
  const [role, setRole] = useState<AppRole>("Student");
  const [identifier, setIdentifier] = useState("");
  const [password, setPassword] = useState("");
  const [visible, setVisible] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setError(""); setSubmitting(true);
    try {
      const user = await login(role === "TU/Admin" ? "admin.uhamka" : identifier.trim(), password, role);
      navigate(user.role === "Student" ? "/student/dashboard" : "/admin/dashboard", { replace: true });
    } catch (cause) {
      setError(cause instanceof ApiError ? cause.message : "Login belum berhasil. Periksa kembali data masuk Anda.");
    } finally { setSubmitting(false); }
  }

  return <main className="auth-layout">
    <BrandHero />
    <section className="auth-panel">
      <div className="auth-panel__inner">
        <p className="eyebrow">WELCOME BACK</p>
        <h2>Selamat datang kembali</h2>
        <p className="muted">Masuk dengan akun universitas yang terdaftar.</p>
        {!isApiConfigured() ? <Notice tone="warning">Mode preview: tampilan tersedia, tetapi backend belum di-host atau URL API belum diatur. Login dan pemuatan data belum aktif.</Notice> : null}
        <div className="role-switch" aria-label="Pilih jenis akun">
          <button type="button" aria-pressed={role === "Student"} className={role === "Student" ? "is-active" : ""} onClick={() => { setRole("Student"); setIdentifier(""); setError(""); }}>Student</button>
          <button type="button" aria-pressed={role === "TU/Admin"} className={role === "TU/Admin" ? "is-active" : ""} onClick={() => { setRole("TU/Admin"); setIdentifier((current) => current || "admin.uhamka"); setError(""); }}>Administrator</button>
        </div>
        <form className="stack-form" onSubmit={submit}>
          <Field label={role === "Student" ? "NIM" : "Username Administrator"}>
            <input
              type="text"
              autoComplete="username"
              placeholder={role === "Student" ? "Masukkan NIM Anda" : "admin.uhamka"}
              value={identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              required
            />
          </Field>
          <Field label="Password">
            <span className="input-with-action">
              <input type={visible ? "text" : "password"} autoComplete="current-password" placeholder="Masukkan password" value={password} onChange={(event) => setPassword(event.target.value)} required />
              <button type="button" className="field-action" onClick={() => setVisible(!visible)} aria-label={visible ? "Sembunyikan password" : "Tampilkan password"}>{visible ? <EyeOff size={18} /> : <Eye size={18} />}</button>
            </span>
          </Field>
          <div className="form-between"><Link to="/forgot-password">Lupa password?</Link></div>
          {error ? <Notice tone="error">{error}</Notice> : null}
          <Button type="submit" disabled={submitting} className="button--wide">{submitting ? "Memeriksa…" : <>Masuk ke RuangKampus <ArrowRight size={17} /></>}</Button>
        </form>
        <div className="secure-note"><ShieldCheck size={18} /><span>Akses akun diproses melalui layanan autentikasi RuangKampus.</span></div>
        <p className="auth-support">Belum punya akun? <Link to="/register">Daftar sebagai Student</Link></p>
        <p className="auth-support">Mengalami kendala? Hubungi administrator kampus untuk bantuan akun.</p>
      </div>
    </section>
  </main>;
}

export function ForgotPasswordPage() {
  const [params] = useSearchParams();
  const token = new URLSearchParams(window.location.hash.replace(/^#/, "")).get("token") || params.get("token") || "";
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const navigate = useNavigate();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault(); setBusy(true); setError(""); setSuccess("");
    try {
      if (token) {
        if (password.length < 10) throw new Error("Password baru minimal 10 karakter.");
        if (password !== confirm) throw new Error("Konfirmasi password belum sama.");
        await authApi.resetPassword(token, password);
        setSuccess("Password berhasil diperbarui. Silakan masuk kembali.");
        window.history.replaceState(null, "", window.location.pathname);
        setTimeout(() => navigate("/login"), 1200);
      } else {
        await authApi.forgotPassword(email.trim());
        setSuccess("Jika email terdaftar dan layanan email aktif, instruksi reset akan dikirim.");
      }
    } catch (cause) {
      setError(cause instanceof ApiError || cause instanceof Error ? cause.message : "Permintaan belum berhasil.");
    } finally { setBusy(false); }
  }

  return <main className="auth-layout">
    <BrandHero />
    <section className="auth-panel"><div className="auth-panel__inner">
      <p className="eyebrow">ACCOUNT SUPPORT</p>
      <h2>{token ? "Buat password baru" : "Lupa password?"}</h2>
      <p className="muted">{token ? "Gunakan password baru yang kuat dan mudah Anda ingat." : "Masukkan email akun Anda untuk meminta instruksi reset password."}</p>
      <form className="stack-form" onSubmit={submit}>
        {token ? <>
          <Field label="Password baru"><input type="password" minLength={10} value={password} onChange={(event) => setPassword(event.target.value)} required /></Field>
          <Field label="Konfirmasi password"><input type="password" minLength={10} value={confirm} onChange={(event) => setConfirm(event.target.value)} required /></Field>
        </> : <Field label="Email kampus"><input type="email" autoComplete="email" placeholder="nama@kampus.ac.id" value={email} onChange={(event) => setEmail(event.target.value)} required /></Field>}
        {error ? <Notice tone="error">{error}</Notice> : null}
        {success ? <Notice tone="success">{success}</Notice> : null}
        <Button type="submit" disabled={busy} className="button--wide">{busy ? "Memproses…" : token ? "Simpan password baru" : "Kirim instruksi reset"}</Button>
      </form>
      <Link className="back-link" to="/login">← Kembali ke halaman masuk</Link>
    </div></section>
  </main>;
}

export function RegisterPage() {
  return <main className="auth-layout">
    <BrandHero />
    <section className="auth-panel">
      <div className="auth-panel__inner">
        <p className="eyebrow">ACCOUNT ACTIVATION</p>
        <h2>Pendaftaran melalui TU/Admin</h2>
        <Notice tone="warning">
          Pendaftaran mandiri sementara dinonaktifkan untuk melindungi NIM mahasiswa. Akun dibuat oleh TU/Admin setelah identitas dicocokkan dengan data resmi kampus.
        </Notice>
        <p className="muted">Siapkan NIM dan email yang tercatat pada data kampus, lalu hubungi administrator fakultas atau unit pengelola RuangKampus.</p>
        <Link className="button button--primary button--wide" to="/login">Kembali ke halaman masuk</Link>
      </div>
    </section>
  </main>;
}
