import { useEffect, useState } from "react";
import * as I from "lucide-react";
import { documentApi, userApi } from "./api/client";
import type { DocumentInfo, Session } from "./types";
import type { Page } from "./types/navigation";
import { Sidebar } from "./components/layout/Sidebar";
import { Topbar } from "./components/layout/Topbar";
import { Auth } from "./features/auth/Auth";
import { AdminPage } from "./features/pages/AdminPage";
import { AskPage } from "./features/pages/AskPage";
import { DraftPage } from "./features/pages/DraftPage";
import { HomePage } from "./features/pages/HomePage";
import { LibraryPage } from "./features/pages/LibraryPage";
import { NoticesPage } from "./features/pages/NoticesPage";
import { SubjectsPage } from "./features/pages/SubjectsPage";
import { UploadPage } from "./features/pages/UploadPage";
import { ProfilePage } from "./features/profile/ProfilePage";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [checking, setChecking] = useState(true);
  const [page, setPage] = useState<Page>("home");
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [docError, setDocError] = useState("");

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
    if (session?.profile?.id) {
      localStorage.removeItem(`scholarhub_chat_history_${session.profile.id}`);
    }
    localStorage.removeItem("scholarhub_chat_history");
    localStorage.removeItem("scholarhub-session");
    setSession(null);
    setPage("home");
  };

  if (checking) {
    return (
      <div className="splash">
        <div className="brand-mark splash-icon">
          <I.GraduationCap />
        </div>
        <div className="splash-loader">
          <div className="spinner" />
          <span>Loading ScholarHub…</span>
        </div>
      </div>
    );
  }

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
        <Topbar session={session} page={page} onPage={setPage} />
        <div className="content-area">
          <PageView
            page={page}
            setPage={setPage}
            session={session}
            documents={documents}
            setDocuments={setDocuments}
            docError={docError}
          />
        </div>
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
      return <HomePage {...props} />;
    case "ask":
      return (
        <AskPage
          documents={props.documents}
          profile={props.session.profile}
        />
      );
    case "library":
      return (
        <LibraryPage documents={props.documents} docError={props.docError} />
      );
    case "notices":
      return <NoticesPage />;
    case "subjects":
      return (
        <SubjectsPage profile={props.session.profile} setPage={props.setPage} />
      );
    case "profile":
      return <ProfilePage session={props.session} />;
    case "upload":
      return (
        <UploadPage
          profile={props.session.profile}
          documents={props.documents}
          setDocuments={props.setDocuments}
        />
      );
    case "draft":
      return <DraftPage />;
    case "admin":
      return <AdminPage />;
  }
}

export default App;
