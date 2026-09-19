"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { FormEvent } from "react";

import { login } from "../../services/authApi";
import { saveAuthSession } from "../../stores/authStore";
import { useChatbotName } from "../branding/BrandProvider";

export default function LoginForm() {
  const chatbotName = useChatbotName();
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    setIsLoading(true);
    setError("");
    try {
      const result = await login({
        email: String(form.get("email")),
        password: String(form.get("password")),
      });
      saveAuthSession(result.access_token, result.user);
      router.replace(result.user.role === "admin" ? "/admin" : "/chat");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Không thể đăng nhập");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <form className="auth-card" onSubmit={handleSubmit}>
      <div>
        <h1>Đăng nhập</h1>
        <p>Tiếp tục các cuộc trò chuyện với Chatbot {chatbotName}.</p>
      </div>
      <label>
        Email
        <input name="email" type="email" autoComplete="email" required />
      </label>
      <label>
        Mật khẩu
        <input name="password" type="password" autoComplete="current-password" minLength={8} required />
      </label>
      {error && <p className="auth-error">{error}</p>}
      <button type="submit" disabled={isLoading}>
        {isLoading ? "Đang đăng nhập..." : "Đăng nhập"}
      </button>
      <p className="auth-switch">Chưa có tài khoản? <Link href="/register">Đăng ký</Link></p>
    </form>
  );
}
