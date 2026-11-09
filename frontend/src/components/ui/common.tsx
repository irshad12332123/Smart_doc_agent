import { useState, type ElementType } from "react";
import * as I from "lucide-react";
import { documentApi } from "../../api/client";
import type { DocumentInfo } from "../../types";

export function Error({ text }: { text: string }) {
  if (!text) return null;
  return (
    <div className="form-error">
      <I.CircleAlert className="icon-alert" />
      <span>{text}</span>
    </div>
  );
}
export function Empty({
  message,
  actionLabel,
  onAction,
}: {
  message: string;
  actionLabel?: string;
  onAction?: () => void;
}) {
  return (
    <div className="empty-state">
      <div className="empty-icon-wrap">
        <I.Inbox />
      </div>
      <p className="empty-message">{message}</p>
      {actionLabel && onAction && (
        <button className="outline-btn empty-action" onClick={onAction}>
          {actionLabel}
        </button>
      )}
    </div>
  );
}

export function SectionTitle({
  icon: Icon,
  title,
  action,
  onAction,
}: {
  icon: ElementType;
  title: string;
  action?: string;
  onAction?: () => void;
}) {
  return (
    <div className="section-title">
      <h2>
        <span className="section-icon-wrap">
          <Icon />
        </span>
        {title}
      </h2>
      {action && (
        <button className="section-action-btn" onClick={onAction}>
          {action}
          <I.ChevronRight />
        </button>
      )}
    </div>
  );
}

export function PanelTitle({
  icon: Icon,
  title,
  badge,
}: {
  icon: ElementType;
  title: string;
  badge?: string;
}) {
  return (
    <div className="panel-title-row">
      <h2 className="panel-title">
        <span className="panel-icon-wrap">
          <Icon />
        </span>
        {title}
      </h2>
      {badge && <span className="panel-badge">{badge}</span>}
    </div>
  );
}

export function getFileTypeTheme(filetype: string) {
  const ext = (filetype || "").toLowerCase().replace(".", "");
  if (ext === "pdf") {
    return {
      type: "PDF",
      className: "type-pdf",
      icon: I.FileText,
      label: "PDF Document",
      color: "var(--color-pdf)",
      bgColor: "var(--color-pdf-bg)",
    };
  }
  if (ext === "docx" || ext === "doc") {
    return {
      type: "DOCX",
      className: "type-docx",
      icon: I.FileCode2,
      label: "Word Document",
      color: "var(--color-docx)",
      bgColor: "var(--color-docx-bg)",
    };
  }
  if (ext === "pptx" || ext === "ppt") {
    return {
      type: "PPTX",
      className: "type-pptx",
      icon: I.Presentation,
      label: "Presentation",
      color: "var(--color-pptx)",
      bgColor: "var(--color-pptx-bg)",
    };
  }
  if (["png", "jpg", "jpeg", "webp", "gif", "image"].includes(ext)) {
    return {
      type: "IMG",
      className: "type-img",
      icon: I.Image,
      label: "Image Asset",
      color: "var(--color-img)",
      bgColor: "var(--color-img-bg)",
    };
  }
  return {
    type: ext.toUpperCase() || "FILE",
    className: "type-generic",
    icon: I.File,
    label: "Academic File",
    color: "var(--color-generic)",
    bgColor: "var(--color-generic-bg)",
  };
}

