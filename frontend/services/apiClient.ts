import { clearAuthSession, getAccessToken } from "../stores/authStore";
import { appPath } from "../config/paths";

export class ApiError extends Error {
  constructor(
    message: string,
    public readonly status: number,
    public readonly retryAfter: number | null,
  ) {
    super(message);
  }
}

export async function request<T>(url: string, options: RequestInit = {}): Promise<T> {
  const headers = new Headers(options.headers);
  const token = getAccessToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (options.body && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }

  const response = await fetch(appPath(url), { cache: "no-store", ...options, headers });
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as {
      detail?: string | { code?: string; message?: string };
    } | null;
    // A late response from account A must not clear account B's new session.
    if (response.status === 401 && getAccessToken() === token) clearAuthSession();
    const detail = error?.detail;
    throw new ApiError(
      typeof detail === "string" ? detail : detail?.message ?? "Không thể kết nối đến máy chủ",
      response.status,
      Number(response.headers.get("Retry-After")) || null,
    );
  }
  return response.json() as Promise<T>;
}
