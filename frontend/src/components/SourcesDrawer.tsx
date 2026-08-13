import { X, FileText } from "lucide-react";
import type { SourceChunk } from "../types";

interface Props {
  sources: SourceChunk[];
  activeIndex: number | null;
  onClose: () => void;
  onSelect: (index: number) => void;
}

export default function SourcesDrawer({ sources, activeIndex, onClose, onSelect }: Props) {
  if (sources.length === 0) return null;

  return (
    <aside
      className="w-80 shrink-0 border-l h-full flex flex-col"
      style={{ borderColor: "var(--border)", background: "var(--surface)" }}
    >
      <div className="flex items-center justify-between px-5 pt-6 pb-3">
        <h2 className="font-display text-sm tracking-tight" style={{ color: "var(--text)" }}>
          Retrieved passages
        </h2>
        <button onClick={onClose} className="md:hidden">
          <X size={16} style={{ color: "var(--text-dim)" }} />
        </button>
      </div>

      <div className="flex-1 overflow-y-auto px-4 pb-6 space-y-3">
        {sources.map((s, i) => {
          const isActive = activeIndex === i;
          return (
            <div
              key={s.chunk_id}
              id={`source-${i}`}
              onClick={() => onSelect(i)}
              className="rounded-lg p-3 cursor-pointer transition-colors border"
              style={{
                background: isActive ? "var(--accent-soft)" : "var(--surface-raised)",
                borderColor: isActive ? "var(--accent)" : "var(--border)",
              }}
            >
              <div className="flex items-center gap-1.5 mb-1.5">
                <span
                  className="citation-mark"
                  style={{ background: isActive ? "var(--accent)" : "var(--accent-soft)", color: isActive ? "#12151c" : "var(--accent-strong)" }}
                >
                  {i + 1}
                </span>
                <FileText size={11} style={{ color: "var(--text-faint)" }} />
                <span className="text-[11px] truncate font-mono" style={{ color: "var(--text-dim)" }}>
                  {s.filename}
                </span>
                <span className="text-[10px] font-mono ml-auto" style={{ color: "var(--text-faint)" }}>
                  {(s.score * 100).toFixed(0)}%
                </span>
              </div>
              <p className="text-xs leading-relaxed line-clamp-6" style={{ color: "var(--text-dim)" }}>
                {s.text}
              </p>
            </div>
          );
        })}
      </div>
    </aside>
  );
}
