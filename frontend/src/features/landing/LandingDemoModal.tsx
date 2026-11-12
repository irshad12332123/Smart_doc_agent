import * as I from "lucide-react";
import assistantPreview from "../../assets/landing-page/ScholarHub Academic AI Assistant.png";

export function LandingDemoModal({ onClose }: { onClose: () => void }) {
  return <div className="landing-modal-backdrop" role="presentation" onMouseDown={onClose}>
    <div className="landing-demo-modal" role="dialog" aria-modal="true" aria-labelledby="demo-title" onMouseDown={(event) => event.stopPropagation()}>
      <div className="landing-modal-header"><div><span className="landing-eyebrow">Interactive preview</span><h2 id="demo-title">Your academic AI workspace</h2></div><button type="button" onClick={onClose} aria-label="Close demo"><I.X /></button></div>
      <img src={assistantPreview} alt="ScholarHub academic AI assistant" />
    </div>
  </div>;
}
