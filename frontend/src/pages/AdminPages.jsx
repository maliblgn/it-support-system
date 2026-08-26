import {
  Activity,
  ArrowLeft,
  ArchiveRestore,
  ClipboardList,
  File,
  KeyRound,
  MessageSquareText,
  Pencil,
  Plus,
  RefreshCw,
  Search,
  ShieldCheck,
  Trash2,
  UserCheck,
  UserRoundX,
  Users,
} from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";

import { api } from "../api/client";
import {
  ConfirmDialog,
  EmptyState,
  ErrorNotice,
  LoadingScreen,
  LoadFailure,
  PageHeader,
  Pagination,
  StatusBadge,
  SuccessNotice,
  TicketTimeline,
} from "../components/UI";
import { formatDate, formatFileSize } from "../utils/format";

const emptyItForm = {
  email: "",
  temporary_password: "",
  first_name: "",
  last_name: "",
  phone: "",
  department: "Bilgi İşlem",
};

const emptyUserActionForm = {
  reason: "",
  temporary_password: "",
  confirmation_email: "",
  first_name: "",
  last_name: "",
  phone: "",
  department: "",
};

export function AdminDashboardPage() {
  const [summary, setSummary] = useState(null);
  const [error, setError] = useState("");

  const load = useCallback(() => {
    return api
      .adminDashboard()
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
          <LoadingScreen label="Yönetim özeti hazırlanıyor…" />
        )}
      </div>
    );
  return (
    <div className="page">
      <PageHeader
        eyebrow="Yönetim alanı"
        title="Admin paneli"
        description="Hesapları, talepleri ve denetim kayıtlarını tek merkezden yönetin."
      />
      <ErrorNotice message={error} />
      <section className="metric-grid">
        <article className="metric-card">
          <span className="metric-card__label">
            <Users size={16} /> Toplam kullanıcı
          </span>
          <strong>{summary.total_users}</strong>
          <small>{summary.active_users} aktif hesap</small>
        </article>
        <article className="metric-card metric-card--blue">
          <span className="metric-card__label">
            <ShieldCheck size={16} /> IT çalışanı
          </span>
          <strong>{summary.it_users}</strong>
          <small>Bilgi işlem hesabı</small>
        </article>
        <article className="metric-card metric-card--amber">
          <span className="metric-card__label">
            <ClipboardList size={16} /> Açık talep
          </span>
          <strong>{summary.open_tickets}</strong>
          <small>İşlem bekliyor</small>
        </article>
        <article className="metric-card metric-card--green">
          <span className="metric-card__label">
            <ArchiveRestore size={16} /> Silinen talep
          </span>
          <strong>{summary.deleted_tickets}</strong>
          <small>Geri yüklenebilir kayıt</small>
        </article>
      </section>
      <section className="admin-shortcuts">
        <Link className="card admin-shortcut" to="/admin/users">
          <Users size={23} />
          <span>
            <strong>Kullanıcıları yönet</strong>
            <small>
              IT hesabı açın, hesapları düzenleyin ve pasifleştirin.
            </small>
          </span>
        </Link>
        <Link className="card admin-shortcut" to="/admin/tickets">
          <Trash2 size={23} />
          <span>
            <strong>Talep ve geri dönüşüm</strong>
            <small>
              {summary.deleted_tickets} silinmiş talebi inceleyin veya geri
              yükleyin.
            </small>
          </span>
        </Link>
        <Link className="card admin-shortcut" to="/admin/audit">
          <Activity size={23} />
          <span>
            <strong>Denetim kayıtları</strong>
            <small>Yönetim ve kritik kullanıcı işlemlerini izleyin.</small>
          </span>
        </Link>
        <Link className="card admin-shortcut" to="/admin/canned-responses">
          <MessageSquareText size={23} />
          <span>
            <strong>Hazır yanıtlar</strong>
            <small>
              BT ekibinin kullanacağı standart çözüm metinlerini yönetin.
            </small>
          </span>
        </Link>
      </section>
    </div>
  );
}

