import { useEffect, useMemo, useRef, useState } from "react";
import * as I from "lucide-react";
import { authApi, documentApi, streamChat } from "./api/client";
import type { ChatMessage, DocumentInfo, Session } from "./types";

type Page =
  | "home"
  | "ask"
  | "library"
  | "notices"
  | "subjects"
  | "profile"
  | "upload"
  | "draft"
  | "admin";

const nav = [
  { id: "home", label: "Home", icon: I.House },
  { id: "ask", label: "Ask AI", icon: I.Sparkles },
  { id: "library", label: "Library", icon: I.Library },
  { id: "notices", label: "Notices", icon: I.Bell },
  { id: "subjects", label: "Subjects", icon: I.GraduationCap },
  { id: "profile", label: "Profile", icon: I.UserRound },
] as const;

const suggestions = [
  "Find my pending assignments",
  "Show Machine Learning notes",
  "What are the latest notices?",
  "Find Software Engineering PDFs",
];

const subjects = [
  "Software Engineering and Testing",
  "Machine Learning and NLP on AWS Cloud",
  "Multimedia and Animation",
  "Internet of Things (IoT)",
  "Software Engineering and Testing Lab",
  "Machine Learning and NLP on AWS Cloud Lab",
  "Project-II",
];

const initials = (name: string) =>
  name
    .split(" ")
    .map((x) => x[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

const uid = () => crypto.randomUUID?.() || Math.random().toString(36).slice(2);

const errorMessage = (value: unknown, fallback: string) =>
  typeof value === "object" && value !== null && "message" in value
    ? String((value as { message?: unknown }).message ?? fallback)
    : fallback;

function App() {
  const [session, setSession] = useState<Session | null>(null),
    [checking, setChecking] = useState(true);
  const [page, setPage] = useState<Page>("home"),
    [documents, setDocuments] = useState<DocumentInfo[]>([]),
    [docError, setDocError] = useState("");

  useEffect(() => {
    const saved = localStorage.getItem("scholarhub-session");
    if (!saved) return setChecking(false);
    try {
      const stored = JSON.parse(saved) as Session;
      authApi
        .me(stored.access_token)
        .then(({ user, profile }) => setSession({ ...stored, user, profile }))
        .catch(() => localStorage.removeItem("scholarhub-session"))
        .finally(() => setChecking(false));
    } catch {
      setChecking(false);
    }
  }, []);

  useEffect(() => {
    if (!session) return;
    documentApi
      .list()
      .then(setDocuments)
      .catch(() => setDocError("Documents could not be loaded."));
  }, [session]);

  const signIn = (next: Session) => {
    localStorage.setItem("scholarhub-session", JSON.stringify(next));
    setSession(next);
  };

  const logout = () => {
    localStorage.removeItem("scholarhub-session");
    setSession(null);
    setPage("home");
  };

  if (checking)
    return (
      <div className="splash">
        <div className="brand-mark">
          <I.GraduationCap />
        </div>
        <span>Loading ScholarHub…</span>
      </div>
    );

  if (!session) return <Auth onSession={signIn} />;
  return (
    <div className="shell">
      <Sidebar
        session={session}
        page={page}
        onPage={setPage}
        onLogout={logout}
      />
      <main className="main">
        <Topbar session={session} onPage={setPage} />
        <PageView
          page={page}
          setPage={setPage}
          session={session}
          documents={documents}
          setDocuments={setDocuments}
          docError={docError}
        />
      </main>
    </div>
  );
}

function Auth({ onSession }: { onSession: (value: Session) => void }) {
  const [view, setView] = useState<"choose" | "verify" | "register" | "login">(
      "choose",
    ),
    [kind, setKind] = useState<"student" | "faculty">("student");
  const [id, setId] = useState(""),
    [eligible, setEligible] = useState<{
      name: string;
      email: string;
      token: string;
    } | null>(null),
    [email, setEmail] = useState(""),
    [password, setPassword] = useState(""),
    [error, setError] = useState(""),
    [busy, setBusy] = useState(false);

  const submitVerify = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const result = await authApi.check(kind, id);
      if (result.status === "registered") {
        setEmail("");
        setView("login");
        setError("This ID already has an account. Please sign in.");
      } else if (
        result.name &&
        result.registered_email &&
        result.registration_token
      ) {
        setEligible({
          name: result.name,
          email: result.registered_email,
          token: result.registration_token,
        });
        setView("register");
      }
    } catch (err: unknown) {
      setError(errorMessage(err, "Could not verify your record."));
    } finally {
      setBusy(false);
    }
  };

  const submitRegister = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!eligible) return;
    setBusy(true);
    setError("");
    try {
      await authApi.register(eligible.token, password);
      setEmail(eligible.email);
      setPassword("");
      setView("login");
      setError("Account created. Sign in to continue.");
    } catch (err: unknown) {
      setError(errorMessage(err, "Could not create your account."));
    } finally {
      setBusy(false);
    }
  };

  const submitLogin = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError("");
    try {
      const login = await authApi.login(email, password);
      const me = await authApi.me(login.access_token);
      onSession({ ...login, ...me });
    } catch (err: unknown) {
      setError(errorMessage(err, "Unable to sign in."));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="auth-page">
      <div className="auth-aside">
        <div className="logo">
          <span className="brand-mark">
            <I.GraduationCap />
          </span>
          <span>
            ScholarHub<small>Academic Knowledge Hub</small>
          </span>
        </div>
        <div className="auth-copy">
          <span className="eyebrow">YOUR ACADEMIC SPACE</span>
          <h1>
            Everything your batch needs.
            <br />
            In one place.
          </h1>
          <p>
            Find notes, assignments, notices, and answers—then open the original
            source.
          </p>
        </div>
        <div className="auth-foot">BCA · 2024–27 · Semester 5</div>
      </div>
      <section className="auth-card">
        <div className="auth-inner">
          {view === "choose" && (
            <>
              <span className="eyebrow">WELCOME TO SCHOLARHUB</span>
              <h2>How would you like to continue?</h2>
              <p className="muted">
                Your access is verified against the university registry.
              </p>
              <div className="role-options">
                <button
                  onClick={() => {
                    setKind("student");
                    setView("verify");
                  }}
                >
                  <I.GraduationCap />
                  <b>Continue as Student</b>
                  <small>Access your batch materials and AI assistant</small>
                  <I.ChevronRight />
                </button>
                <button
                  onClick={() => {
                    setKind("faculty");
                    setView("verify");
                  }}
                >
                  <I.BookOpen />
                  <b>Continue as Faculty</b>
                  <small>Share learning material with your batches</small>
                  <I.ChevronRight />
                </button>
                <button
                  onClick={() => {
                    setView("login");
                  }}
                >
                  <I.ShieldCheck />
                  <b>Administrator</b>
                  <small>Existing admin accounts only</small>
                  <I.ChevronRight />
                </button>
              </div>
              <p className="auth-link">
                Already registered?{" "}
                <button onClick={() => setView("login")}>Sign in</button>
              </p>
            </>
          )}
          {view === "verify" && (
            <>
              <button className="back" onClick={() => setView("choose")}>
                <I.ArrowLeft /> Back
              </button>
              <span className="eyebrow">{kind.toUpperCase()} VERIFICATION</span>
              <h2>Verify your university record</h2>
              <p className="muted">
                Enter your {kind} ID to securely find your official record.
              </p>
              <form onSubmit={submitVerify}>
                <label>
                  {kind === "student" ? "Student ID" : "Faculty ID"}
                  <input
                    autoFocus
                    value={id}
                    onChange={(e) => setId(e.target.value)}
                    placeholder={
                      kind === "student"
                        ? "e.g. 24031009031"
                        : "Enter your faculty ID"
                    }
                    required
                  />
                </label>
                <Error text={error} />
                <button className="primary full" disabled={busy}>
                  {busy ? "Verifying…" : "Verify my record"}
                  <I.ArrowRight />
                </button>
              </form>
            </>
          )}
          {view === "register" && eligible && (
            <>
              <button className="back" onClick={() => setView("verify")}>
                <I.ArrowLeft /> Back
              </button>
              <span className="eyebrow">RECORD VERIFIED</span>
              <h2>Welcome, {eligible.name.split(" ")[0]}.</h2>
              <p className="muted">
                Your {kind} record was found. Set a password to create your
                ScholarHub account.
              </p>
              <div className="verified">
                <I.BadgeCheck />
                <span>
                  <small>OFFICIAL EMAIL</small>
                  <b>{eligible.email}</b>
                </span>
              </div>
              <form onSubmit={submitRegister}>
                <label>
                  Create password
                  <input
                    type="password"
                    minLength={8}
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="At least 8 characters"
                    required
                  />
                </label>
                <Error text={error} />
                <button className="primary full" disabled={busy}>
                  {busy ? "Creating account…" : "Create my account"}
                  <I.ArrowRight />
                </button>
              </form>
            </>
          )}
          {view === "login" && (
            <>
              <button className="back" onClick={() => setView("choose")}>
                <I.ArrowLeft /> Back
              </button>
              <span className="eyebrow">WELCOME BACK</span>
              <h2>Sign in to ScholarHub</h2>
              <p className="muted">
                Use the email address registered with the university.
              </p>
              <form onSubmit={submitLogin}>
                <label>
                  Email address
                  <input
                    type="email"
                    value={email}
                    onChange={(e) => setEmail(e.target.value)}
                    placeholder="you@university.edu"
                    required
                  />
                </label>
                <label>
                  Password
                  <input
                    type="password"
                    value={password}
                    onChange={(e) => setPassword(e.target.value)}
                    placeholder="Your password"
                    required
                  />
                </label>
                <Error text={error} />
                <button className="primary full" disabled={busy}>
                  {busy ? "Signing in…" : "Sign in"}
                  <I.ArrowRight />
                </button>
              </form>
              <p className="auth-link">
                Forgot password?{" "}
                <button
                  disabled
                  title="No password reset endpoint is configured yet."
                >
                  Contact your administrator
                </button>
              </p>
            </>
          )}
        </div>
      </section>
    </div>
  );
}

