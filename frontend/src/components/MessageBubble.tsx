import ReactMarkdown from "react-markdown";
import { Fragment } from "react";
import type { ChatMessage } from "../types";

interface Props {
  message: ChatMessage;
  activeSource: number | null;
  onCitationClick: (index: number) => void;
}

/** Splits text on [n] markers and renders each as a clickable citation-mark span. */
function renderWithCitations(
  text: string,
  activeSource: number | null,
  onCitationClick: (index: number) => void
) {
  const parts = text.split(/(\[\d+\])/g);
  return parts.map((part, i) => {
    const match = part.match(/^\[(\d+)\]$/);
    if (!match) return <Fragment key={i}>{part}</Fragment>;
    const idx = parseInt(match[1], 10) - 1;
    return (
      <span
        key={i}
        className={`citation-mark ${activeSource === idx ? "active" : ""}`}
        onClick={() => onCitationClick(idx)}
      >
        {match[1]}
      </span>
    );
  });
}

export default function MessageBubble({ message, activeSource, onCitationClick }: Props) {
  const isUser = message.role === "user";

  return (
    <div className={`msg-enter flex ${isUser ? "justify-end" : "justify-start"}`}>
      <div
        className="max-w-[75%] rounded-2xl px-4 py-3"
        style={{
          background: isUser ? "var(--user-bubble)" : "transparent",
          border: isUser ? "1px solid var(--border)" : "none",
        }}
      >
        {isUser ? (
          <p className="text-sm leading-relaxed whitespace-pre-wrap" style={{ color: "var(--text)" }}>
            {message.content}
          </p>
        ) : (
          <div
            className="text-sm leading-relaxed prose-sm"
            style={{ color: message.error ? "#e07a5f" : "var(--text)" }}
          >
            {message.content ? (
              <ReactMarkdown
                components={{
                  p: ({ children }) => (
                    <p className="mb-2 last:mb-0">
                      {typeof children === "string"
                        ? renderWithCitations(children, activeSource, onCitationClick)
                        : children}
                    </p>
                  ),
                  code: ({ children }) => (
                    <code className="font-mono text-xs px-1 py-0.5 rounded" style={{ background: "var(--surface-raised)" }}>
                      {children}
                    </code>
                  ),
                }}
              >
                {message.content}
              </ReactMarkdown>
            ) : (
              <span style={{ color: "var(--text-faint)" }}>Thinking</span>
            )}
            {message.streaming && <span className="streaming-caret" />}
          </div>
        )}
      </div>
    </div>
  );
}
