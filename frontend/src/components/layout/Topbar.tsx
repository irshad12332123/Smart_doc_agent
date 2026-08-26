import * as I from "lucide-react";
import type { Session } from "../../types";
import type { Page } from "../../types/navigation";

const initials = (name: string) =>
  name
    .split(" ")
    .map((x) => x[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

export function Topbar({
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
