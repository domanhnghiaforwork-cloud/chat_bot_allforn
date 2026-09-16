export type MessageRole = "user" | "assistant" | "error";

export interface Message {
  id: string;
  role: MessageRole;
  content: string;
  created_at?: string;
}

export interface ChatResponse {
  conversation_id: string;
  answer: string;
  user_message: Message;
  assistant_message: Message;
}
