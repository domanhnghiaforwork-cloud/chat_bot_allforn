"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

import { isChatCommandName } from "../../config/chatCommands";
import { useChatJob } from "../../hooks/useChatJob";
import { sendMessage } from "../../services/chatApi";
import {
  deleteConversation,
  getConversation,
  getConversationTokenUsage,
} from "../../services/conversationApi";
import type { ConversationTokenUsage } from "../../types/conversation";
import type { Message } from "../../types/chat";
import { useChatbotName } from "../branding/BrandProvider";
import GenerationStatus from "../status/GenerationStatus";
import MessageInput from "./MessageInput";
import MessageList from "./MessageList";

const ASYNC_ENABLED = process.env.NEXT_PUBLIC_ASYNC_CHAT_ENABLED === "true";
const TOKEN_FORMATTER = new Intl.NumberFormat("vi-VN");

function commandResponse(
  command: "/token" | "/context",
  usage: ConversationTokenUsage,
): string {
  if (command === "/token") {
    return [
      `Token hội thoại hiện tại: ${TOKEN_FORMATTER.format(usage.current_tokens)} / ${TOKEN_FORMATTER.format(usage.max_conversation_tokens)}`,
      `Còn lại: ${TOKEN_FORMATTER.format(usage.remaining_tokens)} token`,
      `Đã sử dụng: ${usage.utilization_percent}%`,
      "Số token được ước lượng từ nội dung user và assistant đã lưu.",
    ].join("\n");
  }
  return [
    `Context window của chat: ${TOKEN_FORMATTER.format(usage.chat_context_window_tokens)} token`,
    `Input tối đa mỗi lượt (User Input): ${TOKEN_FORMATTER.format(usage.max_user_input_tokens ?? usage.max_chat_input_tokens)} token`,
    `Output tối đa mỗi lượt: ${TOKEN_FORMATTER.format(usage.max_chat_output_tokens)} token`,
  ].join("\n");
}

