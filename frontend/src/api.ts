import Constants from "expo-constants";

const RAW =
  (Constants.expoConfig?.extra as any)?.backendUrl ||
  process.env.EXPO_BACKEND_URL ||
  process.env.EXPO_PUBLIC_BACKEND_URL ||
  "";

export const API_BASE = `${RAW}/api`;

export type ApiOptions = RequestInit & { token?: string };

export async function api<T = any>(path: string, options: ApiOptions = {}): Promise<T> {
  const { token, headers, ...rest } = options;
  const res = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(headers || {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    const detail = body?.detail || body?.message || `Permintaan gagal (${res.status})`;
    throw new Error(typeof detail === "string" ? detail : JSON.stringify(detail));
  }
  if (res.status === 204) return undefined as unknown as T;
  return (await res.json()) as T;
}
