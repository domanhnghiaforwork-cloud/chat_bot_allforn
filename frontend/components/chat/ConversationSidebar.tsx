"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { listConversations } from "../../services/conversationApi";
import { clearAuthSession } from "../../stores/authStore";
import type { User } from "../../types/auth";
import type { Conversation } from "../../types/conversation";
import NewChatButton from "./NewChatButton";

export default function ConversationSidebar({ user }: { user: User }) {
  const pathname = usePathname();
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [error, setError] = useState("");

  const loadConversations = useCallback(async () => {
    try {
      setConversations(await listConversations());
      setError("");
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Không thể tải hội thoại");
    }
  }, []);

  useEffect(() => {
    void loadConversations();
    window.addEventListener("conversations-changed", loadConversations);
    return () => window.removeEventListener("conversations-changed", loadConversations);
  }, [pathname, loadConversations]);

  function logout() {
    clearAuthSession();
    router.replace("/login");
  }

  return (
    <aside className="conversation-sidebar">
      <div className="sidebar-user">
        <span title={user.email}>{user.email}</span>
        <button type="button" onClick={logout}>Đăng xuất</button>
      </div>
      <NewChatButton />
      {user.role === "admin" && <Link className="admin-link" href="/admin">Quản trị hệ thống</Link>}
      <nav aria-label="Lịch sử hội thoại">
        {conversations.map((conversation) => (
          <Link
            key={conversation.id}
            href={`/chat/${conversation.id}`}
            className={pathname.endsWith(conversation.id) ? "active" : ""}
          >
            {conversation.title}
          </Link>
        ))}
      </nav>
      {error && <p className="sidebar-error">{error}</p>}
    </aside>
  );
}
