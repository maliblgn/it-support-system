function readBoolean(value, fallback) {
  if (value == null || value === "") return fallback;
  return !["0", "false", "no", "off"].includes(String(value).trim().toLowerCase());
}

export const APP_NAME = String(import.meta.env.VITE_APP_NAME || "Destek Takip").trim();
export const PUBLIC_REGISTRATION_ENABLED = readBoolean(
  import.meta.env.VITE_PUBLIC_REGISTRATION_ENABLED,
  true,
);
