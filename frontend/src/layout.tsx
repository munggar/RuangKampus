import { useEffect, useMemo, useRef, useState, type ReactNode } from "react";
import {
  Bell, Building2, CalendarDays, CalendarCheck, Clock3, ChevronDown, ClipboardList, FileSpreadsheet, LayoutDashboard,
  LogOut, Moon, Sparkles, Sun, UserRound,
} from "lucide-react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { useAuth } from "./auth";
import { notificationApi } from "./api";
import type { AppRole } from "./types";
import { initialsFromName } from "./ui";

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
    { label: "AI Assistant", shortLabel: "AI", path: base + "/assistant", icon: Sparkles, ai: true },
    { label: "Manage rooms", shortLabel: "Rooms", path: base + "/rooms", icon: Building2 },
    { label: "Profile", shortLabel: "Profile", path: base + "/profile", icon: UserRound },
  ];
}
function Brand() {
  return <img className="brand-logo brand-logo--navigation" src="/brand/logo-primary.png" alt="RuangKampus — Find the Room. Book the Space." />;
}
function useTheme() {
  const [theme, setThemeState] = useState<"light" | "dark">(() => {
    const saved = typeof localStorage === "undefined" ? null : localStorage.getItem("rk-theme");
    return saved === "dark" ? "dark" : "light";
  });
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    if (typeof localStorage !== "undefined") localStorage.setItem("rk-theme", theme);
    window.dispatchEvent(new Event("rk-theme-change"));
  }, [theme]);
  useEffect(() => {
    const syncTheme = () => setThemeState(document.documentElement.dataset.theme === "dark" ? "dark" : "light");
    const syncStorage = (event: StorageEvent) => {
      if (event.key === "rk-theme") setThemeState(event.newValue === "dark" ? "dark" : "light");
    };
    window.addEventListener("rk-theme-change", syncTheme);
    window.addEventListener("storage", syncStorage);
    return () => {
      window.removeEventListener("rk-theme-change", syncTheme);
      window.removeEventListener("storage", syncStorage);
    };
  }, []);
  return { theme, setTheme: setThemeState };
}
function CampusClock() {
  const [now, setNow] = useState(() => new Date());
  useEffect(() => {
    const timer = window.setInterval(() => setNow(new Date()), 1000);
    return () => window.clearInterval(timer);
  }, []);
  const time = new Intl.DateTimeFormat("id-ID", {
    timeZone: "Asia/Jakarta", hour: "2-digit", minute: "2-digit", second: "2-digit", hourCycle: "h23",
  }).format(now);
  const date = new Intl.DateTimeFormat("id-ID", {
    timeZone: "Asia/Jakarta", weekday: "short", day: "2-digit", month: "short",
  }).format(now);
  return <div className="campus-clock" aria-label={"Waktu kampus WIB " + time}>
    <Clock3 size={17} aria-hidden="true" />
    <span><small>Waktu kampus · WIB · {date}</small><strong>{time}</strong></span>
  </div>;
}
function ThemeButton({ theme, toggle }: { theme: "light" | "dark"; toggle: () => void }) {
  const dark = theme === "dark";
  return <button className="icon-button" type="button" onClick={toggle} aria-label={dark ? "Aktifkan mode terang" : "Aktifkan mode gelap"} aria-pressed={dark}>{dark ? <Sun size={18} /> : <Moon size={18} />}</button>;
}
function pageLabel(path: string, role: AppRole) {
  const root = role === "Student" ? "/student" : "/admin";
  if (/^\/student\/rooms\/[^/]+\/book$/.test(path)) return "Ajukan reservasi";
  if (path === "/admin/rooms/new") return "Tambah ruangan";
  if (/^\/admin\/rooms\/[^/]+\/edit$/.test(path)) return "Edit ruangan";
  if (/^\/(student|admin)\/rooms\/[^/]+$/.test(path)) return "Detail ruangan";
  if (path.includes("/reservations/") && path !== root + "/reservations") return "Detail reservasi";
  const items: Array<[string, string]> = [
    [root + "/dashboard", "Dashboard"], [root + "/rooms", "Ruang kampus"],
    [root + "/reservations", role === "Student" ? "Reservasi saya" : "Permohonan reservasi"],
    [root + "/notifications", "Notifikasi"], [root + "/profile", "Profil"],
    [root + "/assistant", "AI Assistant"], [root + "/availability", "Ketersediaan ruangan"],
    [root + "/alternatives", "Slot alternatif"], [root + "/schedules", "Jadwal ruang"], ["/admin/data-imports", "Impor data kampus"],
  ];
  return items.find(([route]) => path === route)?.[1] || "RuangKampus";
}
function Navigation({ items, mobile = false }: { items: NavigationItem[]; mobile?: boolean }) {
  return <nav className={mobile ? "mobile-nav__items" : "sidebar-nav"} aria-label="Navigasi utama">
    {items.map((item) => {
      const Icon = item.icon;
      return <NavLink key={item.path} to={item.path} end={item.path.endsWith("/dashboard")}
        className={({ isActive }) => "nav-link" + (isActive ? " is-active" : "") + (item.ai ? " nav-link--ai" : "")} title={item.label}>
        <span className="nav-link__icon"><Icon size={mobile ? 19 : 18} strokeWidth={1.8} /></span>
        <span className="nav-link__label">{mobile ? item.shortLabel : item.label}</span>
      </NavLink>;
    })}
  </nav>;
}

