"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import type { FormEvent } from "react";

import { register } from "../../services/authApi";
import { saveAuthSession } from "../../stores/authStore";
import { useChatbotName } from "../branding/BrandProvider";

export default function RegisterForm() {
  const chatbotName = useChatbotName();
  const router = useRouter();
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const credentials = {
      email: String(form.get("email")),
      password: String(form.get("password")),
    };
    setIsLoading(true);
    setError("");
    try {
      const result = await register(credentials);
      saveAuthSession(result.access_token, result.user);
      router.replace("/chat");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Không thể đăng ký");
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <form className="auth-card" onSubmit={handleSubmit}>
      <div>
        <h1>Tạo tài khoản</h1>
        <p>Tạo tài khoản để trò chuyện với Chatbot {chatbotName}.</p>
      </div>
      <label>
        Email
        <input name="email" type="email" autoComplete="email" required />
      </label>
      <label>
        Mật khẩu
        <input name="password" type="password" autoComplete="new-password" minLength={8} maxLength={128} required />
      </label>
      {error && <p className="auth-error">{error}</p>}
      <button type="submit" disabled={isLoading}>
        {isLoading ? "Đang tạo tài khoản..." : "Đăng ký"}
      </button>
      <p className="auth-switch">Đã có tài khoản? <Link href="/login">Đăng nhập</Link></p>
    </form>
  );
}
