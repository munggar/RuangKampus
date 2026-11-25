import type { ReactNode } from "react";
import { AlertCircle, Check, Info, LoaderCircle, X } from "lucide-react";
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
function statusLabel(status: string) {
  const values: Record<string, string> = {
    PENDING: "Menunggu", APPROVED: "Disetujui", REJECTED: "Ditolak",
    CANCELLED: "Dibatalkan", COMPLETED: "Selesai", ACTIVE: "Aktif",
    INACTIVE: "Nonaktif", MAINTENANCE: "Pemeliharaan",
  };
  return values[status] || status;
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

export function Modal({ open, title, description, children, onClose }: {
  open: boolean; title: string; description?: string; children: ReactNode; onClose: () => void;
}) {
  if (!open) return null;
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) onClose(); }}>
      <section className="modal-card" role="dialog" aria-modal="true" aria-labelledby="modal-title">
        <button className="modal-close" type="button" onClick={onClose} aria-label="Tutup dialog"><X size={18} /></button>
        <h2 id="modal-title">{title}</h2>
        {description ? <p>{description}</p> : null}
        <div className="modal-card__body">{children}</div>
      </section>
    </div>
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
  return <Modal open={open} title={title} description={description} onClose={onClose}>
    <div className="modal-actions">
      <Button variant="secondary" onClick={onClose} disabled={loading}>Batal</Button>
      <Button variant={destructive ? "danger" : "primary"} onClick={onConfirm} disabled={loading}>
        {loading ? "Memproses…" : confirmText}
      </Button>
    </div>
  </Modal>;
}

export function formatStatus(status: ReservationStatus) { return statusLabel(status); }