import ReactMarkdown from "react-markdown";
import type { Components } from "react-markdown";
import remarkGfm from "remark-gfm";

import CodeBlock from "./CodeBlock";

const LANGUAGE_PATTERN = /language-([\w+#.-]+)/i;

const MARKDOWN_COMPONENTS: Components = {
  a({ children, node: _node, ...props }) {
    return <a {...props} target="_blank" rel="noreferrer">{children}</a>;
  },
  code({ className, children, node: _node, ...props }) {
    const source = String(children);
    const language = LANGUAGE_PATTERN.exec(className ?? "")?.[1];
    const isBlock = Boolean(language) || source.endsWith("\n");
    if (isBlock) {
      return <CodeBlock code={source.replace(/\n$/, "")} language={language} />;
    }
    return <code {...props} className="inline-code">{children}</code>;
  },
  pre({ children }) {
    return <>{children}</>;
  },
  table({ children, node: _node, ...props }) {
    return <div className="markdown-table-wrap"><table {...props}>{children}</table></div>;
  },
};

export default function MarkdownMessage({ content }: { content: string }) {
  return (
    <div className="markdown-body">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={MARKDOWN_COMPONENTS}
        skipHtml
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
