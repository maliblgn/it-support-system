const API_PREFIX = "/api";

function readCookie(name) {
  const prefix = `${encodeURIComponent(name)}=`;
  const item = document.cookie.split("; ").find((cookie) => cookie.startsWith(prefix));
  return item ? decodeURIComponent(item.slice(prefix.length)) : null;
}

export class ApiError extends Error {
  constructor(message, status, details = null) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.details = details;
  }
}

function validationMessage(detail) {
  if (!Array.isArray(detail)) return null;
  return detail
    .slice(0, 3)
    .map((item) => `${item.loc?.at(-1) ?? "Alan"}: ${item.msg ?? "Geçersiz değer"}`)
    .join(" • ");
}

async function parseError(response) {
  let payload = null;
  try {
    payload = await response.json();
  } catch {
    // Sunucu JSON döndürmediyse güvenli genel mesaj kullanılır.
  }
  const message = response.status >= 500
    ? "İşlem sırasında beklenmeyen bir sorun oluştu. Lütfen yeniden deneyin."
    : validationMessage(payload?.detail) ||
      (typeof payload?.detail === "string" ? payload.detail : null) ||
      "İstek tamamlanamadı.";
  return new ApiError(message, response.status, payload);
}

export async function apiRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});
  const bodyIsFormData = options.body instanceof FormData;
  if (options.body && !bodyIsFormData && !headers.has("Content-Type")) {
    headers.set("Content-Type", "application/json");
  }
  const method = (options.method || "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS"].includes(method)) {
    const csrfToken = readCookie("it_ticket_csrf");
    if (csrfToken) headers.set("X-CSRF-Token", csrfToken);
  }

  const response = await fetch(`${API_PREFIX}${path}`, {
    ...options,
    method,
    headers,
    credentials: "include",
  });
  if (!response.ok) throw await parseError(response);
  if (response.status === 204) return null;
  const contentType = response.headers.get("content-type") || "";
  return contentType.includes("application/json") ? response.json() : response.blob();
}

