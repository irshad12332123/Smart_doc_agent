import { useState } from "react";
import * as I from "lucide-react";
import type { DocumentInfo } from "../../types";
import type { Page } from "../../types/navigation";
import { DocumentCard, Empty, Notice, SectionTitle } from "../../components/ui/common";

const suggestions = [
  "Find my pending assignments",
  "Show Machine Learning notes",
  "What are the latest notices?",
  "Find Software Engineering PDFs",
];

const subjects = [
  "Software Engineering and Testing",
  "Machine Learning and NLP on AWS Cloud",
  "Multimedia and Animation",
  "Internet of Things (IoT)",
  "Software Engineering and Testing Lab",
  "Machine Learning and NLP on AWS Cloud Lab",
  "Project-II",
];

export function HomePage({
  setPage,
  documents,
  docError,
}: {
  setPage: (p: Page) => void;
  documents: DocumentInfo[];
  docError: string;
}) {
  const [query, setQuery] = useState("");

  const submit = (e: React.FormEvent) => {
    e.preventDefault();
    if (query.trim()) {
      sessionStorage.setItem("scholarhub-query", query);
      setPage("ask");
    }
  };

  return (
    <div className="page home">
      <section className="hero">
        <h1>
          Everything your batch needs.
          <br />
          In one place.
        </h1>
        <p>
          Ask for notes, assignments, notices, PDFs, or anything uploaded for
          your course.
        </p>
        <form className="ask-bar" onSubmit={submit}>
          <I.Sparkles />
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask anything about your course…"
          />
          <button aria-label="Ask AI">
            <I.ArrowUpRight />
          </button>
        </form>
        <div className="suggestions">
          {suggestions.map((q) => (
            <button
              key={q}
              onClick={() => {
                sessionStorage.setItem("scholarhub-query", q);
                setPage("ask");
              }}
            >
              {q}
            </button>
          ))}
        </div>
      </section>

      <SectionTitle
        icon={I.History}
        title="Latest for you"
        action="View all"
        onAction={() => setPage("library")}
      />
      {docError ? (
        <Empty message={docError} />
      ) : (
        <div className="latest-grid">
          {documents.slice(0, 3).map((d) => (
            <DocumentCard document={d} key={d.doc_id} />
          ))}
          {documents.length === 0 && (
            <Empty message="No documents have been uploaded for your batch yet." />
          )}
        </div>
      )}

      <SectionTitle icon={I.Megaphone} title="Important notices" />
      <div className="notice-list">
        <Notice
          title="No notices are available yet"
          text="Published notices for your academic context will appear here."
          priority="info"
        />
      </div>

      <SectionTitle icon={I.Compass} title="Continue exploring" />
      <div className="subject-grid">
        {subjects.slice(0, 3).map((s, i) => (
          <button
            className="subject-card"
            key={s}
            onClick={() => setPage("subjects")}
          >
            <span className="subject-icon">
              {i === 1 ? <I.Bot /> : <I.Code2 />}
            </span>
            <b>{s}</b>
            <small>{i === 1 ? "ML-452" : "CS-401"} · View subject</small>
          </button>
        ))}
        <button
          className="subject-card outline"
          onClick={() => setPage("subjects")}
        >
          <I.ArrowRight />
          <b>View All Subjects</b>
        </button>
      </div>
    </div>
  );
}