export default function ChatBox({ conversationId }: { conversationId: string }) {
  const router = useRouter();
  const chatbotName = useChatbotName();
  const [title, setTitle] = useState("Đang tải...");
  const [messages, setMessages] = useState<Message[]>([]);
  const [commandMessages, setCommandMessages] = useState<Message[]>([]);
  const [isSending, setIsSending] = useState(false);
  const [isDeleting, setIsDeleting] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [loadError, setLoadError] = useState("");
  const job = useChatJob(conversationId, ASYNC_ENABLED);

  const loadConversation = useCallback(async () => {
    setLoadError("");
    const conversation = await getConversation(conversationId);
    setTitle(conversation.title);
    setMessages(conversation.messages);
    setIsReady(true);
  }, [conversationId]);

  useEffect(() => {
    let active = true;
    setTitle("Đang tải...");
    setMessages([]);
    setCommandMessages([]);
    setIsReady(false);
    loadConversation().catch((error: unknown) => {
      if (active) setLoadError(error instanceof Error ? error.message : "Không thể tải hội thoại");
    });
    return () => { active = false; };
  }, [loadConversation]);

  useEffect(() => {
    if (job.status !== "DONE") return;
    loadConversation().then(() => {
      job.reset();
      window.dispatchEvent(new Event("conversations-changed"));
    }).catch((error: unknown) => {
      setLoadError(error instanceof Error ? error.message : "Không thể đồng bộ hội thoại");
    });
  }, [job.status, job.reset, loadConversation]);

  const displayedMessages = useMemo(
    () => [...messages, ...commandMessages].sort((first, second) => (
      new Date(first.created_at ?? 0).getTime()
      - new Date(second.created_at ?? 0).getTime()
    )),
    [commandMessages, messages],
  );

  async function handleCommand(content: string) {
    const command = content.trim().toLowerCase();
    const createdAt = Date.now();
    setCommandMessages((current) => [
      ...current,
      {
        id: crypto.randomUUID(),
        role: "user",
        content,
        created_at: new Date(createdAt).toISOString(),
      },
    ]);

    if (!isChatCommandName(command)) {
      setCommandMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "error",
          content: "Lệnh không được hỗ trợ. Gõ / để xem danh sách lệnh.",
          created_at: new Date(createdAt + 1).toISOString(),
        },
      ]);
      return;
    }

    setIsSending(true);
    try {
      const usage = await getConversationTokenUsage(conversationId);
      setCommandMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "assistant",
          content: commandResponse(command, usage),
          created_at: new Date(createdAt + 1).toISOString(),
        },
      ]);
    } catch (error) {
      setCommandMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "error",
          content: error instanceof Error ? error.message : "Không thể đọc thông tin token",
          created_at: new Date(createdAt + 1).toISOString(),
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  async function handleSend(content: string) {
    if (content.startsWith("/")) {
      await handleCommand(content);
      return;
    }
    const temporaryId = crypto.randomUUID();
    const temporaryCreatedAt = new Date().toISOString();
    const wasEmpty = messages.length === 0;
    setMessages((current) => [
      ...current,
      {
        id: temporaryId,
        role: "user",
        content,
        created_at: temporaryCreatedAt,
      },
    ]);
    setIsSending(true);
    try {
      if (ASYNC_ENABLED) {
        await job.send(content);
      } else {
        const response = await sendMessage(conversationId, content);
        setMessages((current) => [
          ...current.filter((message) => message.id !== temporaryId),
          response.user_message,
          response.assistant_message,
        ]);
        window.dispatchEvent(new Event("conversations-changed"));
      }
      if (wasEmpty) setTitle(content.slice(0, 120));
    } catch (error) {
      setMessages((current) => [
        ...current.filter((message) => message.id !== temporaryId),
        {
          id: crypto.randomUUID(),
          role: "error",
          content: error instanceof Error ? error.message : "Đã có lỗi xảy ra",
          created_at: new Date().toISOString(),
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  async function handleDelete() {
    const confirmed = window.confirm(
      "Bạn có chắc chắn muốn xóa đoạn chat này không? Tất cả tin nhắn trong đoạn chat sẽ bị xóa vĩnh viễn.",
    );
    if (!confirmed) return;

    setIsDeleting(true);
    try {
      await deleteConversation(conversationId);
      window.dispatchEvent(new Event("conversations-changed"));
      router.replace("/chat");
    } catch (caught) {
      alert(caught instanceof Error ? caught.message : "Không thể xóa đoạn chat");
      setIsDeleting(false);
    }
  }

  const jobActive = ASYNC_ENABLED && ["PENDING", "QUEUED", "GENERATING", "RETRYING"].includes(job.status ?? "");
  return (
    <section className="chat-box">
      <header className="chat-header">
        <div className="chat-header-main">
          <div className="chat-avatar" aria-hidden="true">AI</div>
          <div className="chat-header-info">
            <h1 title={title}>{title}</h1>
            <p>Chatbot {chatbotName} · V4.2 · {ASYNC_ENABLED ? "Hàng đợi an toàn" : "Luồng đồng bộ tương thích"}</p>
          </div>
        </div>
        <div className="chat-header-actions">
          <button
            type="button"
            className="delete-chat-btn"
            title="Xóa đoạn chat này"
            aria-label="Xóa đoạn chat này"
            disabled={isDeleting || !isReady}
            onClick={handleDelete}
          >
            <svg
              width="15"
              height="15"
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
              <line x1="10" y1="11" x2="10" y2="17" />
              <line x1="14" y1="11" x2="14" y2="17" />
            </svg>
            <span>{isDeleting ? "Đang xóa..." : "Xóa đoạn chat"}</span>
          </button>
        </div>
      </header>

      {loadError ? (
        <div className="load-error-container">
          <p className="load-error">{loadError}</p>
        </div>
      ) : (
        <MessageList messages={displayedMessages} isLoading={isSending || jobActive} partial={job.partial} />
      )}

      <footer className="chat-footer">
        <div className="chat-footer-inner">
          <GenerationStatus
            status={job.status}
            queuePosition={job.queuePosition}
            error={job.error}
            onCancel={() => void job.cancel()}
          />
          <MessageInput
            disabled={!isReady || isSending || jobActive || Boolean(loadError) || isDeleting}
            onSend={handleSend}
          />
          <div className="chat-footer-hint">
            <span>Nhấn Enter để gửi, Shift + Enter để xuống dòng · Gõ / để xem lệnh trợ giúp</span>
          </div>
        </div>
      </footer>
    </section>
  );
}
