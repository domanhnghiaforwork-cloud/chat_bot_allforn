import type { Metadata } from "next";
import { Inter } from "next/font/google";
import type { ReactNode } from "react";

import AppShell from "../components/AppShell";
import "./globals.css";

const inter = Inter({ subsets: ["latin", "vietnamese"] });

export const metadata: Metadata = {
  title: "Chatbot Gemini",
  description: "Chatbot v4.2 có quota, hàng đợi và quản trị vận hành",
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
