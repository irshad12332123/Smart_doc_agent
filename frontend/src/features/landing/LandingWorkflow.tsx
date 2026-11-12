import * as I from "lucide-react";

const steps = [
  { number: "01", title: "Find", icon: I.Archive, copy: "Access your organized course materials. Everything is centralized, OCR'd, and prepared for instant semantic reasoning.", label: "Input source", value: "PDF, Slides, Docx" },
  { number: "02", title: "Ask", icon: I.MessagesSquare, copy: "Ask questions in natural language. Inquire about proof derivations, conceptual trade-offs, or exam review summaries.", label: "Query mode", value: "Context-Aware AI" },
  { number: "03", title: "Understand", icon: I.Lightbulb, copy: "Receive contextual answers with supporting citations and page numbers so you can verify and study with high confidence.", label: "Output", value: "100% Attributed" },
];

export function LandingWorkflow() {
  return (
    <section className="landing-section landing-workflow" id="workflow">
      <div className="landing-container">
        <div className="landing-section-heading">
          <span className="landing-eyebrow">Linear execution</span>
          <h2>From your documents to clear answers.</h2>
          <p>Zero complex prompting required. ScholarHub works the moment your materials are dropped in.</p>
        </div>
        <div className="landing-steps">
          <span className="landing-step-line" />
          {steps.map((step) => {
            const Icon = step.icon;
            return <article className={`landing-step ${step.number === "03" ? "is-final" : ""}`} key={step.number}>
              <div className="landing-step-top"><span className="landing-step-number">{step.number}</span><Icon /></div>
              <h3>{step.title}</h3><p>{step.copy}</p>
              <div className="landing-step-meta"><span>{step.label}</span><b>{step.value}</b></div>
            </article>;
          })}
        </div>
      </div>
    </section>
  );
}
