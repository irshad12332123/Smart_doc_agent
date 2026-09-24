import * as I from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import type { Session } from "../../types";
import type { Page } from "../../types/navigation";

const initials = (name: string) =>
  name
    .split(" ")
    .map((x) => x[0])
    .filter(Boolean)
    .join("")
    .slice(0, 2)
    .toUpperCase() || "SH";

export function Topbar({
  session,
  page,
  onPage,
}: {
  session: Session;
  page?: Page;
  onPage: (p: Page) => void;
}) {
  const { theme, toggleTheme } = useTheme();

  return (
    <header className="topbar">
      <button
        className="mobile-logo"
        onClick={() => onPage("home")}
        title="ScholarHub Home"
        aria-label="ScholarHub Home"
      >
        <span className="brand-mark">
          <I.GraduationCap />
        </span>
      </button>

      <div
        className="top-search"
        onClick={() => onPage("ask")}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") {
            onPage("ask");
          }
        }}
        title="Search library or ask AI"
      >
        <I.Search className="search-icon" />
        <span className="search-placeholder">
          Search course materials or ask AI…
        </span>
        <span className="search-shortcut">
          <I.Sparkles className="sparkle-icon" />
          <span>Ask AI</span>
        </span>
      </div>

      <nav className="top-links" aria-label="Top navigation">
        <button
          className={page === "ask" ? "active" : ""}
          onClick={() => onPage("ask")}
        >
          <I.Sparkles /> AI Assistant
        </button>
        <button
          className={page === "subjects" ? "active" : ""}
          onClick={() => onPage("subjects")}
        >
          <I.BookOpen /> Subjects
        </button>
        <button
          className={page === "library" ? "active" : ""}
          onClick={() => onPage("library")}
        >
          <I.Library /> Library
        </button>
      </nav>

      <div className="topbar-actions">
        {/* Theme Toggle Button */}
        <button
          className="theme-toggle-btn"
          onClick={toggleTheme}
          title={theme === "dark" ? "Switch to Light Theme" : "Switch to Dark Theme"}
          aria-label={
            theme === "dark" ? "Switch to Light Theme" : "Switch to Dark Theme"
          }
        >
          {theme === "dark" ? (
            <I.Sun className="theme-icon sun-icon" />
          ) : (
            <I.Moon className="theme-icon moon-icon" />
          )}
        </button>

        {/* Notifications Button */}
        <button
          className="icon-button top-notif-btn"
          onClick={() => onPage("notices")}
          title="Notices and announcements"
          aria-label="Notices"
        >
          <I.Bell />
          <span className="notif-dot" />
        </button>

        {/* Profile Avatar Button */}
        <button
          className="avatar"
          title={`Profile: ${session.profile.full_name}`}
          onClick={() => onPage("profile")}
          aria-label="Open profile"
        >
          <span className="avatar-initials">
            {initials(session.profile.full_name)}
          </span>
          <span className="avatar-badge-dot" />
        </button>
      </div>
    </header>
  );
}