function Error({ text }: { text: string }) {
  return text ? (
    <p className="form-error">
      <I.CircleAlert /> {text}
    </p>
  ) : null;
}

function Sidebar({
  session,
  page,
  onPage,
  onLogout,
}: {
  session: Session;
  page: Page;
  onPage: (p: Page) => void;
  onLogout: () => void;
}) {
  const isFaculty = session.profile.role === "faculty",
    isAdmin = session.profile.role === "admin",
    isCr = session.profile.role === "student";
  return (
    <aside className="sidebar">
      <div className="logo">
        <span className="brand-mark">
          <I.GraduationCap />
        </span>
        <span>
          ScholarHub<small>Academic Knowledge Hub</small>
        </span>
      </div>
      {(isFaculty || isCr) && (
        <button className="primary new-doc" onClick={() => onPage("upload")}>
          <I.Plus /> New Document
        </button>
      )}
      <nav>
        {nav.map((item) => {
          const Icon = item.icon;
          return (
            <button
              className={page === item.id ? "active" : ""}
              key={item.id}
              onClick={() => onPage(item.id)}
            >
              <Icon />
              {item.label}
            </button>
          );
        })}
        {isFaculty && (
          <>
            <span className="nav-label">FACULTY TOOLS</span>
            <button
              className={page === "upload" ? "active" : ""}
              onClick={() => onPage("upload")}
            >
              <I.Upload />
              Upload material
            </button>
            <button
              className={page === "draft" ? "active" : ""}
              onClick={() => onPage("draft")}
            >
              <I.FilePenLine />
              Draft notice
            </button>
          </>
        )}
        {isAdmin && (
          <>
            <span className="nav-label">ADMINISTRATION</span>
            <button
              className={page === "admin" ? "active" : ""}
              onClick={() => onPage("admin")}
            >
              <I.LayoutDashboard />
              Admin management
            </button>
          </>
        )}
      </nav>
      <div className="sidebar-bottom">
        <button>
          <I.Settings />
          Settings
        </button>
        <button onClick={onLogout}>
          <I.LogOut />
          Sign out
        </button>
      </div>
    </aside>
  );
}

