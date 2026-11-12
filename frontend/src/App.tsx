import { useCallback, useEffect, useState } from "react";
import * as I from "lucide-react";
import { userApi } from "./api/client";
import type { Profile, Session } from "./types";
import type { Page } from "./types/navigation";
import { Sidebar } from "./components/layout/Sidebar";
import { Topbar } from "./components/layout/Topbar";
import { Auth } from "./features/auth/Auth";
import { AdminPage } from "./features/pages/AdminPage";
import { AskPage } from "./features/pages/AskPage";
import { HomePage } from "./features/pages/HomePage";
import { LibraryPage } from "./features/pages/LibraryPage";
import { SubjectsPage } from "./features/pages/SubjectsPage";
import { UploadPage } from "./features/pages/UploadPage";
import { ProfilePage } from "./features/profile/ProfilePage";
import { LandingPage } from "./features/landing/LandingPage";

function App() {
  const [session, setSession] = useState<Session | null>(null);
  const [checking, setChecking] = useState(true);
  const [page, setPage] = useState<Page>("home");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null);
  const [profileLoading, setProfileLoading] = useState(false);
  const [profileRequested, setProfileRequested] = useState(false);
  const [profileError, setProfileError] = useState("");
  const [showAuth, setShowAuth] = useState(false);

  useEffect(() => {
    const saved = localStorage.getItem("scholarhub-session");
    if (!saved) return setChecking(false);

    try {
      const stored = JSON.parse(saved) as Partial<Session> & {
        access_token?: string;
      };
      if (!stored.access_token) throw new Error("Stored session is incomplete");
      userApi
        .summary(stored.access_token)
        .then(({ user, summary }) => {
          setProfile(null);
          setProfileRequested(false);
          setSession({
            access_token: stored.access_token!,
            refresh_token: stored.refresh_token,
            expires_at: stored.expires_at,
            user,
            summary,
          });
        })
        .catch(() => localStorage.removeItem("scholarhub-session"))
        .finally(() => setChecking(false));
    } catch {
      setChecking(false);
    }
  }, []);

  const signIn = (next: Session) => {
    localStorage.setItem("scholarhub-session", JSON.stringify(next));
    setProfile(null);
    setProfileRequested(false);
    setProfileError("");
    setSession(next);
  };

  const loadProfile = useCallback(async () => {
    if (!session || profileRequested) return;

    setProfileRequested(true);
    setProfileError("");

    const cacheKey = `scholarhub-profile-${session.summary.id}`;
    const cached = localStorage.getItem(cacheKey);
    if (cached) {
      try {
        setProfile(JSON.parse(cached) as Profile);
      } catch {
        localStorage.removeItem(cacheKey);
      }
    }

    setProfileLoading(true);
    try {
      const result = await userApi.profile(session.access_token);
      setProfile(result.profile);
      localStorage.setItem(cacheKey, JSON.stringify(result.profile));
    } catch {
      if (!cached) setProfileError("Profile data could not be loaded.");
    } finally {
      setProfileLoading(false);
    }
  }, [profileRequested, session]);

  const profileRequired = ["subjects", "profile", "upload"].includes(page);

  useEffect(() => {
    if (session && profileRequired && !profile && !profileLoading) {
      void loadProfile();
    }
  }, [loadProfile, page, profile, profileLoading, profileRequired, session]);

  const logout = () => {
    if (session?.summary.id) {
      localStorage.removeItem(`scholarhub_chat_history_${session.summary.id}`);
      localStorage.removeItem(`scholarhub-profile-${session.summary.id}`);
    }
    localStorage.removeItem("scholarhub_chat_history");
    localStorage.removeItem("scholarhub-session");
    setProfile(null);
    setProfileRequested(false);
    setSession(null);
    setShowAuth(false);
    setPage("home");
    setSidebarOpen(false);
  };

  const navigate = (nextPage: Page) => {
    setPage(nextPage);
    setSidebarOpen(false);
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

  if (!session && !showAuth) {
    return <LandingPage onGetStarted={() => setShowAuth(true)} onLogin={() => setShowAuth(true)} />;
  }

  if (!session) return <Auth onSession={signIn} onBackToLanding={() => setShowAuth(false)} />;

  const profilePageLoading = profileRequired && !profile;

  return (
    <div className={`shell ${page === "ask" ? "shell-chat" : ""}`}>
      <Sidebar
        summary={session.summary}
        page={page}
        onPage={navigate}
        onLogout={logout}
        mobileOpen={sidebarOpen}
      />
      {sidebarOpen && (
        <button
          className="sidebar-backdrop"
          type="button"
          aria-label="Close navigation"
          onClick={() => setSidebarOpen(false)}
        />
      )}
      <main className={`main ${page === "ask" ? "main-chat" : ""}`}>
        <Topbar
          summary={session.summary}
          page={page}
          onPage={navigate}
          onToggleSidebar={() => setSidebarOpen((open) => !open)}
          sidebarOpen={sidebarOpen}
        />
        <div className={`content-area ${page === "ask" ? "content-area-chat" : ""}`}>
          {profilePageLoading ? (
            <div className="page">
              <div className="api-note">
                {profileLoading
                  ? "Loading workspace details…"
                  : profileError || "Workspace details are unavailable."}
              </div>
            </div>
          ) : (
            <PageView
              page={page}
              setPage={setPage}
              profile={profile}
              email={session.user.email}
              userName={session.summary?.full_name}
              userId={session.summary?.id || session.user?.id}
            />
          )}
        </div>
      </main>
    </div>
  );
}

function PageView(props: {
  page: Page;
  setPage: (p: Page) => void;
  profile: Profile | null;
  email: string;
  userName?: string;
  userId?: string;
}) {
  switch (props.page) {
    case "home":
      return <HomePage {...props} />;
    case "ask":
      return (
        <AskPage
          profile={props.profile || undefined}
          userName={props.userName}
          userId={props.userId}
        />
      );
    case "library":
      return <LibraryPage />;
    case "subjects":
      return <SubjectsPage profile={props.profile!} setPage={props.setPage} />;
    case "profile":
      return <ProfilePage profile={props.profile!} email={props.email} />;
    case "upload":
      return <UploadPage profile={props.profile!} />;
    case "admin":
      return <AdminPage />;
  }
}

export default App;
