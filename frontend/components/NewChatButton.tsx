"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { createConversation } from "../services/conversationApi";

export default function NewChatButton() {
  const router = useRouter();
  const [isCreating, setIsCreating] = useState(false);
  const [error, setError] = useState("");

  async function handleClick() {
    setIsCreating(true);
    setError("");
    try {
      const conversation = await createConversation();
      window.dispatchEvent(new Event("conversations-changed"));
      router.push(`/chat/${conversation.id}`);
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : "Không thể tạo hội thoại");
    } finally {
      setIsCreating(false);
    }
  }

  return <>
    <button className="new-chat-button" onClick={handleClick} disabled={isCreating}>
      {isCreating ? "Đang tạo..." : "+ Cuộc trò chuyện mới"}
    </button>
    {error && <p className="sidebar-error">{error}</p>}
  </>;
}
