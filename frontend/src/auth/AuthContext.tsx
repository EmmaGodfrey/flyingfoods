import { createContext, useContext, useMemo, type ReactNode } from "react";

import type { TokenPair } from "../types";
import { useAuthStore } from "../store/authStore";

type AuthContextValue = {
  accessToken: string | null;
  refreshToken: string | null;
  hasHydrated: boolean;
  isAuthenticated: boolean;
  setTokens: (tokens: TokenPair) => void;
  clearTokens: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const accessToken = useAuthStore((state) => state.accessToken);
  const refreshToken = useAuthStore((state) => state.refreshToken);
  const hasHydrated = useAuthStore((state) => state.hasHydrated);
  const setStoreTokens = useAuthStore((state) => state.setTokens);
  const clearTokens = useAuthStore((state) => state.clearTokens);

  const value = useMemo<AuthContextValue>(
    () => ({
      accessToken,
      refreshToken,
      hasHydrated,
      isAuthenticated: Boolean(accessToken && refreshToken),
      setTokens: (tokens) => setStoreTokens(tokens),
      clearTokens,
    }),
    [accessToken, refreshToken, hasHydrated, setStoreTokens, clearTokens],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider");
  }
  return context;
}
