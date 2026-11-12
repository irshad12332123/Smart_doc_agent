import * as I from "lucide-react";

type LandingHeaderProps = {
  onGetStarted: () => void;
  onLogin: () => void;
};

export function LandingHeader({ onGetStarted, onLogin }: LandingHeaderProps) {
  return (
    <header className="landing-header">
      <div className="landing-container landing-header-inner">
        <a className="landing-brand" href="#top" aria-label="ScholarHub home">
          <span className="landing-brand-mark"><I.GraduationCap /></span>
          <span>ScholarHub</span>
        </a>

        <nav className="landing-nav" aria-label="Landing page navigation">
          <a className="is-active" href="#features">Features</a>
          <a href="#workflow">Workflow</a>
          <a href="#demo">Demo</a>
        </nav>

        <div className="landing-header-actions">
          <button className="landing-login-link" type="button" onClick={onLogin}>Log in</button>
          <button className="landing-button landing-button-small" type="button" onClick={onGetStarted}>
            Get started <I.ArrowRight />
          </button>
          <span className="landing-avatar" aria-hidden="true"><I.UserRound /></span>
        </div>
      </div>
    </header>
  );
}
