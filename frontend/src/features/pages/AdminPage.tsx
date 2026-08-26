import * as I from "lucide-react";
import { Empty, PanelTitle } from "../../components/ui/common";

export function AdminPage() {
  return (
    <div className="page">
      <h1>Admin management</h1>
      <p className="lede">
        Manage university records, academic contexts, and access controls.
      </p>
      <section className="panel" style={{ marginTop: "35px" }}>
        <PanelTitle icon={I.ShieldCheck} title="Administrative tools" />
        <Empty message="Admin management is ready for integration once protected administration APIs are available." />
      </section>
    </div>
  );
}
