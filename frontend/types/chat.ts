export type MessageRole = "user" | "assistant" | "error";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
}

export interface ChatResponse {
  answer: string;
}
