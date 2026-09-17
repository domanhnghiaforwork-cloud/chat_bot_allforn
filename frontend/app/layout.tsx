import type { Metadata } from "next";
import { Inter } from "next/font/google";
import type { ReactNode } from "react";

import AppShell from "../components/AppShell";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "vietnamese"] });

export const metadata: Metadata = {
  title: "Chatbot Gemini",
  description: "Chatbot v3 có tài khoản và lịch sử hội thoại riêng",
};

export default function RootLayout({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <html lang="vi">
      <body className={inter.className}>
        <AppShell>{children}</AppShell>
      </body>
    </html>
  );
}
