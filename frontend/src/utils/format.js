export const priorityLabels = {
  LOW: "Düşük",
  NORMAL: "Normal",
  HIGH: "Yüksek",
  CRITICAL: "Kritik",
};

export function formatDate(value, options = {}) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  return new Intl.DateTimeFormat("tr-TR", {
    timeZone: "Europe/Istanbul",
    dateStyle: options.dateOnly ? "medium" : "medium",
    ...(options.dateOnly ? {} : { timeStyle: "short" }),
  }).format(date);
}

export function formatFileSize(bytes) {
  if (!Number.isFinite(bytes)) return "—";
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  if (bytes < 1024 * 1024 * 1024) return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
  if (bytes < 1024 ** 4) return `${(bytes / (1024 ** 3)).toFixed(1)} GB`;
  return `${(bytes / (1024 ** 4)).toFixed(1)} TB`;
}

export function formatDuration(minutes) {
  if (minutes === null || minutes === undefined) return "—";
  if (minutes < 60) return `${Math.round(minutes)} dk`;
  if (minutes < 1440) return `${(minutes / 60).toFixed(1)} sa`;
  return `${(minutes / 1440).toFixed(1)} gün`;
}

export function formatRelativeDate(value, now = new Date()) {
  if (!value) return "—";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";
  const seconds = Math.round((date.getTime() - now.getTime()) / 1000);
  const absolute = Math.abs(seconds);
  const formatter = new Intl.RelativeTimeFormat("tr-TR", { numeric: "auto" });
  if (absolute < 60) return formatter.format(seconds, "second");
  if (absolute < 3600) return formatter.format(Math.round(seconds / 60), "minute");
  if (absolute < 86400) return formatter.format(Math.round(seconds / 3600), "hour");
  if (absolute < 604800) return formatter.format(Math.round(seconds / 86400), "day");
  return formatDate(value);
}

export function initials(user) {
  return `${user?.first_name?.[0] || ""}${user?.last_name?.[0] || ""}`.toLocaleUpperCase("tr-TR");
}
