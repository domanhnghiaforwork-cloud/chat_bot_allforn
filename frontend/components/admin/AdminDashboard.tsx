"use client";

import { useCallback, useEffect, useState } from "react";

import {
  GROUP_TITLES,
  SECRET_TITLES,
  settingPresentation,
} from "../../config/adminSettings";
import {
  getAdminOverview,
  getAdminSettings,
  getAuditLogs,
  updateAdminSettings,
} from "../../services/adminApi";
import type { AdminOverview, AuditLog, EditableSetting } from "../../types/admin";

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
  const [logs, setLogs] = useState<AuditLog[]>([]);
  const [secrets, setSecrets] = useState<Record<string, boolean>>({});
  const [drafts, setDrafts] = useState<Record<string, string | boolean>>({});
  const [pendingResets, setPendingResets] = useState<Record<string, boolean>>({});
  const [reason, setReason] = useState("");
  const [message, setMessage] = useState("");
  const [saving, setSaving] = useState(false);

  const load = useCallback(async () => {
    const [settingsResult, overviewResult, logResult] = await Promise.all([
      getAdminSettings(), getAdminOverview(), getAuditLogs(),
    ]);
    setSettings(settingsResult.settings);
    setOverview(overviewResult);
    setLogs(logResult);
    setSecrets(settingsResult.secrets);
    setDrafts(Object.fromEntries(settingsResult.settings.map((item) => [item.key, draftValue(item, item.value)])));
    setPendingResets({});
  }, []);

  useEffect(() => {
    load().catch((error: unknown) => setMessage(error instanceof Error ? error.message : "Không thể tải trang quản trị"));
  }, [load]);

  const dirtySettings = settings.filter(
    (setting) => pendingResets[setting.key] || isChanged(setting, drafts[setting.key]),
  );

  async function saveAll() {
    if (!dirtySettings.length || saving) return;
    if (reason.trim().length < 3) return setMessage("Hãy nhập lý do thay đổi (tối thiểu 3 ký tự).");
    if (!window.confirm(`Lưu ${dirtySettings.length} thay đổi cấu hình?`)) return;
    setSaving(true);
    try {
      await updateAdminSettings(
        dirtySettings.map((setting) => pendingResets[setting.key]
          ? { key: setting.key, reset: true }
          : { key: setting.key, value: parseValue(setting, drafts[setting.key]) }),
        reason.trim(),
      );
      const needsRestart = dirtySettings.some((setting) => setting.requires_restart);
      setReason("");
      setMessage(
        `Đã lưu ${dirtySettings.length} thay đổi.${needsRestart ? " Cần khởi động lại worker để áp dụng đầy đủ." : ""}`,
      );
      await load();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Không thể lưu cấu hình");
    } finally {
      setSaving(false);
    }
  }

  function changeDraft(setting: EditableSetting, value: string | boolean) {
    setDrafts((current) => ({ ...current, [setting.key]: value }));
    setPendingResets((current) => ({ ...current, [setting.key]: false }));
  }

  function toggleReset(setting: EditableSetting) {
    const isPending = Boolean(pendingResets[setting.key]);
    setDrafts((current) => ({
      ...current,
      [setting.key]: draftValue(setting, isPending ? setting.value : setting.default),
    }));
    setPendingResets((current) => ({
      ...current,
      [setting.key]: !isPending && setting.source === "override",
    }));
  }

  const groups = settings.reduce<Record<string, EditableSetting[]>>((result, item) => {
    (result[item.group] ??= []).push(item);
    return result;
  }, {});
  return (
    <section className="admin-dashboard">
      <header><h1>Vận hành hệ thống</h1><p>Theo dõi tải và điều chỉnh cấu hình chatbot.</p></header>
      <div className="overview-grid">
        <article><span>Job đang hoạt động</span><strong>{overview?.queue_depth ?? "N/A"}</strong></article>
        <article><span>Yêu cầu thất bại</span><strong>{overview?.generation_statuses.FAILED ?? 0}</strong></article>
        <article><span>Yêu cầu đang thử lại</span><strong>{overview?.generation_statuses.RETRYING ?? 0}</strong></article>
        <article><span>Lượt gọi AI trong 24 giờ</span><strong>{overview?.usage_24h.attempts ?? 0}</strong></article>
        <article><span>Token đầu vào trong 24 giờ</span><strong>{overview?.usage_24h.input_tokens ?? 0}</strong></article>
        <article><span>Token đầu ra trong 24 giờ</span><strong>{overview?.usage_24h.output_tokens ?? 0}</strong></article>
      </div>
      {overview && (
        <p className="model-summary">
          Model mặc định: <strong>{overview.models.default}</strong> · Tóm tắt: <strong>{overview.models.summary}</strong> · Nâng cao: <strong>{overview.models.advanced}</strong>
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
          <input value={reason} onChange={(event) => setReason(event.currentTarget.value)} placeholder="Ví dụ: điều chỉnh theo quota AI Studio" />
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
                    max={setting.maximum ?? undefined}
                    step={setting.value_type === "integer" ? 1 : "any"}
                    value={String(drafts[setting.key] ?? "")}
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

      <section className="settings-group">
        <h2>Lịch sử thay đổi gần nhất</h2>
        <div className="audit-list">
          {logs.map((log) => (
            <div key={log.id}>
              <strong>{settingPresentation(log.target).title}</strong>
              <span><code>{log.target}</code> · {log.action} · {log.reason}</span>
            </div>
          ))}
        </div>
      </section>
    </section>
  );
}
