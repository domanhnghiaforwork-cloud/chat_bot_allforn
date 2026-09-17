import type { AuthResponse, User } from "../types/auth";
import { request } from "./apiClient";

interface Credentials {
  email: string;
  password: string;
}

export function register(credentials: Credentials): Promise<AuthResponse> {
  return request("/api/auth/register", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export function login(credentials: Credentials): Promise<AuthResponse> {
  return request("/api/auth/login", {
    method: "POST",
    body: JSON.stringify(credentials),
  });
}

export function getCurrentUser(): Promise<User> {
  return request("/api/users/me");
}
