import {
  Activity,
  ArrowLeft,
  BarChart3,
  CheckCircle2,
  CircleX,
  Download,
  File,
  Inbox,
  Database,
  HardDrive,
  Eye,
  EyeOff,
  LayoutGrid,
  List,
  Plus,
  RefreshCw,
  Search,
  Tag,
  UserCheck,
  Wrench,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";

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
  formatDuration,
  formatFileSize,
  formatRelativeDate,
  priorityLabels,
} from "../utils/format";

function ItTicketTable({ tickets }) {
  if (!tickets.length)
    return (
      <EmptyState
        title="Bu görünümde talep yok"
        description="Filtre koşullarına uyan bir talep bulunamadı."
      />
    );
  return (
    <div className="table-wrap">
      <table className="data-table data-table--it">
        <thead>
          <tr>
            <th>Talep no</th>
            <th>Kullanıcı</th>
            <th>Konu</th>
            <th>Atanan</th>
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
                <Link className="ticket-number" to={`/it/tickets/${ticket.id}`}>
                  {ticket.ticket_number}
                </Link>
              </td>
              <td data-label="Kullanıcı">
                <span className="cell-stack">
                  <strong>
                    {ticket.user.first_name} {ticket.user.last_name}
                  </strong>
                  <small>
                    {ticket.department_snapshot} · {ticket.user.email}
                  </small>
                </span>
              </td>
              <td data-label="Konu">
                <span className="cell-stack">
                  <strong>{ticket.subject}</strong>
                  {ticket.tags?.length > 0 && (
                    <small>
                      {ticket.tags.map((tag) => `#${tag.name}`).join(" · ")}
                    </small>
                  )}
                </span>
              </td>
              <td data-label="Atanan">
                {ticket.assignee
                  ? `${ticket.assignee.first_name} ${ticket.assignee.last_name}`
                  : "Atanmadı"}
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
                <Link className="table-link" to={`/it/tickets/${ticket.id}`}>
                  İncele
                </Link>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export function ItDashboardPage() {
  const { user } = useAuth();
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    return api
      .itDashboard()
      .then((value) => {
        setSummary(value);
        setError("");
      })
      .catch((requestError) => setError(requestError.message));
  }, []);
  useEffect(() => {
    load();
  }, [load]);
  if (!summary)
    return (
      <div className="page">
        {error ? (
          <LoadFailure message={error} onRetry={load} />
        ) : (
          <LoadingScreen label="IT özeti hazırlanıyor…" />
        )}
      </div>
    );
  const maximumDepartment = Math.max(
    1,
    ...summary.departments.map((item) => item.count),
  );
  return (
    <div className="page">
      <PageHeader
        eyebrow="Bilgi işlem alanı"
        title={`Hoş geldiniz, ${user.first_name}.`}
        description="Aktif operasyonun güncel özeti, iş yükü ve bekleyen talepler."
        actions={
          <Link className="button button--primary" to="/it/tickets">
            <Inbox size={18} /> Talep havuzuna git
          </Link>
        }
      />
      <ErrorNotice message={error} />
      <section className="metric-grid">
        <article className="metric-card">
          <span className="metric-card__label">Toplam</span>
          <strong>{summary.total}</strong>
          <small>Aktif kayıt</small>
        </article>
        <article className="metric-card metric-card--amber">
          <span className="metric-card__label">Açık</span>
          <strong>{summary.open}</strong>
          <small>Takip gerektiriyor</small>
        </article>
        <article className="metric-card">
          <span className="metric-card__label">Atanmamış</span>
          <strong>{summary.unassigned}</strong>
          <small>Havuzda bekliyor</small>
        </article>
        <article className="metric-card metric-card--blue">
          <span className="metric-card__label">Benim ticketlarım</span>
          <strong>{summary.mine}</strong>
          <small>Üzerinizde açık</small>
        </article>
        <article className="metric-card metric-card--green">
          <span className="metric-card__label">Çözülen</span>
          <strong>{summary.resolved}</strong>
          <small>Başarıyla tamamlandı</small>
        </article>
        <article className="metric-card metric-card--amber">
          <span className="metric-card__label">Yüksek / kritik</span>
          <strong>{summary.high_priority_open}</strong>
          <small>Açık öncelikli iş</small>
        </article>
        <article className="metric-card">
          <span className="metric-card__label">3+ gündür bekleyen</span>
          <strong>{summary.stale_open}</strong>
          <small>Uzun süredir güncellenmedi</small>
        </article>
      </section>
      <section className="card card--flush">
        <div className="card__header">
          <div>
            <h2>Son oluşturulan ticketlar</h2>
            <p>Operasyona en son eklenen kayıtlar</p>
          </div>
          <Link className="text-link" to="/it/tickets">
            Tümünü gör
          </Link>
        </div>
        <ItTicketTable tickets={summary.recent} />
      </section>
      <div className="content-grid content-grid--half">
        <section className="card card--flush">
          <div className="card__header">
            <div>
              <h2>Uzun süredir bekleyenler</h2>
              <p>Son güncellemesi en eski açık ticketlar</p>
            </div>
          </div>
          <ItTicketTable tickets={summary.stale} />
        </section>
        <section className="card card--flush">
          <div className="card__header">
            <div>
              <h2>Son sonuçlananlar</h2>
              <p>En yakın zamanda kapatılan ticketlar</p>
            </div>
          </div>
          <ItTicketTable tickets={summary.recent_resolved} />
        </section>
      </div>
      <div className="content-grid content-grid--half">
        <section className="card report-card">
          <div className="card__header">
            <div>
              <h2>Departman dağılımı</h2>
              <p>Aktif kayıtların dağılımı</p>
            </div>
            <BarChart3 size={21} />
          </div>
          <div className="bar-list">
            {summary.departments.map((item) => (
              <div className="bar-row" key={item.department}>
                <span>{item.department}</span>
                <div className="bar-row__track">
                  <span
                    style={{
                      width: `${(item.count / maximumDepartment) * 100}%`,
                    }}
                  />
                </div>
                <strong>{item.count}</strong>
              </div>
            ))}
          </div>
        </section>
        <section className="card">
          <div className="card__header">
            <div>
              <h2>Öncelik dağılımı</h2>
              <p>Tüm aktif ticketlar</p>
            </div>
          </div>
          <div className="distribution-list">
            {summary.priorities.map((item) => (
              <div key={item.name}>
                <span>{item.name}</span>
                <strong>{item.count}</strong>
              </div>
            ))}
          </div>
        </section>
      </div>
    </div>
  );
}

