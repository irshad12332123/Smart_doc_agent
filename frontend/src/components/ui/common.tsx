import * as I from "lucide-react";
import type { ElementType } from "react";

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
