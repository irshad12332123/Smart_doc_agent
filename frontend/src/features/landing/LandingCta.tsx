import * as I from "lucide-react";

export function LandingCta({ onGetStarted, onLogin }: { onGetStarted: () => void; onLogin: () => void }) {
  return (
    <section className="landing-cta-section" id="get-started">
      <div className="landing-container">
        <div className="landing-cta-card">
          <span className="landing-cta-icon"><I.GraduationCap /></span>
          <span className="landing-eyebrow">Ready when you are</span>
          <h2>Make your study time count.</h2>
          <p>Everything academic, finally in one intelligent workspace.</p>
          <button className="landing-button" type="button" onClick={onGetStarted}>Get started <I.ArrowRight /></button>
        </div>
      </div>
    </section>
  );
}

export function LandingFooter({ onGetStarted, onLogin }: { onGetStarted: () => void; onLogin: () => void }) {
  return <footer className="landing-footer"><div className="landing-container landing-footer-inner"><div className="landing-footer-brand"><span className="landing-brand-mark"><I.GraduationCap /></span><strong>ScholarHub</strong><span>— The academic AI workspace.</span></div><nav><a href="#features">Features</a><a href="#workflow">How it works</a><button type="button" onClick={onLogin}>Login</button><button type="button" onClick={onGetStarted}>Get started</button></nav><small>© 2025 ScholarHub Inc.</small></div></footer>;
}
