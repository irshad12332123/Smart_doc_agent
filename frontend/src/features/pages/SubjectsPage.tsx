import * as I from "lucide-react";
import type { Page } from "../../types/navigation";

const subjects = [
  "Software Engineering and Testing",
  "Machine Learning and NLP on AWS Cloud",
  "Multimedia and Animation",
  "Internet of Things (IoT)",
  "Software Engineering and Testing Lab",
  "Machine Learning and NLP on AWS Cloud Lab",
  "Project-II",
];

export function SubjectsPage({ setPage }: { setPage: (p: Page) => void }) {
  return (
    <div className="page">
      <h1>My Subjects</h1>
      <p className="lede">
        Your enrolled Semester 5 subjects will be loaded from your academic profile.
      </p>
      <div className="subject-list">
        {subjects.map((s, i) => (
          <article key={s}>
            <span className="subject-icon">
              {i % 2 ? <I.Bot /> : <I.Code2 />}
            </span>
            <div>
              <h3>{s}</h3>
              <p>Semester 5 · BCA · Course resources and academic updates</p>
            </div>
            <button className="outline-btn" onClick={() => setPage("ask")}>
              Ask AI <I.ArrowRight />
            </button>
          </article>
        ))}
      </div>
      <p className="api-note">
        <I.Info /> Subject enrolment is shown from the initial academic context
        until a user-context API is available.
      </p>
    </div>
  );
}
