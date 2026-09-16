import type { ChatResponse } from "../types/chat";

export async function sendMessage(
  conversationId: string,
  message: string,
): Promise<ChatResponse> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ conversation_id: conversationId, message }),
  });

  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(error?.detail ?? "Không thể kết nối đến chatbot");
  }

  return response.json() as Promise<ChatResponse>;
}
