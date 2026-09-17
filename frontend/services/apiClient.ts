import { clearAuthSession, getAccessToken } from "../stores/authStore";

export async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(url, { cache: "no-store", ...options, headers });
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as { detail?: string } | null;
    if (response.status === 401) clearAuthSession();
    throw new Error(error?.detail ?? "Không thể kết nối đến máy chủ");
  }
  return response.json() as Promise<T>;
}
