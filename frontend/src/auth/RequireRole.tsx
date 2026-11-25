import { Navigate, Outlet, useLocation } from "react-router";
import { useAuth, type AppRole } from "./AuthContext";

interface RequireRoleProps {
  allowedRole: AppRole;
}

function homeForRole(role: string) {
  return role === "Student" ? "/student/dashboard" : "/admin/dashboard";
}

/**
 * Client-side route guard for navigation UX only.
 * It does not replace backend authorization or protect API resources.
 */
export function RequireRole({ allowedRole }: RequireRoleProps) {
  const { user } = useAuth();
  const location = useLocation();

  if (!user) {
    return <Navigate to="/login" replace state={{ from: location.pathname }} />;
  }

  if (user.role !== allowedRole) {
    return <Navigate to={homeForRole(user.role)} replace />;
  }

  return <Outlet />;
}
