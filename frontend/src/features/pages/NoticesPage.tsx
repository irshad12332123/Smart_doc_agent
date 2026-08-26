import * as I from "lucide-react";
import { Notice } from "../../components/ui/common";

export function NoticesPage() {
  return (
    <div className="page">
      <h1>Notices</h1>
      <p className="lede">
        Stay updated with important announcements for your batch.
      </p>
      <div className="library-tools">
        {['All', 'Important', 'Academic', 'Assignments', 'Events'].map((x, i) => (
          <button className={i === 0 ? 'selected' : ''} key={x}>
            {x}
          </button>
        ))}
      </div>
      <div className="notice-list">
        <Notice
          title="No published notices"
          text="Notices will appear here once a faculty member publishes them for your batch."
          priority="info"
        />
      </div>
    </div>
  );
}
