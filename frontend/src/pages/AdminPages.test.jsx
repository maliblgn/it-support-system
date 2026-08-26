import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { MemoryRouter } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AdminDashboardPage, AdminTicketsPage, AdminUsersPage } from "./AdminPages";

const apiMocks = vi.hoisted(() => ({
  adminDashboard: vi.fn(),
  adminUsers: vi.fn(),
  adminTickets: vi.fn(),
  assignAdminTicket: vi.fn(),
  deleteAdminTicket: vi.fn(),
  restoreAdminTicket: vi.fn(),
  updateAdminUser: vi.fn(),
  resetAdminUserPassword: vi.fn(),
  setAdminUserStatus: vi.fn(),
  deleteAdminUser: vi.fn(),
}));

vi.mock("../api/client", () => ({ api: apiMocks }));

afterEach(() => {
  cleanup();
  vi.clearAllMocks();
});

describe("yönetim ekranları", () => {
  it("admin özetini ve yönetim kısayollarını gösterir", async () => {
    apiMocks.adminDashboard.mockResolvedValue({
      total_users: 12,
      active_users: 10,
      it_users: 3,
      open_tickets: 4,
      deleted_tickets: 2,
      unrated_resolved_tickets: 5,
    });

    render(<MemoryRouter><AdminDashboardPage /></MemoryRouter>);

    expect(await screen.findByRole("heading", { name: "Admin paneli" })).toBeInTheDocument();
    expect(screen.getByText("12")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Kullanıcıları yönet/ })).toHaveAttribute("href", "/admin/users");
    expect(screen.queryByText(/Ödül/i)).not.toBeInTheDocument();
  });

  it("kullanıcı düzenleme, parola, durum ve kalıcı silme işlemlerini doğru API'lere bağlar", async () => {
    const managedUser = {
      id: 12,
      email: "yonetilen@company.com",
      first_name: "Ayşe",
      last_name: "Yılmaz",
      phone: null,
      department: "Finans",
      role: "USER",
      is_active: true,
      must_change_password: false,
      created_at: "2026-08-24T10:00:00Z",
    };
    apiMocks.adminUsers.mockResolvedValue({ items: [managedUser], total: 1, page: 1, pages: 1 });
    apiMocks.updateAdminUser.mockResolvedValue({ ...managedUser, first_name: "Aysel" });
    apiMocks.resetAdminUserPassword.mockResolvedValue({ ...managedUser, must_change_password: true });
    apiMocks.setAdminUserStatus.mockResolvedValue({ ...managedUser, is_active: false });
    apiMocks.deleteAdminUser.mockResolvedValue(null);

    render(<AdminUsersPage />);
    expect(await screen.findByRole("heading", { name: "Kullanıcılar" })).toBeInTheDocument();

    fireEvent.click(screen.getByRole("button", { name: /Ayşe Yılmaz kullanıcısını düzenle/ }));
    const firstNameInput = screen.getByLabelText("Ad");
    expect(firstNameInput).toHaveFocus();
    fireEvent.change(firstNameInput, { target: { value: "Aysel" } });
    expect(firstNameInput).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Değişiklikleri kaydet" }));
    await waitFor(() => expect(apiMocks.updateAdminUser).toHaveBeenCalledWith(12, {
      first_name: "Aysel",
      last_name: "Yılmaz",
      phone: null,
      department: "Finans",
    }));

    fireEvent.click(screen.getByRole("button", { name: /Ayşe Yılmaz için geçici parola belirle/ }));
    const temporaryPasswordInput = screen.getByLabelText(/^Yeni geçici parola/);
    expect(temporaryPasswordInput).toHaveFocus();
    fireEvent.change(temporaryPasswordInput, { target: { value: "YeniParola123" } });
    expect(temporaryPasswordInput).toHaveFocus();
    fireEvent.change(screen.getByLabelText("İşlem nedeni"), { target: { value: "Kullanıcı istedi." } });
    fireEvent.click(screen.getByRole("button", { name: "Parolayı yenile" }));
    await waitFor(() => expect(apiMocks.resetAdminUserPassword).toHaveBeenCalledWith(12, {
      temporary_password: "YeniParola123",
      reason: "Kullanıcı istedi.",
    }));

    fireEvent.click(screen.getByRole("button", { name: /Ayşe Yılmaz hesabını pasifleştir/ }));
    const statusReasonInput = screen.getByLabelText("İşlem nedeni");
    expect(statusReasonInput).toHaveFocus();
    fireEvent.change(statusReasonInput, { target: { value: "Geçici kapatma." } });
    expect(statusReasonInput).toHaveFocus();
    fireEvent.click(screen.getByRole("button", { name: "Durumu güncelle" }));
    await waitFor(() => expect(apiMocks.setAdminUserStatus).toHaveBeenCalledWith(12, {
      is_active: false,
      reason: "Geçici kapatma.",
    }));

    fireEvent.click(screen.getByRole("button", { name: /Ayşe Yılmaz kullanıcısını kalıcı olarak sil/ }));
    const deleteButton = screen.getByRole("button", { name: "Kalıcı olarak sil" });
    const confirmationEmailInput = screen.getByLabelText(/^Onay için kullanıcının e-postası/);
    expect(deleteButton).toBeDisabled();
    expect(confirmationEmailInput).toHaveFocus();
    fireEvent.change(confirmationEmailInput, { target: { value: managedUser.email } });
    expect(confirmationEmailInput).toHaveFocus();
    fireEvent.change(screen.getByLabelText("İşlem nedeni"), { target: { value: "Hesap kapatıldı." } });
    expect(deleteButton).toBeEnabled();
    fireEvent.click(deleteButton);
    await waitFor(() => expect(apiMocks.deleteAdminUser).toHaveBeenCalledWith(12, {
      confirmation_email: managedUser.email,
      reason: "Hesap kapatıldı.",
    }));
  });

  it("admin talep havuzundan aktif IT çalışanına manuel atama yapar", async () => {
    const itUser = {
      id: 21,
      email: "deniz.it@company.com",
      first_name: "Deniz",
      last_name: "Teknik",
      department: "Bilgi İşlem",
      role: "IT",
      is_active: true,
    };
    const ticket = {
      id: 44,
      ticket_number: "IT-000044",
      subject: "Yazıcı bağlantı sorunu",
      department_snapshot: "Finans",
      assigned_to: null,
      assignee: null,
      is_resolved: false,
      deleted_at: null,
      deletion_reason: null,
      created_at: "2026-08-24T10:00:00Z",
      user: { first_name: "Ayşe", last_name: "Yılmaz" },
    };
    apiMocks.adminUsers.mockResolvedValue({ items: [itUser], total: 1, page: 1, pages: 1 });
    apiMocks.adminTickets.mockResolvedValue({ items: [ticket], total: 1, page: 1, pages: 1 });
    apiMocks.assignAdminTicket.mockResolvedValue({ ...ticket, assigned_to: itUser.id, assignee: itUser });

    render(<MemoryRouter><AdminTicketsPage /></MemoryRouter>);

    expect(await screen.findByRole("heading", { name: "Talep havuzu ve yönetimi" })).toBeInTheDocument();
    expect(screen.getByText("IT çalışanı kendi üzerine alabilir")).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: "IT ata" }));
    const assigneeSelect = screen.getByLabelText("Atanacak IT çalışanı");
    expect(assigneeSelect).toHaveFocus();
    fireEvent.change(assigneeSelect, { target: { value: String(itUser.id) } });
    fireEvent.click(screen.getByRole("button", { name: "Talebi ata" }));

    await waitFor(() => expect(apiMocks.assignAdminTicket).toHaveBeenCalledWith(ticket.id, itUser.id));
    expect(await screen.findByText(/Deniz Teknik adlı IT çalışanına atandı/)).toBeInTheDocument();
  });
});
