"use client";

import { useState } from "react";

import { sendMessage } from "../services/chatApi";
import type { Message } from "../types/chat";
import MessageInput from "./MessageInput";
import MessageList from "./MessageList";

const initialMessage: Message = {
  id: "welcome",
  role: "assistant",
  content: "Xin chào! Tôi có thể giúp gì cho bạn?",
};

export default function ChatBox() {
  const [messages, setMessages] = useState<Message[]>([initialMessage]);
  const [isLoading, setIsLoading] = useState(false);

  async function handleSend(content: string) {
    setMessages((current) => [
      ...current,
      { id: crypto.randomUUID(), role: "user", content },
    ]);
    setIsLoading(true);

    try {
      const answer = await sendMessage(content);
      setMessages((current) => [
        ...current,
        { id: crypto.randomUUID(), role: "assistant", content: answer },
      ]);
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
          <h1>Chatbot Gemini</h1>
          <p>V1 · Mỗi câu hỏi là một lượt độc lập</p>
        </div>
      </header>
      <MessageList messages={messages} isLoading={isLoading} />
      <MessageInput disabled={isLoading} onSend={handleSend} />
    </section>
  );
}
