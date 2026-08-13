import { useCallback, useRef, useState } from "react";
import { FileText, Upload, Trash2, Loader2, BookOpen } from "lucide-react";
import type { DocumentInfo } from "../types";

interface Props {
  documents: DocumentInfo[];
  loading: boolean;
  uploading: boolean;
  indexedChunks: number;
  onUpload: (files: File[]) => void;
  onDelete: (docId: string) => void;
}

const ACCEPTED = ".pdf,.docx,.txt,.md,.markdown";

export default function Sidebar({
  documents,
  loading,
  uploading,
  indexedChunks,
  onUpload,
  onDelete,
}: Props) {
  const [dragOver, setDragOver] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setDragOver(false);
      const files = Array.from(e.dataTransfer.files);
      if (files.length) onUpload(files);
    },
    [onUpload]
  );

  return (
    <aside className="w-72 shrink-0 border-r flex flex-col h-full" style={{ borderColor: "var(--border)", background: "var(--surface)" }}>
      <div className="px-5 pt-6 pb-4">
        <div className="flex items-center gap-2">
          <BookOpen size={18} style={{ color: "var(--accent)" }} />
          <h1 className="font-display text-lg tracking-tight" style={{ color: "var(--text)" }}>
            The Archive
          </h1>
        </div>
        <p className="text-xs mt-1" style={{ color: "var(--text-dim)" }}>
          {indexedChunks} passage{indexedChunks === 1 ? "" : "s"} indexed
        </p>
      </div>

      {/* Upload dropzone */}
      <div className="px-5 pb-4">
        <div
          onDragOver={(e) => {
            e.preventDefault();
            setDragOver(true);
          }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          onClick={() => inputRef.current?.click()}
          className="rounded-lg border border-dashed cursor-pointer transition-colors px-4 py-5 text-center"
          style={{
            borderColor: dragOver ? "var(--accent)" : "var(--border)",
            background: dragOver ? "var(--accent-soft)" : "transparent",
          }}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            accept={ACCEPTED}
            className="hidden"
            onChange={(e) => {
              const files = Array.from(e.target.files || []);
              if (files.length) onUpload(files);
              e.target.value = "";
            }}
          />
          {uploading ? (
            <Loader2 size={20} className="animate-spin mx-auto" style={{ color: "var(--accent)" }} />
          ) : (
            <Upload size={20} className="mx-auto" style={{ color: "var(--text-dim)" }} />
          )}
          <p className="text-xs mt-2" style={{ color: "var(--text-dim)" }}>
            {uploading ? "Reading in…" : "Drop files or click to add"}
          </p>
          <p className="text-[10px] mt-1 font-mono" style={{ color: "var(--text-faint)" }}>
            PDF · DOCX · TXT · MD
          </p>
        </div>
      </div>

      {/* Document list */}
      <div className="flex-1 overflow-y-auto px-3 pb-4">
        {loading ? (
          <div className="flex justify-center py-8">
            <Loader2 size={16} className="animate-spin" style={{ color: "var(--text-faint)" }} />
          </div>
        ) : documents.length === 0 ? (
          <p className="text-xs text-center px-4 py-8 leading-relaxed" style={{ color: "var(--text-faint)" }}>
            Nothing on the shelf yet. Add a document to start building your knowledge base.
          </p>
        ) : (
          <ul className="space-y-1">
            {documents.map((doc) => (
              <li
                key={doc.doc_id}
                className="group flex items-start gap-2 rounded-md px-2 py-2 hover:bg-white/[0.03] transition-colors"
              >
                <FileText size={14} className="mt-0.5 shrink-0" style={{ color: "var(--accent)" }} />
                <div className="min-w-0 flex-1">
                  <p className="text-xs truncate" style={{ color: "var(--text)" }} title={doc.filename}>
                    {doc.filename}
                  </p>
                  <p className="text-[10px] font-mono" style={{ color: "var(--text-faint)" }}>
                    {doc.num_chunks} chunk{doc.num_chunks === 1 ? "" : "s"}
                  </p>
                </div>
                <button
                  onClick={() => onDelete(doc.doc_id)}
                  className="opacity-0 group-hover:opacity-100 transition-opacity shrink-0"
                  title="Remove from index"
                >
                  <Trash2 size={13} style={{ color: "var(--text-faint)" }} />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </aside>
  );
}
