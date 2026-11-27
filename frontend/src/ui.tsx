import { useEffect, useId, useRef, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { IconAlertCircle as AlertCircle, IconCheck as Check, IconInfoCircle as Info, IconLoader2 as LoaderCircle, IconX as X } from "@tabler/icons-react";
import { statusLabel } from "./api";
import type { ReservationStatus } from "./types";

export function Button({ children, onClick, type = "button", variant = "primary", disabled = false, className = "", title }: {
  children: ReactNode; onClick?: () => void; type?: "button" | "submit" | "reset";
  variant?: "primary" | "secondary" | "danger" | "ghost"; disabled?: boolean; className?: string; title?: string;
}) {
  return <button type={type} onClick={onClick} disabled={disabled} title={title} className={"button button--" + variant + (className ? " " + className : "")}>{children}</button>;
}

export function StatusBadge({ status }: { status: string }) {
  return <span className={"status-badge status-badge--" + status.toLowerCase()}>{statusLabel(status)}</span>;
}

export function initialsFromName(name?: string | null): string {
  const initials = (name || "").trim().split(/\s+/).filter(Boolean).slice(0, 2)
    .map((part) => part.charAt(0)).join("").toUpperCase();
  return initials || "RK";
}

export function Notice({ children, tone = "info" }: { children: ReactNode; tone?: "info" | "success" | "warning" | "error" }) {
  const Icon = tone === "success" ? Check : tone === "error" ? AlertCircle : Info;
  return <div className={"notice notice--" + tone} role={tone === "error" ? "alert" : "status"}><Icon size={17} /><div>{children}</div></div>;
}

export function Loading({ label = "Memuat data…" }: { label?: string }) {
  return <div className="loading-inline"><LoaderCircle className="spinner-icon" size={20} /><span>{label}</span></div>;
}

export function EmptyState({ title, description, action, icon }: { title: string; description: string; action?: ReactNode; icon?: ReactNode }) {
  return <div className="empty-state"><span className="empty-state__icon">{icon || <Info size={22} />}</span><strong>{title}</strong><p>{description}</p>{action ? <div className="empty-state__action">{action}</div> : null}</div>;
}

export function Modal({ open, title, description, children, onClose, closeDisabled = false }: {
  open: boolean; title: string; description?: string; children: ReactNode; onClose: () => void; closeDisabled?: boolean;
}) {
  const titleId = useId();
  const descriptionId = useId();
  const dialogRef = useRef<HTMLElement>(null);
  const closeRef = useRef(onClose);
  const closeDisabledRef = useRef(closeDisabled);
  useEffect(() => { closeRef.current = onClose; }, [onClose]);
  useEffect(() => { closeDisabledRef.current = closeDisabled; }, [closeDisabled]);

  useEffect(() => {
    if (!open) return;
    const previousFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
    const dialog = dialogRef.current;
    const previousBodyOverflow = document.body.style.overflow;
    document.body.style.overflow = "hidden";
    const selector = [
      "a[href]", "button:not([disabled])", "input:not([disabled])",
      "select:not([disabled])", "textarea:not([disabled])",
      "[tabindex]:not([tabindex=\"-1\"])",
    ].join(",");
    const getFocusable = () => Array.from(dialog?.querySelectorAll<HTMLElement>(selector) ?? [])
      .filter((element) => !element.hidden && element.getAttribute("aria-hidden") !== "true");
    (getFocusable()[0] || dialog)?.focus();

    function onKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        if (!closeDisabledRef.current) closeRef.current();
        return;
      }
      if (event.key !== "Tab" || !dialog) return;
      const focusable = getFocusable();
      if (!focusable.length) {
        event.preventDefault();
        dialog.focus();
        return;
      }
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && (document.activeElement === first || !dialog.contains(document.activeElement))) {
        event.preventDefault(); last.focus();
      } else if (!event.shiftKey && (document.activeElement === last || !dialog.contains(document.activeElement))) {
        event.preventDefault(); first.focus();
      }
    }

    document.addEventListener("keydown", onKeyDown);
    return () => {
      document.removeEventListener("keydown", onKeyDown);
      document.body.style.overflow = previousBodyOverflow;
      previousFocus?.focus();
    };
  }, [open]);

  if (!open) return null;
  return createPortal(
    <div className="modal-backdrop" role="presentation"
      onMouseDown={(event) => { if (!closeDisabled && event.target === event.currentTarget) onClose(); }}>
      <section ref={dialogRef} className="modal-card" role="dialog" aria-modal="true"
        aria-labelledby={titleId} aria-describedby={description ? descriptionId : undefined} tabIndex={-1}>
        <button className="modal-close" type="button" onClick={onClose} disabled={closeDisabled} aria-label="Tutup dialog"><X size={18} /></button>
        <h2 id={titleId}>{title}</h2>
        {description ? <p id={descriptionId}>{description}</p> : null}
        <div className="modal-card__body">{children}</div>
      </section>
    </div>,
    document.body,
  );
}

export function Field({ label, hint, error, children }: { label: string; hint?: string; error?: string; children: ReactNode }) {
  return <label className="form-field"><span className="form-field__label">{label}</span>{children}{hint ? <small className="form-field__hint">{hint}</small> : null}{error ? <small className="form-field__error">{error}</small> : null}</label>;
}

export function PageSection({ title, action, children }: { title: string; action?: ReactNode; children: ReactNode }) {
  return <section className="page-section"><div className="section-heading"><h2>{title}</h2>{action}</div>{children}</section>;
}

export function ConfirmModal({ open, title, description, confirmText = "Ya, lanjutkan", destructive = false, loading = false, onConfirm, onClose }: {
  open: boolean; title: string; description: string; confirmText?: string; destructive?: boolean;
  loading?: boolean; onConfirm: () => void; onClose: () => void;
}) {
  return <Modal open={open} title={title} description={description} onClose={onClose} closeDisabled={loading}>
    <div className="modal-actions">
      <Button variant="secondary" onClick={onClose} disabled={loading}>Batal</Button>
      <Button variant={destructive ? "danger" : "primary"} onClick={onConfirm} disabled={loading}>
        {loading ? "Memproses…" : confirmText}
      </Button>
    </div>
  </Modal>;
}

export function formatStatus(status: ReservationStatus) { return statusLabel(status); }
