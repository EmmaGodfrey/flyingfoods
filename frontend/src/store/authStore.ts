/**
 * Auth store. The access token lives only in memory (never localStorage) and is
 * mirrored into the API client. On boot we try a silent refresh against the
 * httpOnly refresh cookie so a reload keeps the session without re-login.
 */

import { create } from "zustand";

import { api, setAccessToken, setAuthLostHandler } from "../lib/apiClient";
import type { AuthUser } from "../types";

interface AuthState {
  user: AuthUser | null;
  status: "loading" | "authenticated" | "anonymous";
  login: (email: string, password: string) => Promise<void>;
  logout: () => Promise<void>;
  bootstrap: () => Promise<void>;
}

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  status: "loading",

  login: async (email, password) => {
    const data = await api.authPost<{ access: string; user: AuthUser }>("/auth/login/", {
      email,
      password,
    });
    setAccessToken(data.access);
    set({ user: data.user, status: "authenticated" });
  },

  logout: async () => {
    try {
      await api.post("/auth/logout/");
    } catch {
      // Logging out is best-effort; clear local state regardless.
    }
    setAccessToken(null);
    set({ user: null, status: "anonymous" });
  },

  bootstrap: async () => {
    const fresh = await api.refresh();
    if (!fresh) {
      set({ status: "anonymous" });
      return;
    }
    try {
      const user = await api.get<AuthUser>("/auth/me/");
      set({ user, status: "authenticated" });
    } catch {
      setAccessToken(null);
      set({ status: "anonymous" });
    }
  },
}));

// When a refresh fails mid-session, drop to anonymous so routes redirect.
setAuthLostHandler(() => {
  setAccessToken(null);
  useAuthStore.setState({ user: null, status: "anonymous" });
});
