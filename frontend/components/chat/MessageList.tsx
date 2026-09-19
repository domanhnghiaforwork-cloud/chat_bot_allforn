import { useEffect, useRef } from "react";

import { useChatbotName } from "../branding/BrandProvider";
import type { Message } from "../../types/chat";
import MarkdownMessage from "./MarkdownMessage";

interface MessageListProps {
  messages: Message[];
  isLoading: boolean;
  partial?: string;
}

export default function MessageList({ messages, isLoading, partial = "" }: MessageListProps) {
  const endRef = useRef<HTMLDivElement>(null);
  const chatbotName = useChatbotName();

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: partial ? "auto" : "smooth" });
  }, [messages, isLoading, partial]);

  return (
    <section className="message-list" aria-live="polite" aria-label="Nội dung trò chuyện">
      {messages.length === 0 && (
        <article className="message message-assistant">
          <span className="message-author">{chatbotName}</span>
          <div>Xin chào! Tôi là {chatbotName}. Tôi có thể giúp gì cho bạn?</div>
        </article>
      )}
      {messages.map((message) => (
        <article key={message.id} className={`message message-${message.role}`}>
          {message.role === "assistant" ? (
            <>
              <span className="message-author">{chatbotName}</span>
              <MarkdownMessage content={message.content} />
            </>
          ) : (
            <div className="plain-message">{message.content}</div>
          )}
        </article>
      ))}
      {partial ? (
        <article className="message message-assistant">
          <span className="message-author">{chatbotName}</span>
          <MarkdownMessage content={partial} />
        </article>
      ) : null}
      {isLoading && !partial ? (
        <div className="message message-assistant typing" aria-label={`${chatbotName} đang trả lời`}>
          <span /><span /><span />
        </div>
      ) : null}
      <div ref={endRef} aria-hidden="true" />
    </section>
  );
}
