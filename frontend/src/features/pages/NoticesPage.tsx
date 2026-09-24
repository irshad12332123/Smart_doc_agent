import { useState } from "react";
import * as I from "lucide-react";
import { Notice } from "../../components/ui/common";

const categories = ["All", "Important", "Academic", "Assignments", "Events"];

export function NoticesPage() {
  const [activeCategory, setActiveCategory] = useState("All");

  return (
    <div className="page notices-page">
      <div className="page-header">
        <div className="page-title-group">
          <h1>Notices & Announcements</h1>
          <p className="lede">
            Stay updated with real-time academic notifications from your department and mentors.
          </p>
        </div>
        <div className="page-stat-badge">
          <I.Bell />
          <span>2 Active Notices</span>
        </div>
      </div>

      <div className="library-tools">
        <div className="filter-chips">
          {categories.map((cat) => (
            <button
              className={`filter-btn ${activeCategory === cat ? "selected" : ""}`}
              key={cat}
              onClick={() => setActiveCategory(cat)}
            >
              {cat}
            </button>
          ))}
        </div>
      </div>

      <div className="notice-list">
        <Notice
          title="Semester 5 Mid-Term Evaluation Guidelines"
          text="Project submissions and lab records must be verified by respective faculty mentors before next Friday. Ensure your documentation matches the IEEE standard format."
          priority="important"
          date="Today, 2:30 PM"
          author="Academic Dean"
        />
        <Notice
          title="Cloud Computing Lab Environment Updated"
          text="AWS student account credentials and IAM roles have been refreshed for Machine Learning & NLP coursework batches. Check your university inbox for login details."
          priority="info"
          date="Yesterday, 11:00 AM"
          author="Department of Computer Science"
        />
      </div>
    </div>
  );
}
