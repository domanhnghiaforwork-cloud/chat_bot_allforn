import { getAccessToken } from "../stores/authStore";
import type {
  ChatJobAccepted,
  Generation,
  GenerationEvent,
} from "../types/generation";
import { request } from "./apiClient";

export function createChatJob(
  conversationId: string,
  message: string,
  clientRequestId: string,
  model: "default" | "advanced" = "default",
  signal?: AbortSignal,
): Promise<ChatJobAccepted> {
  return request("/api/chat/jobs", {
    method: "POST",
    signal,
    body: JSON.stringify({
      conversation_id: conversationId,
      message,
      client_request_id: clientRequestId,
      model,
    }),
  });
}

export function getGeneration(requestId: string): Promise<Generation> {
  return request(`/api/generations/${requestId}`);
}

export function getActiveGeneration(conversationId: string): Promise<Generation | null> {
  return request(`/api/generations/active?conversation_id=${encodeURIComponent(conversationId)}`);
}

export function cancelGeneration(requestId: string): Promise<Generation> {
  return request(`/api/generations/${requestId}`, { method: "DELETE" });
}

function parseBlock(block: string): GenerationEvent | null {
  let id = "";
  let event = "";
  const data: string[] = [];
  for (const line of block.split("\n")) {
    if (line.startsWith("id:")) id = line.slice(3).trim();
    else if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data.push(line.slice(5).trim());
  }
  if (!event || !data.length) return null;
  return { id, event, data: JSON.parse(data.join("\n")) } as GenerationEvent;
}

export async function openGenerationEvents(
  requestId: string,
  lastEventId: string,
  signal: AbortSignal,
  onEvent: (event: GenerationEvent) => void,
): Promise<string> {
  const token = getAccessToken();
  const response = await fetch(`/api/generations/${requestId}/events`, {
    cache: "no-store",
    headers: {
      Accept: "text/event-stream",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(lastEventId ? { "Last-Event-ID": lastEventId } : {}),
    },
    signal,
  });
  if (!response.ok || !response.body) throw new Error("Không thể kết nối luồng trạng thái");

  const reader = response.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  let cursor = lastEventId;
  while (true) {
    const { done, value } = await reader.read();
    if (done) return cursor;
    buffer += decoder.decode(value, { stream: true }).replace(/\r\n/g, "\n");
    let boundary = buffer.indexOf("\n\n");
    while (boundary >= 0) {
      const parsed = parseBlock(buffer.slice(0, boundary));
      buffer = buffer.slice(boundary + 2);
      if (parsed) {
        cursor = parsed.id || cursor;
        onEvent(parsed);
        if (parsed.event === "completed" || parsed.event === "failed") {
          await reader.cancel();
          return cursor;
        }
      }
      boundary = buffer.indexOf("\n\n");
    }
  }
}
