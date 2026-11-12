import * as I from "lucide-react";
import type { ReactNode } from "react";

const resources = [
  ["Operating Systems", "12 files"],
  ["Computer Networks", "8 files"],
  ["Database Management Systems", "15 files"],
];

export function LandingFeatures() {
  return (
    <section className="landing-section landing-features" id="features">
      <div className="landing-container">
        <div className="landing-section-heading">
          <span className="landing-eyebrow">Workspace architecture</span>
          <h2>Everything you need to study, in one place.</h2>
          <p>From finding the right material to understanding difficult concepts without friction.</p>
        </div>

        <div className="landing-bento-grid">
          <article className="landing-feature-card landing-feature-card-wide">
            <FeatureHeading label="Direct cited reasoning" icon={<I.BadgeCheck />} />
            <h3>AI Academic Assistant</h3>
            <p>Ask nuanced conceptual questions. ScholarHub anchors each premise directly to your lecture slides and primary textbooks.</p>
            <div className="landing-answer-snippet">
              <div className="landing-snippet-meta"><span>QUERY STREAM #8492</span><b>Latency: 140ms</b></div>
              <div className="landing-question"><strong>Q:</strong> Does Banker&apos;s Algorithm prevent deadlock or avoid it?</div>
              <div className="landing-answer"><strong>It is an <em>avoidance</em> algorithm.</strong><span>It examines the resource-allocation state to ensure a safe sequence exists.</span><small>Ref: Lecture_06_Avoidance.pdf · Slide 14</small></div>
            </div>
          </article>

          <article className="landing-feature-card">
            <FeatureHeading label="Semantic retrieval" icon={<I.Search />} />
            <h3>Intelligent Search</h3>
            <p>Instant vector search across thousands of pages of notes, slides, and scanned lab manuals.</p>
            <div className="landing-search-snippet"><I.Search /><span>Find notes about CPU scheduling</span></div>
            <div className="landing-search-results">
              <SearchResult name="Lecture 5 — Round Robin.pdf" match="99% match" active />
              <SearchResult name="Midterm Review.docx" match="87% match" />
              <SearchResult name="Processes & Threads.pdf" match="74% match" />
            </div>
          </article>

          <article className="landing-feature-card">
            <FeatureHeading label="Taxonomy" icon={<I.Network />} />
            <h3>Organized Resources</h3>
            <p>Automatic semester grouping and modular course hierarchies. Say goodbye to scattered desktop folders.</p>
            <div className="landing-resource-tree">
              <div className="landing-tree-root"><I.FolderOpen /> Semester 4</div>
              <div className="landing-tree-children">
                {resources.map(([name, count], index) => <div className={index === 0 ? "is-current" : ""} key={name}><I.Folder /> <span>{name}</span><small>{count}</small></div>)}
              </div>
            </div>
          </article>

          <article className="landing-feature-card landing-feature-card-small">
            <FeatureHeading label="Audit trail" icon={<I.ShieldCheck />} />
            <h3>Evidence-backed Answers</h3>
            <p>Every sentence traces directly to verified academic sources.</p>
            <div className="landing-evidence-snippet"><div><I.BookOpen /> OS_Silberschatz_v10.pdf</div><blockquote>&quot;...system is in safe state only if there exists a safe sequence...&quot;</blockquote><small>Page 312 · Section 8.4</small></div>
          </article>

          <article className="landing-feature-card landing-feature-card-pipeline">
            <FeatureHeading label="Ingestion pipeline" icon={<I.Zap />} />
            <h3>Smart Document Processing</h3>
            <p>Automated OCR, formula parsing, and dense academic chunking on upload.</p>
            <div className="landing-pipeline"><span>Upload</span><span>Extract</span><span className="is-active">Index</span><span className="is-ready">Ready</span><small>Processing status <b>Complete (0.8s)</b></small></div>
          </article>
        </div>
      </div>
    </section>
  );
}

function FeatureHeading({ label, icon }: { label: string; icon: ReactNode }) {
  return <div className="landing-feature-heading"><span>{label}</span>{icon}</div>;
}

function SearchResult({ name, match, active = false }: { name: string; match: string; active?: boolean }) {
  return <div className={`landing-search-result ${active ? "is-active" : ""}`}><span><I.FileText /> {name}</span><b>{match}</b></div>;
}
