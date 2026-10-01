import * as I from "lucide-react";
import { Empty, PanelTitle } from "../../components/ui/common";

export function AdminPage() {
  return (
    <div className="page admin-page">
      <div className="page-header">
        <div className="page-title-group">
          <h1>University Administration</h1>
          <p className="lede">
            Manage course registries, faculty assignments, batch cohorts, and document permissions.
          </p>
        </div>
      </div>

      <div className="admin-grid-cards">
        <div className="admin-stat-card">
          <div className="stat-icon-wrap stat-blue">
            <I.Users />
          </div>
          <div className="stat-info">
            <span className="stat-label">Registered Students</span>
            <strong className="stat-number">Active Registry</strong>
          </div>
        </div>
        <div className="admin-stat-card">
          <div className="stat-icon-wrap stat-purple">
            <I.GraduationCap />
          </div>
          <div className="stat-info">
            <span className="stat-label">Faculty Accounts</span>
            <strong className="stat-number">Verified</strong>
          </div>
        </div>
        <div className="admin-stat-card">
          <div className="stat-icon-wrap stat-emerald">
            <I.Database />
          </div>
          <div className="stat-info">
            <span className="stat-label">Vector Storage</span>
            <strong className="stat-number">Operational</strong>
          </div>
        </div>
      </div>

      <section className="panel" style={{ marginTop: "24px" }}>
        <PanelTitle icon={I.ShieldCheck} title="Administrative Controls & Audit" />
        <Empty
          message="Administrative management suite is ready for integration once protected university master endpoints are enabled."
        />
      </section>
    </div>
  );
}
