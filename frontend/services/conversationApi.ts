import type {
  Conversation,
  ConversationDetail,
  ConversationTokenUsage,
} from "../types/conversation";
import { request } from "./apiClient";

export function listConversations(): Promise<Conversation[]> {
  return request("/api/conversations");
}

export function getConversation(id: string): Promise<ConversationDetail> {
  return request(`/api/conversations/${id}`);
}

export function createConversation(): Promise<Conversation> {
  return request("/api/conversations", { method: "POST" });
}

export function getConversationTokenUsage(id: string): Promise<ConversationTokenUsage> {
  return request(`/api/conversations/${id}/token-usage`);
}
