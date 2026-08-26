import { useEffect, useMemo, useRef, useState } from "react";
import * as I from "lucide-react";
import { documentApi, streamChat, userApi } from "./api/client";
import type { ChatMessage, DocumentInfo, Session } from "./types";
import type { Page } from "./types/navigation";
import { Sidebar } from "./components/layout/Sidebar";
import { Topbar } from "./components/layout/Topbar";
import { Auth } from "./features/auth/Auth";
import { ProfilePage } from "./features/profile/ProfilePage";
import { Empty, PanelTitle, SectionTitle } from "./components/ui/common";

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
      userApi
        .profile(stored.access_token)
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
      return <ProfilePage session={props.session} />;
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
export default App;
