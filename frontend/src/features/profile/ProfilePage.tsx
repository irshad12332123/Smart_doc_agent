import * as I from "lucide-react";
import { useTheme } from "../../context/ThemeContext";
import type { Session } from "../../types";
import { Empty, PanelTitle } from "../../components/ui/common";

const initials = (name: string) =>
  name
    .split(" ")
    .map((x) => x[0])
    .filter(Boolean)
    .join("")
    .slice(0, 2)
    .toUpperCase() || "SH";

export function ProfilePage({ session }: { session: Session }) {
  const { theme, toggleTheme } = useTheme();
  const p = session.profile;
  const isStudent = p.role === "student";
  const studentMeta = isStudent ? p.student_data : undefined;

  return (
    <div className="page profile-page">
      <section className="profile-hero-card">
        <div className="profile-avatar-container">
          <div className="profile-avatar-circle">
            {initials(p.full_name)}
          </div>
          <div className="profile-verified-badge" title="University verified user">
            <I.BadgeCheck />
          </div>
        </div>

        <div className="profile-hero-info">
          <div className="profile-name-row">
            <h1>{p.full_name}</h1>
            <span className="role-tag-badge">
              {p.role[0].toUpperCase() + p.role.slice(1)}
            </span>
          </div>

          <p className="profile-subtitle">
            {studentMeta
              ? `${studentMeta.course_name} · Semester ${studentMeta.current_semester}`
              : `${p.role[0].toUpperCase() + p.role.slice(1)} Academic Member`}
          </p>

          <div className="chips">
            <span className="chip-item">
              <I.GraduationCap /> Verified {p.role}
            </span>
            {studentMeta && (
              <span className="chip-item">
                <I.CalendarDays /> Batch: {studentMeta.batch_code}
              </span>
            )}
            {studentMeta?.student_role && (
              <span className="chip-item chip-highlight">
                <I.ShieldAlert /> {studentMeta.student_role}
              </span>
            )}
          </div>
        </div>

        <div className="profile-hero-action">
          <button className="outline-btn">
            <I.Pencil /> Edit Details
          </button>
        </div>
      </section>

      <div className="profile-columns">
        <section className="panel">
          <PanelTitle icon={I.GraduationCap} title="Academic Profile" />
          <div className="detail-grid">
            <div className="detail-item">
              <span className="detail-label">PROGRAM / COURSE</span>
              <strong className="detail-val">
                {studentMeta?.course_name ?? "Not applicable"}
              </strong>
            </div>
            <div className="detail-item">
              <span className="detail-label">CURRENT SEMESTER</span>
              <strong className="detail-val">
                {studentMeta
                  ? `Semester ${studentMeta.current_semester}`
                  : "N/A"}
              </strong>
            </div>
            <div className="detail-item">
              <span className="detail-label">BATCH CODE</span>
              <strong className="detail-val">
                {studentMeta?.batch_code ?? "N/A"}
              </strong>
            </div>
            <div className="detail-item">
              <span className="detail-label">STUDENT ID</span>
              <strong className="detail-val">
                {studentMeta?.student_id || p.id || "Registry Record"}
              </strong>
            </div>
          </div>
        </section>

        <section className="panel">
          <PanelTitle icon={I.UserRound} title="Account Information" />
          <div className="details-vertical">
            <div className="detail-item">
              <span className="detail-label">PRIMARY EMAIL</span>
              <strong className="detail-val">{session.user.email}</strong>
            </div>
            <div className="detail-item">
              <span className="detail-label">ACCOUNT ROLE</span>
              <strong className="detail-val">
                {p.role.toUpperCase()}
              </strong>
            </div>
            {studentMeta?.registered_email && (
              <div className="detail-item">
                <span className="detail-label">REGISTRY EMAIL</span>
                <strong className="detail-val">
                  {studentMeta.registered_email}
                </strong>
              </div>
            )}
          </div>
        </section>
      </div>

      <div className="profile-columns">
        <section className="panel activity-panel">
          <PanelTitle icon={I.ChartNoAxesCombined} title="Activity & Analytics" />
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-icon-wrap stat-blue">
                <I.FileText />
              </div>
              <div className="stat-info">
                <span className="stat-label">Indexed Documents</span>
                <strong className="stat-number">Active</strong>
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-icon-wrap stat-purple">
                <I.MessageSquare />
              </div>
              <div className="stat-info">
                <span className="stat-label">AI Queries</span>
                <strong className="stat-number">Available</strong>
              </div>
            </div>
          </div>
        </section>

        <section className="panel">
          <PanelTitle icon={I.Bookmark} title="Saved Materials" />
          <Empty message="Bookmarked documents and notes will appear here." />
        </section>
      </div>

      <section className="panel preferences-panel">
        <PanelTitle icon={I.Settings} title="Settings & Preferences" />
        <div className="preferences-grid">
          {/* Interactive Appearance Toggle */}
          <button
            className="pref-card pref-interactive"
            onClick={toggleTheme}
            title="Toggle theme"
          >
            <div className="pref-icon-box">
              {theme === "dark" ? <I.Moon /> : <I.Sun />}
            </div>
            <div className="pref-meta">
              <strong>Appearance</strong>
              <small>
                Current theme: <b>{theme === "dark" ? "Dark Mode" : "Light Mode"}</b> (Click to toggle)
              </small>
            </div>
            <span className={`theme-toggle-pill ${theme === "dark" ? "on" : ""}`}>
              <span className="theme-toggle-thumb" />
            </span>
          </button>

          <button className="pref-card">
            <div className="pref-icon-box">
              <I.ShieldCheck />
            </div>
            <div className="pref-meta">
              <strong>Security & Session</strong>
              <small>Active tokens and passwords</small>
            </div>
            <I.ChevronRight className="pref-arrow" />
          </button>
        </div>
      </section>
    </div>
  );
}
