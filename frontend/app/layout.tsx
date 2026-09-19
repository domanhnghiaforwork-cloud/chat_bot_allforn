import type { Metadata } from "next";
import { Inter } from "next/font/google";
import type { ReactNode } from "react";

import AppShell from "../components/AppShell";
import { BrandProvider } from "../components/branding/BrandProvider";
import { getPublicConfiguration } from "../services/publicConfig";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "vietnamese"] });

export async function generateMetadata(): Promise<Metadata> {
  const { name_chatbot: chatbotName } = await getPublicConfiguration();
  return {
    title: `Chatbot ${chatbotName}`,
    description: `${chatbotName} - trợ lý AI hỗ trợ hội thoại và lập trình.`,
  };
}

export default async function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  const { name_chatbot: chatbotName } = await getPublicConfiguration();
  return (
    <html lang="vi">
      <body className={inter.className}>
        <BrandProvider chatbotName={chatbotName}>
          <AppShell>{children}</AppShell>
        </BrandProvider>
      </body>
    </html>
  );
}
