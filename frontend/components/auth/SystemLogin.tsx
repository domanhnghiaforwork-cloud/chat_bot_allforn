"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { getCurrentUser, loginFromSystem } from "../../services/authApi";
import { ApiError } from "../../services/apiClient";
import { clearAuthSession, getAuthRevision, getAuthSession, saveAuthSession } from "../../stores/authStore";
import type { AuthResponse } from "../../types/auth";

async function resolveSession(ticket: string | null): Promise<AuthResponse> {
  // A supplied ticket represents the current system account, even if chatbot
  // still has a valid session belonging to another account.
  if (ticket) return loginFromSystem(ticket);
  const existing = getAuthSession();
  if (existing) {
    try {
      const user = await getCurrentUser();
      return { access_token: existing.accessToken, token_type: "bearer", user };
    } catch (error) {
      // A network failure must not overwrite an existing session.
      if (!(error instanceof ApiError) || error.status !== 401) throw error;
    }
  }
  throw new Error("Không có vé đăng nhập. Hãy bấm Chatbot từ system hoặc đăng nhập trực tiếp.");
}

export default function SystemLogin() {
  const router = useRouter();
  const pending = useRef<{ exchange: Promise<AuthResponse>; revision: string | null } | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    let active = true;
    if (!pending.current) {
      const ticket = new URLSearchParams(window.location.hash.slice(1)).get("ticket");
      window.history.replaceState(null, "", window.location.pathname + window.location.search);
      // Reuse the same exchange when React checks effects twice in development.
      if (ticket) clearAuthSession();
      pending.current = { exchange: resolveSession(ticket), revision: getAuthRevision() };
    }
    const attempt = pending.current;
    attempt.exchange.then((session) => {
      if (!active) return;
      if (getAuthRevision() !== attempt.revision) {
        setError("Phiên đăng nhập đã thay đổi. Hãy mở lại Chatbot từ system.");
        return;
      }
      saveAuthSession(session.access_token, session.user);
      router.replace(session.user.role === "admin" ? "/admin" : "/chat");
    }).catch((reason: unknown) => {
      if (active) setError(reason instanceof Error ? reason.message : "Không thể đăng nhập Chatbot.");
    });
    return () => { active = false; };
  }, [router]);

  return (
    <section className="auth-card">
      <h1>Đăng nhập Chatbot</h1>
      {error ? <>
        <p role="alert">{error}</p>
        <Link href="/login">Đăng nhập bằng email và mật khẩu</Link>
      </> : <p role="status">Đang kiểm tra phiên đăng nhập và kết nối với system...</p>}
    </section>
  );
}
