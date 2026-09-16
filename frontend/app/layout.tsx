import type { Metadata } from "next";
import { Inter } from "next/font/google";
import type { ReactNode } from "react";

import ConversationSidebar from "../components/ConversationSidebar";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "vietnamese"] });

export const metadata: Metadata = {
  title: "Chatbot Gemini",
  description: "Chatbot v2 có lịch sử hội thoại",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="vi">
      <body className={inter.className}>
        <div className="app-shell">
          <ConversationSidebar />
          <main>{children}</main>
        </div>
      </body>
    </html>
  );
}
