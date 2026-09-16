import type { ChatResponse } from "../types/chat";

export async function sendMessage(message: string): Promise<string> {
  const response = await fetch("/api/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
  });

  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(error?.detail ?? "Không thể kết nối đến chatbot");
  }

  const data = (await response.json()) as ChatResponse;
  return data.answer;
}
