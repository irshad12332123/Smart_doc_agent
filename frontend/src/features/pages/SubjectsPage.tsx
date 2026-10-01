import * as I from "lucide-react";
import type { Profile } from "../../types";
import type { Page } from "../../types/navigation";

export function SubjectsPage({
  profile,
  setPage,
}: {
  profile: Profile;
  setPage: (p: Page) => void;
}) {
  const subjects =
    profile.role === "student"
      ? profile.student_data.subjects
      : profile.role === "faculty"
        ? profile.faculty_data.courses.flatMap((course) =>
            course.batches.flatMap((batch) => batch.subjects),
          )
        : [];

  const uniqueSubjects = [
    ...new Map(subjects.map((subject) => [subject.id, subject])).values(),
  ];

  const icons = [I.Code2, I.Bot, I.Cpu, I.Layers, I.Database, I.Server];

  const handleAskAboutSubject = (subjectName: string) => {
    sessionStorage.setItem("scholarhub-query", `Show notes and summary for ${subjectName}`);
    setPage("ask");
  };

  return (
    <div className="page subjects-page">
      <div className="page-header">
        <div className="page-title-group">
          <h1>My Subjects & Courses</h1>
          <p className="lede">
            Curated coursework, syllabus modules, and verified academic references.
          </p>
        </div>
        <div className="page-stat-badge">
          <I.BookOpen />
          <span>{uniqueSubjects.length} Registered Subjects</span>
        </div>
      </div>

      {uniqueSubjects.length > 0 ? (
        <div className="subjects-grid">
          {uniqueSubjects.map((s, i) => {
            const Icon = icons[i % icons.length];
            return (
              <article className="subject-item-card" key={s.id}>
                <div className="subject-item-header">
                  <div className={`subject-icon-box idx-${i % 4}`}>
                    <Icon />
                  </div>
                  <span className="subject-code-pill">{s.subject_code}</span>
                </div>

                <div className="subject-item-body">
                  <h3>{s.name}</h3>
                  <p>Course notes, assignments, lab manuals, and exam guides.</p>
                </div>

                <div className="subject-item-footer">
                  <button
                    className="outline-btn subject-ask-btn"
                    onClick={() => handleAskAboutSubject(s.name)}
                  >
                    <I.Sparkles /> Ask AI
                  </button>
                  <button
                    className="icon-button subject-more-btn"
                    onClick={() => setPage("library")}
                    title="View related documents"
                  >
                    <I.ArrowRight />
                  </button>
                </div>
              </article>
            );
          })}
        </div>
      ) : (
        <div className="api-note">
          <I.Info /> No subjects are currently mapped to this profile. Contact your
          academic coordinator.
        </div>
      )}
    </div>
  );
}