export function DocumentCard({
  document,
  onOpen,
  onDownload,
}: {
  document: DocumentInfo;
  onOpen?: (doc: DocumentInfo) => void;
  onDownload?: (doc: DocumentInfo) => void;
}) {
  const [opening, setOpening] = useState(false);
  const [downloading, setDownloading] = useState(false);
  const [actionError, setActionError] = useState("");

  const fileTheme = getFileTypeTheme(document.filetype);
  const Icon = fileTheme.icon;

  const formattedDate = document.uploaded_at
    ? new Date(document.uploaded_at).toLocaleDateString(undefined, {
        month: "short",
        day: "numeric",
        year: "numeric",
      })
    : "Recently uploaded";

  const handleOpen = async (e?: React.MouseEvent) => {
    e?.stopPropagation();
    if (opening || downloading) return;
    setActionError("");
    setOpening(true);
    try {
      if (onOpen) {
        await onOpen(document);
      } else {
        await documentApi.openDocument(document.doc_id);
      }
    } catch (err: unknown) {
      console.error("Failed to view document:", err);
      setActionError("Failed to open");
      setTimeout(() => setActionError(""), 3500);
    } finally {
      setOpening(false);
    }
  };

  const handleDownload = async (e: React.MouseEvent) => {
    e.stopPropagation();
    if (downloading || opening) return;
    setActionError("");
    setDownloading(true);
    try {
      if (onDownload) {
        await onDownload(document);
      } else {
        await documentApi.downloadDocument(document.doc_id, document.filename);
      }
    } catch (err: unknown) {
      console.error("Failed to download document:", err);
      setActionError("Failed to download");
      setTimeout(() => setActionError(""), 3500);
    } finally {
      setDownloading(false);
    }
  };

  return (
    <article
      className="doc-card"
      tabIndex={0}
      role="button"
      onClick={handleOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          handleOpen();
        }
      }}
      title={`Click to view ${document.filename}`}
    >
      <div className={`doc-art ${fileTheme.className}`}>
        <div className="doc-art-bg-glow" />
        <div className="doc-art-icon-circle">
          <Icon />
        </div>
        <div className="doc-art-badges">
          <span className="file-chip">
            <Icon /> {fileTheme.type}
          </span>
          {document.num_chunks ? (
            <span className="chunks-chip">
              {document.num_chunks} {document.num_chunks === 1 ? "section" : "sections"}
            </span>
          ) : null}
        </div>
      </div>

      <div className="doc-info">
        <h3 title={document.filename} className="doc-title">
          {document.filename}
        </h3>

        <p className="doc-desc">
          {document.description || "Course study material and batch reference."}
        </p>

        <div className="doc-tags">
          <span className="tag tag-primary">
            <I.Bookmark /> {document.document_type ? document.document_type.toUpperCase() : "MATERIAL"}
          </span>
          {document.unit != null && (
            <span className="tag tag-primary">Unit {document.unit}</span>
          )}
          <span className="tag tag-muted">{fileTheme.type}</span>
        </div>

        <footer>
          <span className="doc-date">
            <I.Calendar /> {formattedDate}
          </span>
          <div className="doc-actions" onClick={(e) => e.stopPropagation()}>
            {actionError && (
              <span className="doc-action-error" title={actionError}>
                {actionError}
              </span>
            )}
            <button
              type="button"
              className="card-icon-btn"
              onClick={handleOpen}
              disabled={opening}
              title="View document in new tab"
              aria-label={`View ${document.filename}`}
            >
              {opening ? <I.Loader2 className="spinning-loader" /> : <I.ExternalLink />}
            </button>
            <button
              type="button"
              className="card-icon-btn card-icon-btn-download"
              onClick={handleDownload}
              disabled={downloading}
              title="Download document file"
              aria-label={`Download ${document.filename}`}
            >
              {downloading ? <I.Loader2 className="spinning-loader" /> : <I.Download />}
            </button>
          </div>
        </footer>
      </div>
    </article>
  );
}

export function SubjectCard({
  title,
  code,
  iconIndex = 0,
  onClick,
}: {
  title: string;
  code: string;
  iconIndex?: number;
  onClick?: () => void;
}) {
  const icons = [I.Code2, I.Bot, I.Cpu, I.Layers, I.Database, I.Server];
  const Icon = icons[iconIndex % icons.length];

  return (
    <button className="subject-card" onClick={onClick}>
      <div className="subject-card-top">
        <div className={`subject-icon-wrap idx-${iconIndex % 4}`}>
          <Icon />
        </div>
        <span className="subject-code-badge">{code}</span>
      </div>
      <div className="subject-card-content">
        <h3 className="subject-name">{title}</h3>
        <p className="subject-subtext">Course notes, assignments & AI study helper</p>
      </div>
      <div className="subject-card-footer">
        <span>Explore Subject</span>
        <I.ArrowRight className="subject-arrow" />
      </div>
    </button>
  );
}
