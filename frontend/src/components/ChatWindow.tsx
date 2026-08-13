import { useEffect, useRef, useState } from "react";
import { Send, BookOpen } from "lucide-react";
import type { ChatMessage } from "../types";
import MessageBubble from "./MessageBubble";

interface Props {
  messages: ChatMessage[];
  activeSourceByMsg: Record<string, number | null>;
  onCitationClick: (msgId: string, index: number) => void;
  onSend: (text: string) => void;
  disabled: boolean;
}

export default function ChatWindow({ messages, activeSourceByMsg, onCitationClick, onSend, disabled }: Props) {
  const [input, setInput] = useState("");
  const bottomRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const submit = () => {
    const text = input.trim();
    if (!text || disabled) return;
    onSend(text);
    setInput("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";
  };

  return (
    <div className="flex-1 flex flex-col h-full min-w-0">
      <div className="flex-1 overflow-y-auto">
        {messages.length === 0 ? (
          <div className="h-full flex flex-col items-center justify-center px-6 text-center">
            <BookOpen size={28} style={{ color: "var(--accent)" }} className="mb-4" />
            <h2 className="font-display text-2xl mb-2" style={{ color: "var(--text)" }}>
              Ask the archive
            </h2>
            <p className="text-sm max-w-sm leading-relaxed" style={{ color: "var(--text-dim)" }}>
              Add a few documents on the left, then ask a question. Answers are grounded in what
              you've uploaded, with numbered citations you can click to see the source passage.
            </p>
          </div>
        ) : (
          <div className="max-w-3xl mx-auto px-6 py-8 space-y-5">
            {messages.map((m) => (
              <MessageBubble
                key={m.id}
                message={m}
                activeSource={activeSourceByMsg[m.id] ?? null}
                onCitationClick={(idx) => onCitationClick(m.id, idx)}
              />
            ))}
            <div ref={bottomRef} />
          </div>
        )}
      </div>

      {/* Composer */}
      <div className="border-t px-6 py-4" style={{ borderColor: "var(--border)" }}>
        <div
          className="max-w-3xl mx-auto flex items-end gap-2 rounded-xl border px-3 py-2"
          style={{ borderColor: "var(--border)", background: "var(--surface)" }}
        >
          <textarea
            ref={textareaRef}
            value={input}
            placeholder="Ask something about your documents…"
            rows={1}
            className="flex-1 resize-none bg-transparent outline-none text-sm py-1.5 max-h-40"
            style={{ color: "var(--text)" }}
            onChange={(e) => {
              setInput(e.target.value);
              e.target.style.height = "auto";
              e.target.style.height = `${Math.min(e.target.scrollHeight, 160)}px`;
            }}
            onKeyDown={(e) => {
              if (e.key === "Enter" && !e.shiftKey) {
                e.preventDefault();
                submit();
              }
            }}
          />
          <button
            onClick={submit}
            disabled={disabled || !input.trim()}
            className="shrink-0 rounded-lg p-2 transition-colors disabled:opacity-30"
            style={{ background: "var(--accent-soft)", color: "var(--accent-strong)" }}
          >
            <Send size={16} />
          </button>
        </div>
      </div>
    </div>
  );
}
