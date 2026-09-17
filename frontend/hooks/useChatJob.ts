"use client";

import { useCallback, useEffect, useState } from "react";

import {
  cancelGeneration,
  createChatJob,
  getActiveGeneration,
} from "../services/generationApi";
import { ApiError } from "../services/apiClient";
import type {
  ChatJobAccepted,
  GenerationEvent,
  GenerationStatus,
} from "../types/generation";
import { useGenerationEvents } from "./useGenerationEvents";

export function useChatJob(conversationId: string, enabled: boolean) {
  const [requestId, setRequestId] = useState<string | null>(null);
  const [status, setStatus] = useState<GenerationStatus | null>(null);
  const [queuePosition, setQueuePosition] = useState<number | null>(null);
  const [partial, setPartial] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    if (!enabled) return;
    let active = true;
    getActiveGeneration(conversationId).then((generation) => {
      if (!active || !generation) return;
      setRequestId(generation.request_id);
      setStatus(generation.status);
      setError(generation.error_message ?? "");
    }).catch(() => undefined);
    return () => { active = false; };
  }, [conversationId, enabled]);

  const handleEvent = useCallback((event: GenerationEvent) => {
    const nextStatus = event.data.status;
    if (typeof nextStatus === "string") setStatus(nextStatus as GenerationStatus);
    if (event.event === "queued" && typeof event.data.queue_position === "number") {
      setQueuePosition(event.data.queue_position);
    }
    if (event.event === "delta" && typeof event.data.text === "string") {
      setPartial((current) => current + event.data.text);
    }
    if (event.event === "failed") {
      setError(typeof event.data.message === "string" ? event.data.message : "Yêu cầu thất bại");
    }
  }, []);
  useGenerationEvents(enabled ? requestId : null, handleEvent);

  const send = useCallback(async (message: string) => {
    setPartial("");
    setError("");
    setStatus("PENDING");
    const clientRequestId = crypto.randomUUID();
    const submit = async () => {
      const controller = new AbortController();
      const timeout = window.setTimeout(() => controller.abort(), 15_000);
      try {
        return await createChatJob(
          conversationId, message, clientRequestId, "default", controller.signal,
        );
      } finally {
        window.clearTimeout(timeout);
      }
    };
    let result: ChatJobAccepted;
    try {
      result = await submit();
    } catch (error) {
      if (error instanceof ApiError) throw error;
      // POST timeout/network retry dùng lại UUID để backend không tạo job trùng.
      result = await submit();
    }
    setRequestId(result.request_id);
    setStatus(result.status);
    setQueuePosition(result.queue_position);
  }, [conversationId]);

  const cancel = useCallback(async () => {
    if (!requestId) return;
    const result = await cancelGeneration(requestId);
    setStatus(result.status);
  }, [requestId]);

  const reset = useCallback(() => {
    setRequestId(null);
    setStatus(null);
    setQueuePosition(null);
    setPartial("");
    setError("");
  }, []);

  return { requestId, status, queuePosition, partial, error, send, cancel, reset };
}
