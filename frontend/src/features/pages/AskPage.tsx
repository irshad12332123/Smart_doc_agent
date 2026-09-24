import { useEffect, useRef, useState } from "react";
import * as I from "lucide-react";
import { streamChat } from "../../api/client";
import type { ChatMessage, DocumentInfo } from "../../types";
import { getFileTypeTheme } from "../../components/ui/common";

const suggestions = [
  "Find my pending assignments",
  "Show Machine Learning notes",
  "What are the latest notices?",
  "Find Software Engineering PDFs",
];

const uid = () =>
  crypto.randomUUID?.() || Math.random().toString(36).slice(2);

export function AskPage({ documents }: { documents: DocumentInfo[] }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    const saved = sessionStorage.getItem("scholarhub-query");
    if (saved) {
      sessionStorage.removeItem("scholarhub-query");
      setInput(saved);
      setTimeout(() => {
        inputRef.current?.focus();
      }, 50);
    }
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const send = async (e?: React.FormEvent) => {
    e?.preventDefault();
    const text = input.trim();
    if (!text || sending) return;

    const userMsg: ChatMessage = {
      id: uid(),
      role: "user",
      content: text,
    };
    const assistantId = uid();

    setMessages((prev) => [
      ...prev,
      userMsg,
      { id: assistantId, role: "assistant", content: "", streaming: true },
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
            p.map((m) => (m.id === assistantId ? { ...m, sources: s } : m)),
          ),
        token: (t) => {
          full += t;
          setMessages((p) =>
            p.map((m) => (m.id === assistantId ? { ...m, content: full } : m)),
          );
        },
        done: () => {
          setMessages((p) =>
            p.map((m) =>
              m.id === assistantId ? { ...m, streaming: false } : m,
            ),
          );
          setSending(false);
        },
        error: (m) => {
          setMessages((p) =>
            p.map((x) =>
              x.id === assistantId
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
      <div className="ask-header">
        <div className="ask-header-title">
          <div className="brand-mark-ai">
            <I.Sparkles />
          </div>
          <div>
            <h1>Academic AI Assistant</h1>
            <p>
              Ask any question across your uploaded syllabus, lectures, and notices.
            </p>
          </div>
        </div>

        {messages.length > 0 && (
          <button
            className="outline-btn clear-chat-btn"
            onClick={() => setMessages([])}
            disabled={sending}
          >
            <I.RotateCcw /> New Chat
          </button>
        )}
      </div>

      <div className="ask-body">
        {messages.length === 0 ? (
          <div className="ask-empty-state">
            <div className="ask-empty-glow" />
            <div className="ask-empty-icon">
              <I.Sparkles />
            </div>
            <h2>What would you like to know?</h2>
            <p>
              I can summarize documents, locate syllabus points, clarify complex
              concepts, or find specific deadlines with cited sources.
            </p>

            <div className="ask-suggestions-grid">
              {suggestions.map((q) => (
                <button
                  key={q}
                  className="ask-suggestion-card"
                  onClick={() => {
                    setInput(q);
                    inputRef.current?.focus();
                  }}
                >
                  <I.HelpCircle className="card-q-icon" />
                  <span>{q}</span>
                  <I.ArrowUpRight className="card-arrow-icon" />
                </button>
              ))}
            </div>

            {documents.length === 0 && (
              <div className="api-note ask-note">
                <I.Info />
                <span>
                  No documents are indexed yet. Documents uploaded by your faculty
                  or CR will be searchable here.
                </span>
              </div>
            )}
          </div>
        ) : (
          <div className="conversation-flow">
            {messages.map((m) => (
              <article
                className={`chat-message ${m.role} ${m.error ? "msg-error" : ""}`}
                key={m.id}
              >
                <div className="message-avatar-box">
                  {m.role === "user" ? (
                    <I.UserRound />
                  ) : (
                    <I.Sparkles className="sparkle-spin" />
                  )}
                </div>

                <div className="message-bubble-wrap">
                  <div className="message-sender-row">
                    <span className="sender-name">
                      {m.role === "user" ? "You" : "ScholarHub Assistant"}
                    </span>
                    {m.streaming && (
                      <span className="streaming-badge">
                        <span className="pulsing-dot" /> Generating answer…
                      </span>
                    )}
                  </div>

                  <div className="message-text-content">
                    <p>
                      {m.content ||
                        (m.streaming ? "Searching academic knowledge base…" : "")}
                      {m.streaming && <span className="streaming-cursor" />}
                    </p>
                  </div>

                  {m.sources && m.sources.length > 0 && (
                    <div className="sources-container">
                      <div className="sources-header">
                        <I.BookOpen />
                        <span>Referenced Sources ({m.sources.length})</span>
                      </div>
                      <div className="sources-cards-list">
                        {m.sources.map((s, idx) => {
                          const fileType = getFileTypeTheme(
                            s.filename.split(".").pop() || "",
                          );
                          const Icon = fileType.icon;
                          return (
                            <div className="source-citation-card" key={s.chunk_id || idx}>
                              <div className="source-index-badge">{idx + 1}</div>
                              <div className="source-meta">
                                <div className="source-filename-row">
                                  <Icon className="source-file-icon" />
                                  <strong title={s.filename}>{s.filename}</strong>
                                </div>
                                <p className="source-snippet">{s.text}</p>
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    </div>
                  )}
                </div>
              </article>
            ))}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      <div className="composer-dock">
        <form className="composer-bar" onSubmit={send}>
          <button
            type="button"
            className="composer-icon-btn"
            title="Attach file (available in upload tab)"
            aria-label="Attach file"
          >
            <I.Paperclip />
          </button>

          <input
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask a question or request a summary…"
            disabled={sending}
            aria-label="Chat input"
          />

          <button
            type="submit"
            className="composer-send-btn"
            disabled={sending || !input.trim()}
            title="Send message"
            aria-label="Send message"
          >
            {sending ? <I.Loader2 className="spinning-loader" /> : <I.Send />}
          </button>
        </form>
        <p className="composer-footnote">
          ScholarHub AI generates responses based on verified batch materials and course syllabus.
        </p>
      </div>
    </div>
  );
}
