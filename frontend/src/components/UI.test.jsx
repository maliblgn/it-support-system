import { fireEvent, render, screen } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { ConfirmDialog, Pagination, PriorityBadge, StatusBadge } from "./UI";

describe("ortak arayüz bileşenleri", () => {
  it("ticket durum ve önceliğini Türkçe gösterir", () => {
    render(<><StatusBadge resolved /><StatusBadge resolved outcome="UNRESOLVED" /><PriorityBadge priority="HIGH" /></>);
    expect(screen.getByText("Çözüldü")).toBeInTheDocument();
    expect(screen.getByText("Çözülemedi")).toBeInTheDocument();
    expect(screen.getByText("Yüksek")).toBeInTheDocument();
  });

  it("sayfalama sınırlarını ve ileri geçişi uygular", () => {
    const onPageChange = vi.fn();
    render(<Pagination page={1} pages={3} onPageChange={onPageChange} />);
    expect(screen.getByRole("button", { name: "Önceki" })).toBeDisabled();
    fireEvent.click(screen.getByRole("button", { name: "Sonraki" }));
    expect(onPageChange).toHaveBeenCalledWith(2);
  });

  it("onay penceresini Escape ile kapatır", () => {
    const onClose = vi.fn();
    render(<ConfirmDialog open title="Talep çözülsün mü?" description="Bu işlem geri alınamaz." onClose={onClose} onConfirm={vi.fn()} />);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(onClose).toHaveBeenCalledTimes(1);
  });
});