const emptyItFilters = {
  view: "all",
  search: "",
  status: "",
  priority: "",
  department: "",
  owner: "",
  assignee_id: "",
  tag_id: "",
  created_from: "",
  created_to: "",
  updated_from: "",
  updated_to: "",
  resolved_from: "",
  resolved_to: "",
};

function TicketKanban({ tickets }) {
  const columns = [
    [
      "unassigned",
      "Atanmamış",
      tickets.filter((ticket) => !ticket.is_resolved && !ticket.assigned_to),
    ],
    [
      "active",
      "İşlemde",
      tickets.filter((ticket) => !ticket.is_resolved && ticket.assigned_to),
    ],
    ["resolved", "Sonuçlanan", tickets.filter((ticket) => ticket.is_resolved)],
  ];
  return (
    <div className="kanban-board">
      {columns.map(([key, title, items]) => (
        <section className="kanban-column" key={key}>
          <header>
            <h2>{title}</h2>
            <span>{items.length}</span>
          </header>
          <div className="kanban-column__items">
            {items.map((ticket) => (
              <Link
                className="kanban-card"
                to={`/it/tickets/${ticket.id}`}
                key={ticket.id}
              >
                <span className="kanban-card__top">
                  <strong>{ticket.ticket_number}</strong>
                  <PriorityBadge priority={ticket.priority} />
                </span>
                <h3>{ticket.subject}</h3>
                <p>
                  {ticket.user.first_name} {ticket.user.last_name} ·{" "}
                  {ticket.department_snapshot}
                </p>
                {ticket.tags?.length > 0 && (
                  <div className="tag-list">
                    {ticket.tags.map((tag) => (
                      <span
                        className="ticket-tag"
                        style={{ "--tag-color": tag.color }}
                        key={tag.id}
                      >
                        #{tag.name}
                      </span>
                    ))}
                  </div>
                )}
                <small>
                  {ticket.assignee
                    ? `${ticket.assignee.first_name} ${ticket.assignee.last_name}`
                    : "Henüz atanmadı"}{" "}
                  · {formatRelativeDate(ticket.updated_at)}
                </small>
              </Link>
            ))}
            {!items.length && <EmptyState title="Kayıt yok" />}
          </div>
        </section>
      ))}
    </div>
  );
}