function Topbar({
  session,
  onPage,
}: {
  session: Session;
  onPage: (p: Page) => void;
}) {
  return (
    <header className="topbar">
      <button className="mobile-logo" onClick={() => onPage("home")}>
        <I.GraduationCap />
      </button>
      <div className="top-search" onClick={() => onPage("ask")}>
        <I.Search />
        Search library or ask AI… <I.Sparkles />
      </div>
      <div className="top-links">
        <button onClick={() => onPage("ask")}>Research</button>
        <button onClick={() => onPage("subjects")}>Subjects</button>
        <button onClick={() => onPage("library")}>Archive</button>
      </div>
      <button className="icon-button">
        <I.Bell />
      </button>
      <button className="upgrade">Upgrade</button>
      <button
        className="avatar"
        title="Profile"
        onClick={() => onPage("profile")}
      >
        {initials(session.profile.full_name)}
      </button>
    </header>
  );
}

function PageView(props: {
  page: Page;
  setPage: (p: Page) => void;
  session: Session;
  documents: DocumentInfo[];
  setDocuments: (d: DocumentInfo[]) => void;
  docError: string;
}) {
  switch (props.page) {
    case "home":
      return <Home {...props} />;
    case "ask":
      return <Ask {...props} />;
    case "library":
      return <Library {...props} />;
    case "notices":
      return <Notices />;
    case "subjects":
      return <Subjects setPage={props.setPage} />;
    case "profile":
      return <Profile session={props.session} />;
    case "upload":
      return <Upload {...props} />;
    case "draft":
      return <Draft />;
    case "admin":
      return <Admin />;
  }
}
function Home({
  setPage,
  documents,
  docError,
}: {
  setPage: (p: Page) => void;
  documents: DocumentInfo[];
  docError: string;
}) {
  const [query, setQuery] = useState("");
  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      sessionStorage.setItem("scholarhub-query", query);
      setPage("ask");
    }
  };
  return (
    <div className="page home">
      <section className="hero">
        <h1>
          Everything your batch needs.
          <br />
          In one place.
        </h1>
        <p>
          Ask for notes, assignments, notices, PDFs, or anything uploaded for
          your course.
        </p>
        <form className="ask-bar" onSubmit={submit}>
          <I.Sparkles />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask anything about your course…"
          />
          <button aria-label="Ask AI">
            <I.ArrowUpRight />
          </button>
        </form>
        <div className="suggestions">
          {suggestions.map((q) => (
            <button
              key={q}
              onClick={() => {
                sessionStorage.setItem("scholarhub-query", q);
                setPage("ask");
              }}
            >
              {q}
            </button>
          ))}
        </div>
      </section>
      <SectionTitle
        icon={I.History}
        title="Latest for you"
        action="View all"
        onAction={() => setPage("library")}
      />
      {docError ? (
        <Empty message={docError} />
      ) : (
        <div className="latest-grid">
          {documents
            .slice(0, 3)
            .map((d) => <DocumentCard document={d} key={d.doc_id} />) || (
            <Empty message="No documents have been uploaded for your batch yet." />
          )}
        </div>
      )}
      <SectionTitle icon={I.Megaphone} title="Important notices" />
      <div className="notice-list">
        <Notice
          title="No notices are available yet"
          text="Published notices for your academic context will appear here."
          priority="info"
        />
      </div>
      <SectionTitle icon={I.Compass} title="Continue exploring" />
      <div className="subject-grid">
        {subjects.slice(0, 3).map((s, i) => (
          <button
            className="subject-card"
            key={s}
            onClick={() => setPage("subjects")}
          >
            <span className="subject-icon">
              {i === 1 ? <I.Bot /> : <I.Code2 />}
            </span>
            <b>{s}</b>
            <small>{i === 1 ? "ML-452" : "CS-401"} · View subject</small>
          </button>
        ))}
        <button
          className="subject-card outline"
          onClick={() => setPage("subjects")}
        >
          <I.ArrowRight />
          <b>View All Subjects</b>
        </button>
      </div>
    </div>
  );
}
function Ask({ documents }: { documents: DocumentInfo[] }) {
  const [messages, setMessages] = useState<ChatMessage[]>([]),
    [input, setInput] = useState(""),
    [sending, setSending] = useState(false);
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
    const user = { id: uid(), role: "user" as const, content: text },
      id = uid();
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

function Library({
  documents,
  docError,
}: {
  documents: DocumentInfo[];
  docError: string;
}) {
  const [search, setSearch] = useState(""),
    [filter, setFilter] = useState("All");
  const rows = useMemo(
    () =>
      documents.filter(
        (d) =>
          (filter === "All" || d.filetype.toUpperCase() === filter) &&
          d.filename.toLowerCase().includes(search.toLowerCase()),
      ),
    [documents, search, filter],
  );
  return (
    <div className="page">
      <h1>Document Library</h1>
      <p className="lede">
        Browse, filter, and manage your academic resources and notes.
      </p>
      <div className="library-tools">
        <label className="mini-search">
          <I.Search />
          <input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search documents"
          />
        </label>
        {["All", "PDF", "DOCX", "PPTX"].map((f) => (
          <button
            className={filter === f ? "selected" : ""}
            onClick={() => setFilter(f)}
            key={f}
          >
            {f === "All" ? "All Subjects" : f}
          </button>
        ))}
      </div>
      {docError ? (
        <Empty message={docError} />
      ) : (
        <div className="library-grid">
          {rows.map((d) => (
            <DocumentCard document={d} key={d.doc_id} />
          ))}
        </div>
      )}
      {!docError && rows.length === 0 && (
        <Empty message="No documents match this filter." />
      )}
    </div>
  );
}

function DocumentCard({ document }: { document: DocumentInfo }) {
  const ext = document.filetype.toUpperCase() || "FILE";
  return (
    <article className="doc-card">
      <div className={`doc-art ${document.filetype}`}>
        <I.FileText />
        <span>{ext} DOCUMENT</span>
      </div>
      <div className="doc-info">
        <h3 title={document.filename}>{document.filename}</h3>
        <div>
          <span className="tag">Course material</span>
          <span className="tag muted-tag">{ext}</span>
        </div>
        <footer>
          <span>
            <I.Clock />{" "}
            {document.uploaded_at
              ? new Date(document.uploaded_at).toLocaleDateString()
              : "Recently added"}
          </span>
          <button title="Opening original documents requires a signed file URL endpoint.">
            <I.MoreHorizontal />
          </button>
        </footer>
      </div>
    </article>
  );
}

function Notices() {
  return (
    <div className="page">
      <h1>Notices</h1>
      <p className="lede">
        Stay updated with important announcements for your batch.
      </p>
      <div className="library-tools">
        {["All", "Important", "Academic", "Assignments", "Events"].map(
          (x, i) => (
            <button className={i === 0 ? "selected" : ""} key={x}>
              {x}
            </button>
          ),
        )}
      </div>
      <div className="notice-list">
        <Notice
          title="No published notices"
          text="Notices will appear here once a faculty member publishes them for your batch."
          priority="info"
        />
      </div>
    </div>
  );
}

function Notice({
  title,
  text,
  priority,
}: {
  title: string;
  text: string;
  priority: "info" | "alert";
}) {
  return (
    <article className={`notice ${priority}`}>
      <I.Info />
      <div>
        <h3>{title}</h3>
        <p>{text}</p>
      </div>
    </article>
  );
}

function Subjects({ setPage }: { setPage: (p: Page) => void }) {
  return (
    <div className="page">
      <h1>My Subjects</h1>
      <p className="lede">
        Your enrolled Semester 5 subjects will be loaded from your academic
        profile.
      </p>
      <div className="subject-list">
        {subjects.map((s, i) => (
          <article key={s}>
            <span className="subject-icon">
              {i % 2 ? <I.Bot /> : <I.Code2 />}
            </span>
            <div>
              <h3>{s}</h3>
              <p>Semester 5 · BCA · Course resources and academic updates</p>
            </div>
            <button className="outline-btn" onClick={() => setPage("ask")}>
              Ask AI <I.ArrowRight />
            </button>
          </article>
        ))}
      </div>
      <p className="api-note">
        <I.Info /> Subject enrolment is shown from the initial academic context
        until a user-context API is available.
      </p>
    </div>
  );
}

function Profile({ session }: { session: Session }) {
  const p = session.profile;
  return (
    <div className="page profile">
      <section className="profile-hero">
        <div className="profile-avatar">
          {initials(p.full_name)}
          <span>
            <I.BadgeCheck />
          </span>
        </div>
        <div>
          <h1>{p.full_name}</h1>
          <p>
            {p.role[0].toUpperCase() + p.role.slice(1)}{" "}
            {p.role === "student" && "| BCA"}
          </p>
          <div className="chips">
            <span>
              <I.GraduationCap /> Verified{" "}
              {p.role[0].toUpperCase() + p.role.slice(1)}
            </span>
            {p.role === "student" && (
              <span>
                <I.CalendarDays /> Batch: 2024–27
              </span>
            )}
          </div>
        </div>
        <button className="outline-btn">
          <I.Pencil /> Edit profile
        </button>
      </section>
      <div className="profile-columns">
        <section className="panel">
          <PanelTitle icon={I.GraduationCap} title="Academic profile" />
          <div className="detail-grid">
            <div>
              <small>COURSE</small>
              <b>Bachelor of Computer Applications (BCA)</b>
            </div>
            <div>
              <small>CURRENT SEMESTER</small>
              <b>Semester 5</b>
            </div>
            <div>
              <small>BATCH</small>
              <b>24XBCA-1</b>
            </div>
            <div>
              <small>STUDENT ID</small>
              <b>Available from registry</b>
            </div>
          </div>
        </section>
        <section className="panel">
          <PanelTitle icon={I.UserRound} title="Account" />
          <div className="details">
            <div>
              <small>PRIMARY EMAIL</small>
              <b>{session.user.email}</b>
            </div>
            <div>
              <small>ROLE</small>
              <b>{p.role}</b>
            </div>
          </div>
        </section>
      </div>
      <div className="profile-columns">
        <section className="panel activity">
          <PanelTitle icon={I.ChartNoAxesCombined} title="Activity overview" />
          <div className="stat">
            <I.FileText />
            <span>Documents viewed</span>
            <b>—</b>
          </div>
          <div className="stat">
            <I.MessageSquare />
            <span>Questions asked</span>
            <b>—</b>
          </div>
        </section>
        <section className="panel">
          <PanelTitle icon={I.Bookmark} title="Saved content" />
          <Empty message="Saved documents and notices will appear here." />
        </section>
      </div>
      <section className="panel preferences">
        <PanelTitle icon={I.Settings} title="Settings & preferences" />
        <button>
          <I.Palette />
          <span>
            <b>Appearance</b>
            <small>Theme and display</small>
          </span>
          <I.ChevronRight />
        </button>
        <button>
          <I.Bell />
          <span>
            <b>Notifications</b>
            <small>Email and push alerts</small>
          </span>
          <I.ChevronRight />
        </button>
        <button>
          <I.ShieldCheck />
          <span>
            <b>Security</b>
            <small>Password and sessions</small>
          </span>
          <I.ChevronRight />
        </button>
      </section>
    </div>
  );
}

function Upload({
  documents,
  setDocuments,
}: {
  documents: DocumentInfo[];
  setDocuments: (docs: DocumentInfo[]) => void;
}) {
  const [files, setFiles] = useState<File[]>([]),
    [busy, setBusy] = useState(false),
    [message, setMessage] = useState("");
  const picker = useRef<HTMLInputElement>(null);
  const upload = async () => {
    if (!files.length) return;
    setBusy(true);
    setMessage("Uploading and processing document…");
    try {
      await documentApi.upload(files);
      setDocuments(await documentApi.list());
      setFiles([]);
      setMessage("Ready for search ✓");
    } catch (e: unknown) {
      setMessage(errorMessage(e, "Upload failed."));
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="page">
      <h1>Upload material</h1>
      <p className="lede">
        Add useful course materials for your permitted batches.
      </p>
      <div
        className="upload-zone"
        onDragOver={(e) => e.preventDefault()}
        onDrop={(e) => {
          e.preventDefault();
          setFiles(Array.from(e.dataTransfer.files));
        }}
        onClick={() => picker.current?.click()}
      >
        <I.UploadCloud />
        <h2>Drop files here or browse</h2>
        <p>PDF, DOCX, PPTX, and images · Maximum 25 MB per file</p>
        <input
          ref={picker}
          type="file"
          multiple
          accept=".pdf,.docx,.pptx,image/*"
          hidden
          onChange={(e) => setFiles(Array.from(e.target.files || []))}
        />
      </div>
      {files.length > 0 && (
        <div className="file-queue">
          {files.map((f) => (
            <div key={f.name}>
              <I.FileText />
              <span>
                {f.name}
                <small>{(f.size / 1024 / 1024).toFixed(1)} MB</small>
              </span>
              <button onClick={() => setFiles((p) => p.filter((x) => x !== f))}>
                <I.X />
              </button>
            </div>
          ))}
        </div>
      )}
      <div className="upload-meta">
        <label>
          Title
          <input placeholder="Use file name" />
        </label>
        <label>
          Category
          <select>
            <option>Course material</option>
            <option>Notes</option>
            <option>Assignment</option>
            <option>Notice</option>
          </select>
        </label>
        <label>
          Subject
          <select>
            <option>Select subject</option>
            {subjects.map((s) => (
              <option key={s}>{s}</option>
            ))}
          </select>
        </label>
      </div>
      <p className="api-note">
        <I.Info /> The current upload API accepts files only; title, category,
        subject, and batch metadata await an expanded secure upload contract.
      </p>
      {message && (
        <p className={message.includes("failed") ? "form-error" : "success"}>
          {message}
        </p>
      )}
      <button
        className="primary"
        disabled={!files.length || busy}
        onClick={upload}
      >
        {busy ? "Processing…" : "Upload material"}
        <I.Upload />
      </button>
    </div>
  );
}

function Draft() {
  return (
    <div className="page">
      <h1>Draft a notice</h1>
      <p className="lede">
        Create an announcement for the batches assigned to you.
      </p>
      <div className="draft panel">
        <label>
          Notice title
          <input placeholder="e.g. Assignment deadline extended" />
        </label>
        <label>
          Message
          <textarea
            rows={9}
            placeholder="Write the notice your students need to see…"
          />
        </label>
        <div className="upload-meta">
          <label>
            Priority
            <select>
              <option>Regular</option>
              <option>Important</option>
            </select>
          </label>
          <label>
            Distribute to
            <select>
              <option>Assigned batches — backend required</option>
            </select>
          </label>
        </div>
        <p className="api-note">
          <I.Info /> Draft persistence and publishing need a protected faculty
          notices API.
        </p>
        <div>
          <button className="outline-btn">Save draft</button>
          <button className="primary" disabled>
            Publish notice <I.Send />
          </button>
        </div>
      </div>
    </div>
  );
}
function Admin() {
  return (
    <div className="page">
      <h1>Admin management</h1>
      <p className="lede">
        Manage university records, academic contexts, and access controls.
      </p>
      <section className="panel" style={{ marginTop: "35px" }}>
        <PanelTitle icon={I.ShieldCheck} title="Administrative tools" />
        <Empty message="Admin management is ready for integration once protected administration APIs are available." />
      </section>
    </div>
  );
}

function SectionTitle({
  icon: Icon,
  title,
  action,
  onAction,
}: {
  icon: React.ElementType;
  title: string;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <div className="section-title">
      <h2>
        <Icon />
        {title}
      </h2>
      {action && <button onClick={onAction}>{action}</button>}
    </div>
  );
}

function PanelTitle({
  icon: Icon,
  title,
}: {
  icon: React.ElementType;
  title: string;
}) {
  return (
    <h2 className="panel-title">
      <Icon />
      {title}
    </h2>
  );
}

function Empty({ message }: { message: string }) {
  return (
    <div className="empty">
      <I.Inbox />
      <p>{message}</p>
    </div>
  );
}
export default App;
