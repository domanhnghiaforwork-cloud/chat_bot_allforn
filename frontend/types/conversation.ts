import type { Message } from "./chat";

export interface Conversation {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
}

export interface ConversationDetail extends Conversation {
  messages: Message[];
}

export interface ConversationTokenUsage {
  current_tokens: number;
  max_conversation_tokens: number;
  remaining_tokens: number;
  utilization_percent: number;
  chat_context_window_tokens: number;
  max_chat_input_tokens: number;
  max_chat_output_tokens: number;
  estimated: boolean;
}