export function ItTicketsPage({ defaultView = "all" }) {
  const initialParams = new URLSearchParams(window.location.search);
  const initial = {
    ...emptyItFilters,
    view: initialParams.get("view") || defaultView,
    search: initialParams.get("search") || "",
  };
  const [filters, setFilters] = useState(initial);
  const [query, setQuery] = useState(initial);
  const [display, setDisplay] = useState("list");
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);
  const [options, setOptions] = useState({
    departments: [],
    assignees: [],
    tags: [],
  });
  const [error, setError] = useState("");
  const load = useCallback(() => {
    return Promise.all([
      api.itTickets({
        ...query,
        page,
        pageSize: display === "board" ? 100 : 20,
      }),
      api.itTicketFilterOptions(),
    ])
      .then(([tickets, filterOptions]) => {
        setData(tickets);
        setOptions(filterOptions);
        setError("");
      })
      .catch((requestError) => setError(requestError.message));
  }, [query, page, display]);
  useEffect(() => {
    load();
  }, [load]);
  function submit(event) {
    event.preventDefault();
    setPage(1);
    setData(null);
    setQuery(filters);
  }
  function selectView(view) {
    const next = { ...filters, view };
    setFilters(next);
    setQuery(next);
    setPage(1);
  }
  function clearFilters() {
    const next = { ...emptyItFilters, view: defaultView };
    setFilters(next);
    setQuery(next);
    setPage(1);
  }
  const views = [
    ["all", "Tümü"],
    ["unassigned", "Atanmamış"],
    ["mine", "Benimkiler"],
    ["resolved", "Sonuçlananlar"],
  ];
  return (
    <div className="page">
      <PageHeader
        eyebrow="Operasyon"
        title={
          defaultView === "mine"
            ? "Benim Ticketlarım"
            : "Bilgi İşlem Talep Havuzu"
        }
        description="Ticket no, açıklama, kullanıcı, departman, tarih, etiket ve sorumluya göre ayrıntılı arama yapın."
        actions={
          <div className="view-toggle">
            <button
              className={display === "list" ? "active" : ""}
              type="button"
              onClick={() => setDisplay("list")}
            >
              <List size={17} /> Liste
            </button>
            <button
              className={display === "board" ? "active" : ""}
              type="button"
              onClick={() => setDisplay("board")}
            >
              <LayoutGrid size={17} /> Kanban
            </button>
          </div>
        }
      />
      <ErrorNotice message={error} />
      <form className="card advanced-filter" onSubmit={submit}>
        <div className="advanced-filter__top">
          <label className="search-field">
            <Search size={18} />
            <input
              value={filters.search}
              onChange={(event) =>
                setFilters({ ...filters, search: event.target.value })
              }
              placeholder="Ticket no, konu, açıklama, kullanıcı veya e-posta ara"
            />
          </label>
          <div className="segmented-control">
            {views.map(([value, label]) => (
              <button
                key={value}
                className={filters.view === value ? "active" : ""}
                type="button"
                onClick={() => selectView(value)}
              >
                {label}
              </button>
            ))}
          </div>
        </div>
        <div className="advanced-filter__grid">
          <label className="field">
            <span>Durum</span>
            <select
              value={filters.status}
              onChange={(event) =>
                setFilters({ ...filters, status: event.target.value })
              }
            >
              <option value="">Tümü</option>
              <option value="open">Açık</option>
              <option value="resolved">Çözüldü</option>
              <option value="unresolved">Çözülemedi</option>
            </select>
          </label>
          <label className="field">
            <span>Öncelik</span>
            <select
              value={filters.priority}
              onChange={(event) =>
                setFilters({ ...filters, priority: event.target.value })
              }
            >
              <option value="">Tümü</option>
              {Object.entries(priorityLabels).map(([value, label]) => (
                <option value={value} key={value}>
                  {label}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Departman</span>
            <select
              value={filters.department}
              onChange={(event) =>
                setFilters({ ...filters, department: event.target.value })
              }
            >
              <option value="">Tümü</option>
              {options.departments.map((department) => (
                <option key={department}>{department}</option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Sorumlu</span>
            <select
              value={filters.assignee_id}
              onChange={(event) =>
                setFilters({ ...filters, assignee_id: event.target.value })
              }
            >
              <option value="">Tümü</option>
              {options.assignees.map((assignee) => (
                <option value={assignee.id} key={assignee.id}>
                  {assignee.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Etiket</span>
            <select
              value={filters.tag_id}
              onChange={(event) =>
                setFilters({ ...filters, tag_id: event.target.value })
              }
            >
              <option value="">Tümü</option>
              {options.tags.map((tag) => (
                <option value={tag.id} key={tag.id}>
                  #{tag.name}
                </option>
              ))}
            </select>
          </label>
          <label className="field">
            <span>Talep sahibi</span>
            <input
              value={filters.owner}
              onChange={(event) =>
                setFilters({ ...filters, owner: event.target.value })
              }
              placeholder="Ad, soyad veya e-posta"
            />
          </label>
          <label className="field">
            <span>Oluşturma başlangıcı</span>
            <input
              type="date"
              value={filters.created_from}
              onChange={(event) =>
                setFilters({ ...filters, created_from: event.target.value })
              }
            />
          </label>
          <label className="field">
            <span>Oluşturma bitişi</span>
            <input
              type="date"
              value={filters.created_to}
              onChange={(event) =>
                setFilters({ ...filters, created_to: event.target.value })
              }
            />
          </label>
        </div>
        <div className="advanced-filter__actions">
          <button
            className="button button--ghost"
            type="button"
            onClick={clearFilters}
          >
            Filtreleri temizle
          </button>
          <span className="toolbar__count">
            {data ? `Toplam ${data.total} kayıt` : "Sonuçlar hazırlanıyor"}
          </span>
          <button className="button button--primary" type="submit">
            <Search size={17} /> Filtrele
          </button>
        </div>
      </form>
      {!data ? (
        error ? (
          <LoadFailure message={error} onRetry={load} />
        ) : (
          <LoadingScreen label="Talep havuzu yükleniyor…" />
        )
      ) : (
        <>
          {display === "board" ? (
            <TicketKanban tickets={data.items} />
          ) : (
            <section className="card card--flush">
              <ItTicketTable tickets={data.items} />
            </section>
          )}
          {display === "list" && (
            <Pagination page={page} pages={data.pages} onPageChange={setPage} />
          )}
        </>
      )}
    </div>
  );
}

export function ItTicketDetailPage() {
  const { id } = useParams();
  const { user } = useAuth();
  const [ticket, setTicket] = useState(null);
  const [resolution, setResolution] = useState("");
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const [busy, setBusy] = useState(false);
  const [confirmOutcome, setConfirmOutcome] = useState(null);
  const [history, setHistory] = useState([]);
  const [tags, setTags] = useState([]);
  const [cannedResponses, setCannedResponses] = useState([]);
  const [selectedTag, setSelectedTag] = useState("");
  const [newTag, setNewTag] = useState("");
  const load = useCallback(() => {
    return Promise.all([
      api.ticket(id, true),
      api.ticketHistory(id, "IT"),
      api.ticketTags(),
      api.cannedResponses(),
    ])
      .then(([ticketData, historyData, tagData, responseData]) => {
        setTicket(ticketData);
        setHistory(historyData);
        setTags(tagData);
        setCannedResponses(responseData);
        setError("");
      })
      .catch((requestError) => setError(requestError.message));
  }, [id]);
  useEffect(() => {
    load();
  }, [load]);
  async function run(action, message) {
    setBusy(true);
    setError("");
    try {
      await action();
      await load();
      setSuccess(message);
      return true;
    } catch (requestError) {
      setError(requestError.message);
      return false;
    } finally {
      setBusy(false);
    }
  }
  async function download(attachment) {
    try {
      saveBlob(
        await api.downloadAttachment(id, attachment.id),
        attachment.original_file_name,
      );
    } catch (requestError) {
      setError(requestError.message);
    }
  }
  if (!ticket)
    return (
      <div className="page">
        {error ? (
          <LoadFailure message={error} onRetry={load} />
        ) : (
          <LoadingScreen label="Ticket detayı yükleniyor…" />
        )}
      </div>
    );
  const mine = ticket.assigned_to === user.id;
  const watching = ticket.watchers?.some((watcher) => watcher.id === user.id);
  const collision = ticket.assignee && !mine && !ticket.is_resolved;
  const availableTags = tags.filter(
    (tag) => !ticket.tags.some((current) => current.id === tag.id),
  );
  return (
    <div className="page">
      <Link className="back-link" to="/it/tickets">
        <ArrowLeft size={17} /> Talep havuzuna dön
      </Link>
      <PageHeader
        eyebrow={ticket.ticket_number}
        title={ticket.subject}
        description={`${ticket.user.first_name} ${ticket.user.last_name} · ${ticket.department_snapshot}`}
        actions={
          <div className="header-actions">
            <button
              className="button button--secondary button--small"
              type="button"
              disabled={busy}
              onClick={() =>
                run(
                  () =>
                    watching ? api.unwatchTicket(id) : api.watchTicket(id),
                  watching
                    ? "Ticket takibi bırakıldı."
                    : "Ticket takip listenize eklendi.",
                )
              }
            >
              {watching ? <EyeOff size={17} /> : <Eye size={17} />}
              {watching ? "Takibi bırak" : "Takip et"}
            </button>
            <div className="header-badges">
              <StatusBadge
                resolved={ticket.is_resolved}
                outcome={ticket.resolution_outcome}
              />
              <PriorityBadge priority={ticket.priority} />
            </div>
          </div>
        }
      />
      <ErrorNotice message={error} onDismiss={() => setError("")} />
      <SuccessNotice message={success} />
      {collision && (
        <div className="collision-banner">
          <UserCheck size={20} />
          <div>
            <strong>Bu ticket üzerinde başka bir BT çalışanı çalışıyor.</strong>
            <span>
              Sorumlu: {ticket.assignee.first_name} {ticket.assignee.last_name}.
              Çakışmayı önlemek için işlemleri koordine edin.
            </span>
          </div>
        </div>
      )}
      <div className="detail-layout">
        <div className="detail-layout__main">
          <section className="card">
            <div className="card__header">
              <div>
                <h2>Talep açıklaması</h2>
                <p>{formatDate(ticket.created_at)}</p>
              </div>
            </div>
            <p className="long-copy">{ticket.description}</p>
          </section>
          <section className="card">
            <div className="card__header">
              <div>
                <h2>Dosya ekleri</h2>
                <p>{ticket.attachments.length} dosya</p>
              </div>
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
                        {formatFileSize(attachment.file_size_bytes)}
                      </small>
                    </span>
                    <button
                      className="button button--ghost button--small"
                      type="button"
                      onClick={() => download(attachment)}
                    >
                      <Download size={16} /> İndir
                    </button>
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="Dosya eki yok" />
            )}
          </section>
          {ticket.is_resolved ? (
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
                <p className="eyebrow">Sonuç</p>
                <h2>
                  {ticket.resolution_outcome === "UNRESOLVED"
                    ? "Talep çözülemedi"
                    : "Talep çözüldü"}
                </h2>
                <p className="long-copy">{ticket.resolution_note}</p>
                <small>{formatDate(ticket.resolved_at)}</small>
              </div>
            </section>
          ) : (
            <section className="card action-panel">
              <div className="card__header">
                <div>
                  <h2>Talep işlemleri</h2>
                  <p>
                    Öncelik belirleyin, üzerinize alın ve sonuç bilgisini
                    kaydedin.
                  </p>
                </div>
                <Wrench size={21} />
              </div>
              <div className="action-panel__row">
                <label className="field">
                  <span>Öncelik</span>
                  <select
                    value={ticket.priority || ""}
                    onChange={(event) =>
                      run(
                        () => api.setPriority(id, event.target.value),
                        "Öncelik güncellendi.",
                      )
                    }
                    disabled={busy}
                  >
                    <option value="" disabled>
                      Öncelik seçin
                    </option>
                    {Object.entries(priorityLabels).map(([value, label]) => (
                      <option key={value} value={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </label>
                <div className="action-panel__assign">
                  <span>Atama</span>
                  {ticket.assigned_to ? (
                    <span
                      className={`assignment-state ${mine ? "assignment-state--mine" : ""}`}
                    >
                      <UserCheck size={18} />{" "}
                      {mine
                        ? "Üzerinizde"
                        : `${ticket.assignee?.first_name || "Başka"} ${ticket.assignee?.last_name || "BT personeli"}`}
                    </span>
                  ) : (
                    <button
                      className="button button--secondary"
                      type="button"
                      disabled={busy}
                      onClick={() =>
                        run(() => api.assignSelf(id), "Talep üzerinize alındı.")
                      }
                    >
                      <UserCheck size={18} /> Kendime al
                    </button>
                  )}
                </div>
              </div>
              {cannedResponses.length > 0 && (
                <label className="field">
                  <span>Hazır yanıt kullan</span>
                  <select
                    value=""
                    disabled={!mine || busy}
                    onChange={(event) => {
                      const item = cannedResponses.find(
                        (response) =>
                          response.id === Number(event.target.value),
                      );
                      if (item)
                        setResolution((current) =>
                          current
                            ? `${current}\n\n${item.content}`
                            : item.content,
                        );
                    }}
                  >
                    <option value="">Yanıt seçin…</option>
                    {cannedResponses.map((response) => (
                      <option value={response.id} key={response.id}>
                        {response.title}
                      </option>
                    ))}
                  </select>
                </label>
              )}
              <label className="field">
                <span>Sonuç açıklaması</span>
                <textarea
                  rows={5}
                  value={resolution}
                  onChange={(event) => setResolution(event.target.value)}
                  placeholder="Uygulanan adımları ve sonuç bilgisini ayrıntılı yazın."
                  disabled={!mine || busy}
                />
              </label>
              <div className="form-actions">
                <button
                  className="button button--secondary"
                  type="button"
                  disabled={
                    !mine || !ticket.priority || !resolution.trim() || busy
                  }
                  onClick={() => setConfirmOutcome("UNRESOLVED")}
                >
                  <CircleX size={18} /> Çözülemedi
                </button>
                <button
                  className="button button--primary"
                  type="button"
                  disabled={
                    !mine || !ticket.priority || !resolution.trim() || busy
                  }
                  onClick={() => setConfirmOutcome("RESOLVED")}
                >
                  <CheckCircle2 size={18} /> Çözüldü
                </button>
              </div>
              {!mine && (
                <p className="field-hint">
                  Talebi sonuçlandırabilmek için üzerinize almalısınız.
                </p>
              )}
            </section>
          )}
          <TicketTimeline items={history} formatTimestamp={formatDate} />
        </div>
        <aside className="detail-layout__side">
          <section className="card">
            <h2>Kullanıcı ve talep</h2>
            <dl className="detail-list">
              <div>
                <dt>Kullanıcı</dt>
                <dd>
                  {ticket.user.first_name} {ticket.user.last_name}
                </dd>
              </div>
              <div>
                <dt>E-posta</dt>
                <dd>
                  <a href={`mailto:${ticket.user.email}`}>
                    {ticket.user.email}
                  </a>
                </dd>
              </div>
              <div>
                <dt>Telefon</dt>
                <dd>{ticket.user.phone || "—"}</dd>
              </div>
              <div>
                <dt>Departman</dt>
                <dd>{ticket.department_snapshot}</dd>
              </div>
              <div>
                <dt>Talep no</dt>
                <dd>{ticket.ticket_number}</dd>
              </div>
              <div>
                <dt>Sorumlu</dt>
                <dd>
                  {ticket.assignee
                    ? `${ticket.assignee.first_name} ${ticket.assignee.last_name}`
                    : "Atanmadı"}
                </dd>
              </div>
              <div>
                <dt>Son güncelleme</dt>
                <dd>{formatDate(ticket.updated_at)}</dd>
              </div>
            </dl>
          </section>
          <section className="card ticket-tag-panel">
            <div className="card__header">
              <div>
                <h2>Etiketler</h2>
                <p>Ticketı sınıflandırın</p>
              </div>
              <Tag size={19} />
            </div>
            <div className="tag-list">
              {ticket.tags.map((tag) => (
                <button
                  className="ticket-tag ticket-tag--button"
                  style={{ "--tag-color": tag.color }}
                  type="button"
                  key={tag.id}
                  disabled={busy}
                  onClick={() =>
                    run(
                      () => api.removeTicketTag(id, tag.id),
                      "Etiket kaldırıldı.",
                    )
                  }
                >
                  #{tag.name} ×
                </button>
              ))}
              {!ticket.tags.length && <small>Henüz etiket yok.</small>}
            </div>
            {availableTags.length > 0 && (
              <div className="tag-add">
                <select
                  value={selectedTag}
                  onChange={(event) => setSelectedTag(event.target.value)}
                >
                  <option value="">Etiket seçin</option>
                  {availableTags.map((tag) => (
                    <option value={tag.id} key={tag.id}>
                      #{tag.name}
                    </option>
                  ))}
                </select>
                <button
                  className="button button--secondary button--small"
                  type="button"
                  disabled={!selectedTag || busy}
                  onClick={async () => {
                    const completed = await run(
                      () => api.addTicketTag(id, selectedTag),
                      "Etiket eklendi.",
                    );
                    if (completed) setSelectedTag("");
                  }}
                >
                  <Plus size={15} /> Ekle
                </button>
              </div>
            )}
            <div className="tag-add">
              <input value={newTag} maxLength={50} onChange={(event) => setNewTag(event.target.value)} placeholder="Yeni etiket adı" />
              <button className="button button--ghost button--small" type="button" disabled={!newTag.trim() || busy} onClick={async () => {
                const completed = await run(async () => {
                  const created = await api.createTicketTag({ name: newTag, color: "#2F7C91" });
                  return api.addTicketTag(id, created.id);
                }, "Etiket oluşturulup ticketa eklendi.");
                if (completed) setNewTag("");
              }}><Plus size={15} /> Oluştur</button>
            </div>
          </section>
          <section className="card">
            <h2>Takipçiler</h2>
            {ticket.watchers?.length ? (
              <ul className="watcher-list">
                {ticket.watchers.map((watcher) => (
                  <li key={watcher.id}>
                    {watcher.first_name} {watcher.last_name}
                  </li>
                ))}
              </ul>
            ) : (
              <p className="field-hint">
                Bu ticketı takip eden BT çalışanı yok.
              </p>
            )}
          </section>
        </aside>
      </div>
      <ConfirmDialog
        open={!!confirmOutcome}
        title={
          confirmOutcome === "UNRESOLVED"
            ? "Talep çözülemedi olarak işaretlensin mi?"
            : "Talep çözüldü olarak işaretlensin mi?"
        }
        description="Talep sonuçlandırılacak ve açıklama kullanıcıya bildirilecektir. Bu işlem bu ekrandan geri alınamaz."
        confirmLabel={
          confirmOutcome === "UNRESOLVED"
            ? "Evet, çözülemedi"
            : "Evet, talebi çöz"
        }
        busy={busy}
        tone={confirmOutcome === "UNRESOLVED" ? "danger" : "primary"}
        onClose={() => setConfirmOutcome(null)}
        onConfirm={() => {
          const outcome = confirmOutcome;
          setConfirmOutcome(null);
          run(
            () => api.resolveTicket(id, resolution, outcome),
            outcome === "UNRESOLVED"
              ? "Talep çözülemedi olarak sonuçlandırıldı ve kullanıcı bilgilendirildi."
              : "Talep çözüldü ve kullanıcı bilgilendirildi.",
          );
        }}
      />
    </div>
  );
}

export function ReportsPage() {
  const [period, setPeriod] = useState("month");
  const [custom, setCustom] = useState({ date_from: "", date_to: "" });
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const params = useMemo(() => {
    const value = new URLSearchParams({ period });
    if (period === "custom") {
      if (custom.date_from) value.set("date_from", custom.date_from);
      if (custom.date_to) value.set("date_to", custom.date_to);
    }
    return value.toString();
  }, [period, custom]);
  async function load() {
    setBusy(true);
    setError("");
    try {
      setSummary(await api.reportSummary(params));
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }
  useEffect(() => {
    if (period === "custom") return undefined;
    let active = true;
    api
      .reportSummary(params)
      .then((value) => {
        if (active) setSummary(value);
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      });
    return () => {
      active = false;
    };
  }, [period, params]);
  async function exportExcel() {
    try {
      saveBlob(
        await api.exportReport(params),
        `ticket-raporu-${new Date().toISOString().slice(0, 10)}.xlsx`,
      );
    } catch (requestError) {
      setError(requestError.message);
    }
  }
  const maximumDepartment = Math.max(
    1,
    ...(summary?.departments.map((item) => item.count) || [1]),
  );
  const maximumSeries = Math.max(
    1,
    ...(summary?.time_series.map((item) => item.count) || [1]),
  );
  const maximumPerformance = Math.max(
    1,
    ...(summary?.it_performance.map((item) => item.resolved) || [1]),
  );
  return (
    <div className="page">
      <PageHeader
        eyebrow="Analiz"
        title="Raporlar"
        description="Talep hacmini, sonuç durumlarını, çözüm sürelerini ve BT performansını inceleyin."
        actions={
          <button
            className="button button--secondary"
            type="button"
            onClick={exportExcel}
            disabled={!summary}
          >
            <Download size={18} /> Excel'e aktar
          </button>
        }
      />
      <ErrorNotice message={error} />
      <div className="toolbar report-toolbar">
        <div className="segmented-control">
          {[
            ["today", "Bugün"],
            ["week", "Bu hafta"],
            ["month", "Bu ay"],
            ["year", "Bu yıl"],
            ["custom", "Özel aralık"],
          ].map(([value, label]) => (
            <button
              key={value}
              className={period === value ? "active" : ""}
              type="button"
              onClick={() => {
                setSummary(null);
                setPeriod(value);
              }}
            >
              {label}
            </button>
          ))}
        </div>
        {period === "custom" && (
          <div className="date-range">
            <label>
              Başlangıç
              <input
                type="date"
                value={custom.date_from}
                onChange={(event) =>
                  setCustom({ ...custom, date_from: event.target.value })
                }
              />
            </label>
            <label>
              Bitiş
              <input
                type="date"
                value={custom.date_to}
                onChange={(event) =>
                  setCustom({ ...custom, date_to: event.target.value })
                }
              />
            </label>
            <button
              className="button button--secondary button--small"
              type="button"
              onClick={load}
              disabled={busy}
            >
              {busy ? "Hazırlanıyor…" : "Uygula"}
            </button>
          </div>
        )}
      </div>
      {!summary ? (
        error ? (
          <LoadFailure message={error} onRetry={load} />
        ) : (
          <LoadingScreen label="Rapor hazırlanıyor…" />
        )
      ) : (
        <>
          <section className="metric-grid">
            <article className="metric-card">
              <span className="metric-card__label">Toplam talep</span>
              <strong>{summary.total}</strong>
              <small>Seçili tarih aralığı</small>
            </article>
            <article className="metric-card metric-card--green">
              <span className="metric-card__label">Çözülen</span>
              <strong>{summary.resolved}</strong>
              <small>
                {summary.total
                  ? `%${Math.round((summary.resolved / summary.total) * 100)} çözüm oranı`
                  : "Henüz kayıt yok"}
              </small>
            </article>
            <article className="metric-card">
              <span className="metric-card__label">Çözülemedi</span>
              <strong>{summary.could_not_resolve}</strong>
              <small>Sonuçlandırılan talep</small>
            </article>
            <article className="metric-card metric-card--amber">
              <span className="metric-card__label">Açık</span>
              <strong>{summary.unresolved}</strong>
              <small>İşlem bekleyen</small>
            </article>
            <article className="metric-card metric-card--blue">
              <span className="metric-card__label">Ort. çözüm süresi</span>
              <strong className="metric-card__value--compact">
                {formatDuration(summary.average_resolution_minutes)}
              </strong>
              <small>Yalnızca çözülenler</small>
            </article>
            <article className="metric-card metric-card--green">
              <span className="metric-card__label">En hızlı çözüm</span>
              <strong className="metric-card__value--compact">
                {formatDuration(summary.fastest_resolution_minutes)}
              </strong>
              <small>Seçili dönem</small>
            </article>
            <article className="metric-card metric-card--amber">
              <span className="metric-card__label">En uzun bekleyen</span>
              <strong className="metric-card__value--compact">
                {formatDuration(summary.longest_waiting_minutes)}
              </strong>
              <small>Açık ticket</small>
            </article>
          </section>
          <div className="content-grid content-grid--half">
            <section className="card report-card">
              <div className="card__header">
                <div>
                  <h2>Talep trendi</h2>
                  <p>Dönem içindeki oluşturma hacmi</p>
                </div>
                <Activity size={21} />
              </div>
              {summary.time_series.length ? (
                <div className="series-chart">
                  {summary.time_series.map((item) => (
                    <div key={item.label}>
                      <span
                        className="series-chart__bar"
                        style={{
                          height: `${Math.max(6, (item.count / maximumSeries) * 100)}%`,
                        }}
                        title={`${item.label}: ${item.count}`}
                      />
                      <small>{item.label}</small>
                      <strong>{item.count}</strong>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title="Trend verisi yok" />
              )}
            </section>
            <section className="card report-card">
              <div className="card__header">
                <div>
                  <h2>BT çözüm performansı</h2>
                  <p>Seçili dönemde çözülen ticket sayısı</p>
                </div>
                <UserCheck size={21} />
              </div>
              {summary.it_performance.length ? (
                <div className="bar-list">
                  {summary.it_performance.map((item) => (
                    <div className="bar-row" key={item.user_id}>
                      <span>{item.name}</span>
                      <div className="bar-row__track">
                        <span
                          style={{
                            width: `${(item.resolved / maximumPerformance) * 100}%`,
                          }}
                        />
                      </div>
                      <strong>{item.resolved}</strong>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState title="Çözüm verisi yok" />
              )}
            </section>
          </div>
          <div className="content-grid content-grid--half">
            <section className="card report-card">
              <div className="card__header">
                <div>
                  <h2>Departman dağılımı</h2>
                  <p>Seçili aralıkta oluşturulan ticketlar</p>
                </div>
                <BarChart3 size={21} />
              </div>
              {summary.departments.length ? (
                <div className="bar-list">
                  {summary.departments.map((item) => (
                    <div className="bar-row" key={item.department}>
                      <span>{item.department}</span>
                      <div className="bar-row__track">
                        <span
                          style={{
                            width: `${(item.count / maximumDepartment) * 100}%`,
                          }}
                        />
                      </div>
                      <strong>{item.count}</strong>
                    </div>
                  ))}
                </div>
              ) : (
                <EmptyState
                  title="Bu dönemde veri yok"
                  description="Farklı bir tarih aralığı seçebilirsiniz."
                />
              )}
            </section>
            <section className="card">
              <div className="card__header">
                <div>
                  <h2>Öncelik dağılımı</h2>
                  <p>Seçili dönemdeki ticketlar</p>
                </div>
              </div>
              <div className="distribution-list">
                {summary.priorities.map((item) => (
                  <div key={item.name}>
                    <span>{priorityLabels[item.name] || item.name}</span>
                    <strong>{item.count}</strong>
                  </div>
                ))}
              </div>
            </section>
          </div>
        </>
      )}
    </div>
  );
}

function formatUptime(seconds) {
  const days = Math.floor(seconds / 86400);
  const hours = Math.floor((seconds % 86400) / 3600);
  const minutes = Math.floor((seconds % 3600) / 60);
  if (days) return `${days} gün ${hours} sa`;
  if (hours) return `${hours} sa ${minutes} dk`;
  return `${minutes} dk`;
}

export function SystemMonitoringPage() {
  const [overview, setOverview] = useState(null);
  const [logs, setLogs] = useState(null);
  const [level, setLevel] = useState("");
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    let active = true;
    Promise.all([api.systemOverview(), api.systemLogs(level)])
      .then(([overviewData, logData]) => {
        if (active) {
          setOverview(overviewData);
          setLogs(logData);
        }
      })
      .catch((requestError) => {
        if (active) setError(requestError.message);
      });
    return () => {
      active = false;
    };
  }, [level]);

  async function refresh() {
    setBusy(true);
    setError("");
    try {
      const [overviewData, logData] = await Promise.all([
        api.systemOverview(),
        api.systemLogs(level),
      ]);
      setOverview(overviewData);
      setLogs(logData);
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  if (!overview || !logs)
    return (
      <div className="page">
        {error ? (
          <LoadFailure message={error} onRetry={refresh} />
        ) : (
          <LoadingScreen label="Sistem durumu yükleniyor…" />
        )}
      </div>
    );

  return (
    <div className="page">
      <PageHeader
        eyebrow="Operasyon"
        title="Sistem izleme"
        description="Uygulama, MSSQL, dosya alanı ve güvenli operasyon loglarını tek yerden takip edin."
        actions={
          <button
            className="button button--secondary"
            type="button"
            onClick={refresh}
            disabled={busy}
          >
            <RefreshCw size={17} className={busy ? "spin" : ""} /> Yenile
          </button>
        }
      />
      <ErrorNotice message={error} />
      <section className="metric-grid">
        <article className="metric-card">
          <span className="metric-card__label">
            <Activity size={15} /> Genel durum
          </span>
          <strong className="metric-card__value--compact">
            {overview.status === "ok" ? "Sağlıklı" : "Kontrol gerekli"}
          </strong>
          <small>
            v{overview.app_version} · {overview.environment}
          </small>
        </article>
        <article className="metric-card metric-card--green">
          <span className="metric-card__label">
            <Database size={15} /> MSSQL
          </span>
          <strong className="metric-card__value--compact">
            {overview.database_status === "ok" ? "Bağlı" : "Hata"}
          </strong>
          <small>Hazırlık sorgusu</small>
        </article>
        <article className="metric-card metric-card--blue">
          <span className="metric-card__label">
            <HardDrive size={15} /> Dosya alanı
          </span>
          <strong className="metric-card__value--compact">
            {overview.upload_status === "ok" ? "Yazılabilir" : "Hata"}
          </strong>
          <small>
            {overview.upload_free_bytes == null
              ? "Alan okunamadı"
              : `${formatFileSize(overview.upload_free_bytes)} boş`}
          </small>
        </article>
        <article className="metric-card">
          <span className="metric-card__label">Çalışma süresi</span>
          <strong className="metric-card__value--compact">
            {formatUptime(overview.uptime_seconds)}
          </strong>
          <small>Log: {formatFileSize(overview.log_size_bytes)}</small>
        </article>
      </section>
      <section className="card card--flush system-log-card">
        <div className="card__header system-log-header">
          <div>
            <h2>Merkezi uygulama logları</h2>
            <p>
              Son {logs.returned} güvenli olay ·{" "}
              {formatDate(overview.checked_at)}
            </p>
          </div>
          <label className="field field--inline">
            <span>Seviye</span>
            <select
              value={level}
              onChange={(event) => setLevel(event.target.value)}
            >
              <option value="">Tümü</option>
              <option value="INFO">Bilgi</option>
              <option value="WARNING">Uyarı</option>
              <option value="ERROR">Hata</option>
              <option value="CRITICAL">Kritik</option>
            </select>
          </label>
        </div>
        {logs.items.length ? (
          <div className="table-wrap">
            <table className="data-table system-log-table">
              <thead>
                <tr>
                  <th>Zaman</th>
                  <th>Seviye</th>
                  <th>Kaynak</th>
                  <th>Olay</th>
                  <th>Bağlam</th>
                </tr>
              </thead>
              <tbody>
                {logs.items.map((entry, index) => (
                  <tr key={`${entry.timestamp}-${index}`}>
                    <td>{formatDate(entry.timestamp)}</td>
                    <td>
                      <span
                        className={`log-level log-level--${entry.level.toLowerCase()}`}
                      >
                        {entry.level}
                      </span>
                    </td>
                    <td>
                      <code>{entry.logger}</code>
                    </td>
                    <td>
                      {entry.message}
                      {entry.exception_type && (
                        <small>{entry.exception_type}</small>
                      )}
                    </td>
                    <td>
                      <code>
                        {Object.entries(entry.context)
                          .map(([key, value]) => `${key}=${value}`)
                          .join(" · ") || "—"}
                      </code>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Log kaydı yok"
            description="Uygulama olayları oluştukça burada görünecek."
          />
        )}
      </section>
    </div>
  );
}
