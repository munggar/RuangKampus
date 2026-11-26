import { useEffect, useMemo, useState, type ReactNode } from "react";
import {
  Bell, Building2, CalendarDays, CalendarCheck, ChevronDown, ClipboardList, LayoutDashboard,
  LogOut, Moon, Sparkles, Sun, UserRound, Users,
} from "lucide-react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { useAuth } from "./auth";
import type { AppRole } from "./types";

interface NavigationItem {
  label: string; shortLabel: string; path: string; icon: typeof LayoutDashboard; ai?: boolean;
}
function navigationFor(role: AppRole): NavigationItem[] {
  const base = role === "Student" ? "/student" : "/admin";
  return role === "Student" ? [
    { label: "Dashboard", shortLabel: "Home", path: base + "/dashboard", icon: LayoutDashboard },
    { label: "Rooms", shortLabel: "Rooms", path: base + "/rooms", icon: Building2 },
    { label: "AI Assistant", shortLabel: "AI", path: base + "/assistant", icon: Sparkles, ai: true },
    { label: "My bookings", shortLabel: "Bookings", path: base + "/reservations", icon: CalendarCheck },
    { label: "Profile", shortLabel: "Profile", path: base + "/profile", icon: UserRound },
  ] : [
    { label: "Dashboard", shortLabel: "Home", path: base + "/dashboard", icon: LayoutDashboard },
    { label: "Reservation requests", shortLabel: "Requests", path: base + "/reservations", icon: ClipboardList },
    { label: "Manage rooms", shortLabel: "Rooms", path: base + "/rooms", icon: Building2 },
    { label: "Schedules", shortLabel: "Jadwal", path: base + "/schedules", icon: CalendarDays },
    { label: "Manage users", shortLabel: "Users", path: base + "/users", icon: Users },
  ];
}
function Brand() {
  return <span className="brand-mark"><span className="brand-mark__symbol" aria-hidden="true"><span /></span><span className="brand-mark__copy"><strong>RuangKampus</strong><small>Find the Room. Book the Space.</small></span></span>;
}
function useTheme() {
  const [theme, setThemeState] = useState<"light" | "dark">(() => {
    const saved = typeof localStorage === "undefined" ? null : localStorage.getItem("rk-theme");
    return saved === "dark" ? "dark" : "light";
  });
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    if (typeof localStorage !== "undefined") localStorage.setItem("rk-theme", theme);
  }, [theme]);
  return { theme, setTheme: setThemeState };
}
function ThemeButton({ theme, toggle }: { theme: "light" | "dark"; toggle: () => void }) {
  const dark = theme === "dark";
  return <button className="icon-button" type="button" onClick={toggle} aria-label={dark ? "Aktifkan mode terang" : "Aktifkan mode gelap"} aria-pressed={dark}>{dark ? <Sun size={18} /> : <Moon size={18} />}</button>;
}
function pageLabel(path: string, role: AppRole) {
  const root = role === "Student" ? "/student" : "/admin";
  if (path.includes("/rooms/new")) return "Tambah ruangan";
  if (path.includes("/rooms/") && path.endsWith("/edit")) return "Edit ruangan";
  if (path.includes("/rooms/") && !path.endsWith("/edit")) return "Detail ruangan";
  if (path.includes("/reservations/") && path !== root + "/reservations") return "Detail reservasi";
  const items: Array<[string, string]> = [
    [root + "/dashboard", "Dashboard"], [root + "/rooms", "Ruang kampus"],
    [root + "/reservations", role === "Student" ? "Reservasi saya" : "Permohonan reservasi"],
    [root + "/notifications", "Notifikasi"], [root + "/profile", "Profil"],
    [root + "/assistant", "AI Assistant"], [root + "/availability", "Ketersediaan ruangan"],
    [root + "/alternatives", "Slot alternatif"], [root + "/schedules", "Jadwal ruang"],
    [root + "/users", "Kelola pengguna"], [root + "/activity", "Riwayat aktivitas"],
    [root + "/schedule-imports", "Impor jadwal"],
  ];
  return items.find(([route]) => path === route)?.[1] || "RuangKampus";
}
function Navigation({ items, mobile = false }: { items: NavigationItem[]; mobile?: boolean }) {
  return <nav className={mobile ? "mobile-nav__items" : "sidebar-nav"} aria-label="Navigasi utama">
    {items.map((item) => {
      const Icon = item.icon;
      return <NavLink key={item.path} to={item.path} end={item.path.endsWith("/dashboard") || item.path.endsWith("/rooms") || item.path.endsWith("/reservations")}
        className={({ isActive }) => "nav-link" + (isActive ? " is-active" : "") + (item.ai ? " nav-link--ai" : "")} title={item.label}>
        <span className="nav-link__icon"><Icon size={mobile ? 19 : 18} strokeWidth={1.8} /></span>
        <span className="nav-link__label">{mobile ? item.shortLabel : item.label}</span>
      </NavLink>;
    })}
  </nav>;
}

