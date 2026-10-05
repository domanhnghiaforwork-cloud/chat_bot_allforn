"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useCallback, useEffect, useState } from "react";

import { listConversations, deleteConversation } from "../../services/conversationApi";
import { clearAuthSession } from "../../stores/authStore";
import type { User } from "../../types/auth";
import type { Conversation } from "../../types/conversation";
import { useChatbotName } from "../branding/BrandProvider";
import NewChatButton from "./NewChatButton";

function TrashIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <polyline points="3 6 5 6 21 6" />
      <path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
    </svg>
  );
}

function ChatBubbleIcon() {
  return (
    <svg
      width="14"
      height="14"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <path d="M21 15a2 2 0 0 1-2 2H7l-4 4V5a2 2 0 0 1 2-2h14a2 2 0 0 1 2 2z" />
    </svg>
  );
}

export default function ConversationSidebar({ user }: { user: User }) {
  const chatbotName = useChatbotName();
  const pathname = usePathname();
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [deletingId, setDeletingId] = useState<string | null>(null);
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

  async function handleDelete(e: React.MouseEvent, id: string, title: string) {
    e.preventDefault();
    e.stopPropagation();

    const confirmed = window.confirm(`Bạn có chắc chắn muốn xóa đoạn chat "${title}" không?`);
    if (!confirmed) return;

    setDeletingId(id);
    try {
      await deleteConversation(id);
      setConversations((current) => current.filter((c) => c.id !== id));
      window.dispatchEvent(new Event("conversations-changed"));
      if (pathname.endsWith(id)) {
        router.replace("/chat");
      }
    } catch (caught) {
      alert(caught instanceof Error ? caught.message : "Không thể xóa đoạn chat");
    } finally {
      setDeletingId(null);
    }
  }

  return (
    <aside className="conversation-sidebar">
      <div className="sidebar-top">
        <Link className="sidebar-brand" href="/chat" aria-label={`Mở Chatbot ${chatbotName}`}>
          <span className="sidebar-brand-mark" aria-hidden="true" title={chatbotName}>
            {chatbotName}
          </span>
          <span>
            <strong>Chatbot {chatbotName}</strong>
            <small>Trợ lý AI</small>
          </span>
        </Link>
        <NewChatButton />
        {user.role === "admin" && <Link className="admin-link" href="/admin">Quản trị hệ thống</Link>}
      </div>

      <div className="sidebar-history-container">
        <div className="sidebar-history-title">
          <span>Lịch sử đoạn chat</span>
          <span className="sidebar-history-count">{conversations.length}</span>
        </div>
        <nav className="sidebar-history-nav" aria-label="Lịch sử hội thoại">
          {conversations.length === 0 ? (
            <div className="sidebar-empty">Chưa có đoạn chat nào</div>
          ) : (
            conversations.map((conversation) => {
              const isActive = pathname.endsWith(conversation.id);
              const isDeleting = deletingId === conversation.id;
              return (
                <div
                  key={conversation.id}
                  className={`conversation-item ${isActive ? "active" : ""}`}
                >
                  <Link
                    href={`/chat/${conversation.id}`}
                    className="conversation-item-link"
                    title={conversation.title}
                  >
                    <ChatBubbleIcon />
                    <span className="conversation-item-title">{conversation.title}</span>
                  </Link>
                  <button
                    type="button"
                    className="conversation-item-delete"
                    title="Xóa đoạn chat"
                    aria-label={`Xóa đoạn chat ${conversation.title}`}
                    disabled={isDeleting}
                    onClick={(e) => handleDelete(e, conversation.id, conversation.title)}
                  >
                    <TrashIcon />
                  </button>
                </div>
              );
            })
          )}
        </nav>
      </div>

      {error && <p className="sidebar-error">{error}</p>}

      <div className="sidebar-footer">
        <div className="sidebar-user" title={user.email}>
          <div className="sidebar-user-avatar">
            {user.email.slice(0, 1).toUpperCase()}
          </div>
          <span className="sidebar-user-email">{user.email}</span>
        </div>
        <button type="button" className="sidebar-logout-btn" onClick={logout} title="Đăng xuất">
          Đăng xuất
        </button>
      </div>
    </aside>
  );
}

