"use client";

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
import ConversationSidebar from "./chat/ConversationSidebar";

export default function AppShell({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const [user, setUser] = useState<User | null>(null);
  const [checking, setChecking] = useState(true);
  const [authRevision, setAuthRevision] = useState(0);
  const isAuthPage = pathname === "/login" || pathname === "/register";

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
        if (isAuthPage) router.replace("/");
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
  }, [authRevision, isAuthPage, router]);

  if (isAuthPage) {
    return <main className="auth-main">{checking ? <p>Đang kiểm tra...</p> : children}</main>;
  }
  if (checking || !user) return <main className="auth-main"><p>Đang kiểm tra phiên đăng nhập...</p></main>;

  return (
    <div className="app-shell">
      <ConversationSidebar user={user} />
      <main>{children}</main>
    </div>
  );
}
