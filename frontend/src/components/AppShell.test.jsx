import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, describe, expect, it, vi } from "vitest";

import AppShell from "./AppShell";

const authMocks = vi.hoisted(() => ({
  logout: vi.fn(),
  user: {
    role: "IT",
    department: "Bilgi İşlem",
    first_name: "Deniz",
    last_name: "Teknik",
    email: "it.demo@company.com",
  },
}));

afterEach(() => {
  cleanup();
  authMocks.user.role = "IT";
});

vi.mock("../auth/AuthContext", () => ({
  useAuth: () => ({
    user: authMocks.user,
    logout: authMocks.logout,
  }),
}));

function renderShell() {
  render(
    <MemoryRouter initialEntries={["/it/dashboard"]}>
      <Routes>
        <Route element={<AppShell />}>
          <Route path="/it/dashboard" element={<div>IT dashboard</div>} />
          <Route path="/it/tickets" element={<div>Ticket havuzu</div>} />
        </Route>
      </Routes>
    </MemoryRouter>,
  );
}

describe("responsive uygulama kabuğu", () => {
  it("mobil menüyü açar ve perde düğmesiyle kapatır", () => {
    renderShell();
    const sidebar = document.querySelector(".sidebar");
    expect(sidebar).not.toHaveClass("sidebar--open");

    fireEvent.click(screen.getByRole("button", { name: "Menüyü aç" }));
    expect(sidebar).toHaveClass("sidebar--open");

    fireEvent.click(screen.getAllByRole("button", { name: "Menüyü kapat" })[0]);
    expect(sidebar).not.toHaveClass("sidebar--open");
  });

  it("mobil menüden sayfa seçildiğinde menüyü kapatır", () => {
    renderShell();
    const sidebar = document.querySelector(".sidebar");
    fireEvent.click(screen.getByRole("button", { name: "Menüyü aç" }));
    fireEvent.click(screen.getByRole("link", { name: /Talep Havuzu/ }));

    expect(sidebar).not.toHaveClass("sidebar--open");
    expect(screen.getByText("Ticket havuzu")).toBeInTheDocument();
  });

  it("şifre değişikliğini ve kaldırılan modülü sol menüde göstermez", () => {
    renderShell();

    expect(screen.queryByRole("link", { name: /Şifremi değiştir/i })).not.toBeInTheDocument();
    expect(screen.queryByText(/Ödül/i)).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Profilim/i })).toHaveAttribute("href", "/profile");
  });

  it("çalışan app barında yeni talep butonunu kaldırır, sol menü bağlantısını korur", () => {
    authMocks.user.role = "USER";
    renderShell();

    expect(document.querySelector(".topbar__primary-action")).not.toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Yeni Talep" })).toHaveAttribute(
      "href",
      "/tickets/new",
    );
  });
});
