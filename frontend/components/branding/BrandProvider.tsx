"use client";

import { createContext, useContext } from "react";
import type { ReactNode } from "react";

import { DEFAULT_CHATBOT_NAME } from "../../config/branding";

const ChatbotNameContext = createContext(DEFAULT_CHATBOT_NAME);

export function BrandProvider({
  chatbotName,
  children,
}: {
  chatbotName: string;
  children: ReactNode;
}) {
  return (
    <ChatbotNameContext.Provider value={chatbotName}>
      {children}
    </ChatbotNameContext.Provider>
  );
}

export function useChatbotName() {
  return useContext(ChatbotNameContext);
}
