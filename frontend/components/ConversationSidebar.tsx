"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { listConversations } from "../services/conversationApi";
import type { Conversation } from "../types/conversation";
import NewChatButton from "./NewChatButton";

export default function ConversationSidebar() {
  const pathname = usePathname();
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
    // ChatBox phát sự kiện này khi tiêu đề hoặc danh sách hội thoại thay đổi.
    window.addEventListener("conversations-changed", loadConversations);
    return () => window.removeEventListener("conversations-changed", loadConversations);
  }, [pathname, loadConversations]);

  return (
    <aside className="conversation-sidebar">
      <NewChatButton />
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
