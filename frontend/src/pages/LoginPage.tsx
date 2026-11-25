import { useState, type FormEvent } from "react";
import { ArrowRight, Eye, EyeOff, ShieldCheck } from "lucide-react";
import { Link, useNavigate } from "react-router";
import { ApiError } from "../api/http";
import { BrandWordmark } from "../components/BrandWordmark";
import { Button } from "../components/ui/Button";
import { TextField } from "../components/ui/TextField";
import { useAuth, type AppRole } from "../auth/AuthContext";

export function LoginPage() {
  const [role, setRole] = useState<AppRole>("Student");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState("");
  const { login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setIsSubmitting(true);

    try {
      const user = await login(email.trim(), password, role);
      navigate(user.role === "Student" ? "/student/dashboard" : "/admin/dashboard", { replace: true });
    } catch (cause) {
      setError(
        cause instanceof ApiError
          ? cause.message
          : "Login belum berhasil. Periksa kembali data masuk Anda.",
      );
    } finally {
      setIsSubmitting(false);
    }
  }

  return (
    <main className="auth-layout">
      <aside className="auth-hero">
        <BrandWordmark />
        <div className="auth-hero__copy">
          <p className="auth-hero__eyebrow">SMARTER CAMPUS AND LEARNING</p>
          <h1>Temukan ruang.<br />Wujudkan aktivitas.</h1>
          <p>Satu tempat untuk menemukan ruang kampus dan mengelola permohonan reservasi.</p>
        </div>
        <p className="auth-hero__footnote">RuangKampus · Campus room reservation</p>
      </aside>

      <section className="auth-panel" aria-labelledby="login-heading">
        <div className="auth-panel__content">
          <div className="auth-welcome">
            <p className="eyebrow">SELAMAT DATANG</p>
            <h2 id="login-heading">Masuk sebagai {role === "Student" ? "Mahasiswa" : "TU / Admin"}</h2>
            <p>Gunakan akun yang terdaftar untuk melanjutkan.</p>
          </div>

          <div className="role-switch" aria-label="Pilih jenis akun">
            {(["Student", "TU/Admin"] as const).map((option) => (
              <button
                className={role === option ? "role-switch__option is-active" : "role-switch__option"}
                type="button"
                key={option}
                aria-pressed={role === option}
                onClick={() => {
                  setRole(option);
                  setError("");
                }}
              >
                {option === "Student" ? "Mahasiswa" : "TU / Admin"}
              </button>
            ))}
          </div>

          <form className="login-form" onSubmit={handleSubmit}>
            <TextField
              label={role === "Student" ? "Email kampus" : "Email administrator"}
              type="email"
              name="email"
              autoComplete="username"
              placeholder="Masukkan email terdaftar"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
            />

            <TextField
              label="Kata sandi"
              type={showPassword ? "text" : "password"}
              name="password"
              autoComplete="current-password"
              placeholder="Masukkan kata sandi"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              trailingAction={
                <button
                  className="field__icon-button"
                  type="button"
                  onClick={() => setShowPassword((visible) => !visible)}
                  aria-label={showPassword ? "Sembunyikan kata sandi" : "Tampilkan kata sandi"}
                  aria-pressed={showPassword}
                >
                  {showPassword ? <EyeOff size={18} /> : <Eye size={18} />}
                </button>
              }
            />

            <div className="login-options">
              <label className="remember-option" title="Menunggu kesepakatan mekanisme sesi persisten dengan backend.">
                <input type="checkbox" disabled aria-disabled="true" />
                <span>Ingat saya</span>
              </label>
              <Link className="text-link" to="/forgot-password">Lupa kata sandi?</Link>
            </div>

            {error ? <div className="form-alert form-alert--error" role="alert">{error}</div> : null}

            <Button
              className="login-submit"
              type="submit"
              isLoading={isSubmitting}
              trailingIcon={<ArrowRight size={18} aria-hidden="true" />}
            >
              Masuk
            </Button>
          </form>

          <div className="secure-note">
            <ShieldCheck size={18} aria-hidden="true" />
            <span>Akses akun diproses melalui layanan autentikasi RuangKampus.</span>
          </div>

          <div className="account-support">
            <p>Memiliki kendala saat masuk?</p>
            <p className="account-support__detail">Hubungi administrator kampus untuk bantuan akun.</p>
          </div>

          <p className="auth-copyright">© 2026 RuangKampus</p>
        </div>
      </section>
    </main>
  );
}
