import type { TokenPair } from "../../types";

export async function login(params: { baseUrl: string; email: string; password: string }): Promise<TokenPair> {
  const response = await fetch(`${params.baseUrl}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: params.email, password: params.password }),
  });

  if (!response.ok) {
    throw new Error("Login failed. Check credentials.");
  }

  return (await response.json()) as TokenPair;
}
