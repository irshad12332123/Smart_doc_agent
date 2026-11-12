import { useEffect, useState } from "react";
import { LandingCta, LandingFooter } from "./LandingCta";
import { LandingDemoModal } from "./LandingDemoModal";
import { LandingFeatures } from "./LandingFeatures";
import { LandingHeader } from "./LandingHeader";
import { LandingHero } from "./LandingHero";
import { LandingWorkflow } from "./LandingWorkflow";

type LandingPageProps = { onGetStarted: () => void; onLogin: () => void };

export function LandingPage({ onGetStarted, onLogin }: LandingPageProps) {
  const [demoOpen, setDemoOpen] = useState(false);

  useEffect(() => {
    if (!demoOpen) return;
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") setDemoOpen(false);
    };
    document.addEventListener("keydown", closeOnEscape);
    document.body.classList.add("landing-modal-open");
    return () => {
      document.removeEventListener("keydown", closeOnEscape);
      document.body.classList.remove("landing-modal-open");
    };
  }, [demoOpen]);

  return <div className="landing-page">
    <LandingHeader onGetStarted={onGetStarted} onLogin={onLogin} />
    <main>
      <LandingHero onGetStarted={onGetStarted} onOpenDemo={() => setDemoOpen(true)} />
      <LandingFeatures />
      <LandingWorkflow />
      <LandingCta onGetStarted={onGetStarted} onLogin={onLogin} />
    </main>
    <LandingFooter onGetStarted={onGetStarted} onLogin={onLogin} />
    {demoOpen && <LandingDemoModal onClose={() => setDemoOpen(false)} />}
  </div>;
}
