"use client";

import hljs from "highlight.js/lib/common";
import { useEffect, useMemo, useState } from "react";

const LANGUAGE_ALIASES: Record<string, string> = {
  csharp: "csharp",
  html: "xml",
  jsx: "javascript",
  md: "markdown",
  py: "python",
  shell: "bash",
  sh: "bash",
  ts: "typescript",
  tsx: "typescript",
  yml: "yaml",
};

interface CodeBlockProps {
  code: string;
  language?: string;
}

export default function CodeBlock({ code, language = "text" }: CodeBlockProps) {
  const [copyState, setCopyState] = useState<"idle" | "copied" | "error">("idle");
  const normalizedLanguage = LANGUAGE_ALIASES[language.toLowerCase()] ?? language.toLowerCase();
  const highlightedCode = useMemo(() => {
    if (!hljs.getLanguage(normalizedLanguage)) {
      return hljs.highlight(code, { language: "plaintext" }).value;
    }
    return hljs.highlight(code, {
      language: normalizedLanguage,
      ignoreIllegals: true,
    }).value;
  }, [code, normalizedLanguage]);

  useEffect(() => {
    if (copyState === "idle") return;
    const timeout = window.setTimeout(() => setCopyState("idle"), 2_000);
    return () => window.clearTimeout(timeout);
  }, [copyState]);

  async function copyCode() {
    try {
      if (navigator.clipboard?.writeText) {
        await navigator.clipboard.writeText(code);
      } else {
        const textArea = document.createElement("textarea");
        textArea.value = code;
        textArea.style.position = "fixed";
        textArea.style.opacity = "0";
        document.body.appendChild(textArea);
        textArea.select();
        let copied = false;
        try {
          copied = document.execCommand("copy");
        } finally {
          textArea.remove();
        }
        if (!copied) throw new Error("Copy command failed");
      }
      setCopyState("copied");
    } catch {
      setCopyState("error");
    }
  }

  const copyLabel = copyState === "copied"
    ? "Đã sao chép"
    : copyState === "error"
      ? "Không thể sao chép"
      : "Sao chép";

  return (
    <div className="code-block">
      <div className="code-block-header">
        <span>{language}</span>
        <button type="button" onClick={() => void copyCode()} aria-label="Sao chép đoạn mã">
          {copyLabel}
        </button>
      </div>
      <pre>
        <code
          className={`hljs language-${normalizedLanguage}`}
          dangerouslySetInnerHTML={{ __html: highlightedCode }}
        />
      </pre>
    </div>
  );
}
