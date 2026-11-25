import { useEffect, useState } from "react";
import { Bell, ChevronDown, LogOut, Moon, Sun } from "lucide-react";
import { Link, NavLink, Outlet, useLocation, useNavigate } from "react-router";
import { useAuth, type AppRole } from "../../auth/AuthContext";
import { BrandWordmark } from "../BrandWordmark";
import { currentPageTitle, navigationForRole, type NavigationItem } from "./navigation";
import { Breadcrumbs } from "./Breadcrumbs";

interface AppShellProps { role: AppRole; }

function initialsFromName(name: string) {
  return name.trim().split(/\s+/).slice(0, 2).map((part) => part[0] ?? "").join("").toUpperCase() || "RK";
}

function NavigationLinks({ items, compact = false }: { items: NavigationItem[]; compact?: boolean }) {
  return (
    <>
      {items.map(({ label, mobileLabel, to, icon: Icon }) => (
        <NavLink
          key={to}
          to={to}
          end
          className={({ isActive }) => `workspace-nav__link ${isActive ? "is-active" : ""}`.trim()}
          aria-label={label}
          title={compact ? label : undefined}
        >
          <Icon size={19} strokeWidth={1.8} aria-hidden="true" />
          <span>{compact ? mobileLabel : label}</span>
        </NavLink>
      ))}
    </>
  );
}

function Sidebar({ role, items }: { role: AppRole; items: NavigationItem[] }) {
  const homePath = role === "Student" ? "/student/dashboard" : "/admin/dashboard";
  return (
    <aside className="workspace-sidebar">
      <Link className="workspace-sidebar__brand" to={homePath}><BrandWordmark /></Link>
      <div className="workspace-sidebar__label">
        {role === "Student" ? "STUDENT WORKSPACE" : "TU / ADMIN WORKSPACE"}
      </div>
      <nav className="workspace-nav" aria-label="Navigasi utama"><NavigationLinks items={items} /></nav>
      <div className="workspace-sidebar__footer">
        <span className="workspace-sidebar__status" aria-hidden="true" />
        <span>RuangKampus</span>
        <span className="workspace-sidebar__version">Web</span>
      </div>
    </aside>
  );
}

function ThemeToggle() {
  const [isDark, setIsDark] = useState(false);
  useEffect(() => {
    document.documentElement.dataset.theme = isDark ? "dark" : "light";
  }, [isDark]);

  return (
    <button
      className="icon-action"
      type="button"
      onClick={() => setIsDark((current) => !current)}
      aria-label={isDark ? "Aktifkan light mode" : "Aktifkan dark mode"}
      aria-pressed={isDark}
      title={isDark ? "Light mode" : "Dark mode"}
    >
      {isDark ? <Sun size={18} /> : <Moon size={18} />}
    </button>
  );
}

function NotificationButton({ role }: { role: AppRole }) {
  const path = role === "Student" ? "/student/notifications" : "/admin/notifications";
  return (
    <NavLink className="icon-action notification-action" to={path} aria-label="Buka notifikasi" title="Notifikasi">
      <Bell size={18} />
    </NavLink>
  );
}

function ProfileMenu({ role, name, onLogout }: { role: AppRole; name: string; onLogout: () => void }) {
  const [open, setOpen] = useState(false);
  const profilePath = role === "Student" ? "/student/profile" : "/admin/profile";

  return (
    <div className="profile-menu">
      <button
        className="profile-menu__trigger"
        type="button"
        onClick={() => setOpen((current) => !current)}
        aria-expanded={open}
        aria-haspopup="true"
      >
        <span className="avatar">{initialsFromName(name)}</span>
        <span className="profile-menu__identity">
          <strong>{name}</strong>
          <small>{role === "Student" ? "Mahasiswa" : "TU / Administrator"}</small>
        </span>
        <ChevronDown size={16} aria-hidden="true" />
      </button>
      {open ? (
        <div className="profile-menu__panel">
          <Link to={profilePath} onClick={() => setOpen(false)}>Profil akun</Link>
          <button type="button" onClick={() => { setOpen(false); onLogout(); }}>
            <LogOut size={16} aria-hidden="true" />Keluar
          </button>
        </div>
      ) : null}
    </div>
  );
}

export function AppShell({ role }: AppShellProps) {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const items = navigationForRole(role);
  const title = currentPageTitle(location.pathname, role);
  const homePath = role === "Student" ? "/student/dashboard" : "/admin/dashboard";
  const displayName = user?.name?.trim() || (role === "Student" ? "Mahasiswa" : "Administrator");

  async function handleLogout() {
    try {
      await logout();
    } catch {
      // AuthContext clears the in-memory session even if the API cannot be reached.
    } finally {
      navigate("/login", { replace: true });
    }
  }

  return (
    <div className="workspace-shell">
      <Sidebar role={role} items={items} />
      <div className="workspace-main">
        <header className="workspace-topbar">
          <Link className="workspace-topbar__mobile-brand" to={homePath}><BrandWordmark /></Link>
          <div className="workspace-topbar__page-context">
            <span className="workspace-topbar__eyebrow">
              {role === "Student" ? "STUDENT PORTAL" : "ADMINISTRATION"}
            </span>
            <strong>{title}</strong>
          </div>
          <div className="workspace-topbar__actions">
            <ThemeToggle />
            <NotificationButton role={role} />
            <ProfileMenu role={role} name={displayName} onLogout={() => void handleLogout()} />
          </div>
        </header>
        <main className="workspace-content">
          <Breadcrumbs homePath={homePath} current={title} />
          <Outlet />
        </main>
      </div>
      <nav
        className="workspace-mobile-nav"
        aria-label="Navigasi mobile"
        style={{ gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))` }}
      >
        <NavigationLinks items={items} compact />
      </nav>
    </div>
  );
}
