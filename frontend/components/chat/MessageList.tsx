import { useEffect, useRef } from "react";

import type { Message } from "../../types/chat";

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  partial?: string;
}

export default function MessageList({ messages, isLoading, partial = "" }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isLoading]);

  return (
    <section className="message-list" aria-live="polite" aria-label="Nội dung trò chuyện">
      {messages.length === 0 && (
        <div className="message message-assistant">Xin chào! Tôi có thể giúp gì cho bạn?</div>
      )}
      {messages.map((message) => (
        <div key={message.id} className={`message message-${message.role}`}>
          {message.content}
        </div>
      ))}
      {partial && <div className="message message-assistant">{partial}</div>}
      {isLoading && (
        <div className="message message-assistant typing" aria-label="Chatbot đang trả lời">
          <span /><span /><span />
        </div>
      )}
      <div ref={endRef} />
    </section>
  );
}
