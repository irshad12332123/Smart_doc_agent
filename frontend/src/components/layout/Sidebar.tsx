import * as I from "lucide-react";
import type { Session } from "../../types";
import type { Page } from "../../types/navigation";
import { nav } from "../../types/navigation";

export function Sidebar({
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
  const isFaculty = session.profile.role === "faculty";
  const isAdmin = session.profile.role === "admin";
  const isCr = session.profile.role === "student";

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
                      ? I.GraduationCap
                      : I.UserRound;

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
