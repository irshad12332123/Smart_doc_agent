import { Circle } from "lucide-react";
import type { HealthStatus } from "../api/client";

export default function StatusPill({ health }: { health: HealthStatus | null }) {
  if (!health) {
    return (
      <div className="flex items-center gap-1.5 text-xs font-mono" style={{ color: "var(--text-faint)" }}>
        <Circle size={7} fill="var(--text-faint)" strokeWidth={0} />
        checking…
      </div>
    );
  }

  const ok = health.ollama_ready;
  return (
    <div
      className="flex items-center gap-1.5 text-xs font-mono"
      title={health.ollama_message}
      style={{ color: ok ? "var(--accent)" : "#e07a5f" }}
    >
      <Circle size={7} fill={ok ? "var(--accent)" : "#e07a5f"} strokeWidth={0} />
      {ok ? `${health.chat_model}` : "Ollama unavailable"}
    </div>
  );
}
