"use client";

import { useEffect, useState } from "react";

import { sendMessage } from "../../services/chatApi";
import { getConversation } from "../../services/conversationApi";
import type { Message } from "../../types/chat";
import MessageInput from "./MessageInput";
import MessageList from "./MessageList";

interface ChatBoxProps {
  conversationId: string;
}

export default function ChatBox({ conversationId }: ChatBoxProps) {
  const [title, setTitle] = useState("Đang tải...");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isReady, setIsReady] = useState(false);
  const [loadError, setLoadError] = useState("");

  useEffect(() => {
    let active = true;
    setTitle("Đang tải...");
    setMessages([]);
    setLoadError("");
    setIsReady(false);
    getConversation(conversationId)
      .then((conversation) => {
        if (!active) return;
        setTitle(conversation.title);
        setMessages(conversation.messages);
        setIsReady(true);
      })
      .catch((error: unknown) => {
        if (active) setLoadError(error instanceof Error ? error.message : "Không thể tải hội thoại");
      });
    return () => {
      active = false;
    };
  }, [conversationId]);

  async function handleSend(content: string) {
    const temporaryId = crypto.randomUUID();
    setMessages((current) => [...current, { id: temporaryId, role: "user", content }]);
    setIsLoading(true);

    try {
      const response = await sendMessage(conversationId, content);
      // Thay message tạm bằng hai message đã được PostgreSQL cấp ID.
      setMessages((current) => [
        ...current.filter((message) => message.id !== temporaryId),
        response.user_message,
        response.assistant_message,
      ]);
      if (messages.length === 0) setTitle(content.slice(0, 120));
      window.dispatchEvent(new Event("conversations-changed"));
    } catch (error) {
      setMessages((current) => [
        ...current,
        {
          id: crypto.randomUUID(),
          role: "error",
          content: error instanceof Error ? error.message : "Đã có lỗi xảy ra",
        },
      ]);
    } finally {
      setIsLoading(false);
    }
  }

  return (
    <section className="chat-box">
      <header className="chat-header">
        <div className="chat-avatar" aria-hidden="true">AI</div>
        <div>
          <h1>{title}</h1>
          <p>V3 · Hội thoại thuộc tài khoản hiện tại</p>
        </div>
      </header>
      {loadError ? (
        <p className="load-error">{loadError}</p>
      ) : (
        <MessageList messages={messages} isLoading={isLoading} />
      )}
      <MessageInput disabled={!isReady || isLoading || Boolean(loadError)} onSend={handleSend} />
    </section>
  );
}
