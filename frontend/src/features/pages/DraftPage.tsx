import * as I from "lucide-react";

export function DraftPage() {
  return (
    <div className="page draft-page">
      <div className="page-header">
        <div className="page-title-group">
          <h1>Draft an Announcement</h1>
          <p className="lede">
            Broadcast urgent deadlines, syllabus updates, or event notices to your batches.
          </p>
        </div>
      </div>

      <div className="panel draft-form-panel">
        <label className="form-field">
          <span className="field-label">Notice Title</span>
          <input placeholder="e.g. Lab Submission Deadline Extended" />
        </label>

        <label className="form-field">
          <span className="field-label">Announcement Content</span>
          <textarea
            rows={8}
            placeholder="Write the notice details clearly. You can include submission links, classroom numbers, or instructions…"
          />
        </label>

        <div className="draft-meta-grid">
          <label className="form-field">
            <span className="field-label">Priority Level</span>
            <select defaultValue="regular">
              <option value="regular">Regular Announcement</option>
              <option value="important">Important / Urgent</option>
              <option value="event">Event / Webinar</option>
            </select>
          </label>

          <label className="form-field">
            <span className="field-label">Distribute to Batches</span>
            <select defaultValue="all">
              <option value="all">All Assigned Batches</option>
              <option value="bca24">BCA 2024–27 (Semester 5)</option>
            </select>
          </label>
        </div>

        <div className="api-note">
          <I.Info /> Published notices appear instantly on student home dashboards and push notifications.
        </div>

        <div className="draft-actions-row">
          <button className="outline-btn">
            <I.Save /> Save as Draft
          </button>
          <button className="primary" disabled title="Notice publication backend in progress">
            <span>Publish Notice</span>
            <I.Send />
          </button>
        </div>
      </div>
    </div>
  );
}
