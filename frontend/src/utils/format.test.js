import { describe, expect, it } from "vitest";

import { formatDate, formatDuration, formatFileSize, initials, priorityLabels } from "./format";

describe("format yardımcıları", () => {
  it("tarihleri İstanbul saat diliminde gösterir", () => {
    expect(formatDate("2026-08-21T12:30:00Z")).toContain("15:30");
    expect(formatDate("geçersiz")).toBe("—");
  });

  it("dosya boyutu ve süre eşiklerini okunabilir biçime çevirir", () => {
    expect(formatFileSize(512)).toBe("512 B");
    expect(formatFileSize(1536)).toBe("1.5 KB");
    expect(formatFileSize(2 * 1024 * 1024)).toBe("2.0 MB");
    expect(formatFileSize(3 * 1024 ** 3)).toBe("3.0 GB");
    expect(formatDuration(45)).toBe("45 dk");
    expect(formatDuration(90)).toBe("1.5 sa");
    expect(formatDuration(2880)).toBe("2.0 gün");
  });

  it("Türkçe baş harf ve öncelik etiketlerini üretir", () => {
    expect(initials({ first_name: "ışıl", last_name: "öztürk" })).toBe("IÖ");
    expect(priorityLabels.CRITICAL).toBe("Kritik");
  });
});
