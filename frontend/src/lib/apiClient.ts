/**
 * Central API client for the Django backend.
 *
 * Every endpoint returns the envelope `{ success, data | error }`. This client
 * unwraps it: it resolves with `data` on success and throws an `ApiError`
 * carrying the backend error `code` and `message` on failure. The access token
 * lives in memory (the auth store); the refresh token is an httpOnly cookie the
 * backend sets, so refresh needs only `credentials: "include"`.
 */

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";
const API_ROOT = `${API_BASE_URL}/api`;

export class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, message: string, status: number) {
    super(message);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

type Envelope<T> =
  | { success: true; data: T }
  | { success: false; error: { code: string; message: string } };

let accessToken: string | null = null;
let onAuthLost: (() => void) | null = null;

/** Store the in-memory access token (called by the auth store). */
export function setAccessToken(token: string | null): void {
  accessToken = token;
}

/** Register a callback invoked when refresh fails and the session is gone. */
export function setAuthLostHandler(handler: () => void): void {
  onAuthLost = handler;
}

async function refreshAccessToken(): Promise<string | null> {
  const response = await fetch(`${API_ROOT}/auth/refresh/`, {
    method: "POST",
    credentials: "include",
  });
  if (!response.ok) return null;
  const body = (await response.json()) as Envelope<{ access: string }>;
  if (!body.success) return null;
  accessToken = body.data.access;
  return body.data.access;
}

type RequestOptions = {
  method?: string;
  body?: unknown;
  /** Idempotency key for stock-posting endpoints. */
  idempotencyKey?: string;
  /** Skip the automatic 401 refresh-and-retry (used by auth calls). */
  noRetry?: boolean;
  /** Return the raw Response instead of unwrapping (file downloads). */
  raw?: boolean;
};

async function call(path: string, options: RequestOptions): Promise<Response> {
  const headers: Record<string, string> = {};
  if (options.body !== undefined) headers["Content-Type"] = "application/json";
  if (accessToken) headers["Authorization"] = `Bearer ${accessToken}`;
  if (options.idempotencyKey) headers["Idempotency-Key"] = options.idempotencyKey;

  return fetch(`${API_ROOT}${path}`, {
    method: options.method ?? "GET",
    headers,
    credentials: "include",
    body: options.body !== undefined ? JSON.stringify(options.body) : undefined,
  });
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  let response = await call(path, options);

  if (response.status === 401 && !options.noRetry) {
    const fresh = await refreshAccessToken();
    if (fresh) {
      response = await call(path, options);
    } else {
      onAuthLost?.();
      throw new ApiError("AUTH_REQUIRED", "Your session has expired.", 401);
    }
  }

  if (options.raw) {
    if (!response.ok) {
      throw new ApiError("DOWNLOAD_FAILED", "Export failed.", response.status);
    }
    return response as unknown as T;
  }

  if (response.status === 204) {
    return undefined as T;
  }

  const body = (await response.json()) as Envelope<T>;
  if (!body.success) {
    throw new ApiError(body.error.code, body.error.message, response.status);
  }
  return body.data;
}

export const api = {
  get: <T>(path: string) => request<T>(path),
  post: <T>(path: string, body?: unknown, idempotencyKey?: string) =>
    request<T>(path, { method: "POST", body, idempotencyKey }),
  patch: <T>(path: string, body?: unknown) => request<T>(path, { method: "PATCH", body }),
  put: <T>(path: string, body?: unknown) => request<T>(path, { method: "PUT", body }),
  del: <T>(path: string) => request<T>(path, { method: "DELETE" }),
  /** GET returning the raw Response (file downloads), with auth + 401 retry. */
  getRaw: (path: string) => request<Response>(path, { raw: true }),
  /** POST without the 401 retry — used by login/refresh themselves. */
  authPost: <T>(path: string, body?: unknown) =>
    request<T>(path, { method: "POST", body, noRetry: true }),
  refresh: refreshAccessToken,
  /** WebSocket URL with the access token in the query string. */
  wsUrl: (path: string) => {
    const base = API_BASE_URL.replace(/^http/, "ws");
    const token = accessToken ? `?token=${encodeURIComponent(accessToken)}` : "";
    return `${base}${path}${token}`;
  },
};
