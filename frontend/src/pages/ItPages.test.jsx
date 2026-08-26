import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { ItTicketDetailPage } from "./ItPages";

const apiMocks = vi.hoisted(() => ({
  ticket: vi.fn(),
  ticketHistory: vi.fn(),
  ticketTags: vi.fn(),
  cannedResponses: vi.fn(),
  resolveTicket: vi.fn(),
}));

vi.mock("../api/client", () => ({
  api: apiMocks,
  saveBlob: vi.fn(),
}));

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({ user: { id: 21, role: "IT" } }),
}));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("IT talep sonuçlandırma", () => {
  it("atanmış talebi çözülemedi sonucu ve açıklamasıyla kapatır", async () => {
    const openTicket = {
      id: 17,
      ticket_number: "IT-000017",
      subject: "Arızalı cihaz",
      description: "Cihaz açılmıyor.",
      department_snapshot: "Finans",
      priority: "HIGH",
      assigned_to: 21,
      is_resolved: false,
      resolution_outcome: null,
      attachments: [],
      tags: [],
      watchers: [],
      assignee: null,
      created_at: "2026-08-25T08:00:00Z",
      updated_at: "2026-08-25T08:00:00Z",
      user: {
        first_name: "Ayşe",
        last_name: "Yılmaz",
        email: "ayse@company.com",
        phone: null,
      },
    };
    apiMocks.ticket.mockResolvedValue(openTicket);
    apiMocks.ticketHistory.mockResolvedValue([]);
    apiMocks.ticketTags.mockResolvedValue([]);
    apiMocks.cannedResponses.mockResolvedValue([]);
    apiMocks.resolveTicket.mockResolvedValue({
      ...openTicket,
      is_resolved: true,
      resolution_outcome: "UNRESOLVED",
    });

    render(
      <MemoryRouter initialEntries={["/it/tickets/17"]}>
        <Routes>
          <Route path="/it/tickets/:id" element={<ItTicketDetailPage />} />
        </Routes>
      </MemoryRouter>,
    );

    const explanation = await screen.findByRole("textbox", { name: "Sonuç açıklaması" });
    fireEvent.change(explanation, {
      target: { value: "Yedek parça bulunamadığı için işlem tamamlanamadı." },
    });
    fireEvent.click(screen.getByRole("button", { name: "Çözülemedi" }));
    fireEvent.click(screen.getByRole("button", { name: "Evet, çözülemedi" }));

    await waitFor(() => expect(apiMocks.resolveTicket).toHaveBeenCalledWith(
      "17",
      "Yedek parça bulunamadığı için işlem tamamlanamadı.",
      "UNRESOLVED",
    ));
  });
});
