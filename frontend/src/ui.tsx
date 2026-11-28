import { createContext, useCallback, useContext, useEffect, useId, useMemo, useRef, useState, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { IconAlertCircle as AlertCircle, IconAlertTriangle as Warning, IconCircleCheck as Check, IconInfoCircle as Info, IconLoader2 as LoaderCircle, IconX as X } from "@tabler/icons-react";
import { statusLabel } from "./api";
import type { ReservationStatus } from "./types";

export function cleanLocationLabel(value?: string | null): string | null {
  const normalized = value?.trim();
  if (!normalized) return null;
  if (/^(belum ditentukan|belum tersedia|belum diatur|not set|not available|unknown|n\/?a|-)$/i.test(normalized)) return null;
  return normalized;
}

export function BrandLogo({ variant = "navigation" }: { variant?: "navigation" | "auth" | "loading" }) {
  return (
    <span className={"brand-lockup brand-lockup--" + variant} aria-label="RuangKampus — Find the Room. Book the Space.">
      <img className="brand-lockup__mark" src="/brand/favicon/favicon-128x128.png" alt="" aria-hidden="true" />
      <span className="brand-lockup__words"><b>RuangKampus</b><small>Find the Room. Book the Space.</small></span>
    </span>
  );
}

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

export function Notice({ children, tone = "info", floating = false }: { children: ReactNode; tone?: "info" | "success" | "warning" | "error"; floating?: boolean }) {
  const toast = useContext(ToastContext);
  useEffect(() => {
    if (!floating || typeof children !== "string" || !children.trim()) return;
    toast.notify(children, { tone });
  }, [children, floating, toast.notify, tone]);
  if (floating) return null;
  const Icon = tone === "success" ? Check : tone === "error" ? AlertCircle : Info;
  return <div className={"notice notice--" + tone} role={tone === "error" ? "alert" : "status"}><Icon size={17} /><div>{children}</div></div>;
}

export type ToastTone = "success" | "error" | "warning" | "info";
export interface ToastAction { label: string; onClick: () => void; }
interface ToastOptions { title?: string; tone?: ToastTone; duration?: number; action?: ToastAction; }
interface ToastItem extends ToastOptions { id: number; message: ReactNode; exiting: boolean; }
type ToastContextValue = { notify: (message: ReactNode, options?: ToastOptions) => number; dismiss: (id: number) => void; };

const ToastContext = createContext<ToastContextValue>({ notify: () => 0, dismiss: () => undefined });

function FloatingToast({ item, onDismiss, suspended = false }: { item: ToastItem; onDismiss: (id: number) => void; suspended?: boolean }) {
  const [paused, setPaused] = useState(false);
  const remaining = useRef(item.duration ?? 5200);
  const timerStartedAt = useRef(0);
  const timer = useRef<number | null>(null);
  const ToneIcon = item.tone === "success" ? Check : item.tone === "error" ? AlertCircle : item.tone === "warning" ? Warning : Info;
  const timerPaused = paused || suspended;

  useEffect(() => {
    if (timerPaused || item.exiting) return;
    timerStartedAt.current = Date.now();
    timer.current = window.setTimeout(() => onDismiss(item.id), remaining.current);
    return () => {
      if (timer.current !== null) window.clearTimeout(timer.current);
      timer.current = null;
      if (!item.exiting) remaining.current = Math.max(0, remaining.current - (Date.now() - timerStartedAt.current));
    };
  }, [item.exiting, item.id, onDismiss, timerPaused]);

  return <article className={"floating-toast floating-toast--" + (item.tone || "info") + (item.exiting ? " is-exiting" : "")}
    role={item.tone === "error" ? "alert" : "status"}
    aria-atomic="true"
    onPointerEnter={() => setPaused(true)} onPointerLeave={() => setPaused(false)}
    onFocus={() => setPaused(true)} onBlur={(event) => { if (!(event.relatedTarget instanceof Node) || !event.currentTarget.contains(event.relatedTarget)) setPaused(false); }}>
    <span className="floating-toast__icon" aria-hidden="true"><ToneIcon size={19} strokeWidth={2} /></span>
    <span className="floating-toast__copy">
      <strong>{item.title || (item.tone === "success" ? "Berhasil" : item.tone === "error" ? "Terjadi kesalahan" : item.tone === "warning" ? "Perlu perhatian" : "Informasi")}</strong>
      <span>{item.message}</span>
      {item.action ? <button className="floating-toast__action" type="button" onClick={() => { item.action?.onClick(); onDismiss(item.id); }}>{item.action.label}</button> : null}
    </span>
    <button className="floating-toast__close" type="button" aria-label="Tutup notifikasi" onClick={() => onDismiss(item.id)}><X size={16} /></button>
    {!item.exiting ? <span className="floating-toast__timer" aria-hidden="true" style={{ animationDuration: `${item.duration ?? 5200}ms`, animationPlayState: timerPaused ? "paused" : "running" }} /> : null}
  </article>;
}

export function ToastProvider({ children }: { children: ReactNode }) {
  const [items, setItems] = useState<ToastItem[]>([]);
  const [surfaceBlocked, setSurfaceBlocked] = useState(false);
  const nextId = useRef(0);
  const exitTimers = useRef(new Map<number, number>());

  const dismiss = useCallback((id: number) => {
    setItems((current) => {
      const item = current.find((entry) => entry.id === id);
      if (!item || item.exiting) return current;
      return current.map((entry) => entry.id === id ? { ...entry, exiting: true } : entry);
    });
    if (!exitTimers.current.has(id)) {
      exitTimers.current.set(id, window.setTimeout(() => {
        setItems((current) => current.filter((entry) => entry.id !== id));
        exitTimers.current.delete(id);
      }, 140));
    }
  }, []);

  const notify = useCallback((message: ReactNode, options: ToastOptions = {}) => {
    const id = ++nextId.current;
    setItems((current) => {
      const tone = options.tone || "info";
      const duration = options.duration ?? (tone === "error" ? 8000 : tone === "warning" ? 6800 : tone === "info" ? 6000 : 4800);
      const duplicate = current.some((item) => !item.exiting && item.tone === tone && item.title === options.title && item.message === message);
      return duplicate ? current : [...current.slice(-3), { id, message, exiting: false, ...options, duration, tone }];
    });
    return id;
  }, []);

  const contextValue = useMemo(() => ({ notify, dismiss }), [dismiss, notify]);

  useEffect(() => {
    const syncBlockedState = () => setSurfaceBlocked(
      document.visibilityState !== "visible" || Boolean(document.querySelector(".modal-backdrop[role='presentation']")),
    );
    const observer = new MutationObserver(syncBlockedState);
    observer.observe(document.body, { childList: true });
    document.addEventListener("visibilitychange", syncBlockedState);
    syncBlockedState();
    return () => {
      observer.disconnect();
      document.removeEventListener("visibilitychange", syncBlockedState);
      exitTimers.current.forEach((timer) => window.clearTimeout(timer));
    };
  }, []);

  return <ToastContext.Provider value={contextValue}>
    {children}
    <div className="floating-toast-viewport" aria-label="Notifikasi terbaru">
      {items.map((item) => <FloatingToast key={item.id} item={item} onDismiss={dismiss} suspended={surfaceBlocked} />)}
    </div>
  </ToastContext.Provider>;
}

export function useToast() {
  return useContext(ToastContext);
}

export function Loading({ label = "Memuat data…" }: { label?: string }) {
  return <div className="loading-inline"><LoaderCircle className="spinner-icon" size={20} /><span>{label}</span></div>;
}

export function RoomGridSkeleton({ label, count = 6 }: { label: string; count?: number }) {
  return <div className="room-grid room-grid--loading" role="status" aria-label={label}>
    <span className="sr-only">{label}</span>
    {Array.from({ length: count }, (_, index) => <article className="room-card room-skeleton" key={index} aria-hidden="true">
      <div className="room-card__media room-skeleton__media" />
      <div className="room-card__body room-skeleton__body">
        <span className="room-skeleton__shape room-skeleton__shape--short" />
        <span className="room-skeleton__shape room-skeleton__shape--title" />
        <span className="room-skeleton__shape" />
        <span className="room-skeleton__shape room-skeleton__shape--medium" />
        <span className="room-skeleton__shape room-skeleton__shape--button" />
      </div>
    </article>)}
  </div>;
}

export function EmptyState({ title, description, action, icon }: { title: string; description: string; action?: ReactNode; icon?: ReactNode }) {
  return <div className="empty-state"><span className="empty-state__icon">{icon || <Info size={22} />}</span><strong>{title}</strong><p>{description}</p>{action ? <div className="empty-state__action">{action}</div> : null}</div>;
}

export function Modal({ open, title, description, children, onClose, closeDisabled = false }: {
  open: boolean; title: string; description?: string; children: ReactNode; onClose: () => void; closeDisabled?: boolean;
}) {
  const titleId = useId();
  const descriptionId = useId();
  const [present, setPresent] = useState(open);
  const [closing, setClosing] = useState(false);
  const dialogRef = useRef<HTMLElement>(null);
  const closeRef = useRef(onClose);
  const closeDisabledRef = useRef(closeDisabled);
  useEffect(() => { closeRef.current = onClose; }, [onClose]);
  useEffect(() => { closeDisabledRef.current = closeDisabled; }, [closeDisabled]);

  useEffect(() => {
    if (open) {
      setPresent(true);
      setClosing(false);
      return;
    }
    if (!present) return;
    setClosing(true);
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) {
      setPresent(false);
      setClosing(false);
      return;
    }
    const timeout = window.setTimeout(() => {
      setPresent(false);
      setClosing(false);
    }, 120);
    return () => window.clearTimeout(timeout);
  }, [open, present]);

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

  if (!present) return null;
  return createPortal(
    <div className={"modal-backdrop" + (closing ? " is-closing" : "")} role="presentation" aria-hidden={closing || undefined} inert={closing}
      onMouseDown={(event) => { if (!closing && !closeDisabled && event.target === event.currentTarget) onClose(); }}>
      <section ref={dialogRef} className={"modal-card" + (closing ? " is-closing" : "")} role="dialog" aria-modal="true"
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
