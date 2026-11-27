import {
  createContext, useCallback, useContext, useEffect, useMemo, useState, type PropsWithChildren,
} from "react";
import { ApiError, authApi, setAccessToken } from "./api";
import type { AppRole, AuthUser } from "./types";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (identifier: string, password: string, expectedRole: AppRole) => Promise<AuthUser>;
  register: (payload: { name: string; email: string; password: string; student_identifier: string; phone?: string }) => Promise<AuthUser>;
  logout: () => Promise<void>;
  replaceUser: (user: AuthUser) => void;
}
const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: PropsWithChildren) {
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let active = true;
    authApi.refresh().then((session) => {
      if (!active) return;
      if (session?.access_token && session.user) {
        setAccessToken(session.access_token);
        setUser(session.user);
      } else {
        setAccessToken(null);
        setUser(null);
      }
    }).finally(() => {
      if (active) setLoading(false);
    });
    return () => { active = false; };
  }, []);

  const login = useCallback(async (identifier: string, password: string, expectedRole: AppRole) => {
    const session = await authApi.login(identifier, password);
    if (session.user.role !== expectedRole) {
      setAccessToken(null);
      throw new ApiError("Jenis akun yang dipilih tidak sesuai dengan role akun pada server.", 403, "ROLE_MISMATCH");
    }
    setAccessToken(session.access_token);
    setUser(session.user);
    return session.user;
  }, []);

  const register = useCallback(async (payload: { name: string; email: string; password: string; student_identifier: string; phone?: string }) => {
    const session = await authApi.register(payload);
    if (session.user.role !== "Student") {
      setAccessToken(null);
      throw new ApiError("Pendaftaran publik hanya dapat membuat akun Student.", 403, "ROLE_MISMATCH");
    }
    setAccessToken(session.access_token);
    setUser(session.user);
    return session.user;
  }, []);

  const logout = useCallback(async () => {
    try {
      if (user) await authApi.logout();
    } catch {
      // A password change or expired session may already have revoked the server session.
      // Local logout must still complete and must not block navigation to the login page.
    } finally {
      setAccessToken(null);
      setUser(null);
    }
  }, [user]);

  const replaceUser = useCallback((nextUser: AuthUser) => setUser(nextUser), []);
  const value = useMemo(() => ({ user, loading, login, register, logout, replaceUser }), [user, loading, login, register, logout, replaceUser]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}