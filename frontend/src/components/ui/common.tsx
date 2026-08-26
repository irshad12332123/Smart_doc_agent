import * as I from "lucide-react";
import type { ElementType } from "react";
import type { DocumentInfo } from "../../types";

export function Error({ text }: { text: string }) {
  return text ? (
    <p className="form-error">
      <I.CircleAlert /> {text}
    </p>
  ) : null;
}

export function Empty({ message }: { message: string }) {
  return (
    <div className="empty">
      <I.Inbox />
      <p>{message}</p>
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
        <Icon />
        {title}
      </h2>
      {action && <button onClick={onAction}>{action}</button>}
    </div>
  );
}

export function PanelTitle({
  icon: Icon,
  title,
}: {
  icon: ElementType;
  title: string;
}) {
  return (
    <h2 className="panel-title">
      <Icon />
      {title}
    </h2>
  );
}

export function DocumentCard({ document }: { document: DocumentInfo }) {
  const ext = document.filetype.toUpperCase() || "FILE";

  return (
    <article className="doc-card">
      <div className={`doc-art ${document.filetype}`}>
        <I.FileText />
        <span>{ext} DOCUMENT</span>
      </div>
      <div className="doc-info">
        <h3 title={document.filename}>{document.filename}</h3>
        <div>
          <span className="tag">Course material</span>
          <span className="tag muted-tag">{ext}</span>
        </div>
        <footer>
          <span>
            <I.Clock />{" "}
            {document.uploaded_at
              ? new Date(document.uploaded_at).toLocaleDateString()
              : "Recently added"}
          </span>
          <button title="Opening original documents requires a signed file URL endpoint.">
            <I.MoreHorizontal />
          </button>
        </footer>
      </div>
    </article>
  );
}

export function Notice({
  title,
  text,
  priority,
}: {
  title: string;
  text: string;
  priority: "info" | "alert";
}) {
  return (
    <article className={`notice ${priority}`}>
      <I.Info />
      <div>
        <h3>{title}</h3>
        <p>{text}</p>
      </div>
    </article>
  );
}
