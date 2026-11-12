import { useState } from "react";
import * as I from "lucide-react";
import {SiGithub, SiLeetcode} from "react-icons/si";

type LandingHeaderProps = {
  onGetStarted: () => void;
  onLogin: () => void;
};

export function LandingHeader({ onGetStarted, onLogin }: LandingHeaderProps) {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  return (
    <header className={`landing-header ${mobileMenuOpen ? "is-menu-open" : ""}`}>
      <div className="landing-container landing-header-inner">
        <a className="landing-brand" href="#top" aria-label="ScholarHub home">
          <span className="landing-brand-mark"><I.GraduationCap /></span>
          <span>ScholarHub</span>
        </a>

        <nav className="landing-social-nav">
            <p> created by irshad &hearts;  </p>
            <a href="https://github.com/irshad12332123" ><SiGithub /></a>
            <a href="https://leetcode.com/u/Md_Irshad_2005/"><SiLeetcode /></a>
            <a href="https://www.mdirshad.in/">< I.LucideGlobe2 size={18}/></a>
        </nav>

        <button
          className="landing-mobile-menu-button"
          type="button"
          onClick={() => setMobileMenuOpen((open) => !open)}
          aria-label={mobileMenuOpen ? "Close creator links" : "Open creator links"}
          aria-expanded={mobileMenuOpen}
        >
          {mobileMenuOpen ? <I.X /> : <I.Menu />}
        </button>

        <div className="landing-header-actions">
          <button className="landing-button landing-button-small" type="button" onClick={onGetStarted}>
            Get started <I.ArrowRight />
          </button>
        </div>
      </div>

      <div className="landing-mobile-menu" aria-hidden={!mobileMenuOpen}>
        <p>Created by Irshad <span aria-hidden="true">♥</span></p>
        <div>
          <a href="https://github.com/irshad12332123" aria-label="GitHub"><SiGithub /></a>
          <a href="https://leetcode.com/u/Md_Irshad_2005/" aria-label="LeetCode"><SiLeetcode /></a>
          <a href="https://www.mdirshad.in/" aria-label="Personal website"><I.LucideGlobe2 /></a>
        </div>
      </div>
    </header>
  );
}
