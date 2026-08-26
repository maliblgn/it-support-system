import { AlertCircle, CheckCircle2, History, Inbox, LoaderCircle, RefreshCw, X } from "lucide-react";
import { useEffect, useRef } from "react";

import { priorityLabels } from "../utils/format";

export function LoadingScreen({ label = "Bilgiler yükleniyor…" }) {
  return (
    <div className="state-panel state-panel--loading" role="status">
      <LoaderCircle className="spin" size={24} aria-hidden="true" />
      <span>{label}</span>
    </div>
  );
}

export function ErrorNotice({ message, onDismiss }) {
  if (!message) return null;
  return (
    <div className="notice notice--error" role="alert">
      <AlertCircle size={19} aria-hidden="true" />
      <span>{message}</span>
      {onDismiss && (
        <button className="icon-button" type="button" onClick={onDismiss} aria-label="Uyarıyı kapat">
          <X size={17} />
        </button>
      )}
    </div>
  );
}

export function LoadFailure({ message, onRetry }) {
  return (
    <div className="state-panel state-panel--error" role="alert">
      <AlertCircle size={25} aria-hidden="true" />
      <div><strong>Bilgiler yüklenemedi</strong><span>{message || "Beklenmeyen bir bağlantı sorunu oluştu."}</span></div>
      {onRetry && <button className="button button--secondary button--small" type="button" onClick={onRetry}><RefreshCw size={16} /> Yeniden dene</button>}
    </div>
  );
}

export function SuccessNotice({ message }) {
  if (!message) return null;
  return (
    <div className="notice notice--success" role="status">
      <CheckCircle2 size={19} aria-hidden="true" />
      <span>{message}</span>
    </div>
  );
}

export function EmptyState({ title = "Henüz kayıt yok", description, action }) {
  return (
    <div className="empty-state">
      <span className="empty-state__icon"><Inbox size={28} /></span>
      <h3>{title}</h3>
      {description && <p>{description}</p>}
      {action}
    </div>
  );
}

export function StatusBadge({ resolved, outcome }) {
  const couldNotResolve = resolved && outcome === "UNRESOLVED";
  return (
    <span className={`badge ${couldNotResolve ? "badge--unresolved" : resolved ? "badge--resolved" : "badge--open"}`}>
      <span className="badge__dot" />
      {couldNotResolve ? "Çözülemedi" : resolved ? "Çözüldü" : "Açık"}
    </span>
  );
}

export function PriorityBadge({ priority }) {
  if (!priority) return <span className="badge badge--neutral">Belirlenmedi</span>;
  return (
    <span className={`badge badge--priority-${priority.toLowerCase()}`}>
      {priorityLabels[priority] || priority}
    </span>
  );
}

export function Pagination({ page, pages, onPageChange }) {
  if (pages <= 1) return null;
  return (
    <nav className="pagination" aria-label="Sayfalama">
      <button
        className="button button--ghost button--small"
        type="button"
        disabled={page <= 1}
        onClick={() => onPageChange(page - 1)}
      >
        Önceki
      </button>
      <span><strong>{page}</strong> / {pages}</span>
      <button
        className="button button--ghost button--small"
        type="button"
        disabled={page >= pages}
        onClick={() => onPageChange(page + 1)}
      >
        Sonraki
      </button>
    </nav>
  );
}

export function PageHeader({ eyebrow, title, description, actions }) {
  return (
    <header className="page-header">
      <div>
        {eyebrow && <p className="eyebrow">{eyebrow}</p>}
        <h1>{title}</h1>
        {description && <p className="page-header__description">{description}</p>}
      </div>
      {actions && <div className="page-header__actions">{actions}</div>}
    </header>
  );
}

