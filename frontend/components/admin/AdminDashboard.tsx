"use client";

import { useCallback, useEffect, useState } from "react";

import {
  ADMIN_TOKEN_SETTING_KEYS,
  GROUP_TITLES,
  SECRET_TITLES,
  settingPresentation,
} from "../../config/adminSettings";
import { adjustTokenDrafts, type TokenDraftState } from "../../config/adminTokenLimits";
import {
  getAdminOverview,
  getAdminSettings,
  updateAdminSettings,
} from "../../services/adminApi";
import type { AdminOverview, EditableSetting, SettingsResponse } from "../../types/admin";

function parseValue(setting: EditableSetting, raw: string | boolean): unknown {
  if (setting.value_type === "boolean") return Boolean(raw);
  if (setting.value_type === "integer") return Number.parseInt(String(raw), 10);
  if (setting.value_type === "number") return Number(raw);
  return String(raw);
}

function draftValue(setting: EditableSetting, value: unknown): string | boolean {
  return setting.value_type === "boolean" ? Boolean(value) : String(value ?? "");
}

function isChanged(setting: EditableSetting, draft: string | boolean): boolean {
  return !Object.is(parseValue(setting, draft), setting.value);
}

export default function AdminDashboard() {
  const [settings, setSettings] = useState<EditableSetting[]>([]);
  const [overview, setOverview] = useState<AdminOverview | null>(null);
  const [modelConfiguration, setModelConfiguration] = useState<Pick<SettingsResponse, "provider" | "models"> | null>(null);
  const [secrets, setSecrets] = useState<Record<string, boolean>>({});
  const [{ drafts, pendingResets }, setDraftState] = useState<TokenDraftState>({ drafts: {}, pendingResets: {} });
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const [settingsResult, overviewResult] = await Promise.all([
      getAdminSettings(), getAdminOverview(),
    ]);
    const tokenSettings = ADMIN_TOKEN_SETTING_KEYS.flatMap((key) =>
      settingsResult.settings.filter((item) => item.key === key),
    );
    setSettings(tokenSettings);
    setOverview(overviewResult);
    setModelConfiguration({ provider: settingsResult.provider, models: settingsResult.models });
    setSecrets(settingsResult.secrets);
    setDraftState({
      drafts: Object.fromEntries(tokenSettings.map((item) => [item.key, draftValue(item, item.value)])),
      pendingResets: {},
    });
  }, []);

  useEffect(() => {
    load().catch((error: unknown) => setMessage(error instanceof Error ? error.message : "Không thể tải trang quản trị"));
  }, [load]);

  const dirtySettings = settings.filter(
    (setting) => pendingResets[setting.key] || isChanged(setting, drafts[setting.key]),
  );

  async function saveAll() {
    if (saving) return;
    const adjusted = adjustTokenDrafts({ drafts, pendingResets });
    const changes = settings.filter((setting) => adjusted.pendingResets[setting.key] || isChanged(setting, adjusted.drafts[setting.key]));
    setDraftState(adjusted);
    if (!changes.length) return;
    for (const setting of changes) {
      const value = Number(adjusted.drafts[setting.key]);
      if (!Number.isSafeInteger(value) || (setting.minimum !== null && value < setting.minimum)) {
        return setMessage(`${settingPresentation(setting.key).title} phải là số nguyên từ ${setting.minimum ?? 1} trở lên.`);
      }
    }
    if (reason.trim().length < 3) return setMessage("Hãy nhập lý do thay đổi (tối thiểu 3 ký tự).");
    if (!window.confirm(`Lưu ${changes.length} thay đổi cấu hình?`)) return;
    setSaving(true);
    try {
      await updateAdminSettings(
        changes.map((setting) => adjusted.pendingResets[setting.key]
          ? { key: setting.key, reset: true }
          : { key: setting.key, value: parseValue(setting, adjusted.drafts[setting.key]) }),
        reason.trim(),
      );
      const needsRestart = changes.some((setting) => setting.requires_restart);
      setReason("");
      setMessage(
        `Đã lưu ${changes.length} thay đổi.${needsRestart ? " Cần khởi động lại worker để áp dụng đầy đủ." : ""}`,
      );
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Không thể lưu cấu hình");
    } finally {
      setSaving(false);
    }
  }

  function changeDraft(setting: EditableSetting, value: string | boolean) {
    setDraftState((current) => ({
      drafts: { ...current.drafts, [setting.key]: value },
      pendingResets: { ...current.pendingResets, [setting.key]: false },
    }));
  }

  function toggleReset(setting: EditableSetting) {
    setDraftState((current) => {
      const isPending = Boolean(current.pendingResets[setting.key]);
      return adjustTokenDrafts({
        drafts: { ...current.drafts, [setting.key]: draftValue(setting, isPending ? setting.value : setting.default) },
        pendingResets: { ...current.pendingResets, [setting.key]: !isPending && setting.source === "override" },
      });
    });
  }

  const groups = settings.reduce<Record<string, EditableSetting[]>>((result, item) => {
    (result[item.group] ??= []).push(item);
    return result;
  }, {});
  return (
    <section className="admin-dashboard">
      <header><h1>Vận hành hệ thống</h1><p>Theo dõi tải và điều chỉnh 3 giới hạn token của chatbot.</p></header>
      <div className="overview-grid">
        <article><span>Job đang hoạt động</span><strong>{overview?.queue_depth ?? "N/A"}</strong></article>
        <article><span>Yêu cầu thất bại</span><strong>{overview?.generation_statuses.FAILED ?? 0}</strong></article>
        <article><span>Yêu cầu đang thử lại</span><strong>{overview?.generation_statuses.RETRYING ?? 0}</strong></article>
        <article><span>Lượt gọi AI trong 24 giờ</span><strong>{overview?.usage_24h.attempts ?? 0}</strong></article>
        <article><span>Token đầu vào trong 24 giờ</span><strong>{overview?.usage_24h.input_tokens ?? 0}</strong></article>
        <article><span>Token đầu ra trong 24 giờ</span><strong>{overview?.usage_24h.output_tokens ?? 0}</strong></article>
      </div>
      {modelConfiguration && (
        <p className="model-summary">
          Nguồn AI: <strong>{modelConfiguration.provider === "openai" ? "OpenAI" : "Gemini"}</strong> · {" "}
          Model mặc định: <strong>{modelConfiguration.models.default}</strong> · Tóm tắt: <strong>{modelConfiguration.models.summary}</strong> · Nâng cao: <strong>{modelConfiguration.models.advanced}</strong>
        </p>
      )}

      <div className="secret-status">
        {Object.entries(secrets).map(([key, configured]) => (
          <div className="secret-item" key={key}>
            <strong>{SECRET_TITLES[key] ?? key}</strong>
            <small><code>{key}</code> · {configured ? "đã cấu hình" : "chưa cấu hình"}</small>
          </div>
        ))}
      </div>

      <div className={`change-toolbar${dirtySettings.length ? " has-changes" : ""}`}>
        <label className="reason-field">
          Lý do thay đổi
          <input value={reason} onChange={(event) => setReason(event.currentTarget.value)} placeholder="Ví dụ: điều chỉnh giới hạn token cuộc hội thoại" />
        </label>
        <div className="save-actions">
          <span>{dirtySettings.length ? `${dirtySettings.length} mục chưa lưu` : "Chưa có thay đổi"}</span>
          <button type="button" disabled={!dirtySettings.length || saving} onClick={() => void saveAll()}>
            {saving ? "Đang lưu..." : `Lưu tất cả${dirtySettings.length ? ` (${dirtySettings.length})` : ""}`}
          </button>
        </div>
      </div>
      {message && <p className="admin-message" role="status">{message}</p>}

      {Object.entries(groups).map(([group, items]) => (
        <details className="settings-group" key={group} open>
          <summary><strong>{GROUP_TITLES[group] ?? group}</strong><span>{items.length} cấu hình</span></summary>
          {items.map((setting) => {
            const presentation = settingPresentation(setting.key);
            const inputId = `setting-${setting.key}`;
            const dirty = pendingResets[setting.key] || isChanged(setting, drafts[setting.key]);
            return (
              <div className={`setting-row${dirty ? " is-dirty" : ""}`} key={setting.key}>
                <div className="setting-copy">
                  <label htmlFor={inputId}>{presentation.title}</label>
                  <p>{presentation.description}</p>
                  <small>
                    <code>{setting.key}</code> · Nguồn: {setting.source === "env" ? "ENV" : "ghi đè từ quản trị"}
                    {" · "}Mặc định: {String(setting.default ?? "chưa đặt")}
                    {presentation.unit ? ` · Đơn vị: ${presentation.unit}` : ""}
                    {setting.requires_restart ? " · Cần khởi động lại worker" : ""}
                  </small>
                </div>
                {setting.value_type === "integer" || setting.value_type === "number" ? (
                  <input
                    id={inputId}
                    type="number"
                    min={setting.minimum ?? undefined}
                    max={setting.key === "CHAT_CONTEXT_WINDOW_TOKENS" ? Number(drafts.MAX_CONVERSATION_TOKENS) || undefined : setting.maximum ?? undefined}
                    step={setting.value_type === "integer" ? 1 : "any"}
                    value={String(drafts[setting.key] ?? "")}
                    onBlur={() => setDraftState(adjustTokenDrafts)}
                    onChange={(event) => {
                      // Đọc giá trị ngay khi sự kiện còn hiệu lực, không giữ event trong state updater.
                      const value = event.currentTarget.value;
                      changeDraft(setting, value);
                    }}
                  />
                ) : (
                  <select
                    id={inputId}
                    value={String(drafts[setting.key] ?? "")}
                    onChange={(event) => {
                      const value = event.currentTarget.value;
                      changeDraft(setting, setting.value_type === "boolean" ? value === "true" : value);
                    }}
                  >
                    {setting.choices?.map(([value, label]) => (
                      <option key={String(value)} value={String(value)}>{label}</option>
                    ))}
                  </select>
                )}
                <button type="button" className="secondary" onClick={() => toggleReset(setting)}>
                  {pendingResets[setting.key] ? "Hủy dùng ENV" : "Dùng ENV"}
                </button>
              </div>
            );
          })}
        </details>
      ))}
    </section>
  );
}
