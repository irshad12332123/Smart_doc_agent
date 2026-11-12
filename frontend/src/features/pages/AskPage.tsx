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
  userName: userNameProp,
  userId: userIdProp,
}: {
  profile?: Profile;
  userName?: string;
  userId?: string;
}) {
  const resolvedUserName = useMemo(() => {
    if (userNameProp?.trim()) return userNameProp.trim();
    if (profile?.full_name?.trim()) return profile.full_name.trim();
    try {
      const raw = localStorage.getItem("scholarhub-session");
      if (raw) {
        const parsed = JSON.parse(raw);
        if (parsed.summary?.full_name?.trim()) {
          return parsed.summary.full_name.trim();
        }
        if (parsed.user?.full_name?.trim()) {
          return parsed.user.full_name.trim();
        }
        if (parsed.user?.name?.trim()) {
          return parsed.user.name.trim();
        }
        if (parsed.user?.email) {
          const part = parsed.user.email.split("@")[0];
          return part.charAt(0).toUpperCase() + part.slice(1);
        }
      }
    } catch {}
    return "User";
  }, [userNameProp, profile?.full_name]);

  const resolvedUserId = useMemo(() => {
    if (userIdProp) return userIdProp;
    if (profile?.id) return profile.id;
    try {
      const raw = localStorage.getItem("scholarhub-session");
      if (raw) {
        const parsed = JSON.parse(raw);
        return parsed.summary?.id || parsed.user?.id;
      }
    } catch {}
    return undefined;
  }, [userIdProp, profile?.id]);

  const storageKey = useMemo(() => {
    return resolvedUserId
      ? `scholarhub_chat_history_${resolvedUserId}`
      : "scholarhub_chat_history";
  }, [resolvedUserId]);

  // Restore chat history from localStorage for this session
  const [messages, setMessages] = useState<ChatMessage[]>(() => {
    try {
      const key = resolvedUserId
        ? `scholarhub_chat_history_${resolvedUserId}`
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
  const heroInputRef = useRef<HTMLInputElement>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const askBodyRef = useRef<HTMLDivElement>(null);
  const mainPaneRef = useRef<HTMLDivElement>(null);

  // Allow scrolling the message history even when cursor is over header, composer dock, or side padding
  useEffect(() => {
    const pane = mainPaneRef.current;
    if (!pane) return;

    const onWheel = (e: WheelEvent) => {
      const askBody = askBodyRef.current;
      if (!askBody) return;
      if (askBody.contains(e.target as Node)) return;
      askBody.scrollTop += e.deltaY;
    };

    pane.addEventListener("wheel", onWheel, { passive: true });
    return () => pane.removeEventListener("wheel", onWheel);
  }, []);

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

  const scrollToBottom = (behavior: ScrollBehavior = "smooth") => {
    if (askBodyRef.current) {
      askBodyRef.current.scrollTo({
        top: askBodyRef.current.scrollHeight,
        behavior,
      });
    } else {
      messagesEndRef.current?.scrollIntoView({ behavior });
    }
  };

  useEffect(() => {
    const saved = sessionStorage.getItem("scholarhub-query");
    if (saved) {
      sessionStorage.removeItem("scholarhub-query");
      setInput(saved);
      setTimeout(() => {
        (heroInputRef.current || inputRef.current)?.focus();
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

  const renderComposerForm = (isHero: boolean) => (
    <form
      className={`composer-bar ${isHero ? "composer-bar-hero" : ""}`}
      onSubmit={send}
    >
      <button
        type="button"
        className="composer-icon-btn"
        title="Attach file (available in upload tab)"
        aria-label="Attach file"
      >
        <I.Paperclip />
      </button>

      <input
        ref={isHero ? heroInputRef : inputRef}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        placeholder={
          isHero
            ? "Ask a question about your syllabus, lectures, or courses…"
            : "Ask a question or request a summary…"
        }
        disabled={sending}
        aria-label="Chat input"
        autoFocus={isHero}
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
  );

  return (
    <div className={`ask-layout-container ${sourcesSidebarOpen ? "with-sidebar-open" : ""}`}>
      <div className="ask-main-pane" ref={mainPaneRef}>
        <div className="ask-pane-inner">
          <div className="ask-header">
            <div className="ask-header-inner">
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
          </div>

          <div className="ask-body" ref={askBodyRef}>
            {messages.length === 0 ? (
              <div className="ask-empty-state">
                <div className="ask-empty-icon">
                  <I.Sparkles />
                </div>
                <h2 className="ask-hero-greeting">Hello {resolvedUserName}</h2>
                <p className="ask-hero-subtitle">
                  Ask any question across your uploaded syllabus, lectures, and course materials.
                </p>

                <div className="ask-hero-input-wrapper">
                  <div className="hero-glow-field" aria-hidden="true">
                    <div className="glow-orb orb-left" />
                    <div className="glow-orb orb-center" />
                    <div className="glow-orb orb-right" />
                    <div className="glow-flow-border" />
                  </div>
                  {renderComposerForm(true)}
                </div>

                <div className="ask-hero-suggestions">
                  <button
                    type="button"
                    className="ask-hero-chip"
                    onClick={() => {
                      setInput("Summarize key concepts from current syllabus");
                      heroInputRef.current?.focus();
                    }}
                  >
                    <I.BookOpen className="chip-icon" />
                    <span>Summarize syllabus</span>
                  </button>
                  <button
                    type="button"
                    className="ask-hero-chip"
                    onClick={() => {
                      setInput("Explain difficult topics with practical examples");
                      heroInputRef.current?.focus();
                    }}
                  >
                    <I.Sparkles className="chip-icon" />
                    <span>Explain with examples</span>
                  </button>
                  <button
                    type="button"
                    className="ask-hero-chip"
                    onClick={() => {
                      setInput("Generate practice exam questions and answers");
                      heroInputRef.current?.focus();
                    }}
                  >
                    <I.GraduationCap className="chip-icon" />
                    <span>Practice exam questions</span>
                  </button>
                </div>

                <p className="hero-composer-footnote">
                  ScholarHub AI generates responses based on verified batch materials and course syllabus.
                </p>
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

          {messages.length > 0 && (
            <div className="composer-dock">
              <div className="composer-dock-inner">
                {renderComposerForm(false)}
                <p className="composer-footnote">
                  ScholarHub AI generates responses based on verified batch materials and course syllabus.
                </p>
              </div>
            </div>
          )}
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
