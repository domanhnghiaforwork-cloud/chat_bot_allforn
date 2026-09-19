import { useRef, useState } from "react";
import type { FormEvent, KeyboardEvent } from "react";

import { CHAT_COMMANDS } from "../../config/chatCommands";

interface MessageInputProps {
  disabled: boolean;
  onSend: (message: string) => Promise<void>;
}

export default function MessageInput({ disabled, onSend }: MessageInputProps) {
  const [message, setMessage] = useState("");
  const [activeCommandIndex, setActiveCommandIndex] = useState(0);
  const [commandMenuDismissed, setCommandMenuDismissed] = useState(false);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  const commandQuery = message.trim().toLowerCase();
  const matchingCommands = commandQuery.startsWith("/") && !commandQuery.includes(" ")
    ? CHAT_COMMANDS.filter((command) => command.name.startsWith(commandQuery))
    : [];
  const commandMenuOpen = (
    !disabled && !commandMenuDismissed && matchingCommands.length > 0
  );

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const value = message.trim();
    if (!value || disabled) return;

    setMessage("");
    setCommandMenuDismissed(false);
    await onSend(value);
  }

  function handleKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (commandMenuOpen && event.key === "ArrowDown") {
      event.preventDefault();
      setActiveCommandIndex((current) => (current + 1) % matchingCommands.length);
      return;
    }
    if (commandMenuOpen && event.key === "ArrowUp") {
      event.preventDefault();
      setActiveCommandIndex((current) => (
        current - 1 + matchingCommands.length
      ) % matchingCommands.length);
      return;
    }
    if (commandMenuOpen && event.key === "Escape") {
      event.preventDefault();
      setCommandMenuDismissed(true);
      return;
    }
    if (event.key === "Enter" && !event.shiftKey) {
      const exactCommand = matchingCommands.some(
        (command) => command.name === commandQuery,
      );
      if (commandMenuOpen && !exactCommand) {
        event.preventDefault();
        selectCommand(matchingCommands[activeCommandIndex]?.name ?? matchingCommands[0].name);
        return;
      }
      event.preventDefault();
      event.currentTarget.form?.requestSubmit();
    }
  }

  function selectCommand(command: string) {
    setMessage(command);
    setActiveCommandIndex(0);
    setCommandMenuDismissed(false);
    textareaRef.current?.focus();
  }

  return (
    <form className="message-form" onSubmit={handleSubmit}>
      {commandMenuOpen ? (
        <div className="slash-command-menu" role="listbox" aria-label="Lệnh chat">
          {matchingCommands.map((command, index) => (
            <button
              type="button"
              className={index === activeCommandIndex ? "active" : ""}
              role="option"
              aria-selected={index === activeCommandIndex}
              key={command.name}
              onMouseDown={(event) => event.preventDefault()}
              onClick={() => selectCommand(command.name)}
            >
              <code>{command.name}</code>
              <span>{command.description}</span>
            </button>
          ))}
        </div>
      ) : null}
      <textarea
        ref={textareaRef}
        aria-label="Tin nhắn"
        aria-expanded={commandMenuOpen}
        aria-haspopup="listbox"
        placeholder="Nhập câu hỏi hoặc / để xem lệnh..."
        rows={1}
        value={message}
        disabled={disabled}
        onChange={(event) => {
          setMessage(event.currentTarget.value);
          setActiveCommandIndex(0);
          setCommandMenuDismissed(false);
        }}
        onKeyDown={handleKeyDown}
      />
      <button type="submit" disabled={disabled || !message.trim()}>Gửi</button>
    </form>
  );
}