export function AdminUsersPage() {
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    search: "",
    role: "",
    isActive: "",
  });
  const [query, setQuery] = useState(filters);
  const [showCreate, setShowCreate] = useState(false);
  const [form, setForm] = useState(emptyItForm);
  const [action, setAction] = useState(null);
  const [actionForm, setActionForm] = useState(emptyUserActionForm);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");

  const load = useCallback(
    () =>
      api
        .adminUsers({ ...query, page })
        .then((value) => {
          setData(value);
          setError("");
        })
        .catch((requestError) => setError(requestError.message)),
    [page, query],
  );
  useEffect(() => {
    load();
  }, [load]);

  async function createIt(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      await api.createItUser({ ...form, phone: form.phone.trim() || null });
      setForm(emptyItForm);
      setShowCreate(false);
      setSuccess(
        "IT çalışanı hesabı oluşturuldu. İlk girişte geçici parolasını değiştirmesi istenecek.",
      );
      await load();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  function openAction(type, user) {
    setError("");
    setSuccess("");
    setAction({ type, user });
    setActionForm({
      reason: "",
      temporary_password: "",
      confirmation_email: "",
      first_name: user.first_name,
      last_name: user.last_name,
      phone: user.phone || "",
      department: user.department,
    });
  }

  function closeAction() {
    if (busy) return;
    setAction(null);
    setActionForm(emptyUserActionForm);
  }

  async function confirmAction() {
    setBusy(true);
    setError("");
    try {
      if (action.type === "status") {
        await api.setAdminUserStatus(action.user.id, {
          is_active: !action.user.is_active,
          reason: actionForm.reason,
        });
      } else if (action.type === "password") {
        await api.resetAdminUserPassword(action.user.id, {
          temporary_password: actionForm.temporary_password,
          reason: actionForm.reason,
        });
      } else if (action.type === "delete") {
        await api.deleteAdminUser(action.user.id, {
          confirmation_email: actionForm.confirmation_email,
          reason: actionForm.reason,
        });
      } else {
        await api.updateAdminUser(action.user.id, {
          first_name: actionForm.first_name,
          last_name: actionForm.last_name,
          phone: actionForm.phone.trim() || null,
          department: actionForm.department,
        });
      }
      const messages = {
        edit: "Kullanıcı bilgileri güncellendi.",
        password:
          "Geçici parola yenilendi. Kullanıcı ilk girişte yeni parola belirleyecek.",
        status: "Hesap durumu güncellendi.",
        delete: "Kullanıcı veritabanından kalıcı olarak silindi.",
      };
      setSuccess(messages[action.type]);
      setAction(null);
      setActionForm(emptyUserActionForm);
      await load();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }

  if (!data)
    return (
      <div className="page">
        {error ? (
          <LoadFailure message={error} onRetry={load} />
        ) : (
          <LoadingScreen label="Kullanıcılar yükleniyor…" />
        )}
      </div>
    );
  const actionReady =
    action?.type === "edit"
      ? Boolean(
          actionForm.first_name.trim() &&
          actionForm.last_name.trim() &&
          actionForm.department.trim(),
        )
      : action?.type === "password"
        ? actionForm.reason.trim().length >= 3 &&
          actionForm.temporary_password.length >= 12
        : action?.type === "delete"
          ? actionForm.reason.trim().length >= 3 &&
            actionForm.confirmation_email.trim().toLocaleLowerCase("tr-TR") ===
              action.user.email.toLocaleLowerCase("tr-TR")
          : actionForm.reason.trim().length >= 3;

  const actionTitle =
    action?.type === "edit"
      ? "Kullanıcı bilgilerini düzenle"
      : action?.type === "password"
        ? "Geçici parola belirle"
        : action?.type === "delete"
          ? "Kullanıcı kalıcı olarak silinsin mi?"
          : action?.user?.is_active
            ? "Hesap pasifleştirilsin mi?"
            : "Hesap aktifleştirilsin mi?";
  const actionDescription =
    action?.type === "edit"
      ? "Değişiklikler ilgili kullanıcının profiline uygulanır."
      : action?.type === "delete"
        ? "Bu işlem geri alınamaz. İş geçmişine bağlı hesaplar veri bütünlüğünü korumak için silinemez; bunun yerine pasifleştirilebilir."
        : "Bu kritik işlem denetim kaydına nedeni ile birlikte yazılır.";
  const actionLabel =
    action?.type === "edit"
      ? "Değişiklikleri kaydet"
      : action?.type === "password"
        ? "Parolayı yenile"
        : action?.type === "delete"
          ? "Kalıcı olarak sil"
          : "Durumu güncelle";
  return (
    <div className="page">
      <PageHeader
        eyebrow="Hesap yönetimi"
        title="Kullanıcılar"
        description="Çalışan hesaplarını izleyin; IT personelini yalnızca bu güvenli yönetim alanından oluşturun."
        actions={
          <button
            className="button button--primary"
            type="button"
            onClick={() => setShowCreate((value) => !value)}
          >
            <Plus size={17} /> IT hesabı oluştur
          </button>
        }
      />
      <ErrorNotice message={error} onDismiss={() => setError("")} />
      <SuccessNotice message={success} />
      {showCreate && (
        <form className="card form-stack admin-create-form" onSubmit={createIt}>
          <div className="card__header">
            <div>
              <h2>Yeni IT çalışanı</h2>
              <p>
                Geçici parola kullanıcı tarafından ilk girişte
                değiştirilecektir.
              </p>
            </div>
          </div>
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
            <label className="field">
              <span>E-posta</span>
              <input
                type="email"
                value={form.email}
                onChange={(event) =>
                  setForm({ ...form, email: event.target.value })
                }
                required
              />
            </label>
            <label className="field">
              <span>Geçici parola</span>
              <input
                type="password"
                value={form.temporary_password}
                onChange={(event) =>
                  setForm({ ...form, temporary_password: event.target.value })
                }
                minLength={12}
                required
              />
            </label>
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
          <p className="field-hint">
            Parola en az 12 karakter, bir harf ve bir rakam içermelidir.
          </p>
          <div className="form-actions">
            <button
              className="button button--ghost"
              type="button"
              onClick={() => setShowCreate(false)}
            >
              Vazgeç
            </button>
            <button
              className="button button--primary"
              type="submit"
              disabled={busy}
            >
              {busy ? "Oluşturuluyor…" : "Hesabı oluştur"}
            </button>
          </div>
        </form>
      )}
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
            placeholder="Ad, e-posta veya departman ara"
          />
          <button
            className="button button--secondary button--small"
            type="submit"
          >
            Ara
          </button>
        </label>
        <select
          aria-label="Rol filtresi"
          value={filters.role}
          onChange={(event) =>
            setFilters({ ...filters, role: event.target.value })
          }
        >
          <option value="">Tüm roller</option>
          <option value="USER">Çalışan</option>
          <option value="IT">IT</option>
        </select>
        <select
          aria-label="Durum filtresi"
          value={filters.isActive}
          onChange={(event) =>
            setFilters({ ...filters, isActive: event.target.value })
          }
        >
          <option value="">Tüm durumlar</option>
          <option value="true">Aktif</option>
          <option value="false">Pasif</option>
        </select>
        <span className="toolbar__count">{data.total} hesap</span>
      </form>
      <section className="card card--flush">
        {data.items.length ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Kullanıcı</th>
                  <th>Rol</th>
                  <th>Departman</th>
                  <th>Durum</th>
                  <th>Oluşturulma</th>
                  <th>İşlemler</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((user) => (
                  <tr key={user.id}>
                    <td data-label="Kullanıcı">
                      <span className="cell-stack">
                        <strong>
                          {user.first_name} {user.last_name}
                        </strong>
                        <small>
                          {user.email}
                          {user.must_change_password
                            ? " · Parola değişimi bekleniyor"
                            : ""}
                        </small>
                      </span>
                    </td>
                    <td data-label="Rol">
                      <span
                        className={`role-badge role-badge--${user.role.toLowerCase()}`}
                      >
                        {user.role === "IT" ? "IT çalışanı" : "Çalışan"}
                      </span>
                    </td>
                    <td data-label="Departman">{user.department}</td>
                    <td data-label="Durum">
                      <span
                        className={`badge ${user.is_active ? "badge--resolved" : "badge--neutral"}`}
                      >
                        {user.is_active ? "Aktif" : "Pasif"}
                      </span>
                    </td>
                    <td data-label="Oluşturulma">
                      {formatDate(user.created_at)}
                    </td>
                    <td data-label="İşlemler">
                      <div className="table-actions">
                        <button
                          className="icon-button"
                          type="button"
                          onClick={() => openAction("edit", user)}
                          aria-label={`${user.first_name} ${user.last_name} kullanıcısını düzenle`}
                          title="Düzenle"
                        >
                          <Pencil size={16} />
                        </button>
                        <button
                          className="icon-button"
                          type="button"
                          onClick={() => openAction("password", user)}
                          aria-label={`${user.first_name} ${user.last_name} için geçici parola belirle`}
                          title="Geçici parola belirle"
                        >
                          <KeyRound size={16} />
                        </button>
                        <button
                          className={`icon-button ${user.is_active ? "icon-button--danger" : ""}`}
                          type="button"
                          onClick={() => openAction("status", user)}
                          aria-label={`${user.first_name} ${user.last_name} hesabını ${user.is_active ? "pasifleştir" : "aktifleştir"}`}
                          title={user.is_active ? "Pasifleştir" : "Aktifleştir"}
                        >
                          {user.is_active ? (
                            <UserRoundX size={16} />
                          ) : (
                            <UserCheck size={16} />
                          )}
                        </button>
                        <button
                          className="icon-button icon-button--danger"
                          type="button"
                          onClick={() => openAction("delete", user)}
                          aria-label={`${user.first_name} ${user.last_name} kullanıcısını kalıcı olarak sil`}
                          title="Kalıcı sil"
                        >
                          <Trash2 size={16} />
                        </button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState
            title="Bu filtrelerde kullanıcı yok"
            description="Arama ve filtreleri değiştirerek yeniden deneyin."
          />
        )}
      </section>
      <Pagination page={page} pages={data.pages} onPageChange={setPage} />
      <ConfirmDialog
        open={!!action}
        title={actionTitle}
        description={actionDescription}
        confirmLabel={actionLabel}
        tone={
          (action?.type === "status" && action?.user?.is_active) ||
          action?.type === "delete"
            ? "danger"
            : "primary"
        }
        busy={busy}
        confirmDisabled={!actionReady}
        onClose={closeAction}
        onConfirm={confirmAction}
      >
        {action?.type === "edit" ? (
          <div className="form-stack modal-form">
            <div className="form-grid form-grid--two">
              <label className="field">
                <span>Ad</span>
                <input
                  value={actionForm.first_name}
                  onChange={(event) =>
                    setActionForm({
                      ...actionForm,
                      first_name: event.target.value,
                    })
                  }
                />
              </label>
              <label className="field">
                <span>Soyad</span>
                <input
                  value={actionForm.last_name}
                  onChange={(event) =>
                    setActionForm({
                      ...actionForm,
                      last_name: event.target.value,
                    })
                  }
                />
              </label>
            </div>
            <label className="field">
              <span>Departman</span>
              <input
                value={actionForm.department}
                onChange={(event) =>
                  setActionForm({
                    ...actionForm,
                    department: event.target.value,
                  })
                }
              />
            </label>
            <label className="field">
              <span>Telefon</span>
              <input
                value={actionForm.phone}
                onChange={(event) =>
                  setActionForm({ ...actionForm, phone: event.target.value })
                }
              />
            </label>
          </div>
        ) : (
          <div className="form-stack modal-form">
            {action?.type === "password" && (
              <label className="field">
                <span>Yeni geçici parola</span>
                <input
                  type="password"
                  minLength={12}
                  value={actionForm.temporary_password}
                  onChange={(event) =>
                    setActionForm({
                      ...actionForm,
                      temporary_password: event.target.value,
                    })
                  }
                />
                <small>En az 12 karakter, bir harf ve bir rakam.</small>
              </label>
            )}
            {action?.type === "delete" && (
              <label className="field">
                <span>Onay için kullanıcının e-postası</span>
                <input
                  type="email"
                  autoComplete="off"
                  value={actionForm.confirmation_email}
                  onChange={(event) =>
                    setActionForm({
                      ...actionForm,
                      confirmation_email: event.target.value,
                    })
                  }
                  placeholder={action.user.email}
                />
                <small>
                  Kalıcı silmeyi açmak için <strong>{action.user.email}</strong>{" "}
                  yazın.
                </small>
              </label>
            )}
            <label className="field">
              <span>İşlem nedeni</span>
              <textarea
                rows={3}
                value={actionForm.reason}
                onChange={(event) =>
                  setActionForm({ ...actionForm, reason: event.target.value })
                }
                placeholder="Denetim kaydı için en az 3 karakter yazın."
              />
            </label>
          </div>
        )}
      </ConfirmDialog>
    </div>
  );
}

export function AdminTicketsPage() {
  const initialSearch =
    new URLSearchParams(window.location.search).get("search") || "";
  const [data, setData] = useState(null);
  const [itUsers, setItUsers] = useState([]);
  const [page, setPage] = useState(1);
  const [filters, setFilters] = useState({
    state: "active",
    search: initialSearch,
  });
  const [query, setQuery] = useState({
    state: "active",
    search: initialSearch,
  });
  const [target, setTarget] = useState(null);
  const [assignment, setAssignment] = useState(null);
  const [selectedItId, setSelectedItId] = useState("");
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const load = useCallback(
    () =>
      api
        .adminTickets({ ...query, page })
        .then((value) => {
          setData(value);
          setError("");
        })
        .catch((requestError) => setError(requestError.message)),
    [page, query],
  );
  useEffect(() => {
    load();
  }, [load]);
  useEffect(() => {
    api
      .adminUsers({ pageSize: 100, role: "IT", isActive: "true" })
      .then((result) => setItUsers(result.items))
      .catch((requestError) => setError(requestError.message));
  }, []);

  async function removeTicket() {
    setBusy(true);
    try {
      await api.deleteAdminTicket(target.id, reason);
      setTarget(null);
      setReason("");
      setSuccess("Talep geri dönüşüm kutusuna taşındı.");
      await load();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }
  async function restore(ticket) {
    setBusy(true);
    try {
      await api.restoreAdminTicket(ticket.id);
      setSuccess(`${ticket.ticket_number} geri yüklendi.`);
      await load();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }
  function openAssignment(ticket) {
    setAssignment(ticket);
    setSelectedItId(ticket.assigned_to ? String(ticket.assigned_to) : "");
    setError("");
  }
  async function assignTicket() {
    const itUser = itUsers.find((user) => user.id === Number(selectedItId));
    setBusy(true);
    setError("");
    try {
      await api.assignAdminTicket(assignment.id, Number(selectedItId));
      setAssignment(null);
      setSelectedItId("");
      setSuccess(
        `${assignment.ticket_number}, ${itUser.first_name} ${itUser.last_name} adlı IT çalışanına atandı.`,
      );
      await load();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }
  if (!data)
    return (
      <div className="page">
        {error ? (
          <LoadFailure message={error} onRetry={load} />
        ) : (
          <LoadingScreen label="Talepler yükleniyor…" />
        )}
      </div>
    );
  return (
    <div className="page">
      <PageHeader
        eyebrow="Operasyon ve veri yaşam döngüsü"
        title="Talep havuzu ve yönetimi"
        description="Yeni talepleri izleyin, aktif bir IT çalışanına atayın veya IT ekibinin atanmamış talepleri kendi üzerine almasına izin verin."
      />
      <ErrorNotice message={error} onDismiss={() => setError("")} />
      <SuccessNotice message={success} />
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
            placeholder="Talep no, konu, kullanıcı veya departman"
          />
          <button
            className="button button--secondary button--small"
            type="submit"
          >
            Ara
          </button>
        </label>
        <div className="segmented-control">
          {[
            ["active", "Aktif"],
            ["deleted", "Silinen"],
            ["all", "Tümü"],
          ].map(([value, label]) => (
            <button
              type="button"
              key={value}
              className={filters.state === value ? "active" : ""}
              onClick={() => {
                const next = { ...filters, state: value };
                setFilters(next);
                setQuery(next);
                setPage(1);
              }}
            >
              {label}
            </button>
          ))}
        </div>
        <span className="toolbar__count">{data.total} kayıt</span>
      </form>
      <section className="card card--flush">
        {data.items.length ? (
          <div className="table-wrap">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Talep</th>
                  <th>Kullanıcı</th>
                  <th>Durum</th>
                  <th>Atanan IT</th>
                  <th>Tarih</th>
                  <th>Silme bilgisi</th>
                  <th>İşlem</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((ticket) => (
                  <tr key={ticket.id}>
                    <td data-label="Talep">
                      <span className="cell-stack">
                        <Link
                          className="ticket-number"
                          to={`/admin/tickets/${ticket.id}`}
                        >
                          {ticket.ticket_number}
                        </Link>
                        <small>{ticket.subject}</small>
                      </span>
                    </td>
                    <td data-label="Kullanıcı">
                      <span className="cell-stack">
                        <strong>
                          {ticket.user.first_name} {ticket.user.last_name}
                        </strong>
                        <small>{ticket.department_snapshot}</small>
                      </span>
                    </td>
                    <td data-label="Durum">
                      <StatusBadge
                        resolved={ticket.is_resolved}
                        outcome={ticket.resolution_outcome}
                      />
                    </td>
                    <td data-label="Atanan IT">
                      {ticket.assignee ? (
                        <span className="cell-stack">
                          <strong>
                            {ticket.assignee.first_name}{" "}
                            {ticket.assignee.last_name}
                          </strong>
                          <small>{ticket.assignee.email}</small>
                        </span>
                      ) : (
                        <span className="cell-stack">
                          <strong>Atanmadı</strong>
                          <small>IT çalışanı kendi üzerine alabilir</small>
                        </span>
                      )}
                    </td>
                    <td data-label="Tarih">{formatDate(ticket.created_at)}</td>
                    <td data-label="Silme bilgisi">
                      {ticket.deleted_at ? (
                        <span className="cell-stack">
                          <strong>{formatDate(ticket.deleted_at)}</strong>
                          <small>{ticket.deletion_reason}</small>
                        </span>
                      ) : (
                        "—"
                      )}
                    </td>
                    <td data-label="İşlem">
                      {ticket.deleted_at ? (
                        <button
                          className="button button--ghost button--small"
                          type="button"
                          disabled={busy}
                          onClick={() => restore(ticket)}
                        >
                          <ArchiveRestore size={16} /> Geri yükle
                        </button>
                      ) : (
                        <div className="table-actions">
                          {!ticket.is_resolved && (
                            <button
                              className="button button--secondary button--small"
                              type="button"
                              disabled={busy || !itUsers.length}
                              onClick={() => openAssignment(ticket)}
                            >
                              <UserCheck size={16} />{" "}
                              {ticket.assigned_to
                                ? "Atamayı değiştir"
                                : "IT ata"}
                            </button>
                          )}
                          <button
                            className="button button--danger button--small"
                            type="button"
                            disabled={busy}
                            onClick={() => setTarget(ticket)}
                          >
                            <Trash2 size={16} /> Sil
                          </button>
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <EmptyState title="Bu görünümde talep yok" />
        )}
      </section>
      <Pagination page={page} pages={data.pages} onPageChange={setPage} />
      <ConfirmDialog
        open={!!assignment}
        title="Talep IT çalışanına atansın mı?"
        description={
          assignment
            ? `${assignment.ticket_number} için sorumlu IT çalışanını seçin. Mevcut atama varsa bu seçimle değiştirilecektir.`
            : ""
        }
        confirmLabel="Talebi ata"
        tone="primary"
        busy={busy}
        confirmDisabled={
          !selectedItId || Number(selectedItId) === assignment?.assigned_to
        }
        onClose={() => {
          setAssignment(null);
          setSelectedItId("");
        }}
        onConfirm={assignTicket}
      >
        <label className="field modal-form">
          <span>Atanacak IT çalışanı</span>
          <select
            aria-label="Atanacak IT çalışanı"
            value={selectedItId}
            onChange={(event) => setSelectedItId(event.target.value)}
          >
            <option value="">IT çalışanı seçin</option>
            {itUsers.map((user) => (
              <option key={user.id} value={user.id}>
                {user.first_name} {user.last_name} · {user.email}
              </option>
            ))}
          </select>
          <small>Yalnızca aktif IT hesapları listelenir.</small>
        </label>
      </ConfirmDialog>
      <ConfirmDialog
        open={!!target}
        title="Talep geri dönüşüm kutusuna taşınsın mı?"
        description={
          target
            ? `${target.ticket_number} kaydı normal listelerden gizlenecek; yönetici daha sonra geri yükleyebilir.`
            : ""
        }
        confirmLabel="Talebi sil"
        busy={busy}
        confirmDisabled={reason.trim().length < 3}
        onClose={() => {
          setTarget(null);
          setReason("");
        }}
        onConfirm={removeTicket}
      >
        <label className="field modal-form">
          <span>Silme nedeni</span>
          <textarea
            rows={3}
            value={reason}
            onChange={(event) => setReason(event.target.value)}
            placeholder="En az 3 karakter"
          />
        </label>
      </ConfirmDialog>
    </div>
  );
}

export function AdminAuditPage() {
  const [data, setData] = useState(null);
  const [page, setPage] = useState(1);
  const [action, setAction] = useState("");
  const [query, setQuery] = useState("");
  const [error, setError] = useState("");
  const load = useCallback(
    () =>
      api
        .auditEvents(page, query)
        .then((value) => {
          setData(value);
          setError("");
        })
        .catch((requestError) => setError(requestError.message)),
    [page, query],
  );
  useEffect(() => {
    load();
  }, [load]);
  if (!data)
    return (
      <div className="page">
        {error ? (
          <LoadFailure message={error} onRetry={load} />
        ) : (
          <LoadingScreen label="Denetim kayıtları yükleniyor…" />
        )}
      </div>
    );
  return (
    <div className="page">
      <PageHeader
        eyebrow="Güvenlik ve izlenebilirlik"
        title="Denetim kayıtları"
        description="Kritik yönetim ve silme işlemlerini değiştirilemez olay kaydı olarak inceleyin."
        actions={
          <button
            className="button button--secondary"
            type="button"
            onClick={load}
          >
            <RefreshCw size={17} /> Yenile
          </button>
        }
      />
      <ErrorNotice message={error} />
      <form
        className="toolbar toolbar--search"
        onSubmit={(event) => {
          event.preventDefault();
          setPage(1);
          setQuery(action);
        }}
      >
        <label className="search-field">
          <Search size={18} />
          <input
            value={action}
            onChange={(event) => setAction(event.target.value)}
            placeholder="Tam olay kodu (örn. TICKET_DELETED)"
          />
          <button
            className="button button--secondary button--small"
            type="submit"
          >
            Filtrele
          </button>
        </label>
        <span className="toolbar__count">{data.total} olay</span>
      </form>
      <section className="card card--flush">
        {data.items.length ? (
          <div className="table-wrap">
            <table className="data-table audit-table">
              <thead>
                <tr>
                  <th>Zaman</th>
                  <th>İşlem</th>
                  <th>Yapan</th>
                  <th>Varlık</th>
                  <th>Ayrıntı</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((event) => (
                  <tr key={event.id}>
                    <td>{formatDate(event.created_at)}</td>
                    <td>
                      <code>{event.action}</code>
                    </td>
                    <td>{event.actor_name || "Sistem"}</td>
                    <td>
                      {event.entity_type}
                      {event.entity_id ? ` #${event.entity_id}` : ""}
                    </td>
                    <td>
                      <code>
                        {Object.entries(event.details)
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
          <EmptyState title="Denetim kaydı yok" />
        )}
      </section>
      <Pagination page={page} pages={data.pages} onPageChange={setPage} />
    </div>
  );
}

export function AdminTicketDetailPage() {
  const { id } = useParams();
  const [ticket, setTicket] = useState(null);
  const [history, setHistory] = useState([]);
  const [error, setError] = useState("");
  const load = useCallback(() => {
    return Promise.all([api.adminTicket(id), api.ticketHistory(id, "ADMIN")])
      .then(([ticketData, historyData]) => {
        setTicket(ticketData);
        setHistory(historyData);
        setError("");
      })
      .catch((requestError) => setError(requestError.message));
  }, [id]);
  useEffect(() => {
    load();
  }, [load]);
  if (!ticket)
    return (
      <div className="page">
        {error ? (
          <LoadFailure message={error} onRetry={load} />
        ) : (
          <LoadingScreen label="Talep detayı yükleniyor…" />
        )}
      </div>
    );
  return (
    <div className="page">
      <Link className="back-link" to="/admin/tickets">
        <ArrowLeft size={17} /> Talep yönetimine dön
      </Link>
      <PageHeader
        eyebrow={ticket.ticket_number}
        title={ticket.subject}
        description={`${ticket.user.first_name} ${ticket.user.last_name} · ${ticket.department_snapshot}`}
        actions={
          <StatusBadge
            resolved={ticket.is_resolved}
            outcome={ticket.resolution_outcome}
          />
        }
      />
      <ErrorNotice message={error} />
      {ticket.deleted_at && (
        <div className="collision-banner collision-banner--danger">
          <Trash2 size={20} />
          <div>
            <strong>Bu talep geri dönüşüm kutusunda.</strong>
            <span>
              {ticket.deletion_reason} · {formatDate(ticket.deleted_at)}
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
                  </div>
                ))}
              </div>
            ) : (
              <EmptyState title="Dosya eki yok" />
            )}
          </section>
          {ticket.resolution_note && (
            <section className="card resolution-card">
              <span className="resolution-card__icon">
                <ClipboardList size={23} />
              </span>
              <div>
                <p className="eyebrow">Sonuç açıklaması</p>
                <p className="long-copy">{ticket.resolution_note}</p>
                <small>{formatDate(ticket.resolved_at)}</small>
              </div>
            </section>
          )}
          <TicketTimeline items={history} formatTimestamp={formatDate} />
        </div>
        <aside className="detail-layout__side card">
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
                <a href={`mailto:${ticket.user.email}`}>{ticket.user.email}</a>
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
              <dt>Sorumlu</dt>
              <dd>
                {ticket.assignee
                  ? `${ticket.assignee.first_name} ${ticket.assignee.last_name}`
                  : "Atanmadı"}
              </dd>
            </div>
            <div>
              <dt>Öncelik</dt>
              <dd>{ticket.priority || "Belirlenmedi"}</dd>
            </div>
            <div>
              <dt>Son güncelleme</dt>
              <dd>{formatDate(ticket.updated_at)}</dd>
            </div>
          </dl>
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
        </aside>
      </div>
    </div>
  );
}

export function AdminCannedResponsesPage() {
  const emptyForm = { title: "", content: "" };
  const [items, setItems] = useState(null);
  const [form, setForm] = useState(emptyForm);
  const [editingId, setEditingId] = useState(null);
  const [target, setTarget] = useState(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");
  const [success, setSuccess] = useState("");
  const load = useCallback(
    () =>
      api
        .adminCannedResponses()
        .then((value) => {
          setItems(value);
          setError("");
        })
        .catch((requestError) => setError(requestError.message)),
    [],
  );
  useEffect(() => {
    load();
  }, [load]);
  function startEdit(item) {
    setEditingId(item.id);
    setForm({ title: item.title, content: item.content });
    setSuccess("");
  }
  function cancelEdit() {
    setEditingId(null);
    setForm(emptyForm);
  }
  async function submit(event) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      if (editingId) {
        await api.updateAdminCannedResponse(editingId, form);
        setSuccess("Hazır yanıt güncellendi.");
      } else {
        await api.createAdminCannedResponse(form);
        setSuccess("Hazır yanıt oluşturuldu.");
      }
      cancelEdit();
      await load();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }
  async function deactivate() {
    setBusy(true);
    setError("");
    try {
      await api.deleteAdminCannedResponse(target.id);
      setSuccess("Hazır yanıt pasifleştirildi.");
      setTarget(null);
      await load();
    } catch (requestError) {
      setError(requestError.message);
    } finally {
      setBusy(false);
    }
  }
  if (!items)
    return (
      <div className="page">
        {error ? (
          <LoadFailure message={error} onRetry={load} />
        ) : (
          <LoadingScreen label="Hazır yanıtlar yükleniyor…" />
        )}
      </div>
    );
  return (
    <div className="page">
      <PageHeader
        eyebrow="Operasyon içeriği"
        title="Hazır yanıtlar"
        description="BT çalışanlarının çözüm ekranında kullanabileceği tutarlı yanıt şablonlarını yönetin."
      />
      <ErrorNotice message={error} onDismiss={() => setError("")} />
      <SuccessNotice message={success} />
      <div className="content-grid content-grid--half">
        <form className="card form-stack" onSubmit={submit}>
          <div className="card__header">
            <div>
              <h2>{editingId ? "Hazır yanıtı düzenle" : "Yeni hazır yanıt"}</h2>
              <p>Kısa bir başlık ve ayrıntılı çözüm metni yazın.</p>
            </div>
            <MessageSquareText size={21} />
          </div>
          <label className="field">
            <span>Başlık</span>
            <input
              maxLength={120}
              value={form.title}
              onChange={(event) =>
                setForm({ ...form, title: event.target.value })
              }
              required
            />
          </label>
          <label className="field">
            <span>Yanıt metni</span>
            <textarea
              rows={9}
              maxLength={2000}
              value={form.content}
              onChange={(event) =>
                setForm({ ...form, content: event.target.value })
              }
              required
            />
          </label>
          <div className="form-actions">
            {editingId && (
              <button
                className="button button--ghost"
                type="button"
                onClick={cancelEdit}
              >
                Vazgeç
              </button>
            )}
            <button
              className="button button--primary"
              type="submit"
              disabled={busy}
            >
              {editingId ? "Değişiklikleri kaydet" : "Yanıtı oluştur"}
            </button>
          </div>
        </form>
        <section className="card card--flush">
          <div className="card__header">
            <div>
              <h2>Yanıt kütüphanesi</h2>
              <p>{items.filter((item) => item.is_active).length} aktif yanıt</p>
            </div>
          </div>
          {items.length ? (
            <div className="canned-list">
              {items.map((item) => (
                <article
                  className={`canned-item ${item.is_active ? "" : "canned-item--inactive"}`}
                  key={item.id}
                >
                  <div>
                    <span
                      className={`badge ${item.is_active ? "badge--resolved" : "badge--neutral"}`}
                    >
                      {item.is_active ? "Aktif" : "Pasif"}
                    </span>
                    <h3>{item.title}</h3>
                    <p>{item.content}</p>
                    <small>Son güncelleme: {formatDate(item.updated_at)}</small>
                  </div>
                  <div className="table-actions">
                    <button
                      className="icon-button"
                      type="button"
                      onClick={() => startEdit(item)}
                      title="Düzenle"
                    >
                      <Pencil size={16} />
                    </button>
                    {item.is_active && (
                      <button
                        className="icon-button icon-button--danger"
                        type="button"
                        onClick={() => setTarget(item)}
                        title="Pasifleştir"
                      >
                        <Trash2 size={16} />
                      </button>
                    )}
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <EmptyState
              title="Hazır yanıt yok"
              description="İlk yanıtınızı soldaki formdan oluşturun."
            />
          )}
        </section>
      </div>
      <ConfirmDialog
        open={!!target}
        title="Hazır yanıt pasifleştirilsin mi?"
        description="Yanıt geçmiş kayıtlarda korunur ancak BT çalışanlarının seçim listesinde artık görünmez."
        confirmLabel="Pasifleştir"
        busy={busy}
        onClose={() => setTarget(null)}
        onConfirm={deactivate}
      />
    </div>
  );
}
