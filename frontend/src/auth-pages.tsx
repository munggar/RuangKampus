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
          <button type="button" aria-pressed={role === "TU/Admin"} className={role === "TU/Admin" ? "is-active" : ""} onClick={() => { setRole("TU/Admin"); setIdentifier("admin.uhamka"); setError(""); }}>Administrator</button>
        </div>
        <form className="stack-form" onSubmit={submit}>
          <Field label={role === "Student" ? "NIM" : "Username Administrator"}>
            <input
              type="text"
              autoComplete="username"
              placeholder={role === "Student" ? "Masukkan NIM Anda" : "admin.uhamka"}
              value={role === "TU/Admin" ? "admin.uhamka" : identifier}
              onChange={(event) => setIdentifier(event.target.value)}
              readOnly={role === "TU/Admin"}
              required
            />
          </Field>
          <Field label="Password">
            <span className="input-with-action">
              <input type={visible ? "text" : "password"} autoComplete="current-password" placeholder="Masukkan password" value={password} onChange={(event) => setPassword(event.target.value)} required />
              <button type="button" className="field-action" onClick={() => setVisible(!visible)} aria-label={visible ? "Sembunyikan password" : "Tampilkan password"}>{visible ? <EyeOff size={18} /> : <Eye size={18} />}</button>
            </span>
          </Field>
          <div className="form-between"><label className="checkbox-line"><input type="checkbox" disabled />Ingat saya</label><Link to="/forgot-password">Lupa password?</Link></div>
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
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [studentIdentifier, setStudentIdentifier] = useState("");
  const [phone, setPhone] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [visible, setVisible] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const { register } = useAuth();
  const navigate = useNavigate();

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    if (password.length < 10) {
      setError("Password harus terdiri dari minimal 10 karakter.");
      return;
    }
    if (password !== confirm) {
      setError("Konfirmasi password belum sama.");
      return;
    }
    setBusy(true);
    try {
      await register({
        name: name.trim(),
        email: email.trim(),
        password,
        student_identifier: studentIdentifier.trim(),
        ...(phone.trim() ? { phone: phone.trim() } : {}),
      });
      navigate("/student/dashboard", { replace: true });
    } catch (cause) {
      setError(cause instanceof ApiError || cause instanceof Error
        ? cause.message
        : "Pendaftaran belum berhasil. Silakan coba kembali.");
    } finally {
      setBusy(false);
    }
  }

  return <main className="auth-layout">
    <BrandHero />
    <section className="auth-panel">
      <div className="auth-panel__inner">
        <p className="eyebrow">CREATE YOUR ACCOUNT</p>
        <h2>Daftar RuangKampus</h2>
        <p className="muted">Buat akun Student untuk mencari ruangan dan mengajukan reservasi kampus. NIM akan digunakan untuk login.</p>
        {!isApiConfigured() ? <Notice tone="warning">Backend belum dikonfigurasi. Pendaftaran akan aktif setelah layanan API tersedia.</Notice> : null}
        <form className="stack-form" onSubmit={submit}>
          <Field label="Nama lengkap">
            <input type="text" autoComplete="name" minLength={2} maxLength={160} placeholder="Nama sesuai identitas kampus" value={name} onChange={(event) => setName(event.target.value)} required />
          </Field>
          <Field label="Email kampus">
            <input type="email" autoComplete="email" maxLength={254} placeholder="nama@kampus.ac.id" value={email} onChange={(event) => setEmail(event.target.value)} required />
          </Field>
          <Field label="NIM">
            <input type="text" autoComplete="username" minLength={3} maxLength={50} placeholder="Masukkan NIM aktif Anda" value={studentIdentifier} onChange={(event) => setStudentIdentifier(event.target.value)} required />
          </Field>
          <Field label="Nomor telepon (opsional)">
            <input type="tel" autoComplete="tel" maxLength={40} placeholder="08xxxxxxxxxx" value={phone} onChange={(event) => setPhone(event.target.value)} />
          </Field>
          <Field label="Password">
            <span className="input-with-action">
              <input type={visible ? "text" : "password"} autoComplete="new-password" minLength={10} maxLength={128} placeholder="Minimal 10 karakter" value={password} onChange={(event) => setPassword(event.target.value)} required />
              <button type="button" className="field-action" onClick={() => setVisible(!visible)} aria-label={visible ? "Sembunyikan password" : "Tampilkan password"}>{visible ? <EyeOff size={18} /> : <Eye size={18} />}</button>
            </span>
          </Field>
          <Field label="Konfirmasi password">
            <input type="password" autoComplete="new-password" minLength={10} maxLength={128} placeholder="Ulangi password" value={confirm} onChange={(event) => setConfirm(event.target.value)} required />
          </Field>
          {error ? <Notice tone="error">{error}</Notice> : null}
          <Button type="submit" disabled={busy || !isApiConfigured()} className="button--wide">
            {busy ? "Membuat akun…" : <>Buat akun Student <ArrowRight size={17} /></>}
          </Button>
        </form>
        <div className="secure-note"><ShieldCheck size={18} /><span>Pendaftaran publik otomatis membuat role Student. Akun TU/Admin dibuat secara terpisah oleh operator.</span></div>
        <p className="auth-support">Sudah punya akun? <Link to="/login">Masuk di sini</Link></p>
      </div>
    </section>
  </main>;
}
