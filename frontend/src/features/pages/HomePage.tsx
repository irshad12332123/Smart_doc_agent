import { useState } from "react";
import * as I from "lucide-react";
import type { DocumentInfo } from "../../types";
import type { Page } from "../../types/navigation";
import {
  DocumentCard,
  Empty,
  SectionTitle,
  SubjectCard,
} from "../../components/ui/common";

const suggestions = [
  { text: "Find my pending assignments", icon: I.FileCheck2 },
  { text: "Show Machine Learning notes", icon: I.BrainCircuit },
  { text: "Find Software Engineering PDFs", icon: I.BookOpen },
];

const subjects = [
  { name: "Software Engineering & Testing", code: "CS-401" },
  { name: "Machine Learning & NLP on AWS", code: "ML-452" },
  { name: "Multimedia & Animation", code: "MM-303" },
  { name: "Internet of Things (IoT)", code: "IT-404" },
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
      sessionStorage.setItem("scholarhub-query", query.trim());
      setPage("ask");
    }
  };

  const handleSuggestionClick = (text: string) => {
    sessionStorage.setItem("scholarhub-query", text);
    setPage("ask");
  };

  return (
    <div className="page home-page">
      <section className="hero">
        <div className="hero-badge">
          <I.Sparkles className="hero-badge-icon" />
          <span>Academic workspace</span>
        </div>
        <h1 className="hero-title">Your academic workspace</h1>
        <p className="hero-subtitle">
          Search verified course materials and get AI answers grounded in your documents.
        </p>

        <form className="ask-bar" onSubmit={submit}>
          <div className="ask-bar-icon">
            <I.Sparkles />
          </div>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Ask anything about your course, exams, or assignments…"
            aria-label="Ask AI about course material"
          />
          <button
            type="submit"
            className="ask-bar-submit"
            aria-label="Submit search"
            disabled={!query.trim()}
          >
            <span>Ask AI</span>
            <I.ArrowUpRight />
          </button>
        </form>

        <div className="suggestions">
          <span className="suggestions-label">Try asking:</span>
          {suggestions.map((item) => {
            const Icon = item.icon;
            return (
              <button
                key={item.text}
                className="suggestion-chip"
                onClick={() => handleSuggestionClick(item.text)}
              >
                <Icon className="chip-icon" />
                <span>{item.text}</span>
              </button>
            );
          })}
        </div>
      </section>

      {/* Latest Documents Section */}
      <section className="home-section">
        <SectionTitle
          icon={I.Clock}
          title="Latest for your batch"
          action="View library"
          onAction={() => setPage("library")}
        />
        {docError ? (
          <Empty message={docError} />
        ) : documents.length === 0 ? (
          <Empty
            message="No documents have been uploaded for your batch yet."
            actionLabel="Go to Upload"
            onAction={() => setPage("upload")}
          />
        ) : (
          <div className="latest-grid">
            {documents.slice(0, 3).map((d) => (
              <DocumentCard document={d} key={d.doc_id} />
            ))}
          </div>
        )}
      </section>

      {/* Explore Subjects Section */}
      <section className="home-section">
        <SectionTitle
          icon={I.BookOpen}
          title="Continue exploring subjects"
          action="View all subjects"
          onAction={() => setPage("subjects")}
        />
        <div className="subject-grid">
          {subjects.map((s, i) => (
            <SubjectCard
              key={s.code}
              title={s.name}
              code={s.code}
              iconIndex={i}
              onClick={() => setPage("subjects")}
            />
          ))}
          <button
            className="subject-card subject-card-cta"
            onClick={() => setPage("subjects")}
          >
            <div className="cta-icon-box">
              <I.ArrowRight />
            </div>
            <div className="subject-card-content">
              <h3 className="subject-name">Browse All Subjects</h3>
              <p className="subject-subtext">
                Access full syllabus, textbooks, and past materials
              </p>
            </div>
          </button>
        </div>
      </section>
    </div>
  );
}
