import type { ChatResponse } from "../types/chat";
import { request } from "./apiClient";

export async function sendMessage(
  conversationId: string,
  message: string,
): Promise<ChatResponse> {
  return request("/api/chat", {
    method: "POST",
    body: JSON.stringify({ conversation_id: conversationId, message }),
  });
}
