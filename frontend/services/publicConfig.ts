import "server-only";

import { cache } from "react";

import { DEFAULT_CHATBOT_NAME } from "../config/branding";

export interface PublicConfiguration {
  name_chatbot: string;
}

const BACKEND_URL = process.env.BACKEND_URL ?? "http://127.0.0.1:8000";

export const getPublicConfiguration = cache(async (): Promise<PublicConfiguration> => {
  try {
    const response = await fetch(`${BACKEND_URL}/config`, {
      cache: "no-store",
      signal: AbortSignal.timeout(2_500),
    });
    if (!response.ok) return { name_chatbot: DEFAULT_CHATBOT_NAME };

    const config = (await response.json()) as Partial<PublicConfiguration>;
    const name = config.name_chatbot?.trim();
    return { name_chatbot: name || DEFAULT_CHATBOT_NAME };
  } catch {
    return { name_chatbot: DEFAULT_CHATBOT_NAME };
  }
});