function useUnreadNotificationCount() {
  const [unreadCount, setUnreadCount] = useState(0);

  useEffect(() => {
    let active = true;
    const refresh = () => {
      void notificationApi.list(new URLSearchParams({
        unreadOnly: "true",
        page: "1",
        limit: "1",
      })).then((result) => {
        if (!active) return;
        setUnreadCount(result.meta?.total ?? result.items.filter((item) => !item.read_at).length);
      }).catch(() => {
        // Preserve the last known count when the API is temporarily unavailable.
      });
    };
    const refreshWhenVisible = () => {
      if (document.visibilityState === "visible") refresh();
    };

    refresh();
    const interval = window.setInterval(refresh, 30_000);
    window.addEventListener("focus", refresh);
    window.addEventListener("rk-notifications-updated", refresh);
    document.addEventListener("visibilitychange", refreshWhenVisible);

    return () => {
      active = false;
      window.clearInterval(interval);
      window.removeEventListener("focus", refresh);
      window.removeEventListener("rk-notifications-updated", refresh);
      document.removeEventListener("visibilitychange", refreshWhenVisible);
    };
  }, []);

  return unreadCount;
}

export function AppShell({ role }: { role: AppRole }) {
  const { user, logout } = useAuth();
  const { theme, setTheme } = useTheme();
  const navigate = useNavigate();
  const location = useLocation();
  const items = useMemo(() => navigationFor(role), [role]);
  const [menuOpen, setMenuOpen] = useState(false);
  const accountMenuRef = useRef<HTMLDivElement>(null);
  const accountTriggerRef = useRef<HTMLButtonElement>(null);
  const name = user?.name || (role === "Student" ? "Mahasiswa" : "Administrator");
  const initials = initialsFromName(name);
  const root = role === "Student" ? "/student" : "/admin";
  const unreadCount = useUnreadNotificationCount();

  useEffect(() => {
    if (!menuOpen) return;
    const closeOnOutside = (event: PointerEvent) => {
      if (event.target instanceof Node && !accountMenuRef.current?.contains(event.target)) setMenuOpen(false);
    };
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        setMenuOpen(false);
        accountTriggerRef.current?.focus();
      }
    };
    document.addEventListener("pointerdown", closeOnOutside);
    document.addEventListener("keydown", closeOnEscape);
    return () => {
      document.removeEventListener("pointerdown", closeOnOutside);
      document.removeEventListener("keydown", closeOnEscape);
    };
  }, [menuOpen]);

  async function handleLogout() {
    try { await logout(); } finally { navigate("/login", { replace: true }); }
  }

  return <div className="app-shell">
    <aside className="desktop-sidebar">
      <Link className="brand-link" to={root + "/dashboard"}><Brand /></Link>
      <p className="sidebar-caption">{role === "Student" ? "STUDENT WORKSPACE" : "TU / ADMIN WORKSPACE"}</p>
      <Navigation items={items} />
      {role === "TU/Admin" ? <><Link className="sidebar-secondary-link" to="/admin/schedules"><CalendarDays size={17} />Jadwal & pemeliharaan</Link><Link className="sidebar-secondary-link" to="/admin/data-imports"><FileSpreadsheet size={17} />Impor data kampus</Link></> : null}
      <div className="sidebar-footer"><span className="online-dot" />RuangKampus <span>Web</span></div>
    </aside>
    <div className="app-main">
      <header className="topbar">
        <Link className="mobile-brand" to={root + "/dashboard"}><Brand /></Link>
        <div className="topbar-page"><span>{role === "Student" ? "STUDENT PORTAL" : "ADMINISTRATION"}</span><strong>{pageLabel(location.pathname, role)}</strong></div>
        <div className="topbar-actions">
          <ThemeButton theme={theme} toggle={() => setTheme(theme === "dark" ? "light" : "dark")} />
          <Link
            className="icon-button notification-link"
            to={root + "/notifications"}
            aria-label={unreadCount > 0 ? `Notifikasi, ${unreadCount} belum dibaca` : "Buka notifikasi"}
            title={unreadCount > 0 ? `${unreadCount} notifikasi belum dibaca` : "Notifikasi"}
          >
            <Bell size={18} />
            {unreadCount > 0 ? <span className="notification-badge" aria-hidden="true">{unreadCount > 99 ? "99+" : unreadCount}</span> : null}
          </Link>
          <div className="account-menu" ref={accountMenuRef}>
            <button ref={accountTriggerRef} className="account-trigger" type="button" onClick={() => setMenuOpen(!menuOpen)} aria-expanded={menuOpen} aria-controls="account-menu-dropdown">
              <span className="avatar">{initials}</span><span className="account-trigger__name"><b>{name}</b><small>{role === "Student" ? "Mahasiswa" : "TU / Administrator"}</small></span><ChevronDown size={15} />
            </button>
            {menuOpen ? <div id="account-menu-dropdown" className="account-dropdown"><Link to={root + "/profile"} onClick={() => setMenuOpen(false)}>Profil akun</Link><button type="button" onClick={() => { setMenuOpen(false); void handleLogout(); }}><LogOut size={15} />Keluar</button></div> : null}
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