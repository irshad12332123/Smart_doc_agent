import { useEffect, useMemo, useRef, useState } from "react";
import * as I from "lucide-react";
import { streamChat } from "../../api/client";
import type { ChatMessage, Profile } from "../../types";
import { MarkdownView } from "../../components/ui/MarkdownView";
import { SourcesSidebar } from "./SourcesSidebar";

const uid = () =>
  crypto.randomUUID?.() || Math.random().toString(36).slice(2);

export function AskPage({
  profile,
}: {
  profile?: Profile;
}) {
  const storageKey = useMemo(() => {
    return profile?.id
      ? `scholarhub_chat_history_${profile.id}`
      : "scholarhub_chat_history";
  }, [profile?.id]);

  // Restore chat history from localStorage for this session
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    try {
      const key = profile?.id
        ? `scholarhub_chat_history_${profile.id}`
        : "scholarhub_chat_history";
      const saved = localStorage.getItem(key);
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed)) {
          return parsed.map((m) => ({ ...m, streaming: false }));
        }
      }
    } catch (e) {
      console.error("Failed to restore chat history from localStorage", e);
    }
    return [];
  });

  const [input, setInput] = useState("");
  const [sending, setSending] = useState(false);
  const [sourcesSidebarOpen, setSourcesSidebarOpen] = useState(false);
  const [selectedMessageId, setSelectedMessageId] = useState<string | null>(null);

  const inputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Sync messages to localStorage whenever they change
  useEffect(() => {
    try {
      if (messages.length === 0) {
        localStorage.removeItem(storageKey);
      } else {
        const toSave = messages.map((m) => ({ ...m, streaming: false }));
        localStorage.setItem(storageKey, JSON.stringify(toSave));
      }
    } catch (e) {
      console.error("Failed to save chat history to localStorage", e);
    }
  }, [messages, storageKey]);

  const userSubjects = useMemo(() => {
    if (!profile) return [];
    const subjects =
      profile.role === "student"
        ? profile.student_data?.subjects || []
        : profile.role === "faculty"
          ? (profile.faculty_data?.courses || []).flatMap((course) =>
              course.batches.flatMap((batch) => batch.subjects),
            )
          : [];
    return subjects
      .map((s) => ({
        id: s.id,
        name: s.name.trim(),
        code: s.subject_code,
      }))
      .filter((s) => s.name);
  }, [profile]);

  const totalSourcesCount = useMemo(() => {
    return messages.reduce(
      (acc, m) => acc + (m.sources?.length || 0) + (m.documents?.length || 0),
      0,
    );
  }, [messages]);

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

  const handleClearChat = () => {
    setMessages([]);
    localStorage.removeItem(storageKey);
    setSourcesSidebarOpen(false);
    setSelectedMessageId(null);
  };

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
        sources: (s) => {
          setMessages((p) =>
            p.map((m) => (m.id === assistantId ? { ...m, sources: s } : m)),
          );
        },
        documents: (docs) => {
          setMessages((p) =>
            p.map((m) => (m.id === assistantId ? { ...m, documents: docs } : m)),
          );
        },
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
      userSubjects,
    );
  };

  return (
    <div className={`ask-layout-container ${sourcesSidebarOpen ? "with-sidebar-open" : ""}`}>
      <div className="ask-main-pane">
        <div className="ask-pane-inner">
          <div className="ask-header">
            <div className="ask-header-title">
              <div className="brand-mark-ai">
                <I.Sparkles />
              </div>
              <div>
                <h1>Academic AI Assistant</h1>
                <p>
                  Ask any question across your uploaded syllabus, lectures, and course materials.
                </p>
              </div>
            </div>

            <div className="ask-header-actions">
              {totalSourcesCount > 0 && (
                <button
                  type="button"
                  className={`outline-btn toggle-sources-header-btn ${sourcesSidebarOpen ? "active" : ""}`}
                  onClick={() => setSourcesSidebarOpen((prev) => !prev)}
                  title={sourcesSidebarOpen ? "Hide referenced sources" : "View referenced sources"}
                >
                  {sourcesSidebarOpen ? (
                    <I.PanelRightClose />
                  ) : (
                    <I.PanelRightOpen />
                  )}
                  <span>Sources ({totalSourcesCount})</span>
                </button>
              )}

              {messages.length > 0 && (
                <button
                  type="button"
                  className="outline-btn clear-chat-btn"
                  onClick={handleClearChat}
                  disabled={sending}
                  title="Clear conversation history"
                >
                  <I.RotateCcw /> New Chat
                </button>
              )}
            </div>
          </div>

          <div className="ask-body">
            {messages.length === 0 ? (
              <div className="ask-empty-state">
                <div className="ask-empty-glow" />
                <div className="ask-empty-icon">
                  <I.Sparkles />
                </div>
                <h2>How can I serve you today? ✨</h2>
              </div>
            ) : (
              <div className="conversation-flow">
                {messages.map((m) => {
                  const hasSources =
                    (m.sources && m.sources.length > 0) ||
                    (m.documents && m.documents.length > 0);
                  const sourcesCount =
                    (m.sources?.length || 0) + (m.documents?.length || 0);

                  return (
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
                          <MarkdownView
                            content={m.content}
                            streaming={m.streaming}
                          />
                        </div>

                        {hasSources && (
                          <div className="message-sources-summary">
                            <button
                              type="button"
                              className={`message-sources-pill ${selectedMessageId === m.id && sourcesSidebarOpen ? "selected" : ""}`}
                              onClick={() => {
                                setSelectedMessageId(m.id);
                                setSourcesSidebarOpen(true);
                              }}
                              title="Open sources panel on the right"
                            >
                              <I.BookOpen className="pill-icon" />
                              <span className="pill-count">
                                {sourcesCount}{" "}
                                {sourcesCount === 1 ? "source cited" : "sources cited"}
                              </span>
                              <span className="pill-divider">•</span>
                              <span className="pill-action">
                                {sourcesSidebarOpen && selectedMessageId === m.id
                                  ? "Viewing in sidebar"
                                  : "View in sidebar"}
                                <I.ArrowRight className="pill-arrow" />
                              </span>
                            </button>
                          </div>
                        )}
                      </div>
                    </article>
                  );
                })}
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
      </div>

      <SourcesSidebar
        open={sourcesSidebarOpen}
        onClose={() => setSourcesSidebarOpen(false)}
        messages={messages}
        selectedMessageId={selectedMessageId}
        onSelectMessage={(id) => setSelectedMessageId(id)}
      />
    </div>
  );
}
