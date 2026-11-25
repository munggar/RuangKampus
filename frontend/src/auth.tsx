import {
  createContext, useCallback, useContext, useEffect, useMemo, useState, type PropsWithChildren,
} from "react";
import { ApiError, authApi, setAccessToken } from "./api";
import type { AppRole, AuthUser } from "./types";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  login: (email: string, password: string, expectedRole: AppRole) => Promise<AuthUser>;
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

  const login = useCallback(async (email: string, password: string, expectedRole: AppRole) => {
    const session = await authApi.login(email, password);
    if (session.user.role !== expectedRole) {
      setAccessToken(null);
      throw new ApiError("Jenis akun yang dipilih tidak sesuai dengan role akun pada server.", 403, "ROLE_MISMATCH");
    }
    setAccessToken(session.access_token);
    setUser(session.user);
    return session.user;
  }, []);

  const logout = useCallback(async () => {
    try { if (user) await authApi.logout(); }
    finally { setAccessToken(null); setUser(null); }
  }, [user]);

  const replaceUser = useCallback((nextUser: AuthUser) => setUser(nextUser), []);
  const value = useMemo(() => ({ user, loading, login, logout, replaceUser }), [user, loading, login, logout, replaceUser]);
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}