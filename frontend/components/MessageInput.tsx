import { useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";

interface MessageInputProps {
  disabled: boolean;
  onSend: (message: string) => Promise<void>;
}

export default function MessageInput({ disabled, onSend }: MessageInputProps) {
  const [message, setMessage] = useState("");

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = message.trim();
    if (!value || disabled) return;

    setMessage("");
    await onSend(value);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  return (
    <form className="message-form" onSubmit={handleSubmit}>
      <textarea
        aria-label="Tin nhắn"
        placeholder="Nhập câu hỏi..."
        rows={1}
        value={message}
        disabled={disabled}
        onChange={(event) => setMessage(event.currentTarget.value)}
        onKeyDown={handleKeyDown}
      />
      <button type="submit" disabled={disabled || !message.trim()}>
        Gửi
      </button>
    </form>
  );
}
