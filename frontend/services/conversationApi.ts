import type { Conversation, ConversationDetail } from "../types/conversation";

async function request<T>(url: string, options?: RequestInit): Promise<T> {
  const response = await fetch(url, options);
  if (!response.ok) {
    const error = (await response.json().catch(() => null)) as { detail?: string } | null;
    throw new Error(error?.detail ?? "Không thể tải hội thoại");
  }
  return response.json() as Promise<T>;
}

export function listConversations(): Promise<Conversation[]> {
  return request("/api/conversations");
}

export function getConversation(id: string): Promise<ConversationDetail> {
  return request(`/api/conversations/${id}`);
}

export function createConversation(): Promise<Conversation> {
  return request("/api/conversations", { method: "POST" });
}
