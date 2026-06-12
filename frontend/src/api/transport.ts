import type { TokenPair } from "../types";

export type ApiTransportOptions = {
  baseUrl: string;
  getAccessToken: () => string | null;
  getRefreshToken: () => string | null;
  onTokens: (tokens: TokenPair) => void;
  onUnauthorized: () => void;
  onError?: (message: string) => void;
};

export type ApiTransport = {
  request: <T>(path: string, init?: RequestInit, retried?: boolean) => Promise<T>;
};

export function createApiTransport(options: ApiTransportOptions): ApiTransport {
  const refresh = async (): Promise<boolean> => {
    const refreshToken = options.getRefreshToken();
    if (!refreshToken) {
      return false;
    }

    const response = await fetch(`${options.baseUrl}/auth/refresh`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh_token: refreshToken }),
    });

    if (!response.ok) {
      return false;
    }

    const tokens = (await response.json()) as TokenPair;
    options.onTokens(tokens);
    return true;
  };

  const request = async <T>(path: string, init?: RequestInit, retried = false): Promise<T> => {
    const headers = new Headers(init?.headers ?? {});
    const accessToken = options.getAccessToken();
    if (accessToken) {
      headers.set("Authorization", `Bearer ${accessToken}`);
    }

    const response = await fetch(`${options.baseUrl}${path}`, {
      ...init,
      headers,
    });

    if (response.status === 401 && !retried) {
      const refreshed = await refresh();
      if (refreshed) {
        return request<T>(path, init, true);
      }
      options.onUnauthorized();
      const message = "Session expired.";
      options.onError?.(message);
      throw new Error(message);
    }

    if (!response.ok) {
      const message = (await response.text()) || "Request failed.";
      options.onError?.(message);
      throw new Error(message);
    }

    if (response.status === 204) {
      return undefined as T;
    }

    return (await response.json()) as T;
  };

  return { request };
}
