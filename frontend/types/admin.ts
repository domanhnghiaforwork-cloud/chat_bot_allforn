export interface EditableSetting {
  key: string;
  value: unknown;
  default: unknown;
  source: "env" | "override";
  value_type: "string" | "integer" | "number" | "boolean";
  group: string;
  minimum: number | null;
  maximum: number | null;
  requires_restart: boolean;
  choices: Array<[string | boolean, string]> | null;
}

export interface SettingsResponse {
  settings: EditableSetting[];
  secrets: Record<string, boolean>;
}

export interface AdminOverview {
  queue_depth: number | null;
  generation_statuses: Record<string, number>;
  usage_24h: { input_tokens: number; output_tokens: number; attempts: number };
  models: { default: string; summary: string; advanced: string };
}

export interface AuditLog {
  id: number;
  action: string;
  target: string;
  old_value: unknown;
  new_value: unknown;
  reason: string;
  created_at: string;
}
