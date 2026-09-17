"use client";

import { useCallback, useEffect, useState } from "react";

import { useChatJob } from "../../hooks/useChatJob";
import { sendMessage } from "../../services/chatApi";
import { getConversation } from "../../services/conversationApi";
import type { Message } from "../../types/chat";
import GenerationStatus from "../status/GenerationStatus";
import MessageInput from "./MessageInput";
import MessageList from "./MessageList";

const ASYNC_ENABLED = process.env.NEXT_PUBLIC_ASYNC_CHAT_ENABLED === "true";

export default function ChatBox({ conversationId }: { conversationId: string }) {
  const [title, setTitle] = useState("Đang tải...");
  const [messages, setMessages] = useState<Message[]>([]);
  const [isSending, setIsSending] = useState(false);
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

  async function handleSend(content: string) {
    const temporaryId = crypto.randomUUID();
    const wasEmpty = messages.length === 0;
    setMessages((current) => [...current, { id: temporaryId, role: "user", content }]);
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
        },
      ]);
    } finally {
      setIsSending(false);
    }
  }

  const jobActive = ASYNC_ENABLED && ["PENDING", "QUEUED", "GENERATING", "RETRYING"].includes(job.status ?? "");
  return (
    <section className="chat-box">
      <header className="chat-header">
        <div className="chat-avatar" aria-hidden="true">AI</div>
        <div>
          <h1>{title}</h1>
          <p>V4.2 · {ASYNC_ENABLED ? "Hàng đợi an toàn" : "Luồng đồng bộ tương thích"}</p>
        </div>
      </header>
      {loadError ? (
        <p className="load-error">{loadError}</p>
      ) : (
        <MessageList messages={messages} isLoading={isSending || jobActive} partial={job.partial} />
      )}
      <div>
        <GenerationStatus
          status={job.status}
          queuePosition={job.queuePosition}
          error={job.error}
          onCancel={() => void job.cancel()}
        />
        <MessageInput
          disabled={!isReady || isSending || jobActive || Boolean(loadError)}
          onSend={handleSend}
        />
      </div>
    </section>
  );
}
