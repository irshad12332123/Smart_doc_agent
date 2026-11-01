import * as I from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import type { Session } from "../../types";
import type { Page } from "../../types/navigation";
import { nav } from "../../types/navigation";

export function Sidebar({
  session,
  page,
  onPage,
  onLogout,
  mobileOpen,
}: {
  session: Session;
  page: Page;
  onPage: (p: Page) => void;
  onLogout: () => void;
  mobileOpen?: boolean;
}) {
  const { theme, toggleTheme } = useTheme();
  const isFaculty = session.profile.role === "faculty";
  const isAdmin = session.profile.role === "admin";
  const isCr = session.profile.role === "student";

  return (
    <aside className={`sidebar ${mobileOpen ? "mobile-open" : ""}`}>
      <div
        className="logo"
        onClick={() => onPage("home")}
        onKeyDown={(e) => {
          if (e.key === "Enter" || e.key === " ") onPage("home");
        }}
        role="button"
        tabIndex={0}
      >
        <span className="brand-mark">
          <I.GraduationCap />
        </span>
        <div className="logo-text">
          <span className="brand-title">ScholarHub</span>
          <span className="brand-subtitle">Academic Knowledge Hub</span>
        </div>
      </div>

      {(isFaculty || isCr) && (
        <button className="primary new-doc-btn" onClick={() => onPage("upload")}>
          <I.Plus className="icon-plus" />
          <span>New Document</span>
        </button>
      )}

      <nav className="sidebar-nav" aria-label="Main Navigation">
        <span className="nav-label">MAIN MENU</span>
        {nav.map((item) => {
          const Icon =
            item.id === "home"
              ? I.House
              : item.id === "ask"
                ? I.Sparkles
                : item.id === "library"
                  ? I.Library
                  : item.id === "notices"
                    ? I.Bell
                    : item.id === "subjects"
                      ? I.BookOpen
                      : I.UserRound;

          const isActive = page === item.id;

          return (
            <button
              className={`nav-item ${isActive ? "active" : ""}`}
              key={item.id}
              onClick={() => onPage(item.id)}
            >
              <span className="nav-icon-box">
                <Icon />
              </span>
              <span className="nav-text">{item.label}</span>
              {item.id === "ask" && <span className="nav-pill-ai">AI</span>}
            </button>
          );
        })}

        {isFaculty && (
          <div className="nav-group">
            <span className="nav-label">FACULTY TOOLS</span>
            <button
              className={`nav-item ${page === "upload" ? "active" : ""}`}
              onClick={() => onPage("upload")}
            >
              <span className="nav-icon-box">
                <I.UploadCloud />
              </span>
              <span className="nav-text">Upload material</span>
            </button>
            <button
              className={`nav-item ${page === "draft" ? "active" : ""}`}
              onClick={() => onPage("draft")}
            >
              <span className="nav-icon-box">
                <I.FilePenLine />
              </span>
              <span className="nav-text">Draft notice</span>
            </button>
          </div>
        )}

        {isAdmin && (
          <div className="nav-group">
            <span className="nav-label">ADMINISTRATION</span>
            <button
              className={`nav-item ${page === "admin" ? "active" : ""}`}
              onClick={() => onPage("admin")}
            >
              <span className="nav-icon-box">
                <I.ShieldCheck />
              </span>
              <span className="nav-text">Admin control</span>
            </button>
          </div>
        )}
      </nav>

      <div className="sidebar-bottom">
        {/* Quick Theme Switcher */}
        <button
          className="theme-switch-row"
          onClick={toggleTheme}
          title={`Switch to ${theme === "dark" ? "Light" : "Dark"} Mode`}
        >
          <span className="nav-icon-box">
            {theme === "dark" ? <I.Sun /> : <I.Moon />}
          </span>
          <span className="nav-text">
            {theme === "dark" ? "Light Theme" : "Dark Theme"}
          </span>
          <span className={`theme-toggle-pill ${theme === "dark" ? "on" : ""}`}>
            <span className="theme-toggle-thumb" />
          </span>
        </button>

        <button className="nav-item" onClick={() => onPage("profile")}>
          <span className="nav-icon-box">
            <I.Settings />
          </span>
          <span className="nav-text">Settings</span>
        </button>

        <button className="nav-item logout-btn" onClick={onLogout}>
          <span className="nav-icon-box">
            <I.LogOut />
          </span>
          <span className="nav-text">Sign out</span>
        </button>
      </div>
    </aside>
  );
}
