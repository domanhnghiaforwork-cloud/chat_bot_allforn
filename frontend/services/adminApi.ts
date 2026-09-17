import type { AdminOverview, AuditLog, SettingsResponse } from "../types/admin";
import { request } from "./apiClient";

export function getAdminSettings(): Promise<SettingsResponse> {
  return request("/api/admin/settings");
}

export interface AdminSettingChange {
  key: string;
  value?: unknown;
  reset?: boolean;
}

export function updateAdminSettings(changes: AdminSettingChange[], reason: string) {
  return request<{ updated: string[] }>("/api/admin/settings", {
    method: "PATCH",
    body: JSON.stringify({ changes, reason }),
  });
}

export function getAdminOverview(): Promise<AdminOverview> {
  return request("/api/admin/overview");
}

export function getAuditLogs(): Promise<AuditLog[]> {
  return request("/api/admin/audit-logs?limit=50");
}