const historyLabels = {
  TICKET_CREATED: "Ticket oluşturuldu",
  TICKET_UPDATED: "Ticket bilgileri güncellendi",
  TICKET_ASSIGNED_SELF: "Ticket üzerine alındı",
  TICKET_ASSIGNED_BY_ADMIN: "Ticket yönetici tarafından atandı",
  TICKET_PRIORITY_CHANGED: "Öncelik değiştirildi",
  TICKET_ATTACHMENT_ADDED: "Dosya eklendi",
  TICKET_ATTACHMENT_REMOVED: "Dosya kaldırıldı",
  TICKET_RESOLVED: "Ticket çözüldü",
  TICKET_MARKED_UNRESOLVED: "Ticket çözülemedi olarak kapatıldı",
  TICKET_DELETED: "Ticket geri dönüşüm kutusuna taşındı",
  TICKET_RESTORED: "Ticket geri yüklendi",
  TICKET_TAG_ADDED: "Etiket eklendi",
  TICKET_TAG_REMOVED: "Etiket kaldırıldı",
  TICKET_WATCH_STARTED: "Ticket takibe alındı",
  TICKET_WATCH_STOPPED: "Ticket takibi bırakıldı",
};

export function TicketTimeline({ items = [], formatTimestamp }) {
  return (
    <section className="card timeline-card">
      <div className="card__header"><div><h2>İşlem geçmişi</h2><p>Ticket üzerinde yapılan önemli değişiklikler</p></div><History size={21} /></div>
      {items.length ? <ol className="timeline-list">{items.map((item) => (
        <li key={item.id}>
          <span className="timeline-list__dot" />
          <div><strong>{historyLabels[item.action] || item.action}</strong><span>{item.actor_name || "Sistem"}</span><small>{formatTimestamp(item.created_at)}</small></div>
        </li>
      ))}</ol> : <EmptyState title="İşlem geçmişi bulunmuyor" description="Yeni işlemler burada zaman sırasıyla gösterilecek." />}
    </section>
  );
}

export function ConfirmDialog({ open, title, description, confirmLabel = "Onayla", busy, confirmDisabled = false, onConfirm, onClose, tone = "danger", children }) {
  const dialogRef = useRef(null);
  const closeRef = useRef(null);
  const onCloseRef = useRef(onClose);
  const busyRef = useRef(busy);

  useEffect(() => {
    onCloseRef.current = onClose;
    busyRef.current = busy;
  }, [onClose, busy]);

  useEffect(() => {
    if (!open) return undefined;
    const previouslyFocused = document.activeElement;
    const firstField = dialogRef.current?.querySelector("input:not(:disabled), select:not(:disabled), textarea:not(:disabled)");
    (firstField || closeRef.current)?.focus();
    function handleKeyDown(event) {
      if (event.key === "Escape" && !busyRef.current) onCloseRef.current();
      if (event.key !== "Tab" || !dialogRef.current) return;
      const focusable = dialogRef.current.querySelectorAll("button:not(:disabled), [href], input:not(:disabled), select:not(:disabled), textarea:not(:disabled)");
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last?.focus(); }
      if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first?.focus(); }
    }
    document.addEventListener("keydown", handleKeyDown);
    return () => {
      document.removeEventListener("keydown", handleKeyDown);
      previouslyFocused?.focus?.();
    };
  }, [open]);

  if (!open) return null;
  return (
    <div className="modal-backdrop" role="presentation" onMouseDown={() => { if (!busy) onClose(); }}>
      <section
        ref={dialogRef}
        className="modal-card"
        role="dialog"
        aria-modal="true"
        aria-labelledby="confirm-title"
        onMouseDown={(event) => event.stopPropagation()}
      >
        <button ref={closeRef} className="modal-card__close" type="button" onClick={onClose} aria-label="Pencereyi kapat" disabled={busy}>
          <X size={20} />
        </button>
        <h2 id="confirm-title">{title}</h2>
        <p>{description}</p>
        {children}
        <div className="modal-card__actions">
          <button className="button button--ghost" type="button" onClick={onClose} disabled={busy}>Vazgeç</button>
          <button className={`button ${tone === "danger" ? "button--danger" : "button--primary"}`} type="button" onClick={onConfirm} disabled={busy || confirmDisabled}>
            {busy ? "İşleniyor…" : confirmLabel}
          </button>
        </div>
      </section>
    </div>
  );
}
