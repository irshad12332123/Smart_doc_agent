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
  return (
    <div className="page">
      <h1>My Subjects</h1>
      <p className="lede">Subjects available in your academic profile.</p>
      <div className="subject-list">
        {uniqueSubjects.map((s, i) => (
          <article key={s.id}>
            <span className="subject-icon">
              {i % 2 ? <I.Bot /> : <I.Code2 />}
            </span>
            <div>
              <h3>{s.name}</h3>
              <p>{s.subject_code} · Course resources and academic updates</p>
            </div>
            <button className="outline-btn" onClick={() => setPage("ask")}>
              Ask AI <I.ArrowRight />
            </button>
          </article>
        ))}
      </div>
      {!uniqueSubjects.length && (
        <p className="api-note">
          <I.Info /> No subjects are assigned to this profile.
        </p>
      )}
    </div>
  );
}
