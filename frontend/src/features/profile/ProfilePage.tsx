import * as I from "lucide-react";
import type { Session } from "../../types";
import { Empty, PanelTitle } from "../../components/ui/common";

const initials = (name: string) =>
  name
    .split(" ")
    .map((x) => x[0])
    .join("")
    .slice(0, 2)
    .toUpperCase();

export function ProfilePage({ session }: { session: Session }) {
  const p = session.profile;
  const isStudent = p.role === "student";
  const studentMeta = isStudent ? p.student_data : undefined;
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
            {p.role[0].toUpperCase() + p.role.slice(1)}
            {studentMeta && " | " + studentMeta.course_name}
          </p>
          <div className="chips">
            <span>
              <I.GraduationCap /> Verified{" "}
              {p.role[0].toUpperCase() + p.role.slice(1)}
            </span>
            {studentMeta && (
              <span>
                <I.CalendarDays /> Batch: {studentMeta.batch_code}
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
              <b>{studentMeta?.course_name ?? "N/A"}</b>
            </div>
            <div>
              <small>CURRENT SEMESTER</small>
              <b>
                {studentMeta
                  ? `Semester ${studentMeta.current_semester}`
                  : "N/A"}
              </b>
            </div>
            <div>
              <small>BATCH</small>
              <b>{studentMeta?.batch_code ?? "N/A"}</b>
            </div>
            <div>
              <small>STUDENT ID</small>
              <b>
                {typeof p.id === "string" && p.id
                  ? p.id
                  : "Available from registry"}
              </b>
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
            {studentMeta?.student_role && (
              <div>
                <small>STUDENT ROLE</small>
                <b>{studentMeta.student_role}</b>
              </div>
            )}
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
