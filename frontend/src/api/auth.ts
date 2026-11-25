import { apiRequest } from "./http";

export interface AuthUser {
  id: string;
  name: string;
  role: string;
  email?: string;
}

export interface LoginResponse {
  access_token: string;
  token_type: string;
  expires_in: number;
  user: AuthUser;
}

export const authApi = {
  login(email: string, password: string) {
    return apiRequest<LoginResponse>("/auth/login", {
      method: "POST",
      body: { email, password },
    });
  },

  logout() {
    return apiRequest<{ success: boolean }>("/auth/logout", { method: "POST" });
  },

  currentUser() {
    return apiRequest<AuthUser>("/auth/me");
  },
};
