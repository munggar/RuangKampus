import type { ReactNode } from "react";

interface EmptyStateProps {
  title: string;
  description: string;
  icon?: ReactNode;
  action?: ReactNode;
  eyebrow?: string;
}

export function EmptyState({
  title,
  description,
  icon,
  action,
  eyebrow,
}: EmptyStateProps) {
  return (
    <section className="empty-state" aria-label={title}>
      {icon ? <div className="empty-state__icon" aria-hidden="true">{icon}</div> : null}
      {eyebrow ? <p className="eyebrow">{eyebrow}</p> : null}
      <h3>{title}</h3>
      <p>{description}</p>
      {action ? <div className="empty-state__action">{action}</div> : null}
    </section>
  );
}
