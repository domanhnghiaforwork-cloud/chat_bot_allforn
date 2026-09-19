"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import type { ReactNode } from "react";

import { getCurrentUser } from "../services/authApi";
import {
  AUTH_CHANGED_EVENT,
  clearAuthSession,
  getAuthSession,
} from "../stores/authStore";
import type { User } from "../types/auth";
import { useChatbotName } from "./branding/BrandProvider";
import ConversationSidebar from "./chat/ConversationSidebar";

export default function AppShell({ children }: { children: ReactNode }) {
  const chatbotName = useChatbotName();
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [authRevision, setAuthRevision] = useState(0);
  const isAuthPage = pathname === "/login" || pathname === "/register";
  const isAdminPage = pathname.startsWith("/admin");

  useEffect(() => {
    const refresh = () => setAuthRevision((value) => value + 1);
    window.addEventListener(AUTH_CHANGED_EVENT, refresh);
    return () => window.removeEventListener(AUTH_CHANGED_EVENT, refresh);
  }, []);

  useEffect(() => {
    let active = true;
    const session = getAuthSession();
    if (!session) {
      setUser(null);
      setChecking(false);
      if (!isAuthPage) router.replace("/login");
      return;
    }

    setChecking(true);
    getCurrentUser()
      .then((currentUser) => {
        if (!active) return;
        setUser(currentUser);
        setChecking(false);
        if (isAuthPage) router.replace(currentUser.role === "admin" ? "/admin" : "/chat");
        else if (isAdminPage && currentUser.role !== "admin") router.replace("/chat");
        else if (pathname === "/") router.replace(currentUser.role === "admin" ? "/admin" : "/chat");
      })
      .catch(() => {
        if (!active) return;
        clearAuthSession();
        setUser(null);
        setChecking(false);
        router.replace("/login");
      });
    return () => {
      active = false;
    };
  }, [authRevision, isAuthPage, pathname, router]);

  if (isAuthPage) {
    return <main className="auth-main">{checking ? <p>Đang kiểm tra...</p> : children}</main>;
  }
  if (checking || !user) return <main className="auth-main"><p>Đang kiểm tra phiên đăng nhập...</p></main>;
  if (isAdminPage) {
    if (user.role !== "admin") return <main className="auth-main"><p>Đang chuyển hướng...</p></main>;
    return (
      <div className="admin-shell">
        <header className="admin-nav">
          <strong>Quản trị Chatbot {chatbotName}</strong>
          <nav><Link href="/chat">Chat</Link><span>{user.email}</span></nav>
        </header>
        <main className="admin-main">{children}</main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <ConversationSidebar user={user} />
      <main>{children}</main>
    </div>
  );
}
