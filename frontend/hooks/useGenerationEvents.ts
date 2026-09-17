"use client";

import { useEffect, useRef } from "react";

import { getGeneration, openGenerationEvents } from "../services/generationApi";
import type { GenerationEvent } from "../types/generation";

export function useGenerationEvents(
  requestId: string | null,
  onEvent: (event: GenerationEvent) => void,
) {
  const callback = useRef(onEvent);
  callback.current = onEvent;

  useEffect(() => {
    if (!requestId) return;
    const controller = new AbortController();
    let cursor = "";
    let stopped = false;
    let terminal = false;

    async function connect() {
      while (!stopped) {
        try {
          cursor = await openGenerationEvents(
            requestId!, cursor, controller.signal, (event) => {
              terminal = event.event === "completed" || event.event === "failed";
              callback.current(event);
            },
          );
          if (terminal) return;
        } catch {
          if (controller.signal.aborted) return;
          // Event có thể đã hết TTL: GET status là nguồn đồng bộ lại.
          const generation = await getGeneration(requestId!).catch(() => null);
          if (generation?.status === "DONE") {
            callback.current({ id: cursor, event: "completed", data: { status: "DONE" } });
            return;
          }
          if (generation?.status === "FAILED" || generation?.status === "CANCELLED") {
            callback.current({
              id: cursor,
              event: "failed",
              data: {
                status: generation.status,
                error_code: generation.error_code,
                message: generation.error_message,
              },
            });
            return;
          }
          await new Promise((resolve) => setTimeout(resolve, 1000));
        }
      }
    }

    const poll = window.setInterval(() => {
      getGeneration(requestId).then((generation) => {
        if (generation.status === "DONE") {
          terminal = true;
          window.clearInterval(poll);
          callback.current({ id: cursor, event: "completed", data: { status: "DONE" } });
          controller.abort();
        } else if (generation.status === "FAILED" || generation.status === "CANCELLED") {
          terminal = true;
          window.clearInterval(poll);
          callback.current({
            id: cursor,
            event: "failed",
            data: { status: generation.status, message: generation.error_message },
          });
          controller.abort();
        }
      }).catch(() => undefined);
    }, 10_000);
    void connect();
    return () => {
      stopped = true;
      window.clearInterval(poll);
      controller.abort();
    };
  }, [requestId]);
}
