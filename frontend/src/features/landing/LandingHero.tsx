import * as I from "lucide-react";
import assistantPreview from "../../assets/landing-page/ScholarHub Academic AI Assistant.png";

type LandingHeroProps = {
  onGetStarted: () => void;
  onOpenDemo: () => void;
};

export function LandingHero({ onGetStarted, onOpenDemo }: LandingHeroProps) {
  return (
    <section className="landing-hero" id="top">
      <div className="landing-container landing-hero-grid">
        <div className="landing-hero-copy">
          <div className="landing-status-pill">
            <span className="landing-status-dot" />
            Your academic AI workspace
          </div>
          <h1>Stop searching.<br /><span>Start understanding.</span></h1>
          <p>
            Your course materials, academic documents, and an AI assistant that actually
            understands them. All in one place.
          </p>
          <div className="landing-hero-actions">
            <button className="landing-button" type="button" onClick={onGetStarted}>
              Get started <I.ArrowRight />
            </button>
            <a className="landing-text-button" href="#features">
              Explore the workspace <I.ArrowDown />
            </a>
          </div>
          <div className="landing-trust-line">
            <I.BadgeCheck />
            Zero hallucinations via strictly bound citations
          </div>
        </div>

        <button className="landing-preview-wrap" id="demo" type="button" onClick={onOpenDemo} aria-label="Open ScholarHub demo">
          <span className="landing-preview-glow" />
          <span className="landing-preview-window">
            <span className="landing-preview-toolbar">
              <span className="landing-window-dots"><i /><i /><i /></span>
              <span className="landing-preview-path"><I.Folder /> CS301 · Operating Systems <b>/</b> Unit 3</span>
              <span className="landing-live-index"><i /> LIVE INDEX</span>
            </span>
            <img src={assistantPreview} alt="ScholarHub academic AI assistant showing a cited CPU scheduling answer" />
            <span className="landing-preview-caption"><I.Maximize2 /> View assistant demo</span>
          </span>
        </button>
      </div>
    </section>
  );
}