export const api = {
  register: (payload) =>
    apiRequest("/auth/register", { method: "POST", body: JSON.stringify(payload) }),
  login: (payload) =>
    apiRequest("/auth/login", { method: "POST", body: JSON.stringify(payload) }),
  logout: () => apiRequest("/auth/logout", { method: "POST" }),
  me: () => apiRequest("/auth/me"),
  updateProfile: (payload) =>
    apiRequest("/users/me", { method: "PATCH", body: JSON.stringify(payload) }),
  changePassword: (payload) =>
    apiRequest("/users/me/password", { method: "POST", body: JSON.stringify(payload) }),

  userTickets: (page = 1, pageSize = 20, filters = {}) => {
    const params = new URLSearchParams({ page, page_size: pageSize });
    Object.entries(filters).forEach(([key, value]) => {
      if (value !== "" && value != null) params.set(key, value);
    });
    return apiRequest(`/tickets?${params}`);
  },
  ticket: (id, it = false) => apiRequest(`${it ? "/it" : ""}/tickets/${id}`),
  ticketHistory: (id, role = "USER") => {
    const prefix = role === "ADMIN" ? "/admin" : role === "IT" ? "/it" : "";
    return apiRequest(`${prefix}/tickets/${id}/history`);
  },
  createTicket: (payload) =>
    apiRequest("/tickets", { method: "POST", body: JSON.stringify(payload) }),
  updateTicket: (id, payload) =>
    apiRequest(`/tickets/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteTicket: (id, reason) =>
    apiRequest(`/tickets/${id}`, {
      method: "DELETE",
      body: JSON.stringify({ reason }),
    }),
  ticketRating: (id) => apiRequest(`/tickets/${id}/rating`),
  saveTicketRating: (id, payload) =>
    apiRequest(`/tickets/${id}/rating`, { method: "PUT", body: JSON.stringify(payload) }),
  uploadAttachment: (ticketId, file) => {
    const data = new FormData();
    data.append("file", file);
    return apiRequest(`/tickets/${ticketId}/attachments`, { method: "POST", body: data });
  },
  deleteAttachment: (ticketId, attachmentId) =>
    apiRequest(`/tickets/${ticketId}/attachments/${attachmentId}`, { method: "DELETE" }),
  downloadAttachment: (ticketId, attachmentId) =>
    apiRequest(`/tickets/${ticketId}/attachments/${attachmentId}`),

  itTickets: ({ page = 1, pageSize = 20, view = "all", ...filters } = {}) => {
    const params = new URLSearchParams({ page, page_size: pageSize, view });
    Object.entries(filters).forEach(([key, value]) => {
      const normalized = typeof value === "string" ? value.trim() : value;
      if (normalized !== "" && normalized != null) params.set(key, normalized);
    });
    return apiRequest(`/it/tickets?${params}`);
  },
  itTicketFilterOptions: () => apiRequest("/it/tickets/filter-options"),
  itDashboard: () => apiRequest("/it/reports/dashboard"),
  setPriority: (id, priority) =>
    apiRequest(`/it/tickets/${id}/priority`, {
      method: "PATCH",
      body: JSON.stringify({ priority }),
    }),
  assignSelf: (id) => apiRequest(`/it/tickets/${id}/assign-self`, { method: "POST" }),
  watchTicket: (id) => apiRequest(`/it/tickets/${id}/watch`, { method: "POST" }),
  unwatchTicket: (id) => apiRequest(`/it/tickets/${id}/watch`, { method: "DELETE" }),
  ticketTags: () => apiRequest("/it/tags"),
  createTicketTag: (payload) =>
    apiRequest("/it/tags", { method: "POST", body: JSON.stringify(payload) }),
  addTicketTag: (ticketId, tagId) =>
    apiRequest(`/it/tickets/${ticketId}/tags/${tagId}`, { method: "POST" }),
  removeTicketTag: (ticketId, tagId) =>
    apiRequest(`/it/tickets/${ticketId}/tags/${tagId}`, { method: "DELETE" }),
  cannedResponses: () => apiRequest("/it/canned-responses"),
  resolveTicket: (id, resolutionNote, outcome = "RESOLVED") =>
    apiRequest(`/it/tickets/${id}/resolve`, {
      method: "POST",
      body: JSON.stringify({ resolution_note: resolutionNote, outcome }),
    }),

  notifications: (page = 1) => apiRequest(`/notifications?page=${page}&page_size=20`),
  markNotificationRead: (id) => apiRequest(`/notifications/${id}/read`, { method: "PATCH" }),

  reportSummary: (params) => apiRequest(`/it/reports/summary?${params}`),
  exportReport: (params) => apiRequest(`/it/reports/export.xlsx?${params}`),
  systemOverview: () => apiRequest("/it/system/overview"),
  systemLogs: (level = "", limit = 100) => {
    const params = new URLSearchParams({ limit });
    if (level) params.set("level", level);
    return apiRequest(`/it/system/logs?${params}`);
  },

  adminDashboard: () => apiRequest("/admin/dashboard"),
  adminUsers: ({ page = 1, pageSize = 20, search = "", role = "", isActive = "" } = {}) => {
    const params = new URLSearchParams({ page, page_size: pageSize });
    if (search.trim()) params.set("search", search.trim());
    if (role) params.set("role", role);
    if (isActive !== "") params.set("is_active", isActive);
    return apiRequest(`/admin/users?${params}`);
  },
  createItUser: (payload) =>
    apiRequest("/admin/users/it", { method: "POST", body: JSON.stringify(payload) }),
  updateAdminUser: (id, payload) =>
    apiRequest(`/admin/users/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  setAdminUserStatus: (id, payload) =>
    apiRequest(`/admin/users/${id}/status`, { method: "PATCH", body: JSON.stringify(payload) }),
  resetAdminUserPassword: (id, payload) =>
    apiRequest(`/admin/users/${id}/temporary-password`, { method: "POST", body: JSON.stringify(payload) }),
  deleteAdminUser: (id, payload) =>
    apiRequest(`/admin/users/${id}`, { method: "DELETE", body: JSON.stringify(payload) }),
  adminTickets: ({ page = 1, pageSize = 20, state = "active", search = "" } = {}) => {
    const params = new URLSearchParams({ page, page_size: pageSize, state });
    if (search.trim()) params.set("search", search.trim());
    return apiRequest(`/admin/tickets?${params}`);
  },
  adminTicket: (id) => apiRequest(`/admin/tickets/${id}`),
  assignAdminTicket: (id, itUserId) =>
    apiRequest(`/admin/tickets/${id}/assignee`, {
      method: "PATCH",
      body: JSON.stringify({ it_user_id: itUserId }),
    }),
  deleteAdminTicket: (id, reason) =>
    apiRequest(`/admin/tickets/${id}`, {
      method: "DELETE",
      body: JSON.stringify({ reason }),
    }),
  restoreAdminTicket: (id) =>
    apiRequest(`/admin/tickets/${id}/restore`, { method: "POST" }),
  auditEvents: (page = 1, action = "") => {
    const params = new URLSearchParams({ page, page_size: 50 });
    if (action.trim()) params.set("action", action.trim());
    return apiRequest(`/admin/audit-events?${params}`);
  },
  adminCannedResponses: () => apiRequest("/admin/canned-responses"),
  createAdminCannedResponse: (payload) =>
    apiRequest("/admin/canned-responses", { method: "POST", body: JSON.stringify(payload) }),
  updateAdminCannedResponse: (id, payload) =>
    apiRequest(`/admin/canned-responses/${id}`, { method: "PATCH", body: JSON.stringify(payload) }),
  deleteAdminCannedResponse: (id) =>
    apiRequest(`/admin/canned-responses/${id}`, { method: "DELETE" }),
};

export function saveBlob(blob, filename) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}
