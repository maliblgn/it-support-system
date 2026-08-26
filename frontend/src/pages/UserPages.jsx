import {
  ArrowLeft,
  Bell,
  CheckCircle2,
  CircleX,
  Download,
  File,
  FileUp,
  MessageSquareText,
  Paperclip,
  Pencil,
  Plus,
  Save,
  Search,
  Send,
  Star,
  KeyRound,
  Trash2,
} from "lucide-react";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, useLocation, useNavigate, useParams } from "react-router-dom";

import { api, saveBlob } from "../api/client";
import { useAuth } from "../auth/AuthContext";
import {
  ConfirmDialog,
  EmptyState,
  ErrorNotice,
  LoadingScreen,
  LoadFailure,
  PageHeader,
  Pagination,
  PriorityBadge,
  StatusBadge,
  SuccessNotice,
  TicketTimeline,
} from "../components/UI";
import {
  formatDate,
  formatFileSize,
  formatRelativeDate,
  priorityLabels,
} from "../utils/format";

function TicketTable({ tickets, emptyAction }) {
  if (!tickets.length) {
    return (
      <EmptyState
        title="Henüz talep yok"
        description="Yeni bir destek talebi oluşturduğunuzda burada görünecek."
        action={emptyAction}
      />
    );
  }
  return (
    <div className="table-wrap">
      <table className="data-table">
        <thead>
          <tr>
            <th>Talep no</th>
            <th>Konu</th>
            <th>Öncelik</th>
            <th>Durum</th>
            <th>Son güncelleme</th>
            <th aria-label="Aç" />
          </tr>
        </thead>
        <tbody>
          {tickets.map((ticket) => (
            <tr key={ticket.id}>
              <td data-label="Talep no">
                <Link className="ticket-number" to={`/tickets/${ticket.id}`}>
                  {ticket.ticket_number}
                </Link>
              </td>
              <td data-label="Konu">
                <span className="cell-stack">
                  <strong>{ticket.subject}</strong>
                  <small>{ticket.department_snapshot}</small>
                </span>
              </td>
              <td data-label="Öncelik">
                <PriorityBadge priority={ticket.priority} />
              </td>
              <td data-label="Durum">
                <StatusBadge
                  resolved={ticket.is_resolved}
                  outcome={ticket.resolution_outcome}
                />
              </td>
              <td data-label="Son güncelleme">
                <span className="cell-stack">
                  <strong>{formatRelativeDate(ticket.updated_at)}</strong>
                  <small>{formatDate(ticket.updated_at)}</small>
                </span>
              </td>
              <td data-label="İşlem">
                <Link className="table-link" to={`/tickets/${ticket.id}`}>
                  Detay
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function UserDashboardPage() {
  const { user } = useAuth();
  const [tickets, setTickets] = useState(null);
  const [notifications, setNotifications] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    Promise.all([api.userTickets(1, 5), api.notifications(1)])
      .then(([ticketPage, notificationPage]) => {
        setTickets(ticketPage);
        setNotifications(notificationPage);
        setError("");
      })
      .catch((requestError) => setError(requestError.message));
  }, []);
  useEffect(() => {
    load();
  }, [load]);

  if (!tickets || !notifications)
    return (
      <div className="page">
        {error ? (
          <LoadFailure message={error} onRetry={load} />
        ) : (
          <LoadingScreen />
        )}
      </div>
    );
  const openCount = tickets.items.filter(
    (ticket) => !ticket.is_resolved,
  ).length;
  const resolvedCount = tickets.items.filter(
    (ticket) => ticket.resolution_outcome === "RESOLVED",
  ).length;
  const unreadCount = notifications.items.filter(
    (item) => !item.is_read,
  ).length;

  return (
    <div className="page">
      <PageHeader
        eyebrow="Çalışan alanı"
        title={`Merhaba, ${user.first_name}`}
        description="Destek taleplerinizin güncel durumunu buradan takip edebilirsiniz."
        actions={
          <Link className="button button--primary" to="/tickets/new">
            <Plus size={18} /> Yeni talep
          </Link>
        }
      />
      <ErrorNotice message={error} />
      <section className="metric-grid" aria-label="Talep özeti">
        <article className="metric-card">
          <span className="metric-card__label">Toplam talep</span>
          <strong>{tickets.total}</strong>
          <small>Tüm kayıtlarınız</small>
        </article>
        <article className="metric-card metric-card--amber">
          <span className="metric-card__label">Son 5'te açık</span>
          <strong>{openCount}</strong>
          <small>İşlem bekleyen</small>
        </article>
        <article className="metric-card metric-card--green">
          <span className="metric-card__label">Son 5'te çözülen</span>
          <strong>{resolvedCount}</strong>
          <small>Başarıyla tamamlanan</small>
        </article>
        <article className="metric-card metric-card--blue">
          <span className="metric-card__label">Okunmamış bildirim</span>
          <strong>{unreadCount}</strong>
          <small>Yeni gelişmeler</small>
        </article>
      </section>
      <div className="content-grid content-grid--dashboard">
        <section className="card card--flush">
          <div className="card__header">
            <div>
              <h2>Son talepler</h2>
              <p>En son oluşturduğunuz destek kayıtları</p>
            </div>
            <Link className="text-link" to="/tickets">
              Tümünü gör
            </Link>
          </div>
          <TicketTable
            tickets={tickets.items}
            emptyAction={
              <Link className="button button--primary" to="/tickets/new">
                İlk talebi oluştur
              </Link>
            }
          />
        </section>
        <aside className="card">
          <div className="card__header">
            <div>
              <h2>Bildirimler</h2>
              <p>Son durum değişiklikleri</p>
            </div>
            <Bell size={20} />
          </div>
          <div className="notification-mini-list">
            {notifications.items.slice(0, 4).map((item) => (
              <Link
                key={item.id}
                to="/notifications"
                className={`notification-mini ${item.is_read ? "" : "notification-mini--unread"}`}
              >
                <span className="notification-mini__icon">
                  <CheckCircle2 size={17} />
                </span>
                <span>
                  <strong>{item.title}</strong>
                  <small>{formatDate(item.created_at)}</small>
                </span>
              </Link>
            ))}
            {!notifications.items.length && (
              <EmptyState
                title="Bildirim yok"
                description="Ticket gelişmeleri burada görünecek."
              />
            )}
          </div>
        </aside>
      </div>
    </div>
  );
}

export function UserTicketsPage() {
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [error, setError] = useState("");
  const [filters, setFilters] = useState({
    search: "",
    status: "",
    priority: "",
  });
  const [query, setQuery] = useState(filters);

  const load = useCallback(() => {
    let active = true;
    api
      .userTickets(page, 20, query)
      .then((value) => {
        if (active) {
          setData(value);
          setError("");
        }
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      });
    return () => {
      active = false;
    };
  }, [page, query]);
  useEffect(() => load(), [load]);

  if (!data)
    return (
      <div className="page">
        {error ? (
          <LoadFailure message={error} onRetry={load} />
        ) : (
          <LoadingScreen label="Talepleriniz yükleniyor…" />
        )}
      </div>
    );
  return (
    <div className="page">
      <PageHeader
        eyebrow="Destek kayıtları"
        title="Taleplerim"
        description="Açık ve geçmiş tüm destek taleplerinizi görüntüleyin."
        actions={
          <Link className="button button--primary" to="/tickets/new">
            <Plus size={18} /> Yeni talep
          </Link>
        }
      />
      <ErrorNotice message={error} />
      <form
        className="toolbar toolbar--search"
        onSubmit={(event) => {
          event.preventDefault();
          setPage(1);
          setQuery(filters);
        }}
      >
        <label className="search-field">
          <Search size={18} />
          <input
            value={filters.search}
            onChange={(event) =>
              setFilters({ ...filters, search: event.target.value })
            }
            placeholder="Talep no, konu veya açıklama ara"
          />
          <button
            className="button button--secondary button--small"
            type="submit"
          >
            Ara
          </button>
        </label>
        <select
          aria-label="Durum filtresi"
          value={filters.status}
          onChange={(event) =>
            setFilters({ ...filters, status: event.target.value })
          }
        >
          <option value="">Tüm durumlar</option>
          <option value="open">Açık</option>
          <option value="resolved">Çözüldü</option>
          <option value="unresolved">Çözülemedi</option>
        </select>
        <select
          aria-label="Öncelik filtresi"
          value={filters.priority}
          onChange={(event) =>
            setFilters({ ...filters, priority: event.target.value })
          }
        >
          <option value="">Tüm öncelikler</option>
          {Object.entries(priorityLabels).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <button
          className="button button--secondary button--small"
          type="submit"
        >
          Filtrele
        </button>
        <span className="toolbar__count">{data.total} kayıt</span>
      </form>
      <section className="card card--flush">
        <TicketTable
          tickets={data.items}
          emptyAction={
            <Link className="button button--primary" to="/tickets/new">
              Yeni talep oluştur
            </Link>
          }
        />
      </section>
      <Pagination page={page} pages={data.pages} onPageChange={setPage} />
    </div>
  );
}

export function NewTicketPage() {
  const navigate = useNavigate();
  const fileInput = useRef(null);
  const [form, setForm] = useState({ subject: "", description: "" });
  const [files, setFiles] = useState([]);
  const [dragActive, setDragActive] = useState(false);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  function queueFiles(selectedFiles) {
    const allowedExtensions = [".png", ".jpg", ".jpeg", ".pdf"];
    const selected = Array.from(selectedFiles || []);
    const invalid = selected.find(
      (file) =>
        !allowedExtensions.some((extension) =>
          file.name.toLocaleLowerCase("tr-TR").endsWith(extension),
        ) || file.size > 10 * 1024 * 1024,
    );
    if (invalid) {
      setError(
        "Yalnızca PNG, JPG/JPEG veya PDF dosyaları ve dosya başına en fazla 10 MB yükleyebilirsiniz.",
      );
      return;
    }
    setError("");
    setFiles((current) => {
      const unique = selected.filter(
        (file) =>
          !current.some(
            (item) => item.name === file.name && item.size === file.size,
          ),
      );
      return [...current, ...unique].slice(0, 5);
    });
  }
  function addFiles(event) {
    queueFiles(event.target.files);
    event.target.value = "";
  }
  function handleDrop(event) {
    event.preventDefault();
    setDragActive(false);
    queueFiles(event.dataTransfer.files);
  }
  async function handleSubmit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const ticket = await api.createTicket(form);
      const failedFiles = [];
      for (const file of files) {
        try {
          await api.uploadAttachment(ticket.id, file);
        } catch {
          failedFiles.push(file.name);
        }
      }
      navigate(`/tickets/${ticket.id}`, {
        replace: true,
        state: {
          created: true,
          uploadWarning: failedFiles.length
            ? `${failedFiles.length} dosya yüklenemedi (${failedFiles.join(", ")}). Ticket oluşturuldu; dosyaları bu ekrandan yeniden ekleyebilirsiniz.`
            : "",
        },
      });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="page page--form">
      <Link className="back-link" to="/tickets">
        <ArrowLeft size={17} /> Taleplerime dön
      </Link>
      <PageHeader
        eyebrow="Yeni destek kaydı"
        title="Nasıl yardımcı olabiliriz?"
        description="Sorunu açık ve anlaşılır şekilde yazın. IT ekibi talebinizi değerlendirip önceliklendirecektir."
      />
      <ErrorNotice message={error} onDismiss={() => setError("")} />
      <form className="ticket-form" onSubmit={handleSubmit}>
        <section className="card ticket-form__section">
          <div className="form-section">
            <span className="form-section__number">1</span>
            <div>
              <h2>Talep bilgileri</h2>
              <p>Probleminizi kısaca özetleyin ve ayrıntıları paylaşın.</p>
            </div>
          </div>
          <label className="field">
            <span>Konu</span>
            <input
              value={form.subject}
              onChange={(event) =>
                setForm({ ...form, subject: event.target.value })
              }
              required
              maxLength={200}
              placeholder="Örn. Muhasebe yazıcısından çıktı alamıyorum"
            />
            <small>{form.subject.length}/200</small>
          </label>
          <label className="field">
            <span>Açıklama</span>
            <textarea
              value={form.description}
              onChange={(event) =>
                setForm({ ...form, description: event.target.value })
              }
              required
              maxLength={20000}
              rows={7}
              placeholder="Sorunun ne zaman başladığını, aldığınız hata mesajını ve denediğiniz adımları yazın."
            />
            <small>{form.description.length}/20.000</small>
          </label>
        </section>
        <section className="card ticket-form__section">
          <div className="form-section">
            <span className="form-section__number">2</span>
            <div>
              <h2>
                Dosya ekleri <small>(isteğe bağlı)</small>
              </h2>
              <p>PNG, JPG/JPEG veya PDF; dosya başına en fazla 10 MB.</p>
            </div>
          </div>
          <button
            className={`upload-zone ${dragActive ? "upload-zone--active" : ""}`}
            type="button"
            onClick={() => fileInput.current?.click()}
            onDragEnter={(event) => {
              event.preventDefault();
              setDragActive(true);
            }}
            onDragOver={(event) => event.preventDefault()}
            onDragLeave={() => setDragActive(false)}
            onDrop={handleDrop}
          >
            <span className="upload-zone__icon">
              <FileUp size={25} />
            </span>
            <span>
              <strong>
                Dosyaları buraya sürükleyin veya bilgisayardan seçin
              </strong>
              <small>{files.length}/5 dosya seçildi</small>
            </span>
          </button>
          <input
            ref={fileInput}
            className="sr-only"
            type="file"
            multiple
            accept=".png,.jpg,.jpeg,.pdf,image/png,image/jpeg,application/pdf"
            onChange={addFiles}
          />
          {!!files.length && (
            <div className="file-list">
              {files.map((file, index) => (
                <div className="file-row" key={`${file.name}-${index}`}>
                  <span className="file-row__icon">
                    <File size={18} />
                  </span>
                  <span>
                    <strong>{file.name}</strong>
                    <small>{formatFileSize(file.size)}</small>
                  </span>
                  <button
                    className="icon-button icon-button--danger"
                    type="button"
                    onClick={() =>
                      setFiles(
                        files.filter((_, itemIndex) => itemIndex !== index),
                      )
                    }
                    aria-label={`${file.name} dosyasını kaldır`}
                  >
                    <Trash2 size={17} />
                  </button>
                </div>
              ))}
            </div>
          )}
        </section>
        <div className="form-actions form-actions--page">
          <Link className="button button--ghost" to="/tickets">
            Vazgeç
          </Link>
          <button
            className="button button--primary"
            type="submit"
            disabled={busy}
          >
            {busy ? "Talep gönderiliyor…" : "Talebi gönder"}
            <Send size={18} />
          </button>
        </div>
      </form>
    </div>
  );
}

export function UserTicketDetailPage() {
  const { id } = useParams();
  const navigate = useNavigate();
  const location = useLocation();
  const [ticket, setTicket] = useState(null);
  const [history, setHistory] = useState([]);
  const [rating, setRating] = useState(null);
  const [ratingForm, setRatingForm] = useState({ score: 0, comment: "" });
  const [editMode, setEditMode] = useState(false);
  const [form, setForm] = useState({ subject: "", description: "" });
  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleteTicketOpen, setDeleteTicketOpen] = useState(false);
  const [deleteReason, setDeleteReason] = useState("");
  const [error, setError] = useState(location.state?.uploadWarning || "");
  const [success, setSuccess] = useState(
    location.state?.created ? "Talebiniz başarıyla oluşturuldu." : "",
  );
  const [busy, setBusy] = useState(false);

  const loadTicket = useCallback(async () => {
    setError("");
    try {
      const [value, events] = await Promise.all([
        api.ticket(id),
        api.ticketHistory(id),
      ]);
      setTicket(value);
      setHistory(events);
      setForm({ subject: value.subject, description: value.description });
      if (value.resolution_outcome === "RESOLVED") {
        const currentRating = await api.ticketRating(id);
        setRating(currentRating);
        setRatingForm({
          score: currentRating?.score || 0,
          comment: currentRating?.comment || "",
        });
      }
    } catch (requestError) {
      setError(requestError.message);
    }
  }, [id]);
  useEffect(() => {
    let active = true;
    Promise.all([api.ticket(id), api.ticketHistory(id)])
      .then(async ([value, events]) => {
        const currentRating =
          value.resolution_outcome === "RESOLVED"
            ? await api.ticketRating(id)
            : null;
        if (!active) return;
        setTicket(value);
        setHistory(events);
        setForm({ subject: value.subject, description: value.description });
        setRating(currentRating);
        setRatingForm({
          score: currentRating?.score || 0,
          comment: currentRating?.comment || "",
        });
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      });
    return () => {
      active = false;
    };
  }, [id]);

  async function saveEdit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const updated = await api.updateTicket(id, form);
      setTicket(updated);
      setEditMode(false);
      setSuccess("Talep bilgileriniz güncellendi.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }
  async function handleUpload(event) {
    const file = event.target.files?.[0];
    if (!file) return;
    setBusy(true);
    setError("");
    try {
      await api.uploadAttachment(id, file);
      await loadTicket();
      setSuccess("Dosya eklendi.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
      event.target.value = "";
    }
  }
  async function download(attachment) {
    try {
      const blob = await api.downloadAttachment(id, attachment.id);
      saveBlob(blob, attachment.original_file_name);
    } catch (requestError) {
      setError(requestError.message);
    }
  }
  async function removeAttachment() {
    setBusy(true);
    try {
      await api.deleteAttachment(id, deleteTarget.id);
      setDeleteTarget(null);
      await loadTicket();
      setSuccess("Dosya kaldırıldı.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }
  async function saveRating(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const saved = await api.saveTicketRating(id, {
        score: ratingForm.score,
        comment: ratingForm.comment.trim() || null,
      });
      setRating(saved);
      setSuccess("Değerlendirmeniz kaydedildi. Teşekkür ederiz.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }
  async function removeTicket() {
    setBusy(true);
    setError("");
    try {
      await api.deleteTicket(id, deleteReason);
      navigate("/tickets", { replace: true });
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  if (!ticket)
    return (
      <div className="page">
        {error ? (
          <LoadFailure message={error} onRetry={loadTicket} />
        ) : (
          <LoadingScreen label="Talep detayı yükleniyor…" />
        )}
      </div>
    );
  return (
    <div className="page">
      <Link className="back-link" to="/tickets">
        <ArrowLeft size={17} /> Taleplerime dön
      </Link>
      <PageHeader
        eyebrow={ticket.ticket_number}
        title={ticket.subject}
        description={`Oluşturulma: ${formatDate(ticket.created_at)}`}
        actions={
          <div className="header-badges">
            <StatusBadge
              resolved={ticket.is_resolved}
              outcome={ticket.resolution_outcome}
            />
            <PriorityBadge priority={ticket.priority} />
            {!ticket.is_resolved && (
              <button
                className="button button--danger button--small"
                type="button"
                onClick={() => setDeleteTicketOpen(true)}
              >
                <Trash2 size={16} /> Talebi sil
              </button>
            )}
          </div>
        }
      />
      <ErrorNotice message={error} onDismiss={() => setError("")} />
      <SuccessNotice message={success} />
      <div className="detail-layout">
        <div className="detail-layout__main">
          <section className="card">
            <div className="card__header">
              <div>
                <h2>Talep açıklaması</h2>
                <p>IT ekibine ilettiğiniz bilgiler</p>
              </div>
              {!ticket.is_resolved && !editMode && (
                <button
                  className="button button--ghost button--small"
                  type="button"
                  onClick={() => setEditMode(true)}
                >
                  <Pencil size={16} /> Düzenle
                </button>
              )}
            </div>
            {editMode ? (
              <form className="form-stack" onSubmit={saveEdit}>
                <label className="field">
                  <span>Konu</span>
                  <input
                    value={form.subject}
                    onChange={(event) =>
                      setForm({ ...form, subject: event.target.value })
                    }
                    required
                    maxLength={200}
                  />
                </label>
                <label className="field">
                  <span>Açıklama</span>
                  <textarea
                    rows={7}
                    value={form.description}
                    onChange={(event) =>
                      setForm({ ...form, description: event.target.value })
                    }
                    required
                  />
                </label>
                <div className="form-actions">
                  <button
                    className="button button--ghost"
                    type="button"
                    onClick={() => setEditMode(false)}
                  >
                    Vazgeç
                  </button>
                  <button
                    className="button button--primary"
                    type="submit"
                    disabled={busy}
                  >
                    <Save size={17} /> Kaydet
                  </button>
                </div>
              </form>
            ) : (
              <p className="long-copy">{ticket.description}</p>
            )}
          </section>
          {ticket.is_resolved && (
            <section
              className={`card resolution-card ${ticket.resolution_outcome === "UNRESOLVED" ? "resolution-card--unresolved" : ""}`}
            >
              <span className="resolution-card__icon">
                {ticket.resolution_outcome === "UNRESOLVED" ? (
                  <CircleX size={24} />
                ) : (
                  <CheckCircle2 size={24} />
                )}
              </span>
              <div>
                <p className="eyebrow">Sonuç bilgisi</p>
                <h2>
                  {ticket.resolution_outcome === "UNRESOLVED"
                    ? "Talebiniz çözülemedi"
                    : "Talebiniz çözüldü"}
                </h2>
                <p className="long-copy">{ticket.resolution_note}</p>
                <small>{formatDate(ticket.resolved_at)}</small>
              </div>
            </section>
          )}
          {ticket.resolution_outcome === "RESOLVED" && (
            <section className="card rating-card">
              <div className="card__header">
                <div>
                  <h2>Çözümü değerlendirin</h2>
                  <p>
                    {rating
                      ? `${rating.it_user_name} için verdiğiniz puanı güncelleyebilirsiniz.`
                      : "Sorununuzu çözen IT çalışanını 1–5 arasında puanlayın."}
                  </p>
                </div>
                <Star size={21} />
              </div>
              <form className="form-stack" onSubmit={saveRating}>
                <fieldset
                  className="star-rating"
                  disabled={
                    busy ||
                    (rating && new Date(rating.editable_until) < new Date())
                  }
                >
                  <legend>Puanınız</legend>
                  {[1, 2, 3, 4, 5].map((score) => (
                    <button
                      key={score}
                      className={
                        ratingForm.score >= score
                          ? "star-rating__star star-rating__star--active"
                          : "star-rating__star"
                      }
                      type="button"
                      onClick={() => setRatingForm({ ...ratingForm, score })}
                      aria-label={`${score} puan`}
                    >
                      <Star
                        size={29}
                        fill={
                          ratingForm.score >= score ? "currentColor" : "none"
                        }
                      />
                    </button>
                  ))}
                </fieldset>
                <label className="field">
                  <span>
                    Yorum <small>(isteğe bağlı)</small>
                  </span>
                  <textarea
                    rows={3}
                    maxLength={1000}
                    value={ratingForm.comment}
                    onChange={(event) =>
                      setRatingForm({
                        ...ratingForm,
                        comment: event.target.value,
                      })
                    }
                    placeholder="Çözüm süreciyle ilgili kısa değerlendirmeniz"
                    disabled={
                      busy ||
                      (rating && new Date(rating.editable_until) < new Date())
                    }
                  />
                </label>
                {rating && (
                  <p className="field-hint">
                    Değerlendirme {formatDate(rating.editable_until)} tarihine
                    kadar değiştirilebilir.
                  </p>
                )}
                <div className="form-actions">
                  <button
                    className="button button--primary"
                    type="submit"
                    disabled={
                      !ratingForm.score ||
                      busy ||
                      (rating && new Date(rating.editable_until) < new Date())
                    }
                  >
                    {rating ? "Puanı güncelle" : "Puanı gönder"}
                  </button>
                </div>
              </form>
            </section>
          )}
          <section className="card">
            <div className="card__header">
              <div>
                <h2>Dosya ekleri</h2>
                <p>{ticket.attachments.length} dosya</p>
              </div>
              {!ticket.is_resolved && (
                <label className="button button--ghost button--small">
                  <Paperclip size={16} /> Dosya ekle
                  <input
                    className="sr-only"
                    type="file"
                    accept=".png,.jpg,.jpeg,.pdf"
                    onChange={handleUpload}
                    disabled={busy}
                  />
                </label>
              )}
            </div>
            {ticket.attachments.length ? (
              <div className="file-list">
                {ticket.attachments.map((attachment) => (
                  <div className="file-row" key={attachment.id}>
                    <span className="file-row__icon">
                      <File size={18} />
                    </span>
                    <span>
                      <strong>{attachment.original_file_name}</strong>
                      <small>
                        {formatFileSize(attachment.file_size_bytes)} ·{" "}
                        {formatDate(attachment.created_at)}
                      </small>
                    </span>
                    <button
                      className="icon-button"
                      type="button"
                      onClick={() => download(attachment)}
                      aria-label="Dosyayı indir"
                    >
                      <Download size={17} />
                    </button>
                    {!ticket.is_resolved && (
                      <button
                        className="icon-button icon-button--danger"
                        type="button"
                        onClick={() => setDeleteTarget(attachment)}
                        aria-label="Dosyayı kaldır"
                      >
                        <Trash2 size={17} />
                      </button>
                    )}
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState
                title="Dosya eki yok"
                description="Bu talebe henüz dosya eklenmemiş."
              />
            )}
          </section>
          <TicketTimeline items={history} formatTimestamp={formatDate} />
        </div>
        <aside className="detail-layout__side card">
          <h2>Talep özeti</h2>
          <dl className="detail-list">
            <div>
              <dt>Talep no</dt>
              <dd>{ticket.ticket_number}</dd>
            </div>
            <div>
              <dt>Departman</dt>
              <dd>{ticket.department_snapshot}</dd>
            </div>
            <div>
              <dt>Öncelik</dt>
              <dd>
                <PriorityBadge priority={ticket.priority} />
              </dd>
            </div>
            <div>
              <dt>Durum</dt>
              <dd>
                <StatusBadge
                  resolved={ticket.is_resolved}
                  outcome={ticket.resolution_outcome}
                />
              </dd>
            </div>
            <div>
              <dt>Son güncelleme</dt>
              <dd>{formatDate(ticket.updated_at)}</dd>
            </div>
            {ticket.tags?.length > 0 && (
              <div>
                <dt>Etiketler</dt>
                <dd>
                  <span className="tag-list">
                    {ticket.tags.map((tag) => (
                      <span
                        key={tag.id}
                        className="tag-chip"
                        style={{ "--tag-color": tag.color }}
                      >
                        #{tag.name}
                      </span>
                    ))}
                  </span>
                </dd>
              </div>
            )}
          </dl>
        </aside>
      </div>
      <ConfirmDialog
        open={!!deleteTarget}
        title="Dosya kaldırılsın mı?"
        description={
          deleteTarget
            ? `${deleteTarget.original_file_name} kalıcı olarak kaldırılacaktır.`
            : ""
        }
        confirmLabel="Dosyayı kaldır"
        busy={busy}
        onClose={() => setDeleteTarget(null)}
        onConfirm={removeAttachment}
      />
      <ConfirmDialog
        open={deleteTicketOpen}
        title="Talep silinsin mi?"
        description="Talebiniz geri dönüşüm kutusuna taşınacak ve normal listelerden kaldırılacaktır. Çözülmüş talepler silinemez."
        confirmLabel="Talebi sil"
        busy={busy}
        confirmDisabled={deleteReason.trim().length < 3}
        onClose={() => {
          setDeleteTicketOpen(false);
          setDeleteReason("");
        }}
        onConfirm={removeTicket}
      >
        <label className="field modal-form">
          <span>Silme nedeni</span>
          <textarea
            rows={3}
            value={deleteReason}
            onChange={(event) => setDeleteReason(event.target.value)}
            placeholder="Örn. Yanlışlıkla oluşturdum"
          />
        </label>
      </ConfirmDialog>
    </div>
  );
}

export function ProfilePage() {
  const { user, setUser } = useAuth();
  const [form, setForm] = useState({
    email: user.email,
    first_name: user.first_name,
    last_name: user.last_name,
    phone: user.phone || "",
    department: user.department,
  });
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      const updated = await api.updateProfile({
        ...form,
        phone: form.phone.trim() || null,
      });
      setUser(updated);
      setSuccess("Profil bilgileriniz güncellendi.");
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }
  return (
    <div className="page page--narrow">
      <PageHeader
        eyebrow="Hesap ayarları"
        title="Profilim"
        description="İletişim, departman ve güvenlik bilgilerinizi yönetin."
      />
      <ErrorNotice message={error} />
      <SuccessNotice message={success} />
      <form className="card form-stack" onSubmit={submit}>
        <label className="field">
          <span>E-posta</span>
          <input
            type="email"
            value={form.email}
            onChange={(event) =>
              setForm({ ...form, email: event.target.value })
            }
            autoComplete="email"
            required
          />
          <small>
            Yalnızca sistemde izin verilen e-posta alan adları kullanılabilir.
          </small>
        </label>
        <div className="form-grid form-grid--two">
          <label className="field">
            <span>Ad</span>
            <input
              value={form.first_name}
              onChange={(event) =>
                setForm({ ...form, first_name: event.target.value })
              }
              required
            />
          </label>
          <label className="field">
            <span>Soyad</span>
            <input
              value={form.last_name}
              onChange={(event) =>
                setForm({ ...form, last_name: event.target.value })
              }
              required
            />
          </label>
        </div>
        <div className="form-grid form-grid--two">
          <label className="field">
            <span>Departman</span>
            <input
              value={form.department}
              onChange={(event) =>
                setForm({ ...form, department: event.target.value })
              }
              required
            />
          </label>
          <label className="field">
            <span>Telefon</span>
            <input
              value={form.phone}
              onChange={(event) =>
                setForm({ ...form, phone: event.target.value })
              }
            />
          </label>
        </div>
        <div className="form-actions">
          <button
            className="button button--primary"
            type="submit"
            disabled={busy}
          >
            <Save size={17} />{" "}
            {busy ? "Kaydediliyor…" : "Değişiklikleri kaydet"}
          </button>
        </div>
      </form>
      <section className="card profile-security-card">
        <div>
          <p className="eyebrow">Güvenlik</p>
          <h2>Şifre yönetimi</h2>
          <p>Hesap şifrenizi düzenli olarak güncel tutun.</p>
        </div>
        <Link className="button button--secondary" to="/change-password">
          <KeyRound size={17} /> Şifremi değiştir
        </Link>
      </section>
    </div>
  );
}

export function NotificationsPage() {
  const { user } = useAuth();
  const navigate = useNavigate();
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [error, setError] = useState("");
  const load = useCallback(
    () =>
      api
        .notifications(page)
        .then((value) => {
          setData(value);
          setError("");
        })
        .catch((requestError) => setError(requestError.message)),
    [page],
  );
  useEffect(() => {
    load();
  }, [load]);
  async function openNotification(item) {
    try {
      if (!item.is_read) await api.markNotificationRead(item.id);
      if (item.ticket_id == null) return;
      if (user.role === "ADMIN")
        navigate(`/admin/tickets?search=${item.ticket_id}`);
      else
        navigate(
          user.role === "IT"
            ? `/it/tickets/${item.ticket_id}`
            : `/tickets/${item.ticket_id}`,
        );
    } catch (requestError) {
      setError(requestError.message);
    }
  }
  if (!data)
    return (
      <div className="page">
        {error ? (
          <LoadFailure message={error} onRetry={load} />
        ) : (
          <LoadingScreen label="Bildirimler yükleniyor…" />
        )}
      </div>
    );
  return (
    <div className="page page--medium">
      <PageHeader
        eyebrow="Gelişmeler"
        title="Bildirimler"
        description="Talep süreçlerinizdeki son değişiklikleri takip edin."
      />
      <ErrorNotice message={error} />
      <section className="card card--flush">
        {data.items.length ? (
          <div className="notification-list">
            {data.items.map((item) => (
              <button
                key={item.id}
                type="button"
                className={`notification-row ${item.is_read ? "" : "notification-row--unread"}`}
                onClick={() => openNotification(item)}
              >
                <span className="notification-row__icon">
                  {item.type === "TICKET_RESOLVED" ? (
                    <CheckCircle2 size={20} />
                  ) : (
                    <MessageSquareText size={20} />
                  )}
                </span>
                <span className="notification-row__content">
                  <strong>{item.title}</strong>
                  <span>{item.message}</span>
                  <small>
                    {formatDate(item.created_at)} ·{" "}
                    {item.email_status === "SENT"
                      ? "E-posta gönderildi"
                      : item.email_status === "FAILED"
                        ? "E-posta gönderilemedi"
                        : "Sistem bildirimi"}
                  </small>
                </span>
                {!item.is_read && (
                  <span
                    className="notification-row__dot"
                    aria-label="Okunmadı"
                  />
                )}
              </button>
            ))}
          </div>
        ) : (
          <EmptyState
            title="Bildirim yok"
            description="Yeni talep gelişmeleri burada görünecek."
          />
        )}
      </section>
      <Pagination page={page} pages={data.pages} onPageChange={setPage} />
    </div>
  );
}
