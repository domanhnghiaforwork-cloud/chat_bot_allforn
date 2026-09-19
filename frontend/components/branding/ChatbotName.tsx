"use client";

import { useChatbotName } from "./BrandProvider";

export default function ChatbotName() {
  return <>{useChatbotName()}</>;
}
