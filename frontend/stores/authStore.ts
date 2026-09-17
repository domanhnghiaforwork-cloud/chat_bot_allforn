import type { User } from "../types/auth";

const STORAGE_KEY = "chatbot-auth:v3";
export const AUTH_CHANGED_EVENT = "auth-changed";

interface AuthSession {
  accessToken: string;
  user: User;
}

export function getAuthSession(): AuthSession | null {
  if (typeof window === "undefined") return null;
  try {
    const value = JSON.parse(localStorage.getItem(STORAGE_KEY) ?? "null") as AuthSession | null;
    return typeof value?.accessToken === "string" && typeof value.user?.email === "string"
      ? value
      : null;
  } catch {
    return null;
  }
}

export function getAccessToken(): string | null {
  return getAuthSession()?.accessToken ?? null;
}

export function saveAuthSession(accessToken: string, user: User): void {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ accessToken, user }));
  } catch {
    throw new Error("Trình duyệt không cho phép lưu phiên đăng nhập");
  }
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}

export function clearAuthSession(): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.removeItem(STORAGE_KEY);
  } catch {}
  window.dispatchEvent(new Event(AUTH_CHANGED_EVENT));
}
