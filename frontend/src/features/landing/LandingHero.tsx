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
          <h1>Stop searching.<br /><span>Start understanding.</span></h1>
          <p>
            Your course materials, academic documents, and an AI assistant that actually
            understands them. All in one place.
          </p>
          <div className="landing-hero-actions">
            <button className="landing-button" type="button" onClick={onGetStarted}>
              Get started <I.ArrowRight />
            </button>
          </div>
        </div>

        <button className="landing-preview-wrap" id="demo" type="button" onClick={onOpenDemo} aria-label="Open ScholarHub demo">
          <span className="landing-preview-glow" />
          <span className="landing-preview-window">
            <img src={assistantPreview} alt="ScholarHub academic AI assistant showing a cited CPU scheduling answer" />
            {/* <span className="landing-preview-caption"><I.Maximize2 /> View assistant demo</span> */}
          </span>
        </button>
      </div>
    </section>
  );
}
