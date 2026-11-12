import * as I from "lucide-react";
import {SiGithub, SiLeetcode} from "react-icons/si";

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

        <nav style={{ display: "flex", alignItems: "center", gap: "0.5rem" }}>
            <p> created by irshad &hearts;  </p>
            <a href="https://github.com/irshad12332123" ><SiGithub /></a>
            <a href="https://leetcode.com/u/Md_Irshad_2005/"><SiLeetcode /></a>
            <a href="https://www.mdirshad.in/">< I.LucideGlobe2 size={18}/></a>
        </nav>

        <div className="landing-header-actions">
          <button className="landing-button landing-button-small" type="button" onClick={onGetStarted}>
            Get started <I.ArrowRight />
          </button>
        </div>
      </div>
    </header>
  );
}
