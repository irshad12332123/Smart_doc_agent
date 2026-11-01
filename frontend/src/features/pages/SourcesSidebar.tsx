import { useState, useMemo } from "react";
import * as I from "lucide-react";
import type { ChatMessage, SourceChunk, DocumentInfo } from "../../types";
import { getFileTypeTheme } from "../../components/ui/common";

interface SourcesSidebarProps {
  open: boolean;
  onClose: () => void;
  messages: ChatMessage[];
  selectedMessageId: string | null;
  onSelectMessage: (id: string) => void;
}

export function SourcesSidebar({
  open,
  onClose,
  messages,
  selectedMessageId,
  onSelectMessage,
}: SourcesSidebarProps) {
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [viewAll, setViewAll] = useState(false);

  // Find all assistant messages that have sources or matched documents
  const messagesWithSources = useMemo(() => {
    return messages.filter(
      (m) =>
        m.role === "assistant" &&
        ((m.sources && m.sources.length > 0) ||
          (m.documents && m.documents.length > 0)),
    );
  }, [messages]);

  // Determine active message: user selected or latest one
  const activeMessage = useMemo(() => {
    if (selectedMessageId) {
      const found = messagesWithSources.find((m) => m.id === selectedMessageId);
      if (found) return found;
    }
    return messagesWithSources[messagesWithSources.length - 1] || null;
  }, [messagesWithSources, selectedMessageId]);

  // Find user prompt for a given assistant message
  const getUserPromptFor = (assistantMsgId: string) => {
    const idx = messages.findIndex((m) => m.id === assistantMsgId);
    if (idx > 0 && messages[idx - 1]?.role === "user") {
      return messages[idx - 1].content;
    }
    return "";
  };

  const handleCopy = (id: string, text: string) => {
    navigator.clipboard?.writeText(text);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  // Compile active sources and documents
  const activeSources: SourceChunk[] = useMemo(() => {
    if (viewAll) {
      const all: SourceChunk[] = [];
      const seen = new Set<string>();
      for (const m of messagesWithSources) {
        for (const s of m.sources || []) {
          const key = s.chunk_id || `${s.doc_id}-${s.filename}-${s.text.slice(0, 30)}`;
          if (!seen.has(key)) {
            seen.add(key);
            all.push(s);
          }
        }
      }
      return all;
    }
    return activeMessage?.sources || [];
  }, [viewAll, messagesWithSources, activeMessage]);

  const activeDocuments: DocumentInfo[] = useMemo(() => {
    if (viewAll) {
      const all: DocumentInfo[] = [];
      const seen = new Set<string>();
      for (const m of messagesWithSources) {
        for (const doc of m.documents || []) {
          const key = doc.doc_id || doc.filename;
          if (!seen.has(key)) {
            seen.add(key);
            all.push(doc);
          }
        }
      }
      return all;
    }
    return activeMessage?.documents || [];
  }, [viewAll, messagesWithSources, activeMessage]);

  const totalCitations = activeSources.length + activeDocuments.length;

  if (!open) return null;

  return (
    <aside className="sources-sidebar" aria-label="Referenced sources panel">
      <div className="sources-sidebar-header">
          <div className="sources-sidebar-title">
            <div className="sources-header-icon">
              <I.BookOpen />
            </div>
            <div>
              <h3>Referenced Sources</h3>
              <p>
                {totalCitations}{" "}
                {totalCitations === 1 ? "reference found" : "references found"}
              </p>
            </div>
          </div>
          <button
            type="button"
            className="sources-close-btn"
            onClick={onClose}
            title="Close sidebar"
            aria-label="Close sources sidebar"
          >
            <I.X />
          </button>
      </div>

        {/* Response switcher if multiple assistant responses have sources */}
      {messagesWithSources.length > 1 && (
          <div className="sources-sidebar-nav">
            <div className="sources-tab-group">
              <button
                type="button"
                className={`sources-tab-btn ${!viewAll ? "active" : ""}`}
                onClick={() => setViewAll(false)}
              >
                Selected Answer
              </button>
              <button
                type="button"
                className={`sources-tab-btn ${viewAll ? "active" : ""}`}
                onClick={() => setViewAll(true)}
              >
                All in Chat
              </button>
            </div>

            {!viewAll && (
              <div className="sources-select-wrap">
                <label htmlFor="sources-response-select">For question:</label>
                <select
                  id="sources-response-select"
                  value={activeMessage?.id || ""}
                  onChange={(e) => onSelectMessage(e.target.value)}
                >
                  {messagesWithSources.map((msg, i) => {
                    const prompt = getUserPromptFor(msg.id);
                    const label = prompt
                      ? prompt.length > 36
                        ? prompt.slice(0, 36) + "…"
                        : prompt
                      : `Response #${i + 1}`;
                    const isLatest = i === messagesWithSources.length - 1;
                    return (
                      <option key={msg.id} value={msg.id}>
                        {isLatest ? "Latest: " : ""}
                        "{label}"
                      </option>
                    );
                  })}
                </select>
              </div>
            )}
          </div>
      )}

      <div className="sources-sidebar-content">
          {totalCitations === 0 ? (
            <div className="sources-sidebar-empty">
              <div className="empty-sources-icon">
                <I.BookOpenCheck />
              </div>
              <h4>No Citations for this Answer</h4>
              <p>
                When responses reference syllabus notes, lecture slides, or
                academic documents, citations will appear here.
              </p>
            </div>
          ) : (
            <>
              {activeSources.length > 0 && (
                <section className="sources-section">
                  <div className="sources-section-title">
                    <I.FileText />
                    <span>Citations & Snippets ({activeSources.length})</span>
                  </div>

                  <div className="sources-list">
                    {activeSources.map((s, idx) => {
                      const fileType = getFileTypeTheme(
                        s.filename.split(".").pop() || "",
                      );
                      const Icon = fileType.icon;
                      const cardId = s.chunk_id || `chunk-${idx}`;
                      const isCopied = copiedId === cardId;

                      return (
                        <div className="source-sidebar-card" key={cardId}>
                          <div className="source-card-header">
                            <span className="source-card-index">{idx + 1}</span>
                            <div className="source-file-details">
                              <Icon className="source-file-icon" />
                              <span
                                className="source-card-filename"
                                title={s.filename}
                              >
                                {s.filename}
                              </span>
                            </div>
                            <button
                              type="button"
                              className="source-copy-btn"
                              onClick={() => handleCopy(cardId, s.text)}
                              title={isCopied ? "Copied" : "Copy snippet"}
                              aria-label="Copy snippet"
                            >
                              {isCopied ? (
                                <I.Check className="copied-check" />
                              ) : (
                                <I.Copy />
                              )}
                            </button>
                          </div>

                          <div className="source-card-body">
                            <p className="source-card-snippet">{s.text}</p>
                          </div>

                          {typeof s.score === "number" && s.score > 0 && (
                            <div className="source-card-footer">
                              <span className="source-score-badge">
                                Relevance: {(s.score * 100).toFixed(0)}%
                              </span>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}

              {activeDocuments.length > 0 && (
                <section className="sources-section">
                  <div className="sources-section-title">
                    <I.Files />
                    <span>
                      Matched Academic Documents ({activeDocuments.length})
                    </span>
                  </div>

                  <div className="sources-list">
                    {activeDocuments.map((doc, idx) => {
                      const fileType = getFileTypeTheme(
                        doc.filename?.split(".").pop() || "pdf",
                      );
                      const Icon = fileType.icon;

                      return (
                        <div
                          className="source-sidebar-card doc-match-card"
                          key={doc.doc_id || idx}
                        >
                          <div className="source-card-header">
                            <span className="source-card-index">{idx + 1}</span>
                            <div className="source-file-details">
                              <Icon className="source-file-icon" />
                              <span
                                className="source-card-filename"
                                title={doc.filename}
                              >
                                {doc.filename}
                              </span>
                            </div>
                          </div>

                          {doc.description && (
                            <div className="source-card-body">
                              <p className="source-card-snippet">
                                {doc.description}
                              </p>
                            </div>
                          )}

                          {doc.file_url && (
                            <div className="source-card-footer">
                              <a
                                href={doc.file_url}
                                target="_blank"
                                rel="noopener noreferrer"
                                className="source-download-btn"
                              >
                                <I.Download />
                                <span>Download Document</span>
                              </a>
                            </div>
                          )}
                        </div>
                      );
                    })}
                  </div>
                </section>
              )}
            </>
          )}
      </div>
    </aside>
  );
}
