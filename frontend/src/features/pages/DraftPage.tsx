import * as I from "lucide-react";

export function DraftPage() {
  return (
    <div className="page">
      <h1>Draft a notice</h1>
      <p className="lede">
        Create an announcement for the batches assigned to you.
      </p>
      <div className="draft panel">
        <label>
          Notice title
          <input placeholder="e.g. Assignment deadline extended" />
        </label>
        <label>
          Message
          <textarea
            rows={9}
            placeholder="Write the notice your students need to see…"
          />
        </label>
        <div className="upload-meta">
          <label>
            Priority
            <select>
              <option>Regular</option>
              <option>Important</option>
            </select>
          </label>
          <label>
            Distribute to
            <select>
              <option>Assigned batches — backend required</option>
            </select>
          </label>
        </div>
        <p className="api-note">
          <I.Info /> Draft persistence and publishing need a protected faculty
          notices API.
        </p>
        <div>
          <button className="outline-btn">Save draft</button>
          <button className="primary" disabled>
            Publish notice <I.Send />
          </button>
        </div>
      </div>
    </div>
  );
}
