export type GenerationStatus =
  | "PENDING"
  | "QUEUED"
  | "GENERATING"
  | "RETRYING"
  | "DONE"
  | "FAILED"
  | "CANCELLED";

export interface Generation {
  request_id: string;
  conversation_id: string;
  status: GenerationStatus;
  queue_position?: number | null;
  requested_model?: string | null;
  actual_model?: string | null;
  attempt_count: number;
  error_code?: string | null;
  error_message?: string | null;
  user_message_id?: string | null;
  assistant_message_id?: string | null;
}

export interface ChatJobAccepted {
  request_id: string;
  status: GenerationStatus;
  queue_position: number | null;
}

export interface GenerationEvent {
  id: string;
  event: "queued" | "generating" | "delta" | "retrying" | "completed" | "failed";
  data: Record<string, unknown>;
}