export function AppShell({ role }: { role: AppRole }) {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const items = useMemo(() => navigationFor(role), [role]);
  const [menuOpen, setMenuOpen] = useState(false);
  const name = user?.name || (role === "Student" ? "Mahasiswa" : "Administrator");
  const initials = name.trim().split(/\\s+/).slice(0, 2).map((part) => part[0] || "").join("").toUpperCase() || "RK";
  const root = role === "Student" ? "/student" : "/admin";

  async function handleLogout() {
    try { await logout(); } finally { navigate("/login", { replace: true }); }
  }

  return <div className="app-shell">
    <aside className="desktop-sidebar">
      <Link className="brand-link" to={root + "/dashboard"}><Brand /></Link>
      <p className="sidebar-caption">{role === "Student" ? "STUDENT WORKSPACE" : "TU / ADMIN WORKSPACE"}</p>
      <Navigation items={items} />
      {role === "TU/Admin" ? <div className="sidebar-secondary-links">
        <Link className="sidebar-secondary-link" to="/admin/schedule-imports"><CalendarDays size={17} />Impor jadwal</Link>
        <Link className="sidebar-secondary-link" to="/admin/activity"><ClipboardList size={17} />Riwayat aktivitas</Link>
        <Link className="sidebar-secondary-link" to="/admin/assistant"><Sparkles size={17} />Bantuan Admin</Link>
      </div> : null}
      <div className="sidebar-footer"><span className="online-dot" />RuangKampus <span>Web</span></div>
    </aside>
    <div className="app-main">
      <header className="topbar">
        <Link className="mobile-brand" to={root + "/dashboard"}><Brand /></Link>
        <div className="topbar-page"><span>{role === "Student" ? "STUDENT PORTAL" : "ADMINISTRATION"}</span><strong>{pageLabel(location.pathname, role)}</strong></div>
        <div className="topbar-actions">
          <ThemeButton theme={theme} toggle={() => setTheme(theme === "dark" ? "light" : "dark")} />
          <Link className="icon-button notification-link" to={root + "/notifications"} aria-label="Buka notifikasi"><Bell size={18} /></Link>
          <div className="account-menu">
            <button className="account-trigger" type="button" onClick={() => setMenuOpen(!menuOpen)} aria-expanded={menuOpen}>
              <span className="avatar">{initials}</span><span className="account-trigger__name"><b>{name}</b><small>{role === "Student" ? "Mahasiswa" : "TU / Administrator"}</small></span><ChevronDown size={15} />
            </button>
            {menuOpen ? <div className="account-dropdown"><Link to={root + "/profile"} onClick={() => setMenuOpen(false)}>Profil akun</Link><button type="button" onClick={() => { setMenuOpen(false); void handleLogout(); }}><LogOut size={15} />Keluar</button></div> : null}
          </div>
        </div>
      </header>
      <main className="main-content"><Outlet /></main>
      <footer className="desktop-footer">© {new Date().getFullYear()} RuangKampus · Campus facilities</footer>
    </div>
    <div className="mobile-nav-shell"><Navigation items={items} mobile /></div>
  </div>;
}

export function PageTitle({ eyebrow, title, description, action }: { eyebrow?: string; title: string; description?: string; action?: ReactNode }) {
  return <header className="page-title"><div>{eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}<h1>{title}</h1>{description ? <p className="page-description">{description}</p> : null}</div>{action ? <div className="page-title__action">{action}</div> : null}</header>;
}