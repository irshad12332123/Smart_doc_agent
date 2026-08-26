import { useEffect, useRef, useState } from "react";
import * as I from "lucide-react";
import { streamChat } from "../../api/client";
import type { ChatMessage, DocumentInfo } from "../../types";

const suggestions = [
  "Find my pending assignments",
  "Show Machine Learning notes",
  "What are the latest notices?",
  "Find Software Engineering PDFs",
];

const uid = () => crypto.randomUUID?.() || Math.random().toString(36).slice(2);

export function AskPage({ documents }: { documents: DocumentInfo[] }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const saved = sessionStorage.getItem("scholarhub-query");
    if (saved) {
      sessionStorage.removeItem("scholarhub-query");
      setInput(saved);
      setTimeout(() => inputRef.current?.focus(), 0);
    }
  }, []);

  const send = async (e?: React.FormEvent) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    const user = { id: uid(), role: "user" as const, content: text };
    const id = uid();

    setMessages((prev) => [
      ...prev,
      user,
      { id, role: "assistant", content: "", streaming: true },
    ]);
    setInput("");
    setSending(true);

    let full = "";
    await streamChat(
      text,
      messages.map((m) => ({ role: m.role, content: m.content })),
      {
        sources: (s) =>
          setMessages((p) =>
            p.map((m) => (m.id === id ? { ...m, sources: s } : m)),
          ),
        token: (t) => {
          full += t;
          setMessages((p) =>
            p.map((m) => (m.id === id ? { ...m, content: full } : m)),
          );
        },
        done: () => {
          setMessages((p) =>
            p.map((m) => (m.id === id ? { ...m, streaming: false } : m)),
          );
          setSending(false);
        },
        error: (m) => {
          setMessages((p) =>
            p.map((x) =>
              x.id === id
                ? { ...x, content: m, error: true, streaming: false }
                : x,
            ),
          );
          setSending(false);
        },
      },
    );
  };

  return (
    <div className="ask-page">
      <div className="ask-title">
        <span className="brand-mark">
          <I.Sparkles />
        </span>
        <div>
          <h1>Ask ScholarHub</h1>
          <p>Search your academic material and inspect the original sources.</p>
        </div>
      </div>
      {messages.length === 0 ? (
        <div className="ask-empty">
          <I.Sparkles />
          <h2>What can I help you find?</h2>
          <p>
            Ask about uploaded notes, assignments, or notices for your course.
          </p>
          <div className="suggestions">
            {suggestions.map((q) => (
              <button key={q} onClick={() => setInput(q)}>
                {q}
              </button>
            ))}
          </div>
          {documents.length === 0 && (
            <p className="api-note">
              <I.Info /> No documents are currently indexed. Upload material
              before asking.
            </p>
          )}
        </div>
      ) : (
        <div className="conversation">
          {messages.map((m) => (
            <article className={`message ${m.role}`} key={m.id}>
              <div className="message-avatar">
                {m.role === "user" ? <I.UserRound /> : <I.Sparkles />}
              </div>
              <div className="message-body">
                <span className="message-label">
                  {m.role === "user" ? "YOU" : "SCHOLARHUB"}
                </span>
                <p>
                  {m.content || "Searching your academic materials…"}
                  {m.streaming && <i className="cursor" />}
                </p>
                {m.sources && m.sources.length > 0 && (
                  <div className="sources">
                    <b>
                      <I.BookOpen /> Sources
                    </b>
                    {m.sources.map((s, i) => (
                      <div className="source" key={s.chunk_id}>
                        <span>{i + 1}</span>
                        <div>
                          <strong>{s.filename}</strong>
                          <small>{s.text.slice(0, 130)}…</small>
                        </div>
                        <button title="Document preview is pending backend file URLs">
                          <I.ExternalLink />
                        </button>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </article>
          ))}
        </div>
      )}

      <form className="composer" onSubmit={send}>
        <I.Paperclip />
        <input
          ref={inputRef}
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask a follow-up question…"
          disabled={sending}
        />
        <button className="primary" disabled={sending || !input.trim()}>
          <I.Send />
        </button>
      </form>
    </div>
  );
}
